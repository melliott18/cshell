#include "cshell/parser.h"
#include "cshell/alias.h"
#include "cshell/quote.h"

#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

/* Iterative sequences have no fixed length limit. Recursive grammar contexts
 * have an explicit limit so hostile grouping cannot exhaust the C stack. */
#define PARSER_NESTING_LIMIT 128

struct csh_parser {
    struct csh_input *input;
    struct csh_lexer *lexer;
    const struct csh_aliases *aliases;
    enum csh_parse_result failure_result;
    struct csh_error failure;
    int final;
    int eof;
    void (*before_read)(void *, int);
    void *read_context;
    int continuation;
};

struct parse_frame {
    struct csh_parser *parser;
    struct csh_lexer *lexer;
    struct csh_ast_word look;
    int has_look;
    int eof;
    size_t depth;
    struct csh_ast_redirection **documents;
    size_t document_count;
    size_t document_capacity;
};

enum closing {
    CLOSE_NONE, CLOSE_PAREN, CLOSE_BRACE, CLOSE_THEN, CLOSE_IF_BRANCH,
    CLOSE_FI, CLOSE_DO, CLOSE_DONE, CLOSE_CASE
};
struct bytes { unsigned char *data; size_t length, capacity; };

static struct csh_ast *parse_list(struct parse_frame *, enum closing, int,
    struct csh_position);

static int fail_at(struct parse_frame *frame, enum csh_parse_result result,
    const char *message, int number, struct csh_position position)
{
    struct csh_parser *parser = frame->parser;
    if (parser->failure.message == NULL) {
        memset(&parser->failure, 0, sizeof(parser->failure));
        parser->failure.message = message;
        parser->failure.system_errno = number;
        parser->failure.status = number != 0 ? 1 : 2;
        parser->failure.position = position;
        parser->failure_result = result;
    }
    return -1;
}

static struct csh_position token_position(const struct csh_token *token)
{
    return token->invocation_source != NULL ? token->invocation : token->start;
}

static struct csh_position position(struct parse_frame *frame)
{
    size_t length;
    int final;
    struct csh_position result;
    if (frame->has_look)
        return token_position(&frame->look.token);
    (void)csh_lexer_pending(frame->lexer, &length, &result, &final);
    return csh_lexer_diagnostic_position(frame->lexer, result);
}

static int adopt_error(struct parse_frame *frame, const struct csh_error *error)
{
    if (frame->parser->failure.message == NULL) {
        frame->parser->failure = *error;
        if (frame->parser->failure.position.line == 0)
            frame->parser->failure.position = position(frame);
        frame->parser->failure_result = frame->parser->final &&
            error->system_errno == 0 &&
            error->message != NULL &&
            strncmp(error->message, "unterminated ", 13) == 0 ?
            CSH_PARSE_INCOMPLETE : CSH_PARSE_ERROR;
    }
    return -1;
}

static int reserve(struct parse_frame *frame, void **pointer, size_t *capacity,
    size_t count, size_t size)
{
    size_t grown = *capacity == 0 ? 16 : *capacity;
    void *replacement;
    if (count <= *capacity)
        return 0;
    if (count > SIZE_MAX / size)
        return fail_at(frame, CSH_PARSE_ERROR, "parser storage overflow",
            EOVERFLOW, position(frame));
    while (grown < count) {
        if (grown > SIZE_MAX / 2) { grown = count; break; }
        grown *= 2;
    }
    if (grown > SIZE_MAX / size)
        grown = count;
    replacement = realloc(*pointer, grown * size);
    if (replacement == NULL)
        return fail_at(frame, CSH_PARSE_ERROR, "cannot allocate parser storage",
            ENOMEM, position(frame));
    *pointer = replacement;
    *capacity = grown;
    return 0;
}

static int append(struct parse_frame *frame, struct bytes *buffer,
    const void *data, size_t length)
{
    if (length >= SIZE_MAX - buffer->length)
        return fail_at(frame, CSH_PARSE_ERROR, "parser storage overflow",
            EOVERFLOW, position(frame));
    if (reserve(frame, (void **)&buffer->data, &buffer->capacity,
                buffer->length + length + 1, 1) == -1)
        return -1;
    if (length != 0)
        memcpy(buffer->data + buffer->length, data, length);
    buffer->length += length;
    buffer->data[buffer->length] = 0;
    return 0;
}

static int feed_line(struct parse_frame *frame)
{
    struct csh_input_line line;
    struct csh_error error;
    enum csh_input_result result;
    if (frame->parser->before_read != NULL)
        frame->parser->before_read(frame->parser->read_context,
            frame->parser->continuation);
    frame->parser->continuation = 1;
    result = csh_input_read_line(frame->parser->input, &line, &error);
    if (result == CSH_INPUT_ERROR)
        return adopt_error(frame, &error);
    if (result == CSH_INPUT_EOF) {
        frame->parser->final = 1;
        if (csh_lexer_feed(frame->lexer, NULL, 0, 1, &error) == -1)
            return adopt_error(frame, &error);
    } else if (csh_lexer_feed(frame->lexer, line.data, line.length, 0, &error) == -1)
        return adopt_error(frame, &error);
    return 0;
}

static void frame_destroy(struct parse_frame *frame)
{
    csh_ast_word_destroy(&frame->look);
    free(frame->documents);
}

static void discard_replayed_substitutions(struct parse_frame *frame)
{
    size_t first = csh_lexer_command_fragment(frame->lexer);
    while (frame->look.substitution_count != 0) {
        struct csh_ast_substitution *sub =
            &frame->look.substitutions[frame->look.substitution_count - 1];
        if (sub->fragment_index < first)
            break;
        csh_ast_destroy(sub->body);
        --frame->look.substitution_count;
    }
}

