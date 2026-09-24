/* Resolved-dispatch contract checks, not full builtin/function implementations. */
#include "cshell/execute.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void variable(struct csh_state *state, const char *name,
    const char *value, unsigned attributes)
{
    struct csh_variable_view view;
    assert(csh_state_get_variable(state, name, &view) == CSH_STATE_OK);
    assert(view.attributes == attributes);
    assert(value == NULL ? view.value == NULL :
        view.value != NULL && strcmp(view.value, value) == 0);
}

struct probe { int calls, failure, nested; };

static int handler(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result, struct csh_error *error, void *context)
{
    struct probe *probe = context;
    unsigned attributes = result->category == CSH_EXEC_SPECIAL_BUILTIN ? 0 : CSH_VAR_EXPORT;
    (void)command;
    ++probe->calls;
    variable(state, "PREFIX", probe->nested ? "inner" : "last", attributes);
    if (!probe->nested) {
        struct csh_assignment assignment = {"PREFIX", "inner"};
        char *argv[] = {"nested", NULL};
        struct csh_command inner = {0};
        struct csh_execution nested_result;
        struct csh_error nested_error;
        struct probe nested = {0, 1, 1};
        inner.argv = argv;
        inner.argc = 1;
        inner.assignments = &assignment;
        inner.assignment_count = 1;
        assert(csh_execute_resolved(state, &inner, CSH_EXEC_FUNCTION, handler,
            &nested, &nested_result, &nested_error) == -1);
        assert(nested.calls == 1 && nested_result.status == 7);
        variable(state, "PREFIX", "last", attributes);
    }
    assert(csh_state_set_variable(state, "PREFIX", "handler") == CSH_STATE_OK);
    assert(csh_state_update_attributes(state, "PREFIX", CSH_VAR_READONLY, 0) == CSH_STATE_OK);
    assert(csh_state_set_variable(state, "UNRELATED", "kept") == CSH_STATE_OK);
    assert(csh_state_update_options(state, CSH_OPT_NOUNSET, 0) == CSH_STATE_OK);
    { const char *parameters[] = {"retained"};
      assert(csh_state_set_parameters(state, 1, parameters) == CSH_STATE_OK); }
    if (probe->failure) {
        error->message = "fixture handler failure";
        error->status = 7;
        return -1;
    }
    result->status = 9;
    result->exit_requested = 1;
    return 0;
}

