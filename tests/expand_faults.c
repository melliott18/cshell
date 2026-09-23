#define CSHELL_EXPAND_FAULT_IMPLEMENTATION
#include "expand_faults.h"
#include "cshell/expand.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

static void *allocations[16384];
static size_t live_allocations;
static size_t allocation_calls;
static size_t fail_allocation;

static size_t slot_for(void *pointer)
{
    size_t index;
    for (index = 0; index < sizeof(allocations) / sizeof(allocations[0]); ++index) {
        if (allocations[index] == pointer)
            return index;
    }
    assert(!"untracked pointer or exhausted allocation table");
    return 0;
}

static int fail_now(void)
{
    ++allocation_calls;
    if (allocation_calls == fail_allocation) {
        errno = ENOMEM;
        return 1;
    }
    return 0;
}

void *csh_expand_fault_malloc(size_t size)
{
    void *pointer;
    if (fail_now())
        return NULL;
    pointer = malloc(size);
    assert(pointer != NULL);
    allocations[slot_for(NULL)] = pointer;
    ++live_allocations;
    return pointer;
}

void *csh_expand_fault_realloc(void *pointer, size_t size)
{
    size_t slot = slot_for(pointer);
    void *result;
    if (fail_now())
        return NULL;
    if (pointer == NULL)
        ++live_allocations;
    result = realloc(pointer, size);
    assert(result != NULL);
    allocations[slot] = result;
    return result;
}

void csh_expand_fault_free(void *pointer)
{
    if (pointer == NULL)
        return;
    allocations[slot_for(pointer)] = NULL;
    --live_allocations;
    free(pointer);
}

static void variable_is(struct csh_state *state, const char *name,
    const char *value, unsigned attributes)
{
    struct csh_variable_view actual;
    assert(csh_state_get_variable(state, name, &actual) == CSH_STATE_OK);
    assert(actual.attributes == attributes);
    assert(value == NULL ? actual.value == NULL :
        actual.value != NULL && strcmp(value, actual.value) == 0);
}

static enum csh_expand_result substitute(void *user, struct csh_state *state,
    const struct csh_token *token, size_t fragment, const char **bytes,
    size_t *length, struct csh_expand_error *error)
{
    const char *args[] = {"replaced", "arguments"};
    (void)user;
    (void)error;
    assert(token->fragments[fragment].kind == CSH_FRAGMENT_BACKQUOTE);
    assert(csh_state_set_variable(state, "existing", "changed") == CSH_STATE_OK);
    assert(csh_state_update_attributes(state, "existing", CSH_VAR_READONLY, 0) ==
        CSH_STATE_OK);
    assert(csh_state_set_parameters(state, 2, args) == CSH_STATE_OK);
    assert(csh_state_set_status(state, 123) == CSH_STATE_OK);
    assert(csh_state_set_background(state, 12345) == CSH_STATE_OK);
    assert(csh_state_update_options(state, CSH_OPT_XTRACE, 0) == CSH_STATE_OK);
    *bytes = "callback-owned string with * and spaces";
    *length = strlen(*bytes);
    return CSH_EXPAND_OK;
}