static int peek_raw(struct parse_frame *frame)
{
    struct csh_error error;
    if (frame->has_look)
        return 1;
    if (frame->eof)
        return 0;
    for (;;) {
        enum csh_lex_result result = csh_lexer_next(frame->lexer,
            &frame->look.token, &error);
        if (result == CSH_LEX_ERROR)
            return adopt_error(frame, &error);
        if (result == CSH_LEX_MORE) {
            if (feed_line(frame) == -1)
                return -1;
            continue;
        }
        if (result == CSH_LEX_EOF) {
            frame->eof = 1;
            return 0;
        }
        if (result == CSH_LEX_REPLAY) {
            discard_replayed_substitutions(frame);
            continue;
        }
        if (result == CSH_LEX_COMMAND) {
            struct parse_frame child;
            struct csh_ast_substitution substitution;
            struct csh_position opening;
            const char *context;
            memset(&child, 0, sizeof(child));
            memset(&substitution, 0, sizeof(substitution));
            (void)csh_lexer_context(frame->lexer, &context, &opening);
            opening = csh_lexer_diagnostic_position(frame->lexer, opening);
            if (frame->depth >= PARSER_NESTING_LIMIT)
                return fail_at(frame, CSH_PARSE_ERROR, "parser nesting limit exceeded",
                    0, opening);
            child.parser = frame->parser;
            child.depth = frame->depth + 1;
            if (csh_lexer_command_begin(frame->lexer, &child.lexer, &error) == -1)
                return adopt_error(frame, &error);
            substitution.body = parse_list(&child, CLOSE_PAREN, 1, opening);
            if (substitution.body == NULL)
                goto command_error;
            substitution.fragment_index = csh_lexer_command_fragment(frame->lexer);
            if (child.document_count != 0) {
                fail_at(&child, CSH_PARSE_ERROR,
                    "command substitution closes before here-document body", 0,
                    token_position(&child.look.token));
                goto command_error;
            }
            if (csh_lexer_command_end(frame->lexer, child.lexer,
                    &child.look.token, &error) == -1) {
                adopt_error(frame, &error);
                goto command_error;
            }
            frame_destroy(&child);
            if (csh_ast_word_add_substitution(&frame->look, &substitution, &error) == -1) {
                csh_ast_destroy(substitution.body);
                return adopt_error(frame, &error);
            }
            continue;

command_error:
            csh_ast_destroy(substitution.body);
            frame_destroy(&child);
            error = frame->parser->failure;
            {
                int replay = csh_lexer_replay_arithmetic(frame->lexer, &error);
                if (replay != 0) {
                    memset(&frame->parser->failure, 0, sizeof(frame->parser->failure));
                    if (replay == -1)
                        return adopt_error(frame, &error);
                    discard_replayed_substitutions(frame);
                    continue;
                }
            }
            return -1;
        }
        {
            size_t i;
            for (i = 0; i < frame->look.substitution_count; ++i) {
                struct csh_ast_substitution *sub = &frame->look.substitutions[i];
                const struct csh_fragment *fragment =
                    &frame->look.token.fragments[sub->fragment_index];
                sub->begin = fragment->begin;
                sub->end = fragment->end;
            }
        }
        frame->has_look = 1;
        return 1;
    }
}

static void take(struct parse_frame *frame, struct csh_ast_word *word)
{
    *word = frame->look;
    memset(&frame->look, 0, sizeof(frame->look));
    frame->has_look = 0;
}

static void discard(struct parse_frame *frame)
{
    csh_ast_word_destroy(&frame->look);
    frame->has_look = 0;
}

/* Only unquoted text and removed continuations are eligible for reserved-word
 * and IO_NUMBER recognition. Escapes, even of ordinary letters, quote a word. */
static int plain_equal(const struct csh_token *token, const char *text)
{
    size_t i, n = 0;
    if (token->kind != CSH_TOKEN_WORD)
        return 0;
    for (i = 0; i < token->fragment_count; ++i) {
        const struct csh_fragment *f = &token->fragments[i];
        size_t j;
        if (f->kind == CSH_FRAGMENT_CONTINUATION)
            continue;
        if (f->kind != CSH_FRAGMENT_TEXT || f->quote != CSH_QUOTE_NONE)
            return 0;
        for (j = f->begin; j < f->end; ++j) {
            if (text[n] == 0 || token->raw[j] != (unsigned char)text[n])
                return 0;
            ++n;
        }
    }
    return text[n] == 0;
}

static int io_number(const struct csh_token *token)
{
    size_t i, count = 0;
    for (i = 0; i < token->fragment_count; ++i) {
        const struct csh_fragment *f = &token->fragments[i];
        size_t j;
        if (f->kind == CSH_FRAGMENT_CONTINUATION)
            continue;
        if (f->kind != CSH_FRAGMENT_TEXT || f->quote != CSH_QUOTE_NONE)
            return 0;
        for (j = f->begin; j < f->end; ++j) {
            if (token->raw[j] < '0' || token->raw[j] > '9')
                return 0;
            ++count;
        }
    }
    return count != 0;
}

static int name_start(unsigned char c)
{
    return c == '_' || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z');
}

static int assignment(const struct csh_token *token)
{
    size_t i, count = 0;
    for (i = 0; i < token->fragment_count; ++i) {
        const struct csh_fragment *f = &token->fragments[i];
        size_t j;
        if (f->kind == CSH_FRAGMENT_CONTINUATION)
            continue;
        if (f->kind != CSH_FRAGMENT_TEXT || f->quote != CSH_QUOTE_NONE)
            return 0;
        for (j = f->begin; j < f->end; ++j) {
            unsigned char c = token->raw[j];
            if (c == '=')
                return count != 0;
            if (!(name_start(c) || (count != 0 && c >= '0' && c <= '9')))
                return 0;
            ++count;
        }
    }
    return 0;
}

static int valid_name(const struct csh_token *token)
{
    size_t i, count = 0;
    if (token->kind != CSH_TOKEN_WORD)
        return 0;
    for (i = 0; i < token->fragment_count; ++i) {
        const struct csh_fragment *fragment = &token->fragments[i];
        size_t j;
        if (fragment->kind == CSH_FRAGMENT_CONTINUATION)
            continue;
        if (fragment->kind != CSH_FRAGMENT_TEXT || fragment->quote != CSH_QUOTE_NONE)
            return 0;
        for (j = fragment->begin; j < fragment->end; ++j) {
            unsigned char c = token->raw[j];
            if (!(name_start(c) || (count != 0 && c >= '0' && c <= '9')))
                return 0;
            ++count;
        }
    }
    return count != 0;
}

static int reserved(const struct csh_token *token)
{
    static const char *const words[] = {"if", "then", "else", "elif", "fi",
        "do", "done", "case", "esac", "while", "until", "for", "in",
        "{", "}", "!"};
    size_t i;
    for (i = 0; i < sizeof(words) / sizeof(words[0]); ++i)
        if (plain_equal(token, words[i]))
            return 1;
    return 0;
}

/* Alias lookup belongs to the delimited-token boundary, before any later
 * token is read. A raw lookahead acquired without command context remains
 * eligible when the grammar subsequently identifies a command position. */
