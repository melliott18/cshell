/* Structural alias tests use the replacement parser without executing input. */
#include "cshell/alias.h"
#include "cshell/parser.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *current_case;

static void check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "alias parser: %s: %s\n", current_case, message);
        exit(1);
    }
}

static struct csh_aliases *aliases(void)
{
    struct csh_aliases *table = NULL;
    struct csh_error error;
    check(csh_aliases_create(&table, &error) == 0, "create alias table");
    return table;
}

static void set(struct csh_aliases *table, const char *name, const char *value)
{
    struct csh_error error;
    check(csh_aliases_set(table, name, value, &error) == 0, "set alias");
}

static struct csh_parser *parser(const char *source,
    const struct csh_aliases *table, struct csh_input **input)
{
    struct csh_parser *result = NULL;
    struct csh_error error;
    check(csh_input_from_string(input, source, "alias-parser", &error) == 0,
        "create input");
    check(csh_parser_create(&result, *input, &error) == 0, "create parser");
    csh_parser_set_aliases(result, table);
    return result;
}

static struct csh_ast *next(struct csh_parser *parser)
{
    struct csh_ast *tree = NULL;
    struct csh_error error;
    enum csh_parse_result result = csh_parser_next(parser, &tree, &error);
    if (result != CSH_PARSE_TREE)
        fprintf(stderr, "parse result %d: %s at %zu:%zu\n", result,
            error.message == NULL ? "no diagnostic" : error.message,
            error.position.line, error.position.column);
    check(result == CSH_PARSE_TREE && tree != NULL, "expected complete tree");
    return tree;
}

static void eof(struct csh_parser *parser)
{
    struct csh_ast *tree = NULL;
    struct csh_error error;
    check(csh_parser_next(parser, &tree, &error) == CSH_PARSE_EOF && tree == NULL,
        "expected EOF");
}

/* Keep the AST after destroying all input/parser ownership. */
static struct csh_ast *parse(const char *source, const struct csh_aliases *table)
{
    struct csh_input *input = NULL;
    struct csh_parser *p = parser(source, table, &input);
    struct csh_ast *tree = next(p);
    eof(p);
    csh_parser_destroy(p);
    csh_input_destroy(input);
    return tree;
}

static struct csh_ast *item(struct csh_ast *tree, size_t index)
{
    check(tree->kind == CSH_AST_LIST && index < tree->data.list.item_count,
        "expected list item");
    return tree->data.list.items[index].command;
}

static struct csh_ast *one(struct csh_ast *tree)
{
    check(tree->kind == CSH_AST_LIST && tree->data.list.item_count == 1,
        "expected one command");
    return item(tree, 0);
}

static struct csh_position spelling_position(const struct csh_token *token, size_t end)
{
    struct csh_position position = token->start;
    size_t index;
    check(end <= token->length, "fragment range lies within captured spelling");
    for (index = 0; index < end; ++index) {
        ++position.offset;
        if (token->raw[index] == '\n') {
            ++position.line;
            position.column = 1;
        } else
            ++position.column;
    }
    return position;
}

static int same_position(struct csh_position left, struct csh_position right)
{
    return left.offset == right.offset && left.line == right.line &&
        left.column == right.column;
}

static void spelling_positions(const struct csh_token *token)
{
    size_t index;
    check(same_position(token->end, spelling_position(token, token->length)),
        "token position spans its captured spelling across input sources");
    for (index = 0; index < token->fragment_count; ++index) {
        const struct csh_fragment *fragment = &token->fragments[index];
        check(fragment->begin <= fragment->end && fragment->end <= token->length,
            "fragment range is ordered within captured spelling");
        check(same_position(fragment->start, spelling_position(token, fragment->begin)) &&
            same_position(fragment->finish, spelling_position(token, fragment->end)),
            "fragment positions follow captured spelling across input sources");
    }
}

static const struct csh_token *word(struct csh_ast *tree, size_t index,
    const char *raw)
{
    const struct csh_token *token;
    check(tree->kind == CSH_AST_SIMPLE && index < tree->data.simple.word_count,
        "expected simple-command word");
    token = &tree->data.simple.words[index].word.token;
    spelling_positions(token);
    if (token->length != strlen(raw) || memcmp(token->raw, raw, token->length) != 0) {
        fprintf(stderr, "word %zu: expected <%s>, got <%.*s>\n", index, raw,
            (int)token->length, token->raw);
        check(0, "word spelling");
    }
    return token;
}

