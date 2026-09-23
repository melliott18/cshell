#include "cshell/ast.h"

/* Contract checks must execute in release builds, too. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static struct csh_ast *make_node(enum csh_ast_kind kind)
{
    struct csh_ast *node = NULL;
    struct csh_error error;
    assert(csh_ast_create(&node, kind, &error) == 0);
    assert(node != NULL && node->kind == kind);
    assert(error.message == NULL && error.system_errno == 0 && error.status == 0);
    return node;
}

static struct csh_token next_token(struct csh_lexer *lexer,
    enum csh_token_kind kind)
{
    struct csh_token token = {0};
    struct csh_error error;
    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_TOKEN);
    assert(token.kind == kind);
    return token;
}

static struct csh_ast_word make_word(const char *source)
{
    struct csh_ast_word word = {0};
    struct csh_lexer *lexer = NULL;
    struct csh_error error;
    assert(csh_lexer_create(&lexer, "ast-word", &error) == 0);
    assert(csh_lexer_feed(lexer, source, strlen(source), 1, &error) == 0);
    word.token = next_token(lexer, CSH_TOKEN_WORD);
    csh_lexer_destroy(lexer);
    return word;
}

static unsigned char *copy_bytes(const char *source)
{
    size_t length = strlen(source);
    unsigned char *copy = malloc(length + 1);
    assert(copy != NULL);
    memcpy(copy, source, length + 1);
    return copy;
}

static void add_word(struct csh_ast *node, struct csh_ast_word *word,
    int assignment)
{
    unsigned char *raw = word->token.raw;
    struct csh_error error;
    size_t index = node->data.simple.word_count;
    assert(csh_ast_add_word(node, word, assignment, &error) == 0);
    assert(word->token.raw == NULL && word->substitutions == NULL &&
        word->substitution_count == 0 && word->substitution_capacity == 0);
    assert(node->data.simple.words[index].word.token.raw == raw);
    assert(node->data.simple.words[index].assignment == (assignment != 0));
}

static struct csh_ast_redirection *make_redirection(enum csh_token_kind kind)
{
    struct csh_ast_redirection *redirection = NULL;
    struct csh_error error;
    assert(csh_ast_redirection_create(&redirection, kind, &error) == 0);
    assert(redirection != NULL && redirection->operator_kind == kind);
    return redirection;
}

/* Construct a real command using tokens from the replacement lexer, including
 * a grammar-selected substitution handoff. Destroy the lexer before inspecting
 * the tree, so token/source/fragment ownership is independently exercised. */