static int peek_alias(struct parse_frame *frame, int command_position)
{
    int result;
    while ((result = peek_raw(frame)) > 0) {
        const struct csh_token *token = &frame->look.token;
        struct bytes name = {0};
        const char *value;
        struct csh_error error;
        size_t i;
        if (frame->parser->aliases == NULL || token->kind != CSH_TOKEN_WORD ||
            (!command_position && !token->alias_eligible) || reserved(token) ||
            (io_number(token) && csh_lexer_follows_redirection(frame->lexer)))
            return result;
        for (i = 0; i < token->fragment_count; ++i) {
            const struct csh_fragment *fragment = &token->fragments[i];
            if (fragment->kind != CSH_FRAGMENT_CONTINUATION &&
                (fragment->kind != CSH_FRAGMENT_TEXT ||
                 fragment->quote != CSH_QUOTE_NONE))
                return result;
        }
        for (i = 0; i < token->fragment_count; ++i) {
            const struct csh_fragment *fragment = &token->fragments[i];
            if (fragment->kind != CSH_FRAGMENT_CONTINUATION &&
                append(frame, &name, token->raw + fragment->begin,
                       fragment->end - fragment->begin) == -1) {
                free(name.data);
                return -1;
            }
        }
        value = name.data == NULL ? NULL :
            csh_aliases_get(frame->parser->aliases, (const char *)name.data);
        if (value == NULL || csh_lexer_alias_active(frame->lexer,
                                                   (const char *)name.data)) {
            free(name.data);
            return result;
        }
        result = csh_lexer_alias_push(frame->lexer, token,
                                     (const char *)name.data, value, &error);
        free(name.data);
        if (result == -1)
            return adopt_error(frame, &error);
        discard(frame);
    }
    return result;
}

static int peek(struct parse_frame *frame)
{
    return peek_alias(frame, 0);
}

static int redirection_kind(enum csh_token_kind kind)
{
    return kind == CSH_TOKEN_LESS || kind == CSH_TOKEN_GREAT ||
        kind == CSH_TOKEN_DLESS || kind == CSH_TOKEN_DGREAT ||
        kind == CSH_TOKEN_LESS_AND || kind == CSH_TOKEN_GREAT_AND ||
        kind == CSH_TOKEN_LESS_GREAT || kind == CSH_TOKEN_DLESS_DASH ||
        kind == CSH_TOKEN_CLOBBER;
}

/* A here-document delimiter undergoes quote removal without any expansion.
 * Consequently expansion-looking punctuation remains literal: quoting is
 * interpreted over the delimiter spelling, not by evaluating its fragments.
 * For example ${x:-"EOF"} becomes ${x:-EOF}, while "$(echo 'EOF')" keeps
 * the single quotes protected by the delimiter's double quotes. */
static int delimiter_spelling(struct parse_frame *frame,
    const struct csh_token *token, struct bytes *buffer, int *quoted)
{
    size_t i = 0;
    unsigned char quote = 0;
    while (i < token->length) {
        unsigned char byte = token->raw[i];
        if (quote == '\'') {
            if (byte == '\'') {
                quote = 0;
                ++i;
                continue;
            }
        } else if (byte == '\\' && i + 1 < token->length) {
            unsigned char next = token->raw[i + 1];
            if (next == '\n') {
                i += 2;
                continue;
            }
            if (quote == 0 || strchr("$`\\\"", next) != NULL) {
                *quoted = 1;
                if (append(frame, buffer, token->raw + i + 1, 1) == -1)
                    return -1;
                i += 2;
                continue;
            }
        } else if (byte == '"') {
            quote = quote == '"' ? 0 : '"';
            *quoted = 1;
            ++i;
            continue;
        } else if (quote == 0 && byte == '\'') {
            quote = '\'';
            *quoted = 1;
            ++i;
            continue;
        } else if (quote == 0 && byte == '$') {
            size_t opening = i + 1, end, length;
            char *decoded = NULL;
            enum csh_quote_result result;
            while (opening + 1 < token->length && token->raw[opening] == '\\' &&
                   token->raw[opening + 1] == '\n')
                opening += 2;
            if (opening < token->length && token->raw[opening] == '\'') {
                end = opening + 1;
                while (end < token->length && token->raw[end] != '\'') {
                    if (token->raw[end] == '\\' && end + 1 < token->length)
                        ++end;
                    ++end;
                }
                if (end < token->length) {
                    result = csh_quote_decode(token->raw + opening + 1,
                        end - opening - 1, &decoded, &length);
                    if (result != CSH_QUOTE_OK) {
                        free(decoded);
                        return fail_at(frame, CSH_PARSE_ERROR,
                            result == CSH_QUOTE_NOMEM ? "cannot decode here-document delimiter" :
                            "invalid dollar-single-quoted here-document delimiter",
                            result == CSH_QUOTE_NOMEM ? ENOMEM : 0, token_position(token));
                    }
                    *quoted = 1;
                    if (append(frame, buffer, decoded, length) == -1) {
                        free(decoded);
                        return -1;
                    }
                    free(decoded);
                    i = end + 1;
                    continue;
                }
            }
        }
        if (append(frame, buffer, token->raw + i, 1) == -1)
            return -1;
        ++i;
    }
    return 0;
}

static int prepare_document(struct parse_frame *frame,
    struct csh_ast_redirection *redirection)
{
    struct bytes delimiter = {0};
    if (delimiter_spelling(frame, &redirection->operand.token,
                           &delimiter, &redirection->delimiter_quoted) == -1) {
        free(delimiter.data);
        return -1;
    }
    if (append(frame, &delimiter, NULL, 0) == -1) {
        free(delimiter.data);
        return -1;
    }
    redirection->delimiter = delimiter.data;
    redirection->delimiter_length = delimiter.length;
    if (frame->document_count == SIZE_MAX ||
        reserve(frame, (void **)&frame->documents, &frame->document_capacity,
                frame->document_count + 1, sizeof(*frame->documents)) == -1)
        return -1;
    frame->documents[frame->document_count++] = redirection;
    return 0;
}

static int append_document_line(struct parse_frame *frame, struct bytes *body,
    const struct bytes *line, int strip_tabs, int quoted)
{
    size_t i = 0;
    if (strip_tabs) {
        while (i < line->length) {
            if (line->data[i] == '\t') {
                ++i;
            } else if (!quoted && i + 1 < line->length &&
                       line->data[i] == '\\' && line->data[i + 1] == '\n') {
                if (append(frame, body, line->data + i, 2) == -1)
                    return -1;
                i += 2;
            } else
                break;
        }
    }
    return append(frame, body, line->data + i, line->length - i);
}