int main(void)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state = NULL, *copy = NULL;
    struct csh_state_checkpoint *checkpoint = NULL;
    struct csh_variable_save *save = NULL, *inner = NULL;
    struct csh_command command = {0};
    struct csh_execution result;
    struct csh_error error;
    struct csh_state_info info;
    struct csh_assignment assignments[] = {
        {"PREFIX", "first"}, {"NEW", ""}, {"DECLARED", "set"}, {"PREFIX", "last"}
    };
    const char *names[] = {"PREFIX", "NEW", "DECLARED", "PREFIX"};
    char *argv[] = {"fixture", NULL};
    int category, failure;
    invocation.mode = CSH_MODE_STRING;
    invocation.arg0 = "assignment-fixture";
    assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
    assert(csh_state_set_variable(state, "PREFIX", "original") == CSH_STATE_OK);
    assert(csh_state_update_attributes(state, "DECLARED", CSH_VAR_EXPORT, 0) == CSH_STATE_OK);
    assert(csh_state_save(state, &checkpoint) == CSH_STATE_OK);
    command.assignments = assignments;
    command.assignment_count = 4;
    assert(csh_execute_command(state, &command, &result, &error) == 0);
    variable(state, "PREFIX", "last", 0);
    variable(state, "NEW", "", 0);
    variable(state, "DECLARED", "set", CSH_VAR_EXPORT);
    assert(csh_state_restore(state, &checkpoint) == CSH_STATE_OK);
    assert(csh_state_save_variables(state, 4, names, &save) == CSH_STATE_OK);
    assert(csh_state_set_variable(state, "PREFIX", "outer") == CSH_STATE_OK);
    assert(csh_state_save_variables(state, 4, names, &inner) == CSH_STATE_OK);
    assert(csh_state_unset_variable(state, "PREFIX") == CSH_STATE_OK);
    assert(csh_state_restore_variables(state, &inner) == CSH_STATE_OK && inner == NULL);
    variable(state, "PREFIX", "outer", 0);
    assert(csh_state_restore_variables(state, &save) == CSH_STATE_OK && save == NULL);
    variable(state, "PREFIX", "original", 0);
    assert(csh_state_save_variables(state, 0, NULL, &save) == CSH_STATE_OK);
    assert(csh_state_restore_variables(state, &save) == CSH_STATE_OK);
    { const char *invalid[] = {"PREFIX", "bad-name"};
      assert(csh_state_save_variables(state, 2, invalid, &save) == CSH_STATE_INVALID);
      assert(save == NULL); }
    command.argv = argv;
    command.argc = 1;
    for (category = CSH_EXEC_REGULAR_BUILTIN; category <= CSH_EXEC_FUNCTION; ++category) {
        for (failure = 0; failure < 2; ++failure) {
            struct probe probe = {0, failure, 0};
            assert(csh_state_clone(state, &copy) == CSH_STATE_OK);
            assert(csh_execute_resolved(copy, &command, category, handler, &probe,
                &result, &error) == (failure ? -1 : 0));
            assert(probe.calls == 1 && result.status == (failure ? 7 : 9));
            assert(result.exit_requested == !failure);
            variable(copy, "PREFIX", category == CSH_EXEC_SPECIAL_BUILTIN ? "handler" : "original",
                category == CSH_EXEC_SPECIAL_BUILTIN ? CSH_VAR_READONLY : 0);
            variable(copy, "NEW", category == CSH_EXEC_SPECIAL_BUILTIN ? "" : NULL, 0);
            variable(copy, "DECLARED", category == CSH_EXEC_SPECIAL_BUILTIN ? "set" : NULL, CSH_VAR_EXPORT);
            variable(copy, "UNRELATED", "kept", 0);
            assert(strcmp(csh_state_parameter(copy, 1), "retained") == 0);
            assert(csh_state_get_info(copy, &info) == CSH_STATE_OK);
            assert(info.last_status == result.status && (info.options & CSH_OPT_NOUNSET));
            csh_state_destroy(copy);
            copy = NULL;
            variable(state, "PREFIX", "original", 0);
            variable(state, "UNRELATED", NULL, 0);
        }
    }
    /* Redirection failure restores temporary prefixes; persistent assignments
     * have already committed before special-builtin redirection is attempted. */
    for (category = CSH_EXEC_REGULAR_BUILTIN; category <= CSH_EXEC_FUNCTION; ++category) {
        struct probe probe = {0};
        struct csh_redirect redirect = {0};
        redirect.kind = CSH_REDIRECT_READ;
        redirect.fd = 0;
        redirect.path = "missing-assignment-directory/input";
        command.redirections = &redirect;
        command.redirection_count = 1;
        assert(csh_state_clone(state, &copy) == CSH_STATE_OK);
        assert(csh_execute_resolved(copy, &command, category, handler, &probe,
            &result, &error) == -1);
        assert(probe.calls == 0 && result.status != 0);
        variable(copy, "PREFIX", category == CSH_EXEC_SPECIAL_BUILTIN ? "last" : "original", 0);
        variable(copy, "NEW", category == CSH_EXEC_SPECIAL_BUILTIN ? "" : NULL, 0);
        csh_state_destroy(copy);
        copy = NULL;
    }
    /* Readonly is fatal only to the active noninteractive execution context,
     * for every category. No earlier assignment, redirection, or handler runs. */
    assert(csh_state_update_attributes(state, "NEW", CSH_VAR_READONLY, 0) == CSH_STATE_OK);
    for (category = CSH_EXEC_EMPTY; category <= CSH_EXEC_FUNCTION; ++category) {
        int interactive;
        for (interactive = 0; interactive < 2; ++interactive) {
            struct probe probe = {0};
            struct csh_redirect redirect = {0};
            redirect.kind = CSH_REDIRECT_WRITE;
            redirect.fd = 1;
            redirect.path = "readonly-must-not-create";
            command.redirections = &redirect;
            command.redirection_count = 1;
            command.argc = category == CSH_EXEC_EMPTY ? 0 : 1;
            assert(csh_state_update_options(state, interactive ? CSH_OPT_INTERACTIVE : 0,
                interactive ? 0 : CSH_OPT_INTERACTIVE) == CSH_STATE_OK);
            assert(csh_execute_resolved(state, &command, category,
                category >= CSH_EXEC_REGULAR_BUILTIN ? handler : NULL, &probe,
                &result, &error) == -1);
            assert(probe.calls == 0 && result.status == 1);
            assert(result.exit_requested == !interactive);
            assert(strcmp(error.message, "cannot assign to readonly variable") == 0);
            assert(access(redirect.path, F_OK) == -1);
            variable(state, "PREFIX", "original", 0);
            variable(state, "NEW", NULL, CSH_VAR_READONLY);
        }
    }
    command.redirections = NULL;
    command.redirection_count = 0;
    command.argv = NULL;
    command.argc = 0;
    command.assignment_count = 1;
    assert(csh_state_update_options(state, CSH_OPT_ALLEXPORT, 0) == CSH_STATE_OK);
    assert(csh_execute_command(state, &command, &result, &error) == 0);
    variable(state, "PREFIX", "first", CSH_VAR_EXPORT);
    csh_state_destroy(state);
    puts("assignment dispatch checks passed");
    return 0;
}