static void source_order(void)
{
    const char source[] =
        "A='x y' printf pre$(echo nested)post 02>>out 1>&2 <<-'E'\n"
        "\tleft $x\n\tE\n";
    struct csh_lexer *lexer = NULL, *child = NULL;
    struct csh_ast *command = make_node(CSH_AST_SIMPLE);
    struct csh_ast *body = make_node(CSH_AST_SIMPLE);
    struct csh_ast_word word = {0};
    struct csh_ast_substitution substitution = {0};
    struct csh_ast_redirection *here = NULL;
    struct csh_token token = {0};
    struct csh_error error;
    size_t index, pending_length;
    struct csh_position position;
    int final;
    assert(csh_lexer_create(&lexer, "ast-source", &error) == 0);
    assert(csh_lexer_feed(lexer, source, sizeof(source) - 1, 1, &error) == 0);
    word.token = next_token(lexer, CSH_TOKEN_WORD);
    add_word(command, &word, 1);
    word.token = next_token(lexer, CSH_TOKEN_WORD);
    add_word(command, &word, 0);

    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_COMMAND);
    assert(csh_lexer_command_begin(lexer, &child, &error) == 0);
    word.token = next_token(child, CSH_TOKEN_WORD);
    add_word(body, &word, 0);
    word.token = next_token(child, CSH_TOKEN_WORD);
    add_word(body, &word, 0);
    token = next_token(child, CSH_TOKEN_RPAREN);
    assert(csh_lexer_command_end(lexer, child, &token, &error) == 0);
    csh_token_destroy(&token);
    word.token = next_token(lexer, CSH_TOKEN_WORD);
    for (index = 0; index < word.token.fragment_count; ++index) {
        if (word.token.fragments[index].kind == CSH_FRAGMENT_COMMAND)
            break;
    }
    assert(index < word.token.fragment_count);
    substitution.fragment_index = index;
    substitution.begin = word.token.fragments[index].begin;
    substitution.end = word.token.fragments[index].end;
    substitution.body = body;
    assert(csh_ast_word_add_substitution(&word, &substitution, &error) == 0);
    assert(substitution.body == NULL);
    add_word(command, &word, 0);

    for (index = 0; index < 3; ++index) {
        static const enum csh_token_kind kinds[] = {
            CSH_TOKEN_DGREAT, CSH_TOKEN_GREAT_AND, CSH_TOKEN_DLESS_DASH
        };
        struct csh_ast_redirection *redirection = make_redirection(kinds[index]);
        struct csh_ast_redirection *owned = redirection;
        if (index < 2) {
            redirection->has_io_number = 1;
            redirection->io_number = next_token(lexer, CSH_TOKEN_WORD);
        }
        token = next_token(lexer, kinds[index]);
        redirection->start = token.start;
        csh_token_destroy(&token);
        redirection->operand.token = next_token(lexer, CSH_TOKEN_WORD);
        redirection->end = redirection->operand.token.end;
        if (index == 2) {
            here = redirection;
            here->delimiter = copy_bytes("E");
            here->delimiter_length = 1;
            here->delimiter_quoted = 1;
        }
        assert(csh_ast_add_redirection(command, &redirection, &error) == 0);
        assert(redirection == NULL && command->redirections[index] == owned);
    }
    token = next_token(lexer, CSH_TOKEN_NEWLINE);
    csh_token_destroy(&token);
    assert(csh_lexer_pending(lexer, &pending_length, &position, &final) != NULL);
    assert(final && pending_length == strlen("\tleft $x\n\tE\n"));
    here->body = copy_bytes("left $x\n");
    here->body_length = strlen("left $x\n");
    here->body_start = position;
    assert(csh_lexer_skip_raw(lexer, pending_length, &error) == 0);
    (void)csh_lexer_pending(lexer, &pending_length, &here->body_end, &final);
    csh_lexer_destroy(lexer);

    assert(command->data.simple.word_count == 3 && command->redirection_count == 3);
    assert(command->data.simple.words[0].assignment);
    assert(!command->data.simple.words[1].assignment);
    assert(strcmp((char *)command->data.simple.words[0].word.token.raw, "A='x y'") == 0);
    assert(command->data.simple.words[0].word.token.fragment_count >= 2);
    assert(strcmp(command->data.simple.words[0].word.token.source_name, "ast-source") == 0);
    assert(strcmp((char *)command->data.simple.words[1].word.token.raw, "printf") == 0);
    assert(strcmp((char *)command->data.simple.words[2].word.token.raw,
        "pre$(echo nested)post") == 0);
    word = command->data.simple.words[2].word; /* Borrowed view, not a new owner. */
    assert(word.substitution_count == 1 && word.substitutions[0].body == body);
    assert(word.substitutions[0].begin == 3 && word.substitutions[0].end == 17);
    assert(word.token.fragments[word.substitutions[0].fragment_index].kind ==
        CSH_FRAGMENT_COMMAND);
    assert(strcmp((char *)body->data.simple.words[1].word.token.raw, "nested") == 0);
    assert(strcmp((char *)command->redirections[0]->io_number.raw, "02") == 0);
    assert(command->redirections[0]->operator_kind == CSH_TOKEN_DGREAT);
    assert(command->redirections[1]->operator_kind == CSH_TOKEN_GREAT_AND);
    assert(strcmp((char *)command->redirections[1]->operand.token.raw, "2") == 0);
    assert(command->redirections[0]->start.offset < command->redirections[1]->start.offset);
    assert(command->redirections[1]->start.offset < here->start.offset);
    assert(!here->has_io_number && here->delimiter_quoted);
    assert(strcmp((char *)here->operand.token.raw, "'E'") == 0);
    assert(here->delimiter_length == 1 && here->delimiter[0] == 'E');
    assert(here->body_length == 8 && memcmp(here->body, "left $x\n", 8) == 0);
    assert(here->body_start.line == 2 && here->body_end.line == 4);
    csh_ast_destroy(command);
}

