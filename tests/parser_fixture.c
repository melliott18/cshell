/* Replacement API fixture. Input is parsed and inspected, never executed. */
#include "cshell/parser.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void require(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "fixture assertion failed: %s\n", message);
        exit(90);
    }
}

static void json_bytes(const unsigned char *value, size_t length)
{
    size_t index;
    putchar('"');
    for (index = 0; index < length; ++index) {
        unsigned char byte = value[index];
        if (byte == '"' || byte == '\\') {
            putchar('\\');
            putchar(byte);
        } else if (byte < 32 || byte > 126)
            printf("\\u%04x", (unsigned int)byte);
        else
            putchar(byte);
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

static void json_token(const struct csh_token *token)
{
    size_t index;
    fputs("{\"raw\":", stdout);
    json_bytes(token->raw, token->length);
    fputs(",\"source\":", stdout);
    json_string(token->source_name);
    fputs(",\"start\":", stdout);
    json_position(token->start);
    fputs(",\"end\":", stdout);
    json_position(token->end);
    fputs(",\"fragments\":[", stdout);
    for (index = 0; index < token->fragment_count; ++index) {
        const struct csh_fragment *fragment = &token->fragments[index];
        if (index != 0)
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
        printf(",\"begin\":%zu,\"end\":%zu,\"start\":", fragment->begin, fragment->end);
        json_position(fragment->start);
        fputs(",\"finish\":", stdout);
        json_position(fragment->finish);
        putchar('}');
    }
    fputs("]}", stdout);
}

static void json_tree(const struct csh_ast *tree);

static void json_word(const struct csh_ast_word *word)
{
    size_t index;
    fputs("{\"token\":", stdout);
    json_token(&word->token);
    fputs(",\"substitutions\":[", stdout);
    for (index = 0; index < word->substitution_count; ++index) {
        const struct csh_ast_substitution *sub = &word->substitutions[index];
        if (index != 0)
            putchar(',');
        printf("{\"fragment\":%zu,\"begin\":%zu,\"end\":%zu,\"body\":",
            sub->fragment_index, sub->begin, sub->end);
        json_tree(sub->body);
        putchar('}');
    }
    fputs("]}", stdout);
}

static void json_redirection(const struct csh_ast_redirection *redirection)
{
    fputs("{\"operator\":", stdout);
    json_string(csh_token_kind_name(redirection->operator_kind));
    fputs(",\"start\":", stdout);
    json_position(redirection->start);
    fputs(",\"end\":", stdout);
    json_position(redirection->end);
    fputs(",\"io_number\":", stdout);
    if (redirection->has_io_number)
        json_token(&redirection->io_number);
    else
        fputs("null", stdout);
    fputs(",\"operand\":", stdout);
    json_word(&redirection->operand);
    fputs(",\"delimiter\":", stdout);
    if (redirection->delimiter != NULL)
        json_bytes(redirection->delimiter, redirection->delimiter_length);
    else
        fputs("null", stdout);
    printf(",\"quoted\":%s,\"body\":", redirection->delimiter_quoted ? "true" : "false");
    if (redirection->body != NULL)
        json_bytes(redirection->body, redirection->body_length);
    else
        fputs("null", stdout);
    fputs(",\"body_start\":", stdout);
    json_position(redirection->body_start);
    fputs(",\"body_end\":", stdout);
    json_position(redirection->body_end);
    putchar('}');
}

static const char *separator_name(enum csh_ast_separator separator)
{
    switch (separator) {
    case CSH_AST_END: return "end";
    case CSH_AST_SEMI: return "semi";
    case CSH_AST_AMPERSAND: return "ampersand";
    case CSH_AST_NEWLINE: return "newline";
    }
    return "invalid";
}

static const char *case_terminator_name(enum csh_ast_case_terminator terminator)
{
    switch (terminator) {
    case CSH_AST_CASE_END: return "end";
    case CSH_AST_CASE_BREAK: return "break";
    case CSH_AST_CASE_FALLTHROUGH: return "fallthrough";
    }
    return "invalid";
}

static void json_word_vector(const struct csh_ast_word_vector *words)
{
    size_t index;
    putchar('[');
    for (index = 0; index < words->count; ++index) {
        if (index != 0)
            putchar(',');
        json_word(&words->items[index]);
    }
    putchar(']');
}

static void json_tree(const struct csh_ast *tree)
{
    size_t index;
    if (tree == NULL) {
        fputs("null", stdout);
        return;
    }
    fputs("{\"kind\":", stdout);
    json_string(csh_ast_kind_name(tree->kind));
    fputs(",\"start\":", stdout);
    json_position(tree->start);
    fputs(",\"end\":", stdout);
    json_position(tree->end);
    fputs(",\"redirections\":[", stdout);
    for (index = 0; index < tree->redirection_count; ++index) {
        if (index != 0)
            putchar(',');
        json_redirection(tree->redirections[index]);
    }
    putchar(']');
    switch (tree->kind) {
    case CSH_AST_SIMPLE:
        fputs(",\"words\":[", stdout);
        for (index = 0; index < tree->data.simple.word_count; ++index) {
            const struct csh_ast_command_word *word = &tree->data.simple.words[index];
            if (index != 0)
                putchar(',');
            printf("{\"assignment\":%s,\"word\":", word->assignment ? "true" : "false");
            json_word(&word->word);
            putchar('}');
        }
        putchar(']');
        break;
    case CSH_AST_PIPELINE:
        printf(",\"negated\":%s,\"commands\":[", tree->data.pipeline.negated ? "true" : "false");
        for (index = 0; index < tree->data.pipeline.command_count; ++index) {
            if (index != 0)
                putchar(',');
            json_tree(tree->data.pipeline.commands[index]);
        }
        putchar(']');
        break;
    case CSH_AST_AND:
    case CSH_AST_OR:
        fputs(",\"left\":", stdout);
        json_tree(tree->data.binary.left);
        fputs(",\"right\":", stdout);
        json_tree(tree->data.binary.right);
        break;
    case CSH_AST_LIST:
        fputs(",\"items\":[", stdout);
        for (index = 0; index < tree->data.list.item_count; ++index) {
            const struct csh_ast_list_item *item = &tree->data.list.items[index];
            if (index != 0)
                putchar(',');
            fputs("{\"separator\":", stdout);
            json_string(separator_name(item->separator));
            fputs(",\"separator_start\":", stdout);
            json_position(item->separator_start);
            fputs(",\"separator_end\":", stdout);
            json_position(item->separator_end);
            fputs(",\"command\":", stdout);
            json_tree(item->command);
            putchar('}');
        }
        putchar(']');
        break;
    case CSH_AST_SUBSHELL:
    case CSH_AST_BRACE:
        fputs(",\"body\":", stdout);
        json_tree(tree->data.group.body);
        break;
    case CSH_AST_IF:
        fputs(",\"branches\":[", stdout);
        for (index = 0; index < tree->data.if_clause.branch_count; ++index) {
            const struct csh_ast_if_branch *branch = &tree->data.if_clause.branches[index];
            if (index != 0)
                putchar(',');
            fputs("{\"condition\":", stdout);
            json_tree(branch->condition);
            fputs(",\"body\":", stdout);
            json_tree(branch->body);
            putchar('}');
        }
        fputs("],\"else_body\":", stdout);
        json_tree(tree->data.if_clause.else_body);
        break;
    case CSH_AST_FOR:
        fputs(",\"name\":", stdout);
        json_word(&tree->data.for_clause.name);
        fputs(",\"words\":", stdout);
        json_word_vector(&tree->data.for_clause.words);
        printf(",\"has_in\":%s,\"body\":", tree->data.for_clause.has_in ? "true" : "false");
        json_tree(tree->data.for_clause.body);
        break;
    case CSH_AST_WHILE:
    case CSH_AST_UNTIL:
        fputs(",\"condition\":", stdout);
        json_tree(tree->data.loop.condition);
        fputs(",\"body\":", stdout);
        json_tree(tree->data.loop.body);
        break;
    case CSH_AST_CASE:
        fputs(",\"word\":", stdout);
        json_word(&tree->data.case_clause.word);
        fputs(",\"items\":[", stdout);
        for (index = 0; index < tree->data.case_clause.item_count; ++index) {
            const struct csh_ast_case_item *item = &tree->data.case_clause.items[index];
            if (index != 0)
                putchar(',');
            fputs("{\"patterns\":", stdout);
            json_word_vector(&item->patterns);
            fputs(",\"body\":", stdout);
            json_tree(item->body);
            fputs(",\"terminator\":", stdout);
            json_string(case_terminator_name(item->terminator));
            fputs(",\"terminator_start\":", stdout);
            json_position(item->terminator_start);
            fputs(",\"terminator_end\":", stdout);
            json_position(item->terminator_end);
            putchar('}');
        }
        putchar(']');
        break;
    case CSH_AST_FUNCTION:
        fputs(",\"name\":", stdout);
        json_word(&tree->data.function.name);
        fputs(",\"body\":", stdout);
        json_tree(tree->data.function.body);
        break;
    default:
        require(0, "parser published unsupported AST kind");
    }
    putchar('}');
}

static void check_repeat(struct csh_parser *parser, enum csh_parse_result result,
    const struct csh_error *first)
{
    int repeat;
    for (repeat = 0; repeat < 3; ++repeat) {
        struct csh_ast *tree = NULL;
        struct csh_error error;
        require(csh_parser_next(parser, &tree, &error) == result && tree == NULL,
            "terminal parse result is sticky and has no tree");
        require(error.message == first->message && error.system_errno == first->system_errno &&
            error.status == first->status && error.position.offset == first->position.offset,
            "terminal parse diagnostic is stable");
    }
}

static void parse_stdin(void)
{
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *saved = NULL;
    struct csh_error error;
    enum csh_parse_result result;
    size_t count = 0;
    require(csh_input_from_fd(&input, STDIN_FILENO, "fixture-source", &error) == 0,
        "input construction");
    require(csh_parser_create(&parser, input, &error) == 0, "parser construction");
    require(strcmp(csh_parser_source_name(parser), "fixture-source") == 0, "source name");
    fputs("{\"trees\":[", stdout);
    for (;;) {
        struct csh_ast *tree = NULL;
        result = csh_parser_next(parser, &tree, &error);
        if (result != CSH_PARSE_TREE) {
            require(tree == NULL, "failed or EOF parse publishes no tree");
            break;
        }
        require(tree != NULL, "successful parse publishes a tree");
        if (count++ != 0)
            putchar(',');
        json_tree(tree);
        csh_ast_destroy(saved);
        saved = tree;
    }
    check_repeat(parser, result, &error);
    fputs("],\"result\":", stdout);
    json_string(result == CSH_PARSE_EOF ? "eof" :
        result == CSH_PARSE_INCOMPLETE ? "incomplete" : "error");
    fputs(",\"input_position\":", stdout);
    json_position(csh_input_position(input));
    fputs(",\"error\":", stdout);
    if (result == CSH_PARSE_EOF)
        fputs("null", stdout);
    else {
        fputs("{\"message\":", stdout);
        json_string(error.message);
        printf(",\"errno\":%d,\"status\":%d,\"position\":", error.system_errno, error.status);
        json_position(error.position);
        putchar('}');
    }
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    /* A published tree owns its tokens and all children after the providers die. */
    csh_ast_destroy(saved);
    fputs(",\"repeats\":3}\n", stdout);
}

static void boundary(const char *source, size_t consumed)
{
    int descriptors[2];
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *tree = NULL;
    struct csh_error error;
    char remainder[128];
    size_t remaining = strlen(source) - consumed;
    require(remaining < sizeof(remainder), "boundary fixture capacity");
    require(pipe(descriptors) == 0, "pipe");
    require(write(descriptors[1], source, strlen(source)) == (ssize_t)strlen(source), "pipe write");
    /* Keep the writer open: premature read-ahead also causes a bounded runner timeout. */
    require(csh_input_from_fd(&input, descriptors[0], "boundary", &error) == 0, "pipe input");
    require(csh_parser_create(&parser, input, &error) == 0, "pipe parser");
    require(csh_parser_next(parser, &tree, &error) == CSH_PARSE_TREE, "complete command before EOF");
    require(csh_input_position(input).offset == consumed, "complete command has no input read-ahead");
    require(read(descriptors[0], remainder, remaining) == (ssize_t)remaining, "next command remains on descriptor");
    require(memcmp(remainder, source + consumed, remaining) == 0, "unread bytes preserved");
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    csh_ast_destroy(tree);
    require(close(descriptors[0]) == 0 && close(descriptors[1]) == 0, "pipe close");
}

static void contracts(void)
{
    const char *simple = "first\nsecond\n";
    const char *list = "first; second &\nthird\n";
    const char *continued = "first |\nsecond &&\nthird\nfourth\n";
    const char *heredocs = "cat <<A <<-'B'\none\nA\n\t$two\n\tB\ntrailing\n";
    const char *conditional = "if condition\nthen body\nelse other\nfi\ntrailing\n";
    const char *function = "worker()\n{ cat <<END\nbody\nEND\n}\ntrailing\n";
    boundary(simple, strlen(simple) - strlen("second\n"));
    boundary(list, strlen(list) - strlen("third\n"));
    boundary(continued, strlen(continued) - strlen("fourth\n"));
    boundary(heredocs, strlen(heredocs) - strlen("trailing\n"));
    boundary(conditional, strlen(conditional) - strlen("trailing\n"));
    boundary(function, strlen(function) - strlen("trailing\n"));
    {
        const char *replay[] = {
            "echo $((echo hi); )\ntrailing\n",
            "echo $((echo $(cat <<END\ninside\nEND\n)); )\ntrailing\n",
            "echo $((cat <<END\n$(|)\nEND\n))\ntrailing\n"
        };
        size_t index;
        for (index = 0; index < sizeof(replay) / sizeof(replay[0]); ++index)
            boundary(replay[index], strlen(replay[index]) - strlen("trailing\n"));
    }
    puts("ok");
}

static void chain(void)
{
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *tree = NULL;
    struct csh_ast *node;
    struct csh_error error;
    size_t count = 1;
    require(csh_input_from_fd(&input, STDIN_FILENO, "chain", &error) == 0, "chain input");
    require(csh_parser_create(&parser, input, &error) == 0, "chain parser");
    require(csh_parser_next(parser, &tree, &error) == CSH_PARSE_TREE, "chain tree");
    require(tree->kind == CSH_AST_LIST && tree->data.list.item_count == 1, "chain list");
    node = tree->data.list.items[0].command;
    while (node->kind == CSH_AST_AND || node->kind == CSH_AST_OR) {
        require(node->data.binary.right->kind == CSH_AST_SIMPLE, "left associative chain");
        ++count;
        node = node->data.binary.left;
    }
    require(node->kind == CSH_AST_SIMPLE, "chain starts in simple command");
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    csh_ast_destroy(tree);
    printf("%zu\n", count);
}

static void consumed_input(void)
{
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_input_line line;
    struct csh_error error;
    require(csh_input_from_string(&input, "before\nafter\n", "consumed", &error) == 0, "consumed input");
    require(csh_input_read_line(input, &line, &error) == CSH_INPUT_LINE, "consume one line");
    require(csh_parser_create(&parser, input, &error) == -1 && parser == NULL,
        "parser rejects input whose source position is no longer initial");
    require(error.system_errno == EINVAL && error.status != 0 && error.message != NULL,
        "consumed source diagnostic");
    csh_input_destroy(input);
    puts("ok");
}

static void read_failure(void)
{
    int descriptors[2];
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *tree = NULL;
    struct csh_error error;
    require(pipe(descriptors) == 0, "read-failure pipe");
    require(csh_input_from_fd(&input, descriptors[1], "write-only-input", &error) == 0,
        "retain write-only pipe descriptor");
    require(csh_parser_create(&parser, input, &error) == 0, "read-failure parser");
    require(csh_parser_next(parser, &tree, &error) == CSH_PARSE_ERROR && tree == NULL,
        "input read failure is a parse error with no published tree");
    require(error.system_errno == EBADF && error.status != 0 && error.message != NULL,
        "underlying read diagnostic survives parser handoff");
    require(error.position.offset == 0 && error.position.line == 1 && error.position.column == 1,
        "read-failure source position");
    check_repeat(parser, CSH_PARSE_ERROR, &error);
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    require(close(descriptors[0]) == 0 && close(descriptors[1]) == 0,
        "borrowed pipe descriptors remain open");
    puts("ok");
}

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "parse") == 0)
        parse_stdin();
    else if (argc == 2 && strcmp(argv[1], "contracts") == 0)
        contracts();
    else if (argc == 2 && strcmp(argv[1], "chain") == 0)
        chain();
    else if (argc == 2 && strcmp(argv[1], "consumed") == 0)
        consumed_input();
    else if (argc == 2 && strcmp(argv[1], "read-failure") == 0)
        read_failure();
    else {
        fputs("usage: parser_fixture parse|contracts|chain|consumed|read-failure\n", stderr);
        return 2;
    }
    return 0;
}
