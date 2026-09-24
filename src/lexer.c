#include "cshell/lexer.h"

#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* All command frames share one source tape. Alias values are inserted at the
 * cursor, with a stack restoring the physical input position on return. Each
 * pending word captures its own raw spelling so an alias inside $(...) does
 * not rewrite the outer word's physical spelling. */
struct alias_source {
    char *name, *source_name, *invocation_source;
    struct csh_position invocation, resume;
    size_t end, owner_depth;
    int trailing_blank;
};
struct source {
    char *name;
    unsigned char *data;
    size_t length, capacity, cursor;
    struct csh_position position;
    struct alias_source *aliases;
    size_t alias_count, alias_capacity, sequence;
    int alias_eligible;
    /* At most three logical characters are needed. Cache skipped continuation
     * runs across feeds so a split opener cannot cause quadratic rescanning. */
    size_t look_offset, look_count, look_scan, look_positions[3];
    int look_valid;
    int final;
    struct csh_error failure;
};

enum frame_kind { SINGLE, DOUBLE, DOLLAR_SINGLE, PARAMETER, SIMPLE,
                  ARITHMETIC, BACKQUOTE, COMMAND };
struct frame {
    enum frame_kind kind;
    enum csh_quote quote;
    size_t fragment, parentheses;
    int parameter_stage;
};
struct csh_lexer {
    struct source *source;
    struct csh_lexer *root, *parent, *child;
    struct csh_position start, spelling_position;
    unsigned char *raw;
    size_t raw_length, raw_capacity, depth;
    char *token_name, *alias_name, *invocation_source;
    struct csh_position invocation;
    int alias_eligible;
    struct csh_fragment *fragments;
    size_t fragment_count, fragment_capacity;
    struct frame *frames;
    size_t frame_count, frame_capacity;
    int active, comment, command;
    enum csh_token_kind kind;
    char operator_text[4];
    size_t operator_length;
    enum csh_token_kind last_kind;
    struct csh_position last_start, last_end;
    int has_last;
    size_t last_sequence;
};

struct operator { const char *text; enum csh_token_kind kind; };
static const struct operator operators[] = {
    {"&&", CSH_TOKEN_AND_IF}, {"||", CSH_TOKEN_OR_IF},
    {";;", CSH_TOKEN_DSEMI}, {";&", CSH_TOKEN_SEMI_AND},
    {"<<-", CSH_TOKEN_DLESS_DASH}, {"<<", CSH_TOKEN_DLESS},
    {">>", CSH_TOKEN_DGREAT}, {"<&", CSH_TOKEN_LESS_AND},
    {">&", CSH_TOKEN_GREAT_AND}, {"<>", CSH_TOKEN_LESS_GREAT},
    {">|", CSH_TOKEN_CLOBBER}, {"|", CSH_TOKEN_PIPE},
    {"&", CSH_TOKEN_AMPERSAND}, {";", CSH_TOKEN_SEMI},
    {"(", CSH_TOKEN_LPAREN}, {")", CSH_TOKEN_RPAREN},
    {"<", CSH_TOKEN_LESS}, {">", CSH_TOKEN_GREAT}
};

static void clear_error(struct csh_error *error)
{
    memset(error, 0, sizeof(*error));
}

static int plain_error(struct csh_error *error, const char *message, int number)
{
    clear_error(error);
    error->message = message;
    error->system_errno = number;
    error->status = number == ENOMEM || number == EOVERFLOW ? 1 : 2;
    error->position.line = error->position.column = 1;
    return -1;
}

static void release_alias(struct alias_source *alias)
{
    free(alias->name);
    free(alias->source_name);
    free(alias->invocation_source);
    memset(alias, 0, sizeof(*alias));
}

static void release_aliases(struct source *source)
{
    while (source->alias_count != 0)
        release_alias(&source->aliases[--source->alias_count]);
    free(source->aliases);
    source->aliases = NULL;
    source->alias_capacity = 0;
}

static void release_work(struct csh_lexer *lexer)
{
    free(lexer->raw);
    free(lexer->token_name);
    free(lexer->alias_name);
    free(lexer->invocation_source);
    lexer->raw = NULL;
    lexer->raw_length = lexer->raw_capacity = 0;
    lexer->token_name = lexer->alias_name = lexer->invocation_source = NULL;
    free(lexer->fragments);
    free(lexer->frames);
    lexer->fragments = NULL;
    lexer->frames = NULL;
    lexer->fragment_count = lexer->fragment_capacity = 0;
    lexer->frame_count = lexer->frame_capacity = 0;
    lexer->active = lexer->command = lexer->comment = 0;
}

struct csh_position csh_lexer_diagnostic_position(const struct csh_lexer *lexer,
    struct csh_position position)
{
    const struct source *source = lexer->source;
    if (source->alias_count != 0)
        return source->aliases[source->alias_count - 1].invocation;
    if (lexer->invocation_source != NULL)
        return lexer->invocation;
    return position;
}

static int fail_at(struct csh_lexer *lexer, struct csh_error *error,
    const char *message, int number, struct csh_position position)
{
    struct source *source = lexer->source;
    struct csh_lexer *cursor;
    if (source->failure.message == NULL) {
        plain_error(&source->failure, message, number);
        /* Public parser diagnostics name the physical input; generated token
         * positions remain available separately with alias provenance. */
        source->failure.position = csh_lexer_diagnostic_position(lexer, position);
        for (cursor = lexer->root; cursor != NULL; cursor = cursor->child)
            release_work(cursor);
        release_aliases(source);
        free(source->data);
        source->data = NULL;
        source->length = source->capacity = source->cursor = 0;
    }
    *error = source->failure;
    return -1;
}