static int collect_documents(struct parse_frame *frame)
{
    size_t i;
    struct csh_error error;
    for (i = 0; i < frame->document_count; ++i) {
        struct csh_ast_redirection *document = frame->documents[i];
        struct bytes body = {0}, line = {0}, logical = {0};
        struct csh_position line_start;
        int strip_tabs = document->operator_kind == CSH_TOKEN_DLESS_DASH;
        document->body_start = position(frame);
        line_start = document->body_start;
        for (;;) {
            const unsigned char *pending;
            size_t available, length, content, backslashes = 0, skip = 0;
            struct csh_position start;
            int final, continued;
            pending = csh_lexer_pending(frame->lexer, &available, &start, &final);
            if (available == 0) {
                if (final) {
                    fail_at(frame, CSH_PARSE_INCOMPLETE,
                        "unterminated here-document", 0, token_position(&document->operand.token));
                    goto document_failed;
                }
                if (feed_line(frame) == -1)
                    goto document_failed;
                continue;
            }
            if (line.length == 0)
                line_start = start;
            for (length = 0; length < available && pending[length] != '\n'; ++length)
                ;
            content = length;
            if (length < available)
                ++length;
            if (!document->delimiter_quoted && length > content) {
                while (backslashes < content &&
                       pending[content - backslashes - 1] == '\\')
                    ++backslashes;
            }
            continued = (backslashes % 2) != 0;
            if (append(frame, &line, pending, length) == -1 ||
                append(frame, &logical, pending, content - (continued ? 1 : 0)) == -1)
                goto document_failed;
            if (csh_lexer_skip_raw(frame->lexer, length, &error) == -1) {
                adopt_error(frame, &error);
                goto document_failed;
            }
            if (continued)
                continue;
            if (strip_tabs)
                while (skip < logical.length && logical.data[skip] == '\t')
                    ++skip;
            if (logical.length - skip == document->delimiter_length &&
                memcmp(logical.data + skip, document->delimiter,
                       document->delimiter_length) == 0) {
                if (append(frame, &body, NULL, 0) == -1)
                    goto document_failed;
                document->body = body.data;
                document->body_length = body.length;
                document->body_end = line_start;
                free(line.data);
                free(logical.data);
                break;
            }
            if (append_document_line(frame, &body, &line, strip_tabs,
                                     document->delimiter_quoted) == -1)
                goto document_failed;
            line.length = logical.length = 0;
        }
        continue;
    document_failed:
        free(body.data);
        free(line.data);
        free(logical.data);
        return -1;
    }
    frame->document_count = 0;
    return 0;
}

static int newline(struct parse_frame *frame)
{
    discard(frame);
    return collect_documents(frame);
}

static struct csh_ast *new_node(struct parse_frame *frame, enum csh_ast_kind kind)
{
    struct csh_ast *node = NULL;
    struct csh_error error;
    if (csh_ast_create(&node, kind, &error) == -1)
        adopt_error(frame, &error);
    return node;
}

/* The operator is lookahead. An optional IO_NUMBER has already been moved
 * out of lookahead so one token suffices for adjacency classification. */
static int parse_redirection(struct parse_frame *frame, struct csh_ast *node,
    struct csh_ast_word *descriptor)
{
    struct csh_ast_redirection *redirection = NULL;
    struct csh_error error;
    struct csh_position opening = frame->look.token.start;
    struct csh_position diagnostic_opening = token_position(&frame->look.token);
    int result;
    if (csh_ast_redirection_create(&redirection, frame->look.token.kind, &error) == -1)
        return adopt_error(frame, &error);
    redirection->start = descriptor == NULL ? opening : descriptor->token.start;
    if (descriptor != NULL) {
        redirection->has_io_number = 1;
        redirection->io_number = descriptor->token;
        memset(&descriptor->token, 0, sizeof(descriptor->token));
    }
    discard(frame);
    result = peek(frame);
    if (result <= 0) {
        if (result == 0)
            fail_at(frame, CSH_PARSE_INCOMPLETE, "missing redirection operand", 0, diagnostic_opening);
        csh_ast_redirection_destroy(redirection);
        return -1;
    }
    if (frame->look.token.kind != CSH_TOKEN_WORD) {
        fail_at(frame, CSH_PARSE_ERROR, "expected redirection operand", 0, position(frame));
        csh_ast_redirection_destroy(redirection);
        return -1;
    }
    redirection->end = frame->look.token.end;
    take(frame, &redirection->operand);
    if (redirection->operator_kind == CSH_TOKEN_DLESS ||
        redirection->operator_kind == CSH_TOKEN_DLESS_DASH) {
        if (prepare_document(frame, redirection) == -1) {
            csh_ast_redirection_destroy(redirection);
            return -1;
        }
    }
    node->end = redirection->end;
    if (csh_ast_add_redirection(node, &redirection, &error) == -1) {
        csh_ast_redirection_destroy(redirection);
        return adopt_error(frame, &error);
    }
    return 0;
}

static int skip_newlines(struct parse_frame *frame)
{
    int result;
    while ((result = peek_alias(frame, 1)) > 0 && frame->look.token.kind == CSH_TOKEN_NEWLINE)
        if (newline(frame) == -1)
            return -1;
    return result;
}

/* Expectations distinguish final EOF from a token that cannot complete the
 * current production. Successful calls leave the expected token in lookahead. */
static int expect_token(struct parse_frame *frame, enum csh_token_kind kind,
    const char *spelling, const char *message)
{
    int result = peek(frame);
    if (result < 0)
        return -1;
    if (result == 0)
        return fail_at(frame, CSH_PARSE_INCOMPLETE, message, 0, position(frame));
    if (frame->look.token.kind != kind ||
        (spelling != NULL && !plain_equal(&frame->look.token, spelling)))
        return fail_at(frame, CSH_PARSE_ERROR, message, 0, position(frame));
    return 0;
}

static int consume_keyword(struct parse_frame *frame, struct csh_ast *node,
    const char *spelling)
{
    if (expect_token(frame, CSH_TOKEN_WORD, spelling,
            "expected compound command keyword") == -1)
        return -1;
    node->end = frame->look.token.end;
    discard(frame);
    return 0;
}

static int parse_if(struct parse_frame *frame, struct csh_ast *node)
{
    struct csh_error error;
    for (;;) {
        struct csh_ast_if_branch branch = {0};
        discard(frame); /* if or elif */
        branch.condition = parse_list(frame, CLOSE_THEN, 0, node->start);
        if (branch.condition == NULL)
            return -1;
        if (consume_keyword(frame, node, "then") == -1) {
            csh_ast_destroy(branch.condition);
            return -1;
        }
        branch.body = parse_list(frame, CLOSE_IF_BRANCH, 0, node->start);
        if (branch.body == NULL || csh_ast_if_add(node, &branch, &error) == -1) {
            if (branch.body != NULL)
                adopt_error(frame, &error);
            csh_ast_destroy(branch.condition);
            csh_ast_destroy(branch.body);
            return -1;
        }
        if (!plain_equal(&frame->look.token, "elif"))
            break;
    }
    if (plain_equal(&frame->look.token, "else")) {
        discard(frame);
        node->data.if_clause.else_body = parse_list(frame, CLOSE_FI, 0, node->start);
        if (node->data.if_clause.else_body == NULL)
            return -1;
    }
    return consume_keyword(frame, node, "fi");
}