static void words(struct csh_ast *tree, size_t count, const char *const *raw)
{
    size_t index;
    check(tree->kind == CSH_AST_SIMPLE && tree->data.simple.word_count == count,
        "simple-command word count");
    for (index = 0; index < count; ++index)
        word(tree, index, raw[index]);
}

static void spellings(const char *source, struct csh_aliases *table,
    size_t count, const char *const *raw)
{
    struct csh_ast *tree = parse(source, table);
    words(one(tree), count, raw);
    csh_ast_destroy(tree);
}

#define WORDS(source, table, ...) do { \
    const char *expected[] = { __VA_ARGS__ }; \
    spellings(source, table, sizeof(expected) / sizeof(expected[0]), expected); \
} while (0)

static void eligibility(void)
{
    struct csh_aliases *table = aliases();
    current_case = "command position and quoting";
    set(table, "a", "echo");
    WORDS("a a\n", table, "echo", "a");
    WORDS("echo a\n", table, "echo", "a");
    WORDS("'a' a\n", table, "'a'", "a");
    WORDS("\"a\" a\n", table, "\"a\"", "a");
    WORDS("\\a a\n", table, "\\a", "a");
    WORDS("a'' a\n", table, "a''", "a");
    WORDS("a\\\n a\n", table, "echo", "a");
    set(table, "a", "printf '%s\\n' \"two words\"");
    WORDS("a tail\n", table, "printf", "'%s\\n'", "\"two words\"", "tail");
    csh_aliases_destroy(table);
}

static void trailing_blank(void)
{
    struct csh_aliases *table = aliases();
    current_case = "trailing-blank continuation";
    set(table, "a", "echo ");
    set(table, "b", "B");
    set(table, "c", "C");
    WORDS("a b c\n", table, "echo", "B", "c");
    WORDS("a missing b\n", table, "echo", "missing", "b");
    WORDS("a 'b' c\n", table, "echo", "'b'", "c");
    set(table, "a", "echo\t");
    WORDS("a b c\n", table, "echo", "B", "c");
    set(table, "b", "B ");
    WORDS("a b c\n", table, "echo", "B", "C");
    set(table, "b", "c");
    WORDS("a b\n", table, "echo", "C");
    set(table, "a", "b ");
    set(table, "b", "echo");
    WORDS("a c\n", table, "echo", "C");
    set(table, "a", "echo\\ ");
    WORDS("a c\n", table, "echo\\ ", "C");
    set(table, "a", "b c");
    set(table, "b", "echo ");
    WORDS("a\n", table, "echo", "C");
    set(table, "a", "echo ");
    set(table, "b", "");
    WORDS("a b c\n", table, "echo", "c");
    csh_aliases_destroy(table);
}