static void invalid_and_overflow(void)
{
    struct csh_ast *simple = make_node(CSH_AST_SIMPLE);
    struct csh_ast *pipeline = make_node(CSH_AST_PIPELINE);
    struct csh_ast *list = make_node(CSH_AST_LIST);
    struct csh_ast *child = make_node(CSH_AST_SIMPLE);
    struct csh_ast *saved_child = child;
    struct csh_ast_word word = make_word("'owned word'");
    struct csh_ast_word nested_word = {0};
    struct csh_ast_redirection *redirection = make_redirection(CSH_TOKEN_LESS);
    struct csh_ast_redirection *saved_redirection = redirection;
    struct csh_ast_substitution substitution = {0};
    struct csh_ast_list_item item = {0};
    struct csh_error error;
    unsigned char *raw = word.token.raw;
    enum csh_ast_kind kind;

    for (kind = CSH_AST_IF; kind <= CSH_AST_FUNCTION; ++kind) {
        struct csh_ast *out = simple;
        assert(csh_ast_create(&out, kind, &error) == -1 && out == NULL);
        assert(error.system_errno == EINVAL && error.status == 2);
        assert(strcmp(csh_ast_kind_name(kind), "UNKNOWN") != 0);
    }
    assert(strcmp(csh_ast_kind_name((enum csh_ast_kind)-1), "UNKNOWN") == 0);
    assert(csh_ast_create(NULL, CSH_AST_SIMPLE, &error) == -1);
    assert(csh_ast_add_word(pipeline, &word, 0, &error) == -1);
    assert(word.token.raw == raw && pipeline->data.pipeline.command_count == 0);
    simple->data.simple.word_count = SIZE_MAX;
    assert(csh_ast_add_word(simple, &word, 0, &error) == -1);
    assert(error.system_errno == EOVERFLOW && error.status == 1);
    assert(word.token.raw == raw && simple->data.simple.words == NULL &&
        simple->data.simple.word_capacity == 0);
    simple->data.simple.word_count = 0;
    add_word(simple, &word, 1);

    assert(csh_ast_pipeline_add(simple, &child, &error) == -1 && child == saved_child);
    pipeline->data.pipeline.command_count = SIZE_MAX;
    assert(csh_ast_pipeline_add(pipeline, &child, &error) == -1);
    assert(error.system_errno == EOVERFLOW && child == saved_child);
    pipeline->data.pipeline.command_count = 0;
    assert(csh_ast_pipeline_add(pipeline, &child, &error) == 0 && child == NULL);
    assert(pipeline->data.pipeline.commands[0] == saved_child);
    assert(csh_ast_pipeline_add(pipeline, &pipeline, &error) == -1);

    assert(csh_ast_add_redirection(NULL, &redirection, &error) == -1);
    assert(redirection == saved_redirection);
    simple->redirection_count = SIZE_MAX;
    assert(csh_ast_add_redirection(simple, &redirection, &error) == -1);
    assert(error.system_errno == EOVERFLOW && redirection == saved_redirection);
    simple->redirection_count = 0;
    assert(csh_ast_add_redirection(simple, &redirection, &error) == 0);
    assert(redirection == NULL && simple->redirections[0] == saved_redirection);
    redirection = saved_redirection;
    assert(csh_ast_redirection_create(&redirection, CSH_TOKEN_PIPE, &error) == -1);
    assert(redirection == NULL && error.system_errno == EINVAL);

    substitution.body = simple;
    assert(csh_ast_word_add_substitution(NULL, &substitution, &error) == -1);
    assert(substitution.body == simple);
    nested_word.substitution_count = SIZE_MAX;
    assert(csh_ast_word_add_substitution(&nested_word, &substitution, &error) == -1);
    assert(error.system_errno == EOVERFLOW && substitution.body == simple);
    nested_word.substitution_count = 0;
    assert(csh_ast_word_add_substitution(&nested_word, &substitution, &error) == 0);
    assert(substitution.body == NULL && nested_word.substitutions[0].body == simple);

    item.command = pipeline;
    item.separator = CSH_AST_AMPERSAND;
    item.separator_start = (struct csh_position){9, 1, 10};
    item.separator_end = (struct csh_position){10, 1, 11};
    assert(csh_ast_list_add(simple, &item, &error) == -1 && item.command == pipeline);
    list->data.list.item_count = SIZE_MAX;
    assert(csh_ast_list_add(list, &item, &error) == -1);
    assert(error.system_errno == EOVERFLOW && item.command == pipeline);
    list->data.list.item_count = 0;
    assert(csh_ast_list_add(list, &item, &error) == 0 && item.command == NULL);
    assert(list->data.list.items[0].command == pipeline &&
        list->data.list.items[0].separator == CSH_AST_AMPERSAND &&
        list->data.list.items[0].separator_start.offset == 9 &&
        list->data.list.items[0].separator_end.offset == 10);

    csh_ast_word_destroy(&nested_word);
    csh_ast_word_destroy(&nested_word);
    csh_ast_destroy(list);
}