static int parse_loop(struct parse_frame *frame, struct csh_ast *node)
{
    discard(frame);
    node->data.loop.condition = parse_list(frame, CLOSE_DO, 0, node->start);
    if (node->data.loop.condition == NULL || consume_keyword(frame, node, "do") == -1)
        return -1;
    node->data.loop.body = parse_list(frame, CLOSE_DONE, 0, node->start);
    if (node->data.loop.body == NULL)
        return -1;
    return consume_keyword(frame, node, "done");
}

static int parse_for(struct parse_frame *frame, struct csh_ast *node)
{
    struct csh_error error;
    int result, semicolon = 0, had_newline;
    discard(frame);
    if (expect_token(frame, CSH_TOKEN_WORD, NULL, "expected for variable name") == -1)
        return -1;
    if (!valid_name(&frame->look.token))
        return fail_at(frame, CSH_PARSE_ERROR, "invalid for variable name", 0, position(frame));
    take(frame, &node->data.for_clause.name);
    result = peek(frame);
    if (result < 0)
        return -1;
    had_newline = result > 0 && frame->look.token.kind == CSH_TOKEN_NEWLINE;
    result = skip_newlines(frame);
    if (result < 0)
        return -1;
    if (!had_newline && result > 0 && frame->look.token.kind == CSH_TOKEN_SEMI) {
        semicolon = 1;
        discard(frame);
        if (skip_newlines(frame) < 0)
            return -1;
    }
    if (!semicolon && frame->has_look && plain_equal(&frame->look.token, "in")) {
        node->data.for_clause.has_in = 1;
        discard(frame);
        while ((result = peek(frame)) > 0 && frame->look.token.kind == CSH_TOKEN_WORD) {
            struct csh_ast_word word = {0};
            take(frame, &word);
            if (csh_ast_word_vector_add(&node->data.for_clause.words, &word, &error) == -1) {
                csh_ast_word_destroy(&word);
                return adopt_error(frame, &error);
            }
        }
        if (result < 0)
            return -1;
        if (result == 0)
            return fail_at(frame, CSH_PARSE_INCOMPLETE,
                "expected separator after for words", 0, position(frame));
        if (frame->look.token.kind == CSH_TOKEN_NEWLINE) {
            if (newline(frame) == -1)
                return -1;
        } else if (frame->look.token.kind == CSH_TOKEN_SEMI)
            discard(frame);
        else
            return fail_at(frame, CSH_PARSE_ERROR,
                "expected separator after for words", 0, position(frame));
        if (skip_newlines(frame) < 0)
            return -1;
    }
    if (consume_keyword(frame, node, "do") == -1)
        return -1;
    node->data.for_clause.body = parse_list(frame, CLOSE_DONE, 0, node->start);
    if (node->data.for_clause.body == NULL)
        return -1;
    return consume_keyword(frame, node, "done");
}

static int parse_case(struct parse_frame *frame, struct csh_ast *node)
{
    struct csh_error error;
    int result;
    discard(frame);
    if (expect_token(frame, CSH_TOKEN_WORD, NULL, "expected case word") == -1)
        return -1;
    take(frame, &node->data.case_clause.word);
    if (skip_newlines(frame) < 0 || consume_keyword(frame, node, "in") == -1)
        return -1;
    for (;;) {
        struct csh_ast_case_item item = {0};
        result = skip_newlines(frame);
        if (result < 0)
            return -1;
        if (result == 0)
            return fail_at(frame, CSH_PARSE_INCOMPLETE, "unterminated case command", 0, node->start);
        if (plain_equal(&frame->look.token, "esac"))
            return consume_keyword(frame, node, "esac");
        if (frame->look.token.kind == CSH_TOKEN_LPAREN)
            discard(frame);
        for (;;) {
            struct csh_ast_word pattern = {0};
            if (expect_token(frame, CSH_TOKEN_WORD, NULL, "expected case pattern") == -1)
                goto failed;
            take(frame, &pattern);
            if (csh_ast_word_vector_add(&item.patterns, &pattern, &error) == -1) {
                csh_ast_word_destroy(&pattern);
                adopt_error(frame, &error);
                goto failed;
            }
            result = peek(frame);
            if (result < 0)
                goto failed;
            if (result == 0 || frame->look.token.kind != CSH_TOKEN_PIPE)
                break;
            discard(frame);
        }
        if (expect_token(frame, CSH_TOKEN_RPAREN, NULL, "expected ')' after case patterns") == -1)
            goto failed;
        discard(frame);
        item.body = parse_list(frame, CLOSE_CASE, 1, node->start);
        if (item.body == NULL)
            goto failed;
        if (frame->look.token.kind == CSH_TOKEN_DSEMI ||
            frame->look.token.kind == CSH_TOKEN_SEMI_AND) {
            item.terminator = frame->look.token.kind == CSH_TOKEN_DSEMI ?
                CSH_AST_CASE_BREAK : CSH_AST_CASE_FALLTHROUGH;
            item.terminator_start = frame->look.token.start;
            item.terminator_end = frame->look.token.end;
            discard(frame);
        }
        if (csh_ast_case_add(node, &item, &error) == -1) {
            adopt_error(frame, &error);
            goto failed;
        }
        continue;
    failed:
        csh_ast_case_item_destroy(&item);
        return -1;
    }
}

static int compound_kind(const struct csh_token *token, enum csh_ast_kind *kind)
{
    if (token->kind == CSH_TOKEN_LPAREN) *kind = CSH_AST_SUBSHELL;
    else if (plain_equal(token, "{")) *kind = CSH_AST_BRACE;
    else if (plain_equal(token, "if")) *kind = CSH_AST_IF;
    else if (plain_equal(token, "for")) *kind = CSH_AST_FOR;
    else if (plain_equal(token, "while")) *kind = CSH_AST_WHILE;
    else if (plain_equal(token, "until")) *kind = CSH_AST_UNTIL;
    else if (plain_equal(token, "case")) *kind = CSH_AST_CASE;
    else return 0;
    return 1;
}

/* Trailing redirections belong to the caller: for a function definition they
 * are saved on the function node, to be applied when invoked by CSH-028. */