static void replacement_boundaries(void)
{
    struct csh_aliases *table = aliases();
    struct csh_ast *tree, *node;
    struct csh_ast_word *argument;
    struct csh_input *input = NULL;
    struct csh_parser *p;
    current_case = "replacement source boundaries";
    set(table, "a", "echo");
    tree = parse("a>out\n", table);
    node = one(tree);
    word(node, 0, "echo");
    check(node->redirection_count == 1 &&
        strcmp((const char *)node->redirections[0]->operand.token.raw, "out") == 0,
        "original operator follows generated word");
    csh_ast_destroy(tree);
    set(table, "a", "22");
    tree = parse("a >out\n", table);
    node = one(tree);
    word(node, 0, "22");
    check(node->redirection_count == 1 && !node->redirections[0]->has_io_number,
        "unrelated source offsets do not make an IO number");
    csh_ast_destroy(tree);
    set(table, "a", "2");
    tree = parse("a>out\n", table);
    node = one(tree);
    word(node, 0, "2");
    check(node->redirection_count == 1 && !node->redirections[0]->has_io_number,
        "synthetic separator prevents cross-source IO number");
    csh_ast_destroy(tree);
    set(table, "a", "echo 2>out");
    tree = parse("a\n", table);
    node = one(tree);
    word(node, 0, "echo");
    check(node->redirection_count == 1 && node->redirections[0]->has_io_number &&
        strcmp((const char *)node->redirections[0]->io_number.raw, "2") == 0,
        "adjacent descriptor inside replacement is an IO number");
    csh_ast_destroy(tree);
    set(table, "a", "echo \"");
    WORDS("a suffix\"\n", table, "echo", "\"  suffix\"");
    set(table, "a", "echo $(");
    set(table, "b", "printf");
    tree = parse("a b)\n", table);
    word(one(tree), 1, "$(  b)");
    argument = &one(tree)->data.simple.words[1].word;
    check(argument->substitution_count == 1, "substitution crosses replacement boundary");
    word(one(argument->substitutions[0].body), 0, "printf");
    csh_ast_destroy(tree);
    set(table, "a", "cat <<END\nfrom alias\nEND\n");
    tree = parse("a\n", table);
    check(strcmp((const char *)one(tree)->redirections[0]->body, "from alias\n") == 0,
        "here-document body supplied by alias source");
    csh_ast_destroy(tree);
    set(table, "a", "echo # comment");
    WORDS("a ignored\n", table, "echo");
    set(table, "a", "echo\nb");
    set(table, "b", "before");
    p = parser("a\n", table, &input);
    tree = next(p);
    word(one(tree), 0, "echo");
    csh_ast_destroy(tree);
    set(table, "a", "changed");
    set(table, "b", "after");
    tree = next(p);
    word(one(tree), 0, "after");
    csh_ast_destroy(tree);
    eof(p);
    csh_parser_destroy(p);
    csh_input_destroy(input);
    csh_aliases_destroy(table);
}

static void recursion(void)
{
    struct csh_aliases *table = aliases();
    struct csh_ast *tree;
    size_t index;
    char name[32], value[32];
    current_case = "recursion and finite chains";
    set(table, "a", "a x");
    WORDS("a y\n", table, "a", "x", "y");
    tree = parse("a; a\n", table);
    check(tree->data.list.item_count == 2, "separate invocations are not suppressed");
    word(item(tree, 0), 0, "a");
    word(item(tree, 1), 0, "a");
    csh_ast_destroy(tree);
    set(table, "a", "b x");
    set(table, "b", "a y");
    WORDS("a z\n", table, "a", "y", "x", "z");
    set(table, "a", "b ");
    set(table, "b", "a ");
    WORDS("a\n", table, "a");
    for (index = 0; index < 300; ++index) {
        snprintf(name, sizeof(name), "chain%zu", index);
        snprintf(value, sizeof(value), "chain%zu", index + 1);
        set(table, name, index == 299 ? "finished" : value);
    }
    WORDS("chain0\n", table, "finished");
    csh_aliases_destroy(table);
}

static void empty_replacements(void)
{
    struct csh_aliases *table = aliases();
    struct csh_input *input = NULL;
    struct csh_parser *p;
    struct csh_ast *tree;
    current_case = "empty replacement";
    set(table, "a", "");
    set(table, "b", "echo");
    WORDS("a b tail\n", table, "echo", "tail");
    p = parser("a\n", table, &input);
    eof(p);
    csh_parser_destroy(p);
    csh_input_destroy(input);
    tree = parse(">out a\n", table);
    check(one(tree)->data.simple.word_count == 0 && one(tree)->redirection_count == 1,
        "empty alias preserves redirection-only command");
    csh_ast_destroy(tree);
    tree = parse("b; a\n", table);
    check(tree->data.list.item_count == 1, "empty alias after semicolon before newline");
    word(item(tree, 0), 0, "echo");
    csh_ast_destroy(tree);
    csh_aliases_destroy(table);
}

