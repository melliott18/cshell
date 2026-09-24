/* Direct alias-source ownership and lexer handoff regression checks. */
#include "cshell/lexer.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>

static struct csh_lexer *create(const char *text)
{
    struct csh_lexer *lexer = NULL;
    struct csh_error error;
    assert(csh_lexer_create(&lexer, "physical-input", &error) == 0);
    assert(csh_lexer_feed(lexer, text, strlen(text), 1, &error) == 0);
    return lexer;
}

static struct csh_token word(struct csh_lexer *lexer, const char *spelling)
{
    struct csh_token token = {0};
    struct csh_error error;
    size_t index;
    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_TOKEN);
    assert(token.kind == CSH_TOKEN_WORD);
    assert(token.length == strlen(spelling));
    assert(memcmp(token.raw, spelling, token.length) == 0);
    assert(token.end.offset == token.start.offset + token.length);
    for (index = 0; index < token.fragment_count; ++index) {
        assert(token.fragments[index].start.offset ==
            token.start.offset + token.fragments[index].begin);
        assert(token.fragments[index].finish.offset ==
            token.start.offset + token.fragments[index].end);
    }
    return token;
}

static void substitute(struct csh_lexer *lexer, struct csh_token *token,
    const char *name, const char *value)
{
    struct csh_error error;
    assert(!csh_lexer_alias_active(lexer, name));
    assert(csh_lexer_alias_push(lexer, token, name, value, &error) == 0);
    assert(csh_lexer_alias_active(lexer, name));
    csh_token_destroy(token);
}

static void eof(struct csh_lexer *lexer)
{
    struct csh_token token = {0};
    struct csh_error error;
    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_EOF);
    csh_lexer_destroy(lexer);
}

static void chain_and_provenance(void)
{
    struct csh_lexer *lexer = create("  a tail");
    struct csh_token token = word(lexer, "a"), saved;
    char name[] = "a", value[] = "b ";
    substitute(lexer, &token, name, value);
    name[0] = value[0] = '!';
    token = word(lexer, "b");
    assert(strcmp(token.source_name, "alias:a") == 0);
    assert(strcmp(token.alias_name, "a") == 0);
    assert(strcmp(token.invocation_source, "physical-input") == 0);
    assert(token.start.offset == 0 && token.start.line == 1 && token.start.column == 1);
    assert(token.invocation.offset == 2 && token.invocation.column == 3);
    substitute(lexer, &token, "b", "a");
    token = word(lexer, "a");
    assert(csh_lexer_alias_active(lexer, "a"));
    assert(csh_lexer_alias_active(lexer, "b"));
    assert(strcmp(token.alias_name, "b") == 0 && token.invocation.offset == 2);
    saved = token;
    token = word(lexer, "tail");
    assert(token.alias_eligible);
    assert(token.alias_name == NULL && token.invocation_source == NULL);
    assert(token.start.offset == 4 && token.start.column == 5);
    assert(!csh_lexer_alias_active(lexer, "a"));
    assert(!csh_lexer_alias_active(lexer, "b"));
    csh_token_destroy(&token);
    eof(lexer);
    assert(strcmp(saved.raw ? (const char *)saved.raw : "", "a") == 0);
    assert(strcmp(saved.source_name, "alias:b") == 0);
    assert(strcmp(saved.invocation_source, "physical-input") == 0);
    csh_token_destroy(&saved);
}

static void trailing_blank_and_empty(void)
{
    struct csh_lexer *lexer = create("a b c d");
    struct csh_token token = word(lexer, "a");
    substitute(lexer, &token, "a", "echo ");
    token = word(lexer, "echo");
    assert(!token.alias_eligible);
    csh_token_destroy(&token);
    token = word(lexer, "b");
    assert(token.alias_eligible);
    substitute(lexer, &token, "b", "next");
    token = word(lexer, "next");
    assert(token.alias_eligible);
    csh_token_destroy(&token);
    token = word(lexer, "c");
    assert(!token.alias_eligible);
    substitute(lexer, &token, "c", "");
    token = word(lexer, "d");
    assert(!token.alias_eligible && token.start.offset == 6);
    csh_token_destroy(&token);
    eof(lexer);
}

static void command_frame_spelling(void)
{
    struct csh_lexer *lexer = create("pre$(a)post tail"), *child = NULL;
    struct csh_token token = {0};
    struct csh_error error;
    size_t fragment;
    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_COMMAND);
    fragment = csh_lexer_command_fragment(lexer);
    assert(fragment != CSH_FRAGMENT_ROOT);
    assert(csh_lexer_command_begin(lexer, &child, &error) == 0);
    token = word(child, "a");
    substitute(child, &token, "a", "echo hi");
    token = word(child, "echo");
    csh_token_destroy(&token);
    token = word(child, "hi");
    csh_token_destroy(&token);
    assert(csh_lexer_next(child, &token, &error) == CSH_LEX_TOKEN);
    assert(token.kind == CSH_TOKEN_RPAREN);
    assert(csh_lexer_command_end(lexer, child, &token, &error) == 0);
    csh_token_destroy(&token);
    token = word(lexer, "pre$(a)post");
    assert(token.fragments[fragment].begin == 3 && token.fragments[fragment].end == 7);
    assert(token.end.offset == 11);
    csh_token_destroy(&token);
    token = word(lexer, "tail");
    assert(token.start.offset == 12);
    csh_token_destroy(&token);
    eof(lexer);
}