static struct csh_ast *parse_compound(struct parse_frame *frame, enum csh_ast_kind kind)
{
    struct csh_ast *node;
    int result = -1;
    if (frame->depth >= PARSER_NESTING_LIMIT) {
        fail_at(frame, CSH_PARSE_ERROR, "parser nesting limit exceeded", 0, position(frame));
        return NULL;
    }
    node = new_node(frame, kind);
    if (node == NULL)
        return NULL;
    node->start = position(frame);
    ++frame->depth;
    switch (kind) {
    case CSH_AST_SUBSHELL:
    case CSH_AST_BRACE:
        discard(frame);
        node->data.group.body = parse_list(frame,
            kind == CSH_AST_SUBSHELL ? CLOSE_PAREN : CLOSE_BRACE, 0, node->start);
        if (node->data.group.body != NULL) {
            node->end = frame->look.token.end;
            discard(frame);
            result = 0;
        }
        break;
    case CSH_AST_IF: result = parse_if(frame, node); break;
    case CSH_AST_FOR: result = parse_for(frame, node); break;
    case CSH_AST_WHILE:
    case CSH_AST_UNTIL: result = parse_loop(frame, node); break;
    case CSH_AST_CASE: result = parse_case(frame, node); break;
    default: break;
    }
    --frame->depth;
    if (result == -1) {
        csh_ast_destroy(node);
        return NULL;
    }
    return node;
}

static int trailing_redirections(struct parse_frame *frame, struct csh_ast *node)
{
    int result;
    while ((result = peek(frame)) > 0) {
        if (redirection_kind(frame->look.token.kind)) {
            if (parse_redirection(frame, node, NULL) == -1)
                return -1;
        } else if (frame->look.token.kind == CSH_TOKEN_WORD && io_number(&frame->look.token)) {
            struct csh_ast_word descriptor = {0};
            int adjacent = csh_lexer_follows_redirection(frame->lexer);
            take(frame, &descriptor);
            result = peek(frame);
            if (adjacent && result > 0 && redirection_kind(frame->look.token.kind)) {
                result = parse_redirection(frame, node, &descriptor);
            } else {
                if (result >= 0)
                    fail_at(frame, CSH_PARSE_ERROR, "unexpected word after compound command", 0,
                        token_position(&descriptor.token));
                result = -1;
            }
            csh_ast_word_destroy(&descriptor);
            if (result < 0)
                return -1;
        } else
            return 0;
    }
    return result < 0 ? -1 : 0;
}

static struct csh_ast *parse_function(struct parse_frame *frame, struct csh_ast_word *name)
{
    struct csh_ast *node;
    enum csh_ast_kind kind;
    int result;
    if (!valid_name(&name->token)) {
        fail_at(frame, CSH_PARSE_ERROR, "invalid function name", 0, name->token.start);
        return NULL;
    }
    node = new_node(frame, CSH_AST_FUNCTION);
    if (node == NULL)
        return NULL;
    node->start = name->token.start;
    node->data.function.name = *name;
    *name = (struct csh_ast_word){0};
    discard(frame); /* '(' */
    if (expect_token(frame, CSH_TOKEN_RPAREN, NULL, "expected ')' in function definition") == -1)
        goto failed;
    discard(frame);
    result = skip_newlines(frame);
    if (result < 0)
        goto failed;
    if (result == 0 || !compound_kind(&frame->look.token, &kind)) {
        fail_at(frame, result == 0 ? CSH_PARSE_INCOMPLETE : CSH_PARSE_ERROR,
            "expected compound function body", 0, position(frame));
        goto failed;
    }
    node->data.function.body = parse_compound(frame, kind);
    if (node->data.function.body == NULL)
        goto failed;
    node->end = node->data.function.body->end;
    if (trailing_redirections(frame, node) == -1)
        goto failed;
    return node;
failed:
    csh_ast_destroy(node);
    return NULL;
}

static struct csh_ast *parse_command(struct parse_frame *frame)
{
    struct csh_ast *node = NULL;
    struct csh_error error;
    struct csh_position opening, diagnostic_opening;
    enum csh_ast_kind kind;
    int result = peek_alias(frame, 1), command_name = 0, prefix = 0;
    if (result <= 0) {
        if (result == 0)
            fail_at(frame, CSH_PARSE_INCOMPLETE, "expected command", 0, position(frame));
        return NULL;
    }
    opening = frame->look.token.start;
    diagnostic_opening = token_position(&frame->look.token);
    if (compound_kind(&frame->look.token, &kind)) {
        node = parse_compound(frame, kind);
        if (node == NULL)
            return NULL;
        if (trailing_redirections(frame, node) == -1)
            goto failed;
        return node;
    }
    node = new_node(frame, CSH_AST_SIMPLE);
    if (node == NULL)
        return NULL;
    node->start = opening;
    for (;;) {
        struct csh_ast_word word = {0};
        int is_assignment, descriptor_candidate;
        result = peek_alias(frame, !command_name);
        if (result <= 0)
            break;
        if (redirection_kind(frame->look.token.kind)) {
            if (parse_redirection(frame, node, NULL) == -1)
                goto failed;
            prefix = 1;
            continue;
        }
        if (frame->look.token.kind != CSH_TOKEN_WORD)
            break;
        if (!command_name && !prefix && reserved(&frame->look.token)) {
            fail_at(frame, CSH_PARSE_ERROR, "unexpected reserved word", 0, position(frame));
            goto failed;
        }
        descriptor_candidate = io_number(&frame->look.token) &&
            csh_lexer_follows_redirection(frame->lexer);
        take(frame, &word);
        result = peek(frame);
        if (result < 0) {
            csh_ast_word_destroy(&word);
            goto failed;
        }
        if (!prefix && result > 0 && frame->look.token.kind == CSH_TOKEN_LPAREN) {
            struct csh_ast *function = parse_function(frame, &word);
            csh_ast_word_destroy(&word);
            csh_ast_destroy(node);
            return function;
        }
        if (descriptor_candidate && result > 0 && redirection_kind(frame->look.token.kind)) {
            if (parse_redirection(frame, node, &word) == -1) {
                csh_ast_word_destroy(&word);
                goto failed;
            }
            csh_ast_word_destroy(&word);
            prefix = 1;
            continue;
        }
        is_assignment = !command_name && assignment(&word.token);
        if (!is_assignment)
            command_name = 1;
        prefix = 1;
        node->end = word.token.end;
        if (csh_ast_add_word(node, &word, is_assignment, &error) == -1) {
            csh_ast_word_destroy(&word);
            adopt_error(frame, &error);
            goto failed;
        }
    }
    if (result < 0)
        goto failed;
    if (node->data.simple.word_count == 0 && node->redirection_count == 0) {
        fail_at(frame, CSH_PARSE_ERROR, "expected command", 0, diagnostic_opening);
        goto failed;
    }
    return node;
failed:
    csh_ast_destroy(node);
    return NULL;
}