static void grammar(void)
{
    struct csh_aliases *table = aliases();
    struct csh_ast *tree, *node, *left;
    current_case = "grammar positions and replacement operators";
    set(table, "a", "echo");
    set(table, "2", "wrong");
    tree = parse("2>out a\n", table);
    node = one(tree);
    word(node, 0, "echo");
    check(node->redirection_count == 1 && node->redirections[0]->has_io_number &&
        strcmp((const char *)node->redirections[0]->io_number.raw, "2") == 0,
        "IO numbers take precedence over aliases");
    csh_ast_destroy(tree);
    tree = parse("A=1 >a B='two' a | a && (a; a) || { a; }\n", table);
    node = one(tree);
    check(node->kind == CSH_AST_OR && node->data.binary.left->kind == CSH_AST_AND,
        "AND/OR shape");
    left = node->data.binary.left->data.binary.left;
    check(left->kind == CSH_AST_PIPELINE && left->data.pipeline.command_count == 2,
        "pipeline shape");
    word(left->data.pipeline.commands[0], 0, "A=1");
    word(left->data.pipeline.commands[0], 1, "B='two'");
    word(left->data.pipeline.commands[0], 2, "echo");
    check(left->data.pipeline.commands[0]->data.simple.words[0].assignment &&
        left->data.pipeline.commands[0]->data.simple.words[1].assignment &&
        !left->data.pipeline.commands[0]->data.simple.words[2].assignment,
        "assignment classification before alias");
    check(strcmp((const char *)left->data.pipeline.commands[0]->redirections[0]->operand.token.raw,
        "a") == 0, "redirection operands do not expand");
    word(left->data.pipeline.commands[1], 0, "echo");
    left = node->data.binary.left->data.binary.right;
    check(left->kind == CSH_AST_SUBSHELL, "subshell shape");
    word(item(left->data.group.body, 0), 0, "echo");
    word(item(left->data.group.body, 1), 0, "echo");
    check(node->data.binary.right->kind == CSH_AST_BRACE, "brace shape");
    word(one(node->data.binary.right->data.group.body), 0, "echo");
    csh_ast_destroy(tree);
    set(table, "a", "left | right && (inner; tail)");
    tree = parse("a\n", table);
    node = one(tree);
    check(node->kind == CSH_AST_AND && node->data.binary.left->kind == CSH_AST_PIPELINE &&
        node->data.binary.right->kind == CSH_AST_SUBSHELL,
        "replacement text is parsed as shell grammar");
    word(node->data.binary.left->data.pipeline.commands[0], 0, "left");
    word(node->data.binary.left->data.pipeline.commands[1], 0, "right");
    word(item(node->data.binary.right->data.group.body, 0), 0, "inner");
    word(item(node->data.binary.right->data.group.body, 1), 0, "tail");
    csh_ast_destroy(tree);
    set(table, "a", "X=1 >out b");
    set(table, "b", "echo");
    tree = parse("a\n", table);
    node = one(tree);
    word(node, 0, "X=1");
    word(node, 1, "echo");
    check(node->data.simple.words[0].assignment && node->redirection_count == 1,
        "replacement prefixes retain command position");
    csh_ast_destroy(tree);
    set(table, "a", "{ b; }; b");
    tree = parse("a\n", table);
    check(tree->data.list.item_count == 2 && item(tree, 0)->kind == CSH_AST_BRACE,
        "replacement list/group delimiters");
    word(one(item(tree, 0)->data.group.body), 0, "echo");
    word(item(tree, 1), 0, "echo");
    csh_ast_destroy(tree);
    csh_aliases_destroy(table);
}

static void mutation_timing(void)
{
    struct csh_aliases *table = aliases();
    struct csh_aliases *replacement = aliases();
    struct csh_input *input = NULL;
    struct csh_parser *p;
    struct csh_ast *tree;
    struct csh_error error;
    current_case = "alias changes between complete commands";
    set(table, "a", "before");
    set(replacement, "a", "replaced");
    p = parser("a; a\na\na\na\na\n", table, &input);
    tree = next(p);
    check(tree->data.list.item_count == 2, "same-line list is one read unit");
    word(item(tree, 0), 0, "before");
    word(item(tree, 1), 0, "before");
    csh_ast_destroy(tree);
    set(table, "a", "after");
    tree = next(p);
    word(one(tree), 0, "after");
    csh_ast_destroy(tree);
    check(csh_aliases_unset(table, "a", &error) == 0, "unset alias");
    tree = next(p);
    word(one(tree), 0, "a");
    csh_ast_destroy(tree);
    csh_parser_set_aliases(p, replacement);
    tree = next(p);
    word(one(tree), 0, "replaced");
    csh_ast_destroy(tree);
    csh_parser_set_aliases(p, NULL);
    tree = next(p);
    word(one(tree), 0, "a");
    csh_ast_destroy(tree);
    eof(p);
    csh_parser_destroy(p);
    csh_input_destroy(input);
    set(table, "a", "before");
    p = parser("(\na\n)\na\n", table, &input);
    tree = next(p);
    check(one(tree)->kind == CSH_AST_SUBSHELL, "multiline read unit");
    word(one(one(tree)->data.group.body), 0, "before");
    csh_ast_destroy(tree);
    set(table, "a", "after");
    tree = next(p);
    word(one(tree), 0, "after");
    csh_ast_destroy(tree);
    eof(p);
    csh_parser_destroy(p);
    csh_input_destroy(input);
    csh_aliases_destroy(table);
    csh_aliases_destroy(replacement);
}