static int fail(struct csh_lexer *lexer, struct csh_error *error,
    const char *message, int number)
{
    return fail_at(lexer, error, message, number, lexer->source->position);
}

static int reserve(void **pointer, size_t *capacity, size_t count, size_t size)
{
    size_t grown = *capacity == 0 ? 16 : *capacity;
    void *result;
    if (count <= *capacity)
        return 0;
    if (count > SIZE_MAX / size) {
        errno = EOVERFLOW;
        return -1;
    }
    while (grown < count) {
        if (grown > SIZE_MAX / 2) {
            grown = count;
            break;
        }
        grown *= 2;
    }
    if (grown > SIZE_MAX / size)
        grown = count;
    result = realloc(*pointer, grown * size);
    if (result == NULL)
        return -1;
    *pointer = result;
    *capacity = grown;
    return 0;
}

int csh_lexer_create(struct csh_lexer **out, const char *source_name,
    struct csh_error *error)
{
    struct csh_lexer *lexer;
    struct source *source;
    *out = NULL;
    clear_error(error);
    if (source_name == NULL)
        return plain_error(error, "invalid lexer source name", EINVAL);
    lexer = malloc(sizeof(*lexer));
    if (lexer == NULL)
        return plain_error(error, "cannot allocate lexer", ENOMEM);
    memset(lexer, 0, sizeof(*lexer));
    source = malloc(sizeof(*source));
    if (source == NULL) {
        free(lexer);
        return plain_error(error, "cannot allocate lexer source", ENOMEM);
    }
    memset(source, 0, sizeof(*source));
    source->name = malloc(strlen(source_name) + 1);
    if (source->name == NULL) {
        free(source);
        free(lexer);
        return plain_error(error, "cannot allocate lexer source name", ENOMEM);
    }
    strcpy(source->name, source_name);
    source->position.line = source->position.column = 1;
    lexer->root = lexer;
    lexer->source = source;
    *out = lexer;
    return 0;
}

void csh_lexer_destroy(struct csh_lexer *lexer)
{
    struct source *source;
    int owns_source;
    if (lexer == NULL)
        return;
    source = lexer->source;
    owns_source = lexer->parent == NULL;
    if (lexer->parent != NULL)
        lexer->parent->child = NULL;
    while (lexer != NULL) {
        struct csh_lexer *child = lexer->child;
        release_work(lexer);
        free(lexer);
        lexer = child;
    }
    if (owns_source) {
        release_aliases(source);
        free(source->name);
        free(source->data);
        free(source);
    }
}

int csh_lexer_feed(struct csh_lexer *lexer, const void *bytes, size_t length,
    int final, struct csh_error *error)
{
    struct source *source = lexer->source;
    clear_error(error);
    if (source->failure.message != NULL) {
        *error = source->failure;
        return -1;
    }
    if (source->final || (length != 0 && bytes == NULL))
        return fail(lexer, error, "invalid lexer feed", EINVAL);
    /* Words capture raw bytes independently of the shared input tape. */
    if (source->cursor != 0) {
        size_t index;
        for (index = 0; index < source->alias_count; ++index)
            source->aliases[index].end -= source->cursor;
        memmove(source->data, source->data + source->cursor,
                source->length - source->cursor);
        source->length -= source->cursor;
        source->cursor = 0;
    }
    if (length > SIZE_MAX - source->length)
        return fail(lexer, error, "lexer source is too large", EOVERFLOW);
    if (reserve((void **)&source->data, &source->capacity,
                source->length + length, 1) == -1)
        return fail(lexer, error, "cannot grow lexer source", errno);
    if (length != 0)
        memcpy(source->data + source->length, bytes, length);
    source->length += length;
    source->final = final != 0;
    return 0;
}

void csh_token_destroy(struct csh_token *token)
{
    if (token == NULL)
        return;
    free(token->alias_name);
    free(token->invocation_source);
    free(token->source_name);
    free(token->raw);
    free(token->fragments);
    memset(token, 0, sizeof(*token));
}

