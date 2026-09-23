/* Replacement-only lexer driver. Its tiny command-substitution recognizer
 * counts subshell parentheses; it deliberately does not implement shell
 * grammar. Explicit handoff checks below supply case/here-document decisions. */
#include "cshell/lexer.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FRAMES 4096

static void require(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "fixture assertion failed: %s\n", message);
        exit(90);
    }
}

static void json_bytes(const unsigned char *value, size_t length)
{
    size_t i;
    putchar('"');
    for (i = 0; i < length; ++i) {
        unsigned char byte = value[i];
        if (byte == '"' || byte == '\\') {
            putchar('\\');
            putchar(byte);
        } else if (byte < 32 || byte > 126) {
            printf("\\u%04x", (unsigned int)byte);
        } else {
            putchar(byte);
        }
    }
    putchar('"');
}

static void json_string(const char *value)
{
    if (value == NULL)
        fputs("null", stdout);
    else
        json_bytes((const unsigned char *)value, strlen(value));
}

static void json_position(struct csh_position position)
{
    printf("[%zu,%zu,%zu]", position.offset, position.line, position.column);
}

static void json_error(const struct csh_error *error)
{
    fputs("{\"message\":", stdout);
    json_string(error->message);
    printf(",\"errno\":%d,\"status\":%d,\"position\":",
        error->system_errno, error->status);
    json_position(error->position);
    putchar('}');
}

static void json_token(const struct csh_token *token)
{
    size_t i;
    fputs("{\"kind\":", stdout);
    json_string(csh_token_kind_name(token->kind));
    fputs(",\"source\":", stdout);
    json_string(token->source_name);
    fputs(",\"raw\":", stdout);
    json_bytes(token->raw, token->length);
    fputs(",\"start\":", stdout);
    json_position(token->start);
    fputs(",\"end\":", stdout);
    json_position(token->end);
    fputs(",\"fragments\":[", stdout);
    for (i = 0; i < token->fragment_count; ++i) {
        const struct csh_fragment *fragment = &token->fragments[i];
        if (i != 0)
            putchar(',');
        fputs("{\"kind\":", stdout);
        json_string(csh_fragment_kind_name(fragment->kind));
        fputs(",\"quote\":", stdout);
        json_string(csh_quote_name(fragment->quote));
        fputs(",\"parent\":", stdout);
        if (fragment->parent == CSH_FRAGMENT_ROOT)
            fputs("null", stdout);
        else
            printf("%zu", fragment->parent);
        printf(",\"begin\":%zu,\"end\":%zu,\"start\":",
            fragment->begin, fragment->end);
        json_position(fragment->start);
        fputs(",\"finish\":", stdout);
        json_position(fragment->finish);
        putchar('}');
    }
    fputs("]}", stdout);
}

static void check_clear(const struct csh_token *token)
{
    require(token->raw == NULL && token->length == 0 &&
        token->source_name == NULL && token->fragments == NULL &&
        token->fragment_count == 0, "non-token result clears token");
}

static void check_sticky(struct csh_lexer *lexer, struct csh_error first)
{
    int i;
    for (i = 0; i < 3; ++i) {
        struct csh_token token = {0};
        struct csh_error repeated;
        require(csh_lexer_next(lexer, &token, &repeated) == CSH_LEX_ERROR,
            "lexical errors are sticky");
        check_clear(&token);
        require(repeated.message == first.message &&
            repeated.system_errno == first.system_errno &&
            repeated.status == first.status &&
            repeated.position.offset == first.position.offset,
            "sticky diagnostic is stable");
    }
}

static unsigned char *read_stdin(size_t *length)
{
    size_t capacity = 4096;
    unsigned char *data = malloc(capacity);
    require(data != NULL, "allocate fixture input");
    *length = 0;
    for (;;) {
        size_t count;
        if (*length == capacity) {
            unsigned char *grown;
            capacity *= 2;
            grown = realloc(data, capacity);
            require(grown != NULL, "grow fixture input");
            data = grown;
        }
        count = fread(data + *length, 1, capacity - *length, stdin);
        *length += count;
        if (count == 0) {
            require(!ferror(stdin), "read fixture input");
            return data;
        }
    }
}