static void split_quote_and_feed(void)
{
    struct csh_lexer *lexer = NULL;
    struct csh_token token = {0};
    struct csh_error error;
    assert(csh_lexer_create(&lexer, "physical-input", &error) == 0);
    assert(csh_lexer_feed(lexer, "a ", 2, 0, &error) == 0);
    token = word(lexer, "a");
    substitute(lexer, &token, "a", "'open");
    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_MORE);
    assert(csh_lexer_feed(lexer, "close' tail", 11, 1, &error) == 0);
    token = word(lexer, "'open  close'");
    assert(strcmp(token.source_name, "alias:a") == 0);
    assert(token.fragments[0].begin == 0 && token.fragments[0].end == token.length);
    csh_token_destroy(&token);
    token = word(lexer, "tail");
    assert(token.start.offset == 9);
    csh_token_destroy(&token);
    eof(lexer);
}

static void diagnostic_positions(void)
{
    struct csh_lexer *lexer = create("   a )"), *child = NULL;
    struct csh_token token = word(lexer, "a");
    struct csh_error error;
    struct csh_position local = {19, 4, 7}, mapped;
    const char *context;
    mapped = csh_lexer_diagnostic_position(lexer, local);
    assert(mapped.offset == 19 && mapped.line == 4 && mapped.column == 7);
    substitute(lexer, &token, "a", "$(echo");
    mapped = csh_lexer_diagnostic_position(lexer, local);
    assert(mapped.offset == 3 && mapped.line == 1 && mapped.column == 4);
    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_COMMAND);
    assert(csh_lexer_context(lexer, &context, &local));
    mapped = csh_lexer_diagnostic_position(lexer, local);
    assert(mapped.offset == 3 && mapped.line == 1 && mapped.column == 4);
    assert(csh_lexer_command_begin(lexer, &child, &error) == 0);
    token = word(child, "echo");
    csh_token_destroy(&token);
    assert(csh_lexer_next(child, &token, &error) == CSH_LEX_TOKEN);
    assert(token.kind == CSH_TOKEN_RPAREN);
    assert(!csh_lexer_alias_active(lexer, "a"));
    /* The alias input is exhausted, but the suspended parent word retains
     * the source of its opening context until publication. */
    mapped = csh_lexer_diagnostic_position(lexer, local);
    assert(mapped.offset == 3 && mapped.line == 1 && mapped.column == 4);
    assert(csh_lexer_command_end(lexer, child, &token, &error) == 0);
    csh_token_destroy(&token);
    token = word(lexer, "$(echo  )");
    csh_token_destroy(&token);
    mapped = csh_lexer_diagnostic_position(lexer, local);
    assert(mapped.offset == local.offset && mapped.line == local.line &&
        mapped.column == local.column);
    eof(lexer);

    lexer = create("   a");
    token = word(lexer, "a");
    substitute(lexer, &token, "a", "echo $(");
    token = word(lexer, "echo");
    csh_token_destroy(&token);
    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_COMMAND);
    assert(csh_lexer_command_begin(lexer, &child, &error) == 0);
    assert(csh_lexer_next(child, &token, &error) == CSH_LEX_ERROR);
    assert(strcmp(error.message, "unterminated command substitution") == 0);
    assert(error.position.offset == 3 && error.position.line == 1 &&
        error.position.column == 4);
    csh_lexer_destroy(lexer);
}

static void syntax_and_error_cleanup(void)
{
    struct csh_lexer *lexer = create("a tail");
    struct csh_token token = word(lexer, "a");
    struct csh_error error;
    substitute(lexer, &token, "a", "echo|");
    token = word(lexer, "echo");
    csh_token_destroy(&token);
    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_TOKEN);
    assert(token.kind == CSH_TOKEN_PIPE && !token.alias_eligible);
    csh_token_destroy(&token);
    token = word(lexer, "tail");
    csh_token_destroy(&token);
    eof(lexer);

    lexer = create("   a");
    token = word(lexer, "a");
    substitute(lexer, &token, "a", "'");
    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_ERROR);
    assert(error.position.offset == 3 && error.position.column == 4);
    assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_ERROR);
    assert(!csh_lexer_alias_active(lexer, "a"));
    csh_lexer_destroy(lexer);
}

int main(void)
{
    chain_and_provenance();
    trailing_blank_and_empty();
    command_frame_spelling();
    split_quote_and_feed();
    diagnostic_positions();
    syntax_and_error_cleanup();
    puts("ok");
    return 0;
}