static int consume(struct csh_lexer *lexer, size_t count, struct csh_error *error)
{
    struct source *source = lexer->source;
    size_t index;
    source->look_valid = 0;
    for (index = 0; index < count; ++index) {
        struct csh_lexer *capture;
        unsigned char byte = source->data[source->cursor];
        if (byte == 0)
            return fail(lexer, error, "NUL byte in shell input", 0);
        if (source->sequence == SIZE_MAX || source->position.offset == SIZE_MAX ||
            (byte == '\n' ? source->position.line : source->position.column) == SIZE_MAX)
            return fail(lexer, error, "lexer position overflow", EOVERFLOW);
        for (capture = lexer->root; capture != NULL; capture = capture->child) {
            if (!capture->active || (capture != lexer &&
                source->alias_count != 0 &&
                source->aliases[source->alias_count - 1].owner_depth > capture->depth))
                continue;
            if (capture->raw_length == SIZE_MAX - 1)
                return fail(lexer, error, "token spelling is too large", EOVERFLOW);
            if (capture->spelling_position.offset == SIZE_MAX ||
                (byte == '\n' ? capture->spelling_position.line :
                    capture->spelling_position.column) == SIZE_MAX)
                return fail(lexer, error, "token position overflow", EOVERFLOW);
            if (reserve((void **)&capture->raw, &capture->raw_capacity,
                    capture->raw_length + 2, 1) == -1)
                return fail(lexer, error, "cannot grow token spelling", errno);
            capture->raw[capture->raw_length++] = byte;
            ++capture->spelling_position.offset;
            if (byte == '\n') {
                ++capture->spelling_position.line;
                capture->spelling_position.column = 1;
            } else {
                ++capture->spelling_position.column;
            }
        }
        ++source->sequence;
        ++source->position.offset;
        if (byte == '\n') {
            ++source->position.line;
            source->position.column = 1;
        } else {
            ++source->position.column;
        }
        ++source->cursor;
        while (source->alias_count != 0 &&
            source->cursor == source->aliases[source->alias_count - 1].end) {
            struct alias_source *alias = &source->aliases[source->alias_count - 1];
            source->position = alias->resume;
            source->alias_eligible |= alias->trailing_blank;
            release_alias(alias);
            --source->alias_count;
        }
    }
    return 0;
}

static char *copy_string(const char *value)
{
    char *copy = malloc(strlen(value) + 1);
    if (copy != NULL)
        strcpy(copy, value);
    return copy;
}

static int start_token(struct csh_lexer *lexer, struct csh_error *error)
{
    struct source *source = lexer->source;
    const struct alias_source *alias = source->alias_count == 0 ? NULL :
        &source->aliases[source->alias_count - 1];
    lexer->token_name = copy_string(alias == NULL ? source->name : alias->source_name);
    if (alias != NULL) {
        lexer->alias_name = copy_string(alias->name);
        lexer->invocation_source = copy_string(alias->invocation_source);
        lexer->invocation = alias->invocation;
    }
    if (lexer->token_name == NULL || (alias != NULL &&
        (lexer->alias_name == NULL || lexer->invocation_source == NULL)))
        return fail(lexer, error, "cannot allocate token source", ENOMEM);
    lexer->active = 1;
    lexer->start = lexer->spelling_position = source->position;
    lexer->alias_eligible = source->alias_eligible;
    source->alias_eligible = 0;
    return 0;
}

static size_t parent_fragment(const struct csh_lexer *lexer)
{
    return lexer->frame_count == 0 ? CSH_FRAGMENT_ROOT :
        lexer->frames[lexer->frame_count - 1].fragment;
}

static int add_fragment(struct csh_lexer *lexer, enum csh_fragment_kind kind,
    enum csh_quote quote, size_t *index, struct csh_error *error)
{
    struct csh_fragment *fragment;
    if (lexer->fragment_count == SIZE_MAX ||
        reserve((void **)&lexer->fragments, &lexer->fragment_capacity,
                lexer->fragment_count + 1, sizeof(*fragment)) == -1)
        return fail(lexer, error, "cannot grow word fragments", errno);
    *index = lexer->fragment_count++;
    fragment = &lexer->fragments[*index];
    fragment->kind = kind;
    fragment->quote = quote;
    fragment->parent = parent_fragment(lexer);
    fragment->begin = lexer->raw_length;
    fragment->end = fragment->begin;
    fragment->start = fragment->finish = lexer->spelling_position;
    return 0;
}

static void finish_fragment(struct csh_lexer *lexer, size_t index)
{
    lexer->fragments[index].end = lexer->raw_length;
    lexer->fragments[index].finish = lexer->spelling_position;
}

static int piece(struct csh_lexer *lexer, enum csh_fragment_kind kind,
    enum csh_quote quote, size_t count, struct csh_error *error)
{
    size_t index;
    if (kind == CSH_FRAGMENT_TEXT && lexer->fragment_count != 0) {
        struct csh_fragment *last = &lexer->fragments[lexer->fragment_count - 1];
        if (last->kind == kind && last->quote == quote &&
            last->parent == parent_fragment(lexer) &&
            last->end == lexer->raw_length) {
            index = lexer->fragment_count - 1;
            if (consume(lexer, count, error) == -1)
                return -1;
            finish_fragment(lexer, index);
            return 0;
        }
    }
    if (add_fragment(lexer, kind, quote, &index, error) == -1 ||
        consume(lexer, count, error) == -1)
        return -1;
    finish_fragment(lexer, index);
    return 0;
}

/* Look ahead in logical characters, retaining physical bytes for provenance.
 * Return -2 when another feed can change the answer, -1 at final EOF. */
static int peek(struct csh_lexer *lexer, size_t wanted,
    size_t *physical)
{
    struct source *source = lexer->source;
    size_t available = source->length - source->cursor;
    if (!source->look_valid || source->look_offset != source->position.offset) {
        source->look_valid = 1;
        source->look_offset = source->position.offset;
        source->look_count = source->look_scan = 0;
    }
    while (source->look_count <= wanted) {
        size_t cursor = source->look_scan;
        if (cursor == available)
            return source->final ? -1 : -2;
        if (source->data[source->cursor + cursor] == '\\') {
            if (cursor + 1 == available && !source->final)
                return -2;
            if (cursor + 1 < available &&
                source->data[source->cursor + cursor + 1] == '\n') {
                source->look_scan += 2;
                continue;
            }
        }
        source->look_positions[source->look_count++] = cursor;
        source->look_scan = cursor + 1;
    }
    *physical = source->look_positions[wanted] + 1;
    return source->data[source->cursor + source->look_positions[wanted]];
}