static int scan(const char *mode)
{
    struct frame {
        struct csh_lexer *lexer;
        size_t parentheses;
    } frames[MAX_FRAMES];
    struct csh_error error;
    size_t length, fed = 0, depth = 0, emitted = 0, commands = 0;
    unsigned char *data = read_stdin(&length);
    int ended = 0;
    require(strcmp(mode, "full") == 0 || strcmp(mode, "line") == 0 ||
        strcmp(mode, "byte") == 0, "known feed mode");
    require(csh_lexer_create(&frames[0].lexer, "fixture-source", &error) == 0,
        "create lexer");
    frames[0].parentheses = 0;
    fputs("{\"tokens\":[", stdout);
    for (;;) {
        struct csh_token token = {0};
        struct csh_lexer *active = frames[depth].lexer;
        enum csh_lex_result result = csh_lexer_next(active, &token, &error);
        if (result == CSH_LEX_TOKEN) {
            require(error.message == NULL && error.status == 0 &&
                error.system_errno == 0, "successful scan clears diagnostic");
            if (depth == 0) {
                if (emitted++ != 0)
                    putchar(',');
                json_token(&token);
            } else if (token.kind == CSH_TOKEN_LPAREN) {
                ++frames[depth].parentheses;
            } else if (token.kind == CSH_TOKEN_RPAREN) {
                if (frames[depth].parentheses != 0) {
                    --frames[depth].parentheses;
                } else {
                    require(csh_lexer_command_end(frames[depth - 1].lexer,
                        active, &token, &error) == 0, "close child command");
                    --depth;
                }
            }
            csh_token_destroy(&token);
            check_clear(&token);
        } else if (result == CSH_LEX_COMMAND) {
            check_clear(&token);
            require(depth + 1 < MAX_FRAMES, "bounded mini-parser nesting");
            require(csh_lexer_command_begin(active, &frames[depth + 1].lexer,
                &error) == 0, "begin child command");
            ++depth;
            ++commands;
            frames[depth].parentheses = 0;
        } else if (result == CSH_LEX_MORE) {
            size_t count = length - fed;
            check_clear(&token);
            require(!ended, "final source never requests more bytes");
            if (strcmp(mode, "byte") == 0 && count > 1)
                count = 1;
            else if (strcmp(mode, "line") == 0 && count != 0) {
                unsigned char *newline = memchr(data + fed, '\n', count);
                if (newline != NULL)
                    count = (size_t)(newline - data - fed) + 1;
            }
            ended = fed + count == length;
            if (csh_lexer_feed(frames[0].lexer, data + fed, count, ended,
                &error) != 0) {
                check_sticky(active, error);
                fputs("],\"error\":", stdout);
                json_error(&error);
                printf(",\"commands\":%zu,\"eof_repeats\":0}\n", commands);
                break;
            }
            fed += count;
        } else if (result == CSH_LEX_ERROR) {
            check_clear(&token);
            check_sticky(active, error);
            fputs("],\"error\":", stdout);
            json_error(&error);
            printf(",\"commands\":%zu,\"eof_repeats\":0}\n", commands);
            break;
        } else {
            int repeat;
            check_clear(&token);
            require(result == CSH_LEX_EOF && depth == 0,
                "only complete root reaches EOF");
            for (repeat = 0; repeat < 3; ++repeat) {
                require(csh_lexer_next(active, &token, &error) == CSH_LEX_EOF,
                    "repeat EOF");
                check_clear(&token);
            }
            printf("],\"error\":null,\"commands\":%zu,\"eof_repeats\":3}\n",
                commands);
            break;
        }
    }
    csh_lexer_destroy(frames[0].lexer);
    free(data);
    return 0;
}