static void growing_vectors(void)
{
    static const enum csh_token_kind kinds[] = {
        CSH_TOKEN_LESS, CSH_TOKEN_GREAT, CSH_TOKEN_DLESS, CSH_TOKEN_DGREAT,
        CSH_TOKEN_LESS_AND, CSH_TOKEN_GREAT_AND, CSH_TOKEN_LESS_GREAT,
        CSH_TOKEN_DLESS_DASH, CSH_TOKEN_CLOBBER
    };
    struct csh_ast *simple = make_node(CSH_AST_SIMPLE);
    struct csh_ast *pipeline = make_node(CSH_AST_PIPELINE);
    struct csh_ast *list = make_node(CSH_AST_LIST);
    struct csh_ast_word nested_word = {0};
    struct csh_error error;
    size_t index;
    pipeline->data.pipeline.negated = 1;
    for (index = 0; index < 41; ++index) {
        struct csh_ast_word word = make_word(index % 2 ? "argument" : "A=value");
        struct csh_ast *child = make_node(CSH_AST_SIMPLE);
        struct csh_ast_list_item item = {0};
        struct csh_ast_substitution substitution = {0};
        struct csh_ast_redirection *redirection = make_redirection(
            kinds[index % (sizeof(kinds) / sizeof(kinds[0]))]);
        add_word(simple, &word, index % 2 == 0);
        assert(csh_ast_add_redirection(simple, &redirection, &error) == 0);
        assert(csh_ast_pipeline_add(pipeline, &child, &error) == 0);
        item.command = make_node(CSH_AST_SIMPLE);
        item.separator = (enum csh_ast_separator)(index % 4);
        assert(csh_ast_list_add(list, &item, &error) == 0);
        substitution.fragment_index = index;
        substitution.body = make_node(CSH_AST_SIMPLE);
        assert(csh_ast_word_add_substitution(&nested_word, &substitution, &error) == 0);
    }
    assert(simple->data.simple.word_count == 41 && simple->redirection_count == 41);
    assert(pipeline->data.pipeline.command_count == 41 && pipeline->data.pipeline.negated);
    assert(list->data.list.item_count == 41 && nested_word.substitution_count == 41);
    for (index = 0; index < 41; ++index) {
        assert(simple->data.simple.words[index].assignment == (index % 2 == 0));
        assert(simple->redirections[index]->operator_kind ==
            kinds[index % (sizeof(kinds) / sizeof(kinds[0]))]);
        assert(list->data.list.items[index].separator == (enum csh_ast_separator)(index % 4));
        assert(nested_word.substitutions[index].fragment_index == index);
    }
    csh_ast_destroy(simple);
    csh_ast_destroy(pipeline);
    csh_ast_destroy(list);
    csh_ast_word_destroy(&nested_word);
}

/* Long binary chains and nested owned words must not consume the C stack.
 * Keep the fixture small enough to run in each native and sanitizer suite. */
static void deep_cleanup(void)
{
    struct csh_ast *root = make_node(CSH_AST_SIMPLE);
    struct csh_error error;
    size_t index;
    for (index = 0; index < 20000; ++index) {
        struct csh_ast *node = make_node(index % 2 ? CSH_AST_AND : CSH_AST_OR);
        node->data.binary.left = root;
        node->data.binary.right = make_node(CSH_AST_SIMPLE);
        root = node;
    }
    for (index = 0; index < 10000; ++index) {
        struct csh_ast *node;
        if (index % 3 == 0) {
            struct csh_ast_word word = {0};
            struct csh_ast_substitution substitution = {0};
            node = make_node(CSH_AST_SIMPLE);
            substitution.body = root;
            assert(csh_ast_word_add_substitution(&word, &substitution, &error) == 0);
            add_word(node, &word, 0);
        } else {
            node = make_node(index % 3 == 1 ? CSH_AST_BRACE : CSH_AST_SUBSHELL);
            node->data.group.body = root;
        }
        root = node;
    }
    csh_ast_destroy(root);
    csh_ast_destroy(NULL);
    csh_ast_word_destroy(NULL);
    csh_ast_redirection_destroy(NULL);
}

int main(void)
{
    source_order();
    invalid_and_overflow();
    growing_vectors();
    deep_cleanup();
    puts("PASS: AST ownership, source order, overflow, reserved kinds, deep cleanup");
    return 0;
}