/* Consume a known physical span of delimiters, exposing any continuations. */
static int delimiter(struct csh_lexer *lexer, size_t count,
    enum csh_quote quote, struct csh_error *error)
{
    while (count != 0) {
        struct source *source = lexer->source;
        if (count >= 2 && source->data[source->cursor] == '\\' &&
            source->data[source->cursor + 1] == '\n') {
            if (piece(lexer, CSH_FRAGMENT_CONTINUATION, quote, 2, error) == -1)
                return -1;
            count -= 2;
        } else {
            if (consume(lexer, 1, error) == -1)
                return -1;
            --count;
        }
    }
    return 0;
}

static int push(struct csh_lexer *lexer, enum frame_kind kind,
    enum csh_fragment_kind fragment_kind, enum csh_quote quote,
    size_t count, struct csh_error *error)
{
    struct frame *frame;
    size_t index;
    if (add_fragment(lexer, fragment_kind, quote, &index, error) == -1)
        return -1;
    if (lexer->frame_count == SIZE_MAX ||
        reserve((void **)&lexer->frames, &lexer->frame_capacity,
                lexer->frame_count + 1, sizeof(*frame)) == -1)
        return fail(lexer, error, "cannot grow lexical contexts", errno);
    frame = &lexer->frames[lexer->frame_count++];
    memset(frame, 0, sizeof(*frame));
    frame->kind = kind;
    frame->quote = quote;
    frame->fragment = index;
    return delimiter(lexer, count, quote, error);
}

static int pop(struct csh_lexer *lexer, size_t count, struct csh_error *error)
{
    size_t index = lexer->frames[lexer->frame_count - 1].fragment;
    if (delimiter(lexer, count, lexer->frames[lexer->frame_count - 1].quote, error) == -1)
        return -1;
    finish_fragment(lexer, index);
    --lexer->frame_count;
    return 0;
}

static const char *frame_name(enum frame_kind kind)
{
    switch (kind) {
    case SINGLE: return "single quote";
    case DOUBLE: return "double quote";
    case DOLLAR_SINGLE: return "dollar-single quote";
    case PARAMETER: return "parameter expansion";
    case SIMPLE: return "parameter name";
    case ARITHMETIC: return "arithmetic expansion";
    case BACKQUOTE: return "backquote substitution";
    case COMMAND: return "command substitution";
    }
    return "word";
}

static const char *unterminated_context(enum frame_kind kind)
{
    switch (kind) {
    case SINGLE: return "unterminated single quote";
    case DOUBLE: return "unterminated double quote";
    case DOLLAR_SINGLE: return "unterminated dollar-single quote";
    case PARAMETER: return "unterminated parameter expansion";
    case ARITHMETIC: return "unterminated arithmetic expansion";
    case BACKQUOTE: return "unterminated backquote substitution";
    case COMMAND: return "unterminated command substitution";
    case SIMPLE: return "unterminated parameter name";
    }
    return "unterminated word";
}

int csh_lexer_context(const struct csh_lexer *lexer, const char **context,
    struct csh_position *opening)
{
    const struct source *source = lexer->source;
    if (source->cursor < source->length &&
        source->data[source->cursor] == '\\' &&
        source->length - source->cursor == 1) {
        *context = "escape";
        *opening = lexer->active ? lexer->spelling_position : source->position;
        return 1;
    }
    if (lexer->frame_count != 0) {
        const struct frame *frame = &lexer->frames[lexer->frame_count - 1];
        *context = frame_name(frame->kind);
        *opening = lexer->fragments[frame->fragment].start;
        return 1;
    }
    *context = lexer->active ? "word" : NULL;
    *opening = lexer->active ? lexer->start : lexer->source->position;
    return lexer->active;
}

static int publish(struct csh_lexer *lexer, struct csh_token *token,
    struct csh_error *error)
{
    struct source *source = lexer->source;
    (void)error;
    lexer->raw[lexer->raw_length] = 0;
    token->kind = lexer->kind;
    token->raw = lexer->raw;
    token->length = lexer->raw_length;
    token->source_name = lexer->token_name;
    token->alias_name = lexer->alias_name;
    token->invocation_source = lexer->invocation_source;
    token->invocation = lexer->invocation;
    token->alias_eligible = lexer->alias_eligible;
    token->start = lexer->start;
    token->end = lexer->spelling_position;
    token->fragments = lexer->fragments;
    token->fragment_count = lexer->fragment_count;
    lexer->raw = NULL;
    lexer->raw_length = lexer->raw_capacity = 0;
    lexer->token_name = lexer->alias_name = lexer->invocation_source = NULL;
    memset(&lexer->invocation, 0, sizeof(lexer->invocation));
    lexer->fragments = NULL;
    lexer->fragment_count = lexer->fragment_capacity = 0;
    lexer->active = 0;
    lexer->operator_length = 0;
    lexer->last_kind = token->kind;
    lexer->last_start = token->start;
    lexer->last_end = token->end;
    lexer->last_sequence = source->sequence;
    lexer->has_last = 1;
    return CSH_LEX_TOKEN;
}