static void sweep(const char *source, enum csh_expand_context context)
{
    struct csh_lexer *lexer;
    struct csh_token token = {0};
    struct csh_error lex_error;
    const char *args[] = {"first", "", "last words"};
    size_t point;
    assert(csh_lexer_create(&lexer, "expansion-allocation-fault", &lex_error) == 0);
    assert(csh_lexer_feed(lexer, source, strlen(source), 1, &lex_error) == 0);
    {
        enum csh_lex_result result = csh_lexer_next(lexer, &token, &lex_error);
        if (result != CSH_LEX_TOKEN)
            fprintf(stderr, "fault fixture could not lex %.100s: %d %s\n", source,
                result, lex_error.message);
        assert(result == CSH_LEX_TOKEN);
    }
    assert(token.kind == CSH_TOKEN_WORD);
    csh_lexer_destroy(lexer);
    for (point = 1; point < 10000; ++point) {
        struct csh_invocation invocation = {0};
        struct csh_state *state;
        struct csh_state_info before, after;
        struct csh_expansion out = {0};
        struct csh_expand_error error;
        struct csh_expand_options options = {context, substitute, NULL};
        enum csh_expand_result result;
        invocation.arg0 = "fault-zero";
        invocation.mode = CSH_MODE_STRING;
        assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
        assert(csh_state_set_variable(state, "existing", "unchanged") == CSH_STATE_OK);
        assert(csh_state_update_attributes(state, "existing", CSH_VAR_EXPORT, 0) == CSH_STATE_OK);
        assert(csh_state_set_variable(state, "HOME", "/home/test") == CSH_STATE_OK);
        assert(csh_state_set_variable(state, "path", "abcabc") == CSH_STATE_OK);
        assert(csh_state_set_variable(state, "pattern", "a*c") == CSH_STATE_OK);
        assert(csh_state_set_variable(state, "number", "4") == CSH_STATE_OK);
        assert(csh_state_set_parameters(state, 3, args) == CSH_STATE_OK);
        assert(csh_state_set_status(state, 7) == CSH_STATE_OK);
        assert(csh_state_set_background(state, 42) == CSH_STATE_OK);
        assert(csh_state_get_info(state, &before) == CSH_STATE_OK);
        assert(live_allocations == 0);
        allocation_calls = 0;
        fail_allocation = point;
        result = csh_expand_word(state, &token, &options, &out, &error);
        if (result == CSH_EXPAND_OK) {
            assert(point > allocation_calls);
        } else {
            if (result != CSH_EXPAND_NOMEM)
                fprintf(stderr, "fault source %s point %zu: %d %s\n", source,
                    point, result, error.message);
            assert(result == CSH_EXPAND_NOMEM && error.code == CSH_EXPAND_NOMEM);
            assert(point <= allocation_calls);
            assert(out.fields == NULL && out.field_count == 0);
            assert(error.message[0] != '\0');
            variable_is(state, "existing", "unchanged", CSH_VAR_EXPORT);
            variable_is(state, "new", NULL, 0);
            variable_is(state, "later", NULL, 0);
            variable_is(state, "nested", NULL, 0);
            variable_is(state, "number", "4", 0);
            assert(csh_state_get_info(state, &after) == CSH_STATE_OK);
            assert(before.argument_count == after.argument_count);
            assert(before.last_status == after.last_status);
            assert(before.shell_pid == after.shell_pid);
            assert(before.background_pid == after.background_pid);
            assert(before.mode == after.mode && before.options == after.options);
            assert(strcmp(csh_state_parameter(state, 0), "fault-zero") == 0);
            assert(strcmp(csh_state_parameter(state, 1), "first") == 0);
            assert(strcmp(csh_state_parameter(state, 2), "") == 0);
            assert(strcmp(csh_state_parameter(state, 3), "last words") == 0);
        }
        fail_allocation = 0;
        csh_expansion_destroy(&out);
        assert(live_allocations == 0);
        csh_state_destroy(state);
        if (result == CSH_EXPAND_OK) {
            csh_token_destroy(&token);
            return;
        }
    }
    assert(!"expansion allocation sweep did not converge");
}

int main(void)
{
    char large[16384];
    size_t index;
    sweep("literal", CSH_EXPAND_ARGUMENT);
    sweep("''", CSH_EXPAND_ARGUMENT);
    sweep("pre\"$@\"post", CSH_EXPAND_ARGUMENT);
    sweep("\"$*\"", CSH_EXPAND_ARGUMENT);
    sweep("~/a:~/b", CSH_EXPAND_ASSIGNMENT);
    sweep("${new:=${absent:-${nested:=deep}}}${later:=tail}", CSH_EXPAND_ARGUMENT);
    sweep("${new:=set}${path#${absent:-a*c}}${path%%\"$pattern\"}", CSH_EXPAND_ARGUMENT);
    sweep("${new:=set}$'a\\101\\x42\\cC\\0discarded'last", CSH_EXPAND_ARGUMENT);
    sweep("${new:=set}$((number += 3))${later:=tail}", CSH_EXPAND_ARGUMENT);
    sweep("${new:=set}`selected`${later:=tail}", CSH_EXPAND_ARGUMENT);
    sweep("${new:=set}`selected`${later:=tail}", CSH_EXPAND_PATTERN);
    memcpy(large, "${new:=set}$'", sizeof("${new:=set}$'") - 1);
    for (index = sizeof("${new:=set}$'") - 1; index < sizeof(large) - 2; ++index)
        large[index] = 'x';
    large[sizeof(large) - 2] = '\'';
    large[sizeof(large) - 1] = '\0';
    sweep(large, CSH_EXPAND_ARGUMENT);
    puts("PASS: every expansion/decoder allocation failure, cleanup, full-state rollback");
    return 0;
}