static void nested_and_heredocs(void)
{
    struct csh_aliases *table = aliases();
    struct csh_ast *tree, *node, *sub;
    struct csh_ast_word *argument;
    struct csh_ast_redirection *redir;
    current_case = "nested substitutions and heredoc ownership";
    set(table, "a", "echo");
    set(table, "b", "printf");
    tree = parse("echo $(a $(b))\n", table);
    node = one(tree);
    word(node, 1, "$(a $(b))");
    argument = &node->data.simple.words[1].word;
    check(argument->substitution_count == 1, "outer substitution parsed");
    sub = one(argument->substitutions[0].body);
    word(sub, 0, "echo");
    word(sub, 1, "$(b)");
    argument = &sub->data.simple.words[1].word;
    check(argument->substitution_count == 1, "inner substitution parsed");
    word(one(argument->substitutions[0].body), 0, "printf");
    csh_ast_destroy(tree);
    set(table, "a", "echo $(b)");
    tree = parse("a\n", table);
    argument = &one(tree)->data.simple.words[1].word;
    check(argument->substitution_count == 1, "alias-generated substitution parsed");
    word(one(argument->substitutions[0].body), 0, "printf");
    csh_ast_destroy(tree);
    set(table, "a", "echo $(a)");
    tree = parse("a\n", table);
    argument = &one(tree)->data.simple.words[1].word;
    check(argument->substitution_count == 1, "recursive substitution parsed");
    word(one(argument->substitutions[0].body), 0, "a");
    csh_ast_destroy(tree);
    set(table, "a", "cat");
    set(table, "END", "WRONG");
    tree = parse("a <<END\na b END\nEND\n", table);
    node = one(tree);
    word(node, 0, "cat");
    check(node->redirection_count == 1, "heredoc attached");
    redir = node->redirections[0];
    check(strcmp((const char *)redir->delimiter, "END") == 0 &&
        strcmp((const char *)redir->body, "a b END\n") == 0,
        "heredoc delimiters and bodies are not aliases");
    csh_ast_destroy(tree);
    set(table, "a", "cat <<END");
    tree = parse("a\nbody\nEND\n", table);
    redir = one(tree)->redirections[0];
    check(strcmp((const char *)redir->body, "body\n") == 0,
        "alias-generated heredoc consumes original source");
    csh_ast_destroy(tree);
    tree = parse("echo $(a\ninside\nEND\n)\n", table);
    argument = &one(tree)->data.simple.words[1].word;
    check(argument->substitution_count == 1, "nested heredoc substitution parsed");
    redir = one(argument->substitutions[0].body)->redirections[0];
    check(strcmp((const char *)redir->body, "inside\n") == 0,
        "nested alias-generated heredoc body");
    csh_ast_destroy(tree);
    csh_aliases_destroy(table);
}

static void provenance(void)
{
    struct csh_aliases *table = aliases();
    struct csh_ast *tree, *node;
    const struct csh_token *generated, *original;
    current_case = "owned generated-token provenance";
    set(table, "a", "b");
    set(table, "b", "echo");
    tree = parse("  a tail\n", table);
    csh_aliases_destroy(table);
    node = one(tree);
    generated = word(node, 0, "echo");
    original = word(node, 1, "tail");
    check(generated->alias_name != NULL && strcmp(generated->alias_name, "b") == 0,
        "generated token owns alias name");
    check(strcmp(generated->source_name, "alias:b") == 0 && generated->start.offset == 0 &&
        generated->start.line == 1 && generated->start.column == 1,
        "generated token positions refer to replacement source");
    check(generated->invocation_source != NULL &&
        strcmp(generated->invocation_source, "alias-parser") == 0 &&
        generated->invocation.offset == 2 && generated->invocation.line == 1 &&
        generated->invocation.column == 3, "chained alias keeps outer invocation");
    check(strcmp(original->source_name, "alias-parser") == 0 &&
        original->start.offset == 4 && original->start.line == 1 &&
        original->start.column == 5 && original->alias_name == NULL &&
        original->invocation_source == NULL, "original source positions resume");
    csh_ast_destroy(tree);
}