static int name_start(int byte)
{
    return (byte >= 'a' && byte <= 'z') || (byte >= 'A' && byte <= 'Z') || byte == '_';
}
static int digit(int byte) { return byte >= '0' && byte <= '9'; }
static int name_char(int byte) { return name_start(byte) || digit(byte); }
static int operator_char(int byte)
{
    return byte > 0 && strchr("|&;()<>", byte) != NULL;
}

/* Only four pattern-removal operators reset an enclosing double-quote context.
 * Keep the result's quote on the PARAMETER fragment; children use the reset. */
static void parameter_context(struct frame *frame, int byte)
{
    if (frame->parameter_stage == 0) {
        /* A leading # can also be the special parameter itself. A following
         * name (length expansion) keeps inherited quoting; a following pattern
         * operator resets it. Parameter grammar/value validation is separate. */
        if (byte == '#') { frame->parameter_stage = 4; return; }
        frame->parameter_stage = 1;
    }
    if (frame->parameter_stage == 1) {
        frame->parameter_stage = name_start(byte) ? 2 : digit(byte) ? 3 : 4;
        return;
    }
    if ((frame->parameter_stage == 2 && name_char(byte)) ||
        (frame->parameter_stage == 3 && digit(byte)))
        return;
    if (frame->parameter_stage != 5) {
        if (byte == '#' || byte == '%')
            frame->quote = CSH_QUOTE_NONE;
        frame->parameter_stage = 5;
    }
}

static int operator_step(struct csh_lexer *lexer, struct csh_token *token,
    struct csh_error *error)
{
    size_t index, physical = 0;
    int byte, extendible = 0, matched = 0;
    char candidate[4];
    for (index = 0; index < sizeof(operators) / sizeof(operators[0]); ++index) {
        if (strncmp(operators[index].text, lexer->operator_text,
                    lexer->operator_length) == 0 &&
            strlen(operators[index].text) > lexer->operator_length)
            extendible = 1;
    }
    if (!extendible)
        return publish(lexer, token, error);
    byte = peek(lexer, 0, &physical);
    if (byte == -2)
        return CSH_LEX_MORE;
    if (byte < 0)
        return publish(lexer, token, error);
    memcpy(candidate, lexer->operator_text, lexer->operator_length);
    candidate[lexer->operator_length] = (char)byte;
    candidate[lexer->operator_length + 1] = 0;
    for (index = 0; index < sizeof(operators) / sizeof(operators[0]); ++index) {
        if (strcmp(candidate, operators[index].text) == 0) {
            lexer->kind = operators[index].kind;
            matched = 1;
            break;
        }
    }
    if (!matched)
        return publish(lexer, token, error);
    if (delimiter(lexer, physical, CSH_QUOTE_NONE, error) == -1)
        return CSH_LEX_ERROR;
    strcpy(lexer->operator_text, candidate);
    ++lexer->operator_length;
    return operator_step(lexer, token, error); /* At most three operator bytes. */
}

static int eof(struct csh_lexer *lexer, struct csh_token *token,
    struct csh_error *error)
{
    if (lexer->frame_count != 0) {
        struct frame *frame = &lexer->frames[lexer->frame_count - 1];
        if (frame->kind == SIMPLE) {
            if (pop(lexer, 0, error) == -1)
                return CSH_LEX_ERROR;
            return eof(lexer, token, error);
        }
        return fail_at(lexer, error, unterminated_context(frame->kind), 0,
                        lexer->fragments[frame->fragment].start);
    }
    if (lexer->active)
        return publish(lexer, token, error);
    if (lexer->parent != NULL) {
        struct csh_lexer *parent = lexer->parent;
        /* The opening belongs to the suspended parent word. Its alias source
         * may be exhausted even though the child is still awaiting ')'. */
        return fail_at(parent, error, "unterminated command substitution", 0,
            parent->fragments[parent->frames[parent->frame_count - 1].fragment].start);
    }
    return CSH_LEX_EOF;
}

/* Handle a dollar at the current cursor. 0 means ordinary text, 1 consumed,
 * 2 needs more input, 3 needs the parser, -1 failed. */
static int dollar(struct csh_lexer *lexer, enum csh_quote quote,
    struct csh_error *error)
{
    size_t physical = 0, third_physical = 0;
    int next = peek(lexer, 1, &physical);
    if (next == -2)
        return 2;
    if (next == '{')
        return push(lexer, PARAMETER, CSH_FRAGMENT_PARAMETER, quote, physical, error) == -1 ? -1 : 1;
    if (next == '(') {
        int third = peek(lexer, 2, &third_physical);
        if (third == -2)
            return 2;
        if (third == '(')
            return push(lexer, ARITHMETIC, CSH_FRAGMENT_ARITHMETIC, quote,
                        third_physical, error) == -1 ? -1 : 1;
        if (push(lexer, COMMAND, CSH_FRAGMENT_COMMAND, quote, physical, error) == -1)
            return -1;
        lexer->command = 1;
        return 3;
    }
    if (next == '\'' && quote == CSH_QUOTE_NONE)
        return push(lexer, DOLLAR_SINGLE, CSH_FRAGMENT_QUOTED,
                    CSH_QUOTE_DOLLAR_SINGLE, physical, error) == -1 ? -1 : 1;
    if (name_start(next))
        return push(lexer, SIMPLE, CSH_FRAGMENT_PARAMETER, quote, physical, error) == -1 ? -1 : 1;
    if (digit(next) || (next > 0 && strchr("@*#?-$!", next) != NULL)) {
        if (push(lexer, SIMPLE, CSH_FRAGMENT_PARAMETER, quote, physical, error) == -1 ||
            pop(lexer, 0, error) == -1)
            return -1;
        return 1;
    }
    return 0;
}