static void next_kind(struct csh_lexer *lexer, enum csh_token_kind kind,
    struct csh_token *token)
{
    struct csh_error error;
    require(csh_lexer_next(lexer, token, &error) == CSH_LEX_TOKEN &&
        token->kind == kind, "explicit grammar receives expected token");
}

static void discard_kind(struct csh_lexer *lexer, enum csh_token_kind kind)
{
    struct csh_token token = {0};
    next_kind(lexer, kind, &token);
    csh_token_destroy(&token);
}

static void handoff_case(void)
{
    const char source[] = "$(case x in x) echo yes;; esac)tail";
    struct csh_lexer *root, *child;
    struct csh_token token = {0};
    struct csh_error error;
    size_t i;
    require(csh_lexer_create(&root, "case", &error) == 0, "create case lexer");
    require(csh_lexer_feed(root, source, sizeof(source) - 1, 1, &error) == 0,
        "feed case");
    require(csh_lexer_next(root, &token, &error) == CSH_LEX_COMMAND,
        "case requests parser handoff");
    require(csh_lexer_command_begin(root, &child, &error) == 0, "begin case");
    for (i = 0; i < 4; ++i)
        discard_kind(child, CSH_TOKEN_WORD);
    /* A parser knows this is a case-pattern delimiter, so it does not call
     * command_end. Parenthesis counting alone would incorrectly end here. */
    discard_kind(child, CSH_TOKEN_RPAREN);
    discard_kind(child, CSH_TOKEN_WORD);
    discard_kind(child, CSH_TOKEN_WORD);
    discard_kind(child, CSH_TOKEN_DSEMI);
    discard_kind(child, CSH_TOKEN_WORD);
    next_kind(child, CSH_TOKEN_RPAREN, &token);
    require(csh_lexer_command_end(root, child, &token, &error) == 0,
        "grammar selects substitution's closing parenthesis");
    csh_token_destroy(&token);
    next_kind(root, CSH_TOKEN_WORD, &token);
    require(token.length == sizeof(source) - 1 &&
        memcmp(token.raw, source, token.length) == 0,
        "case parentheses retained within one substitution word");
    csh_token_destroy(&token);
    require(csh_lexer_next(root, &token, &error) == CSH_LEX_EOF, "case EOF");
    csh_lexer_destroy(root);
}

static void handoff_heredoc(void)
{
    const char prefix[] = "$(cat <<EOF\n";
    const char body[] = "body ) \" ${\nEOF\n";
    const char suffix[] = ")tail";
    struct csh_lexer *root, *child;
    struct csh_token token = {0};
    struct csh_error error;
    struct csh_position position;
    const unsigned char *pending;
    size_t length;
    int final;
    require(csh_lexer_create(&root, "heredoc", &error) == 0, "create heredoc");
    require(csh_lexer_feed(root, prefix, sizeof(prefix) - 1, 0, &error) == 0,
        "feed heredoc header only");
    require(csh_lexer_next(root, &token, &error) == CSH_LEX_COMMAND,
        "heredoc requests parser handoff");
    require(csh_lexer_command_begin(root, &child, &error) == 0, "begin heredoc");
    discard_kind(child, CSH_TOKEN_WORD);
    discard_kind(child, CSH_TOKEN_DLESS);
    discard_kind(child, CSH_TOKEN_WORD);
    discard_kind(child, CSH_TOKEN_NEWLINE);
    (void)csh_lexer_pending(child, &length, &position, &final);
    require(length == 0 && !final && position.line == 2,
        "newline leaves heredoc body unacquired");
    require(csh_lexer_feed(root, body, sizeof(body) - 1, 0, &error) == 0,
        "parser acquires raw heredoc lines");
    pending = csh_lexer_pending(child, &length, &position, &final);
    require(length == sizeof(body) - 1 && !final &&
        memcmp(pending, body, length) == 0, "parser sees exact raw body");
    require(csh_lexer_skip_raw(child, length, &error) == 0,
        "parser skips body and matching delimiter without lexing");
    require(csh_lexer_feed(root, suffix, sizeof(suffix) - 1, 1, &error) == 0,
        "feed true substitution close");
    next_kind(child, CSH_TOKEN_RPAREN, &token);
    require(token.start.line == 4 && token.start.column == 1,
        "raw skip advances physical source position");
    require(csh_lexer_command_end(root, child, &token, &error) == 0,
        "only grammar-selected close ends heredoc substitution");
    csh_token_destroy(&token);
    next_kind(root, CSH_TOKEN_WORD, &token);
    require(token.length == sizeof(prefix) + sizeof(body) + sizeof(suffix) - 3 &&
        memcmp(token.raw, prefix, sizeof(prefix) - 1) == 0 &&
        memcmp(token.raw + sizeof(prefix) - 1, body, sizeof(body) - 1) == 0,
        "command fragment preserves raw heredoc");
    csh_token_destroy(&token);
    csh_lexer_destroy(root);
}