static struct csh_ast *parse_pipeline(struct parse_frame *frame)
{
    struct csh_ast *pipeline = NULL, *command;
    struct csh_position opening = position(frame);
    struct csh_error error;
    int negated;
    int result = peek_alias(frame, 1);
    if (result < 0)
        return NULL;
    negated = result > 0 && plain_equal(&frame->look.token, "!");
    if (negated)
        discard(frame);
    command = parse_command(frame);
    if (command == NULL)
        return NULL;
    result = peek(frame);
    if (result < 0) {
        csh_ast_destroy(command);
        return NULL;
    }
    if (!negated && (result == 0 || frame->look.token.kind != CSH_TOKEN_PIPE))
        return command;
    pipeline = new_node(frame, CSH_AST_PIPELINE);
    if (pipeline == NULL) {
        csh_ast_destroy(command);
        return NULL;
    }
    pipeline->start = opening;
    pipeline->end = command->end;
    pipeline->data.pipeline.negated = negated;
    if (csh_ast_pipeline_add(pipeline, &command, &error) == -1) {
        adopt_error(frame, &error);
        goto failed;
    }
    while (result > 0 && frame->look.token.kind == CSH_TOKEN_PIPE) {
        struct csh_position pipe_position = token_position(&frame->look.token);
        discard(frame);
        result = skip_newlines(frame);
        if (result <= 0) {
            if (result == 0)
                fail_at(frame, CSH_PARSE_INCOMPLETE, "missing command after pipe", 0, pipe_position);
            goto failed;
        }
        command = parse_command(frame);
        if (command == NULL)
            goto failed;
        pipeline->end = command->end;
        if (csh_ast_pipeline_add(pipeline, &command, &error) == -1) {
            adopt_error(frame, &error);
            goto failed;
        }
        result = peek(frame);
        if (result < 0)
            goto failed;
    }
    return pipeline;
failed:
    csh_ast_destroy(command);
    csh_ast_destroy(pipeline);
    return NULL;
}

static struct csh_ast *parse_and_or(struct parse_frame *frame)
{
    struct csh_ast *left = parse_pipeline(frame);
    int result;
    if (left == NULL)
        return NULL;
    for (;;) {
        enum csh_ast_kind kind;
        struct csh_ast *node, *right;
        struct csh_position operator_position;
        result = peek(frame);
        if (result < 0)
            goto failed;
        if (result == 0 || (frame->look.token.kind != CSH_TOKEN_AND_IF &&
                            frame->look.token.kind != CSH_TOKEN_OR_IF))
            return left;
        kind = frame->look.token.kind == CSH_TOKEN_AND_IF ? CSH_AST_AND : CSH_AST_OR;
        operator_position = token_position(&frame->look.token);
        discard(frame);
        result = skip_newlines(frame);
        if (result <= 0) {
            if (result == 0)
                fail_at(frame, CSH_PARSE_INCOMPLETE, "missing command after and-or operator",
                    0, operator_position);
            goto failed;
        }
        right = parse_pipeline(frame);
        if (right == NULL)
            goto failed;
        node = new_node(frame, kind);
        if (node == NULL) {
            csh_ast_destroy(right);
            goto failed;
        }
        node->start = left->start;
        node->end = right->end;
        node->data.binary.left = left;
        node->data.binary.right = right;
        left = node;
    }
failed:
    csh_ast_destroy(left);
    return NULL;
}

static int at_close(struct parse_frame *frame, enum closing closing)
{
    const struct csh_token *token = &frame->look.token;
    if (!frame->has_look)
        return 0;
    switch (closing) {
    case CLOSE_PAREN: return token->kind == CSH_TOKEN_RPAREN;
    case CLOSE_BRACE: return plain_equal(token, "}");
    case CLOSE_THEN: return plain_equal(token, "then");
    case CLOSE_IF_BRANCH:
        return plain_equal(token, "elif") || plain_equal(token, "else") || plain_equal(token, "fi");
    case CLOSE_FI: return plain_equal(token, "fi");
    case CLOSE_DO: return plain_equal(token, "do");
    case CLOSE_DONE: return plain_equal(token, "done");
    case CLOSE_CASE:
        return token->kind == CSH_TOKEN_DSEMI || token->kind == CSH_TOKEN_SEMI_AND ||
            plain_equal(token, "esac");
    case CLOSE_NONE: return 0;
    }
    return 0;
}

/* Reserved closers immediately after a compound delimiter need no separator.
 * A redirect operand is not such a delimiter (POSIX grammar Rule 1). Operator
 * closers ')' and ';;'/';&' remain unambiguous after either form. */
static int ends_with_redirection(const struct csh_ast *node)
{
    while (node->kind == CSH_AST_AND || node->kind == CSH_AST_OR)
        node = node->data.binary.right;
    if (node->kind == CSH_AST_PIPELINE)
        node = node->data.pipeline.commands[node->data.pipeline.command_count - 1];
    return node->redirection_count != 0;
}

/* A nested list leaves its closing token in lookahead for the group or lexer
 * handshake. A root list stops immediately after the first complete newline. */