enum csh_lex_result csh_lexer_next(struct csh_lexer *lexer,
    struct csh_token *token, struct csh_error *error)
{
    struct source *source = lexer->source;
    memset(token, 0, sizeof(*token));
    clear_error(error);
    if (source->failure.message != NULL) {
        *error = source->failure;
        return CSH_LEX_ERROR;
    }
    if (lexer->child != NULL)
        return fail(lexer, error, "read the active command lexer", EINVAL);
    if (lexer->command)
        return CSH_LEX_COMMAND;
    for (;;) {
        struct frame *frame = lexer->frame_count == 0 ? NULL :
            &lexer->frames[lexer->frame_count - 1];
        enum csh_quote quote = frame == NULL ? CSH_QUOTE_NONE : frame->quote;
        int byte, next;
        size_t physical = 0;
        if (lexer->active && lexer->kind != CSH_TOKEN_WORD)
            return operator_step(lexer, token, error);
        if (source->cursor == source->length) {
            if (!source->final)
                return CSH_LEX_MORE;
            return eof(lexer, token, error);
        }
        byte = source->data[source->cursor];
        if (byte == 0)
            return fail(lexer, error, "NUL byte in shell input", 0);
        if (lexer->comment) {
            if (byte == '\n')
                lexer->comment = 0;
            else {
                if (consume(lexer, 1, error) == -1)
                    return CSH_LEX_ERROR;
                continue;
            }
        }
        /* A simple parameter name ends at its first non-name logical byte. */
        if (frame != NULL && frame->kind == SIMPLE) {
            next = peek(lexer, 0, &physical);
            if (next == -2)
                return CSH_LEX_MORE;
            if (!name_char(next)) {
                if (pop(lexer, 0, error) == -1)
                    return CSH_LEX_ERROR;
                continue;
            }
            if (delimiter(lexer, physical, quote, error) == -1)
                return CSH_LEX_ERROR;
            continue;
        }
        if (frame != NULL && frame->kind == SINGLE) {
            if (byte == '\'') {
                if (pop(lexer, 1, error) == -1)
                    return CSH_LEX_ERROR;
            } else if (piece(lexer, CSH_FRAGMENT_TEXT, quote, 1, error) == -1)
                return CSH_LEX_ERROR;
            continue;
        }
        if (frame != NULL && frame->kind == PARAMETER) {
            if (byte == '}') {
                if (pop(lexer, 1, error) == -1)
                    return CSH_LEX_ERROR;
                continue;
            }
            /* Continuations must not advance the parameter header state. */
            if (byte != '\\')
                parameter_context(frame, byte);
            quote = frame->quote;
        }
        if (frame != NULL && frame->kind == ARITHMETIC) {
            quote = CSH_QUOTE_DOUBLE;
            if (byte == '(') {
                if (frame->parentheses == SIZE_MAX)
                    return fail(lexer, error, "arithmetic nesting overflow", EOVERFLOW);
                ++frame->parentheses;
            } else if (byte == ')') {
                if (frame->parentheses != 0)
                    --frame->parentheses;
                else {
                    next = peek(lexer, 1, &physical);
                    if (next == -2)
                        return CSH_LEX_MORE;
                    if (next == ')') {
                        if (pop(lexer, physical, error) == -1)
                            return CSH_LEX_ERROR;
                        continue;
                    }
                }
            }
        }
        if (byte == '\\') {
            if (source->cursor + 1 == source->length) {
                if (!source->final)
                    return CSH_LEX_MORE;
                return fail(lexer, error, "unterminated escape", 0);
            }
            next = source->data[source->cursor + 1];
            if (frame != NULL && frame->kind == DOLLAR_SINGLE) {
                if (piece(lexer, CSH_FRAGMENT_ESCAPE, quote, 2, error) == -1)
                    return CSH_LEX_ERROR;
                continue;
            }
            if (next == '\n' && !(frame != NULL && frame->kind == BACKQUOTE &&
                                    quote == CSH_QUOTE_NONE)) {
                if (lexer->active) {
                    if (piece(lexer, CSH_FRAGMENT_CONTINUATION, quote, 2, error) == -1)
                        return CSH_LEX_ERROR;
                } else if (consume(lexer, 2, error) == -1)
                    return CSH_LEX_ERROR;
                continue;
            }
            if ((frame != NULL && frame->kind == BACKQUOTE) ?
                (strchr("$`\\", next) != NULL ||
                 (quote == CSH_QUOTE_DOUBLE && next == '"')) :
                (quote != CSH_QUOTE_DOUBLE ||
                 strchr("$`\\", next) != NULL ||
                 (next == '"' && !(frame != NULL && frame->kind == ARITHMETIC)) ||
                 (frame != NULL && frame->kind == PARAMETER && next == '}'))) {
                if (!lexer->active) {
                    if (start_token(lexer, error) == -1)
                        return CSH_LEX_ERROR;
                    lexer->kind = CSH_TOKEN_WORD;
                }
                if (piece(lexer, CSH_FRAGMENT_ESCAPE, quote, 2, error) == -1)
                    return CSH_LEX_ERROR;
                continue;
            }
        }
        if (frame != NULL && (frame->kind == DOLLAR_SINGLE || frame->kind == BACKQUOTE)) {
            if (byte == (frame->kind == DOLLAR_SINGLE ? '\'' : '`')) {
                if (pop(lexer, 1, error) == -1)
                    return CSH_LEX_ERROR;
            } else if (piece(lexer, CSH_FRAGMENT_TEXT, quote, 1, error) == -1)
                return CSH_LEX_ERROR;
            continue;
        }
        if (frame == NULL && (byte == ' ' || byte == '\t' || byte == '\n' || operator_char(byte))) {
            if (lexer->active)
                return publish(lexer, token, error);
            if (byte == ' ' || byte == '\t') {
                if (consume(lexer, 1, error) == -1)
                    return CSH_LEX_ERROR;
                continue;
            }
            if (start_token(lexer, error) == -1)
                return CSH_LEX_ERROR;
            if (byte == '\n') {
                lexer->kind = CSH_TOKEN_NEWLINE;
                if (consume(lexer, 1, error) == -1)
                    return CSH_LEX_ERROR;
                return publish(lexer, token, error);
            }
            lexer->operator_text[0] = (char)byte;
            lexer->operator_text[1] = 0;
            lexer->operator_length = 1;
            {
                size_t index;
                for (index = 0; index < sizeof(operators) / sizeof(operators[0]); ++index)
                    if (strcmp(lexer->operator_text, operators[index].text) == 0)
                        lexer->kind = operators[index].kind;
            }
            if (consume(lexer, 1, error) == -1)
                return CSH_LEX_ERROR;
            continue;
        }
        if (!lexer->active && byte == '#') {
            lexer->comment = 1;
            continue;
        }
        if (!lexer->active) {
            if (start_token(lexer, error) == -1)
                return CSH_LEX_ERROR;
            lexer->kind = CSH_TOKEN_WORD;
        }
        if (byte == '"' && !(frame != NULL && frame->kind == ARITHMETIC)) {
            if (frame != NULL && frame->kind == DOUBLE) {
                if (pop(lexer, 1, error) == -1)
                    return CSH_LEX_ERROR;
            } else if (push(lexer, DOUBLE, CSH_FRAGMENT_QUOTED, CSH_QUOTE_DOUBLE, 1, error) == -1)
                return CSH_LEX_ERROR;
            continue;
        }
        if (byte == '\'' && quote == CSH_QUOTE_NONE) {
            if (push(lexer, SINGLE, CSH_FRAGMENT_QUOTED, CSH_QUOTE_SINGLE, 1, error) == -1)
                return CSH_LEX_ERROR;
            continue;
        }
        if (byte == '$') {
            int result = dollar(lexer, quote, error);
            if (result == -1)
                return CSH_LEX_ERROR;
            if (result == 2)
                return CSH_LEX_MORE;
            if (result == 3)
                return CSH_LEX_COMMAND;
            if (result == 1)
                continue;
        }
        if (byte == '`') {
            if (push(lexer, BACKQUOTE, CSH_FRAGMENT_BACKQUOTE, quote, 1, error) == -1)
                return CSH_LEX_ERROR;
            continue;
        }
        if (piece(lexer, CSH_FRAGMENT_TEXT, quote, 1, error) == -1)
            return CSH_LEX_ERROR;
    }
}