static void ownership(void)
{
    char source[] = "a''\"b\"";
    char name[] = "owned-source";
    struct csh_lexer *lexer;
    struct csh_token token = {0};
    struct csh_error error;
    require(csh_lexer_create(&lexer, name, &error) == 0, "create owned lexer");
    require(csh_lexer_feed(lexer, source, sizeof(source) - 1, 1, &error) == 0,
        "feed owned bytes");
    memset(source, '#', sizeof(source) - 1);
    memset(name, '#', sizeof(name) - 1);
    next_kind(lexer, CSH_TOKEN_WORD, &token);
    csh_lexer_destroy(lexer);
    require(strcmp(token.source_name, "owned-source") == 0 &&
        token.length == 6 && memcmp(token.raw, "a''\"b\"", 6) == 0 &&
        token.fragment_count >= 3, "token survives source and lexer destruction");
    csh_token_destroy(&token);
    csh_token_destroy(&token);
    check_clear(&token);
    csh_lexer_destroy(NULL);
}

static void contexts(void)
{
    const char *samples[] = {"'abc", "\"abc", "$'abc", "${abc", "$((1+2", "`abc", "abc\\"};
    size_t i;
    for (i = 0; i < sizeof(samples) / sizeof(samples[0]); ++i) {
        struct csh_lexer *lexer;
        struct csh_token token = {0};
        struct csh_error error;
        struct csh_position opening;
        const char *context = NULL;
        require(csh_lexer_create(&lexer, "context", &error) == 0, "create context");
        require(csh_lexer_feed(lexer, samples[i], strlen(samples[i]), 0, &error) == 0,
            "feed incomplete context");
        require(csh_lexer_next(lexer, &token, &error) == CSH_LEX_MORE,
            "incomplete context requests more input");
        require(csh_lexer_context(lexer, &context, &opening) == 1 &&
            context != NULL && opening.line == 1 && opening.column >= 1,
            "report opening context for secondary input policy");
        require(csh_lexer_feed(lexer, NULL, 0, 1, &error) == 0, "mark final EOF");
        require(csh_lexer_next(lexer, &token, &error) == CSH_LEX_ERROR &&
            error.status == 2 && error.message != NULL,
            "EOF of incomplete context is syntax error");
        require(error.position.offset == opening.offset,
            "EOF diagnostic points at reported opening context");
        csh_lexer_destroy(lexer);
    }
}

int main(int argc, char **argv)
{
    require(argc >= 2, "fixture subcommand required");
    if (strcmp(argv[1], "scan") == 0) {
        require(argc == 3, "scan feed mode required");
        return scan(argv[2]);
    }
    require(strcmp(argv[1], "contracts") == 0, "known fixture subcommand");
    ownership();
    contexts();
    handoff_case();
    handoff_heredoc();
    puts("ok");
    return 0;
}