static struct csh_ast *parse_list(struct parse_frame *frame, enum closing closing,
    int allow_empty, struct csh_position opening)
{
    struct csh_ast *list = new_node(frame, CSH_AST_LIST);
    struct csh_error error;
    int result;
    if (list == NULL)
        return NULL;
    list->start = opening;
    list->end = opening;
    result = skip_newlines(frame);
    if (result < 0)
        goto failed;
    if (at_close(frame, closing)) {
        if (!allow_empty) {
            fail_at(frame, CSH_PARSE_ERROR, "empty command group", 0, position(frame));
            goto failed;
        }
        return list;
    }
    for (;;) {
        struct csh_ast_list_item item;
        memset(&item, 0, sizeof(item));
        if (result == 0) {
            if (closing != CLOSE_NONE) {
                fail_at(frame, CSH_PARSE_INCOMPLETE, "unterminated command group", 0, opening);
                goto failed;
            }
            break;
        }
        item.command = parse_and_or(frame);
        if (item.command == NULL)
            goto failed;
        if (list->data.list.item_count == 0)
            list->start = item.command->start;
        list->end = item.command->end;
        result = peek(frame);
        if (result < 0) {
            csh_ast_destroy(item.command);
            goto failed;
        }
        if (result > 0) {
            enum csh_token_kind kind = frame->look.token.kind;
            if (kind == CSH_TOKEN_SEMI || kind == CSH_TOKEN_AMPERSAND ||
                kind == CSH_TOKEN_NEWLINE) {
                item.separator = kind == CSH_TOKEN_SEMI ? CSH_AST_SEMI :
                    kind == CSH_TOKEN_AMPERSAND ? CSH_AST_AMPERSAND : CSH_AST_NEWLINE;
                item.separator_start = frame->look.token.start;
                item.separator_end = frame->look.token.end;
                list->end = item.separator_end;
            } else if (!at_close(frame, closing) ||
                (kind == CSH_TOKEN_WORD && ends_with_redirection(item.command))) {
                fail_at(frame, CSH_PARSE_ERROR, "expected command separator", 0, position(frame));
                csh_ast_destroy(item.command);
                goto failed;
            }
        }
        {
            enum csh_ast_separator separator = item.separator;
            if (csh_ast_list_add(list, &item, &error) == -1) {
                csh_ast_destroy(item.command);
                adopt_error(frame, &error);
                goto failed;
            }
            if (separator == CSH_AST_NEWLINE) {
                if (newline(frame) == -1)
                    goto failed;
                if (closing == CLOSE_NONE)
                    return list;
            } else if (separator == CSH_AST_SEMI || separator == CSH_AST_AMPERSAND)
                discard(frame);
            else {
                if (result == 0 && closing != CLOSE_NONE) {
                    fail_at(frame, CSH_PARSE_INCOMPLETE, "unterminated command group", 0, opening);
                    goto failed;
                }
                break;
            }
        }
        /* A semicolon followed by a newline ends the same complete command.
         * Never peek past this newline before returning a root tree. */
        result = peek_alias(frame, 1);
        if (result < 0)
            goto failed;
        if (closing == CLOSE_NONE && result > 0 &&
            frame->look.token.kind == CSH_TOKEN_NEWLINE) {
            list->end = frame->look.token.end;
            if (newline(frame) == -1)
                goto failed;
            return list;
        }
        if (closing != CLOSE_NONE) {
            result = skip_newlines(frame);
            if (result < 0)
                goto failed;
        }
        if (at_close(frame, closing))
            break;
    }
    if (closing == CLOSE_NONE && frame->document_count != 0) {
        fail_at(frame, CSH_PARSE_INCOMPLETE, "here-document requires a following newline",
            0, token_position(&frame->documents[0]->operand.token));
        goto failed;
    }
    return list;
failed:
    csh_ast_destroy(list);
    return NULL;
}

int csh_parser_create(struct csh_parser **out, struct csh_input *input,
    struct csh_error *error)
{
    struct csh_parser *parser;
    *out = NULL;
    memset(error, 0, sizeof(*error));
    if (input == NULL || csh_input_position(input).offset != 0) {
        error->message = input == NULL ? "invalid parser input" :
            "parser requires an unread input source";
        error->system_errno = EINVAL;
        error->status = 1;
        error->position.line = error->position.column = 1;
        return -1;
    }
    parser = calloc(1, sizeof(*parser));
    if (parser == NULL) {
        error->message = "cannot allocate parser";
        error->system_errno = ENOMEM;
        error->status = 1;
        error->position.line = error->position.column = 1;
        return -1;
    }
    parser->input = input;
    if (csh_lexer_create(&parser->lexer, csh_input_name(input), error) == -1) {
        free(parser);
        return -1;
    }
    *out = parser;
    return 0;
}

void csh_parser_set_aliases(struct csh_parser *parser,
    const struct csh_aliases *aliases)
{
    parser->aliases = aliases;
}

void csh_parser_destroy(struct csh_parser *parser)
{
    if (parser == NULL)
        return;
    csh_lexer_destroy(parser->lexer);
    free(parser);
}

void csh_parser_set_read_hook(struct csh_parser *parser,
    void (*before_read)(void *, int), void *context)
{
    parser->before_read = before_read;
    parser->read_context = context;
}

const char *csh_parser_source_name(const struct csh_parser *parser)
{
    return csh_input_name(parser->input);
}

enum csh_parse_result csh_parser_next(struct csh_parser *parser,
    struct csh_ast **out, struct csh_error *error)
{
    struct parse_frame frame;
    int result;
    *out = NULL;
    memset(error, 0, sizeof(*error));
    if (parser->failure.message != NULL) {
        *error = parser->failure;
        return parser->failure_result;
    }
    if (parser->eof)
        return CSH_PARSE_EOF;
    memset(&frame, 0, sizeof(frame));
    frame.parser = parser;
    frame.lexer = parser->lexer;
    /* Leading blank/comment lines start another primary prompt. Newlines
     * consumed inside parse_list retain the continuation prompt instead. */
    parser->continuation = 0;
    while ((result = peek_alias(&frame, 1)) > 0 &&
           frame.look.token.kind == CSH_TOKEN_NEWLINE) {
        if (newline(&frame) == -1) { result = -1; break; }
        parser->continuation = 0;
    }
    if (result == 0) {
        parser->eof = 1;
        frame_destroy(&frame);
        return CSH_PARSE_EOF;
    }
    if (result > 0)
        *out = parse_list(&frame, CLOSE_NONE, 0, position(&frame));
    frame_destroy(&frame);
    if (*out != NULL)
        return CSH_PARSE_TREE;
    csh_lexer_destroy(parser->lexer);
    parser->lexer = NULL;
    *error = parser->failure;
    return parser->failure_result;
}

int csh_parser_document(const void *bytes, size_t length,
    struct csh_ast_word *out, struct csh_error *error)
{
    struct csh_parser parser = {0};
    struct parse_frame frame = {0};
    int rc = -1, read;
    memset(out, 0, sizeof(*out));
    memset(error, 0, sizeof(*error));
    if (csh_lexer_create(&parser.lexer, "here-document", error) == -1) return -1;
    parser.final = 1;
    frame.parser = &parser;
    frame.lexer = parser.lexer;
    csh_lexer_document(parser.lexer);
    if (csh_lexer_feed(parser.lexer, bytes, length, 1, error) == -1) goto done;
    read = peek_raw(&frame);
    if (read == -1) { *error = parser.failure; goto done; }
    if (read == 0) {
        out->token.kind = CSH_TOKEN_WORD;
        out->token.raw = calloc(1, 1);
        if (out->token.raw == NULL) {
            error->message = "cannot allocate here-document word";
            error->system_errno = ENOMEM;
            error->status = 1;
            goto done;
        }
    } else take(&frame, out);
    rc = 0;
done:
    frame_destroy(&frame);
    csh_lexer_destroy(parser.lexer);
    return rc;
}