size_t csh_lexer_command_fragment(const struct csh_lexer *lexer)
{
    return lexer->command && lexer->frame_count != 0 ?
        lexer->frames[lexer->frame_count - 1].fragment : CSH_FRAGMENT_ROOT;
}

int csh_lexer_command_begin(struct csh_lexer *parent, struct csh_lexer **child,
    struct csh_error *error)
{
    struct csh_lexer *created;
    *child = NULL;
    clear_error(error);
    if (parent->source->failure.message != NULL) {
        *error = parent->source->failure;
        return -1;
    }
    if (!parent->command || parent->child != NULL)
        return fail(parent, error, "no pending command substitution", EINVAL);
    created = malloc(sizeof(*created));
    if (created == NULL)
        return fail(parent, error, "cannot allocate command lexer", ENOMEM);
    memset(created, 0, sizeof(*created));
    created->source = parent->source;
    created->root = parent->root;
    created->parent = parent;
    created->depth = parent->depth + 1;
    parent->child = created;
    *child = created;
    return 0;
}

int csh_lexer_command_end(struct csh_lexer *parent, struct csh_lexer *child,
    const struct csh_token *closing, struct csh_error *error)
{
    clear_error(error);
    if (parent->source->failure.message != NULL) {
        *error = parent->source->failure;
        return -1;
    }
    if (child == NULL || parent->child != child || child->child != NULL ||
        !parent->command || child->active || !child->has_last || closing == NULL ||
        closing->kind != CSH_TOKEN_RPAREN || child->last_kind != CSH_TOKEN_RPAREN ||
        closing->start.offset != child->last_start.offset ||
        closing->end.offset != child->last_end.offset ||
        child->last_sequence != parent->source->sequence)
        return fail(parent, error, "invalid command-substitution boundary", EINVAL);
    csh_lexer_destroy(child);
    parent->command = 0;
    return pop(parent, 0, error);
}

int csh_lexer_alias_active(const struct csh_lexer *lexer, const char *name)
{
    size_t index;
    if (name == NULL)
        return 0;
    for (index = 0; index < lexer->source->alias_count; ++index)
        if (strcmp(lexer->source->aliases[index].name, name) == 0)
            return 1;
    return 0;
}

