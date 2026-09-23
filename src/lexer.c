#include "cshell/lexer.h"

#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* A root and its suspended command frames share one physical byte stream.
 * Retain the outer word until it is published; child tokens own copies. */
struct source {
    char *name;
    unsigned char *data;
    size_t length, capacity, cursor;
    struct csh_position position;
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
    struct csh_position start;
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

static void release_work(struct csh_lexer *lexer)
{
    free(lexer->fragments);
    free(lexer->frames);
    lexer->fragments = NULL;
    lexer->frames = NULL;
    lexer->fragment_count = lexer->fragment_capacity = 0;
    lexer->frame_count = lexer->frame_capacity = 0;
    lexer->active = lexer->command = lexer->comment = 0;
}

static int fail_at(struct csh_lexer *lexer, struct csh_error *error,
    const char *message, int number, struct csh_position position)
{
    struct source *source = lexer->source;
    struct csh_lexer *cursor;
    if (source->failure.message == NULL) {
        plain_error(&source->failure, message, number);
        source->failure.position = position;
        for (cursor = lexer->root; cursor != NULL; cursor = cursor->child)
            release_work(cursor);
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
    /* No active outer word needs the consumed prefix. */
    if (!lexer->root->active && source->cursor != 0) {
        memmove(source->data, source->data + source->cursor,
                source->length - source->cursor);
        source->length -= source->cursor;
        source->cursor = 0;
    }
    if (length > SIZE_MAX - source->length ||
        length > SIZE_MAX - source->position.offset -
            (source->length - source->cursor))
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
    free(token->source_name);
    free(token->raw);
    free(token->fragments);
    memset(token, 0, sizeof(*token));
}

static int consume(struct csh_lexer *lexer, size_t count, struct csh_error *error)
{
    struct source *source = lexer->source;
    size_t index;
    for (index = 0; index < count; ++index) {
        unsigned char byte = source->data[source->cursor];
        if (byte == 0)
            return fail(lexer, error, "NUL byte in shell input", 0);
        if (source->position.offset == SIZE_MAX ||
            (byte == '\n' ? source->position.line : source->position.column) == SIZE_MAX)
            return fail(lexer, error, "lexer position overflow", EOVERFLOW);
        ++source->position.offset;
        if (byte == '\n') {
            ++source->position.line;
            source->position.column = 1;
        } else {
            ++source->position.column;
        }
        ++source->cursor;
    }
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
    fragment->begin = lexer->source->position.offset - lexer->start.offset;
    fragment->end = fragment->begin;
    fragment->start = fragment->finish = lexer->source->position;
    return 0;
}

static void finish_fragment(struct csh_lexer *lexer, size_t index)
{
    lexer->fragments[index].end = lexer->source->position.offset - lexer->start.offset;
    lexer->fragments[index].finish = lexer->source->position;
}

static int piece(struct csh_lexer *lexer, enum csh_fragment_kind kind,
    enum csh_quote quote, size_t count, struct csh_error *error)
{
    size_t index;
    if (kind == CSH_FRAGMENT_TEXT && lexer->fragment_count != 0) {
        struct csh_fragment *last = &lexer->fragments[lexer->fragment_count - 1];
        if (last->kind == kind && last->quote == quote &&
            last->parent == parent_fragment(lexer) &&
            last->finish.offset == lexer->source->position.offset) {
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
        *opening = source->position;
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
    size_t length = source->position.offset - lexer->start.offset;
    unsigned char *raw;
    char *name;
    if (length == SIZE_MAX)
        return fail(lexer, error, "token is too large", EOVERFLOW);
    raw = malloc(length + 1);
    name = malloc(strlen(source->name) + 1);
    if (raw == NULL || name == NULL) {
        free(raw);
        free(name);
        return fail(lexer, error, "cannot allocate token", ENOMEM);
    }
    memcpy(raw, source->data + source->cursor - length, length);
    raw[length] = 0;
    strcpy(name, source->name);
    token->kind = lexer->kind;
    token->raw = raw;
    token->length = length;
    token->source_name = name;
    token->start = lexer->start;
    token->end = source->position;
    token->fragments = lexer->fragments;
    token->fragment_count = lexer->fragment_count;
    lexer->fragments = NULL;
    lexer->fragment_count = lexer->fragment_capacity = 0;
    lexer->active = 0;
    lexer->operator_length = 0;
    lexer->last_kind = token->kind;
    lexer->last_start = token->start;
    lexer->last_end = token->end;
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
        return fail_at(lexer, error, "unterminated command substitution", 0,
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
                    lexer->active = 1;
                    lexer->kind = CSH_TOKEN_WORD;
                    lexer->start = source->position;
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
            lexer->active = 1;
            lexer->start = source->position;
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
            lexer->active = 1;
            lexer->kind = CSH_TOKEN_WORD;
            lexer->start = source->position;
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
        closing->end.offset != parent->source->position.offset)
        return fail(parent, error, "invalid command-substitution boundary", EINVAL);
    csh_lexer_destroy(child);
    parent->command = 0;
    return pop(parent, 0, error);
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