static void invalid_replacements(void)
{
    static const struct {
        const char *replacement;
        const char *source;
        enum csh_parse_result expected;
    } cases[] = {
        { "echo >", "a\n", CSH_PARSE_ERROR },
        { "echo )", "a\n", CSH_PARSE_ERROR },
        { "(", "a\n", CSH_PARSE_INCOMPLETE },
        { "echo 'unfinished", "a\n", CSH_PARSE_INCOMPLETE },
        { "", "echo; a; echo\n", CSH_PARSE_ERROR }
    };
    struct csh_aliases *table = aliases();
    size_t index;
    current_case = "alias-generated syntax errors are sticky";
    for (index = 0; index < sizeof(cases) / sizeof(cases[0]); ++index) {
        struct csh_input *input = NULL;
        struct csh_parser *p;
        struct csh_ast *tree = NULL;
        struct csh_error first, repeated;
        set(table, "a", cases[index].replacement);
        p = parser(cases[index].source, table, &input);
        check(csh_parser_next(p, &tree, &first) == cases[index].expected && tree == NULL,
            "invalid replacement result");
        check(first.message != NULL && first.status == 2 && first.system_errno == 0,
            "syntax diagnostic");
        check(csh_parser_next(p, &tree, &repeated) == cases[index].expected && tree == NULL &&
            repeated.message == first.message && repeated.position.offset == first.position.offset,
            "repeated syntax diagnostic");
        csh_parser_destroy(p);
        csh_input_destroy(input);
    }
    csh_aliases_destroy(table);
}

static void diagnostic_positions(void)
{
    static const struct {
        const char *replacement;
        enum csh_parse_result expected;
    } cases[] = {
        { "echo )", CSH_PARSE_ERROR },
        { "(", CSH_PARSE_INCOMPLETE },
        { "cat <<END", CSH_PARSE_INCOMPLETE },
        { "echo 'unfinished", CSH_PARSE_INCOMPLETE },
        { "echo $(", CSH_PARSE_INCOMPLETE }
    };
    struct csh_aliases *table = aliases();
    size_t index;
    current_case = "diagnostics retain physical alias invocation";
    for (index = 0; index < sizeof(cases) / sizeof(cases[0]); ++index) {
        struct csh_input *input = NULL;
        struct csh_parser *p;
        struct csh_ast *tree;
        struct csh_error error;
        set(table, "a", cases[index].replacement);
        p = parser("echo\n  a\n", table, &input);
        tree = next(p);
        csh_ast_destroy(tree);
        tree = NULL;
        check(csh_parser_next(p, &tree, &error) == cases[index].expected && tree == NULL,
            "expected alias syntax failure");
        if (error.position.offset != 7 || error.position.line != 2 || error.position.column != 3)
            fprintf(stderr, "replacement <%s>: physical diagnostic %zu:%zu offset %zu\n",
                cases[index].replacement, error.position.line, error.position.column,
                error.position.offset);
        check(error.position.offset == 7 && error.position.line == 2 && error.position.column == 3,
            "diagnostic must identify physical invocation, not replacement coordinates");
        check(strcmp(csh_parser_source_name(p), "alias-parser") == 0,
            "diagnostic source is original input");
        csh_parser_destroy(p);
        csh_input_destroy(input);
    }
    csh_aliases_destroy(table);
}

int main(void)
{
    current_case = "initialization";
    eligibility();
    trailing_blank();
    recursion();
    empty_replacements();
    grammar();
    mutation_timing();
    nested_and_heredocs();
    provenance();
    invalid_replacements();
    replacement_boundaries();
    diagnostic_positions();
    puts("ok");
    return 0;
}