int csh_lexer_follows_redirection(struct csh_lexer *lexer)
{
    size_t physical = 0;
    int byte = peek(lexer, 0, &physical);
    return byte == '<' || byte == '>';
}

int csh_lexer_alias_push(struct csh_lexer *lexer, const struct csh_token *token,
    const char *name, const char *value, struct csh_error *error)
{
    struct source *source = lexer->source;
    struct alias_source alias;
    size_t length, added, index, name_length;
    clear_error(error);
    if (source->failure.message != NULL) {
        *error = source->failure;
        return -1;
    }
    if (token == NULL || name == NULL || value == NULL || *name == 0 ||
        lexer->child != NULL || lexer->active || !lexer->has_last ||
        token->kind != CSH_TOKEN_WORD || lexer->last_kind != CSH_TOKEN_WORD ||
        token->start.offset != lexer->last_start.offset ||
        token->end.offset != lexer->last_end.offset ||
        lexer->last_sequence != source->sequence || csh_lexer_alias_active(lexer, name))
        return fail(lexer, error, "invalid alias substitution boundary", EINVAL);
    length = strlen(value);
    name_length = strlen(name);
    if (length == SIZE_MAX || source->length > SIZE_MAX - length - 1 ||
        source->alias_count == SIZE_MAX || name_length > SIZE_MAX - 7)
        return fail(lexer, error, "alias source is too large", EOVERFLOW);
    added = length + 1;
    memset(&alias, 0, sizeof(alias));
    alias.name = copy_string(name);
    alias.source_name = malloc(name_length + 7);
    alias.invocation_source = copy_string(token->invocation_source != NULL ?
        token->invocation_source : token->source_name);
    if (alias.name == NULL || alias.source_name == NULL || alias.invocation_source == NULL) {
        release_alias(&alias);
        return fail(lexer, error, "cannot allocate alias source", ENOMEM);
    }
    memcpy(alias.source_name, "alias:", 6);
    memcpy(alias.source_name + 6, name, name_length + 1);
    alias.invocation = token->invocation_source != NULL ? token->invocation : token->start;
    alias.resume = source->position;
    alias.end = source->cursor + added;
    alias.owner_depth = lexer->depth;
    alias.trailing_blank = length != 0 &&
        (value[length - 1] == ' ' || value[length - 1] == '\t');
    if (reserve((void **)&source->aliases, &source->alias_capacity,
            source->alias_count + 1, sizeof(*source->aliases)) == -1 ||
        reserve((void **)&source->data, &source->capacity,
            source->length + added, 1) == -1) {
        int number = errno;
        release_alias(&alias);
        return fail(lexer, error, "cannot grow alias input", number);
    }
    memmove(source->data + source->cursor + added, source->data + source->cursor,
        source->length - source->cursor);
    memcpy(source->data + source->cursor, value, length);
    source->data[source->cursor + length] = ' ';
    source->length += added;
    for (index = 0; index < source->alias_count; ++index)
        source->aliases[index].end += added;
    source->aliases[source->alias_count++] = alias;
    source->position = (struct csh_position){0, 1, 1};
    source->alias_eligible = length != 0 && token->alias_eligible;
    source->look_valid = 0;
    lexer->has_last = 0;
    return 0;
}

const unsigned char *csh_lexer_pending(const struct csh_lexer *lexer,
    size_t *length, struct csh_position *position, int *final)
{
    const struct source *source = lexer->source;
    *length = source->length - source->cursor;
    *position = source->position;
    *final = source->final;
    return source->data == NULL ? NULL : source->data + source->cursor;
}

int csh_lexer_skip_raw(struct csh_lexer *lexer, size_t length,
    struct csh_error *error)
{
    clear_error(error);
    if (lexer->source->failure.message != NULL) {
        *error = lexer->source->failure;
        return -1;
    }
    if (lexer->child != NULL || lexer->active || lexer->comment ||
        length > lexer->source->length - lexer->source->cursor)
        return fail(lexer, error, "invalid raw input handoff", EINVAL);
    lexer->has_last = 0;
    return consume(lexer, length, error);
}

const char *csh_token_kind_name(enum csh_token_kind kind)
{
    static const char *const names[] = {"WORD", "NEWLINE", "AND_IF", "OR_IF",
        "DSEMI", "SEMI_AND", "DLESS", "DGREAT", "LESS_AND", "GREAT_AND",
        "LESS_GREAT", "DLESS_DASH", "CLOBBER", "PIPE", "AMPERSAND", "SEMI",
        "LPAREN", "RPAREN", "LESS", "GREAT"};
    return (unsigned)kind < sizeof(names) / sizeof(names[0]) ? names[kind] : "UNKNOWN";
}
const char *csh_fragment_kind_name(enum csh_fragment_kind kind)
{
    static const char *const names[] = {"TEXT", "QUOTED", "ESCAPE", "CONTINUATION",
        "PARAMETER", "COMMAND", "ARITHMETIC", "BACKQUOTE"};
    return (unsigned)kind < sizeof(names) / sizeof(names[0]) ? names[kind] : "UNKNOWN";
}
const char *csh_quote_name(enum csh_quote quote)
{
    static const char *const names[] = {"NONE", "SINGLE", "DOUBLE", "DOLLAR_SINGLE"};
    return (unsigned)quote < sizeof(names) / sizeof(names[0]) ? names[quote] : "UNKNOWN";
}
