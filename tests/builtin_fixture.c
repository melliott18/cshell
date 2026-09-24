#include "cshell/builtin.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state;
    struct csh_variable_view v;
    struct csh_state_info info;
    struct csh_execution result;
    struct csh_error error;
    size_t i;
    struct row { char *args[5]; int status; const char *value; unsigned attrs; size_t count; };
    const struct row rows[] = {
        {{"export", "X=one", NULL}, 0, "one", CSH_VAR_EXPORT, 0},
        {{"readonly", "X", NULL}, 0, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 0},
        {{"export", "X=two", NULL}, 1, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 0},
        {{"unset", "X", NULL}, 1, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 0},
        {{"export", "1bad=x", NULL}, 1, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 0},
        {{"set", "--", "a", "b", NULL}, 0, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 2},
        {{"shift", "0", NULL}, 0, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 2},
        {{"shift", "3", NULL}, 1, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 2},
        {{"shift", "-1", NULL}, 1, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 2},
        {{"shift", "9999999999999999999999999", NULL}, 1, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 2},
        {{"shift", NULL}, 0, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 1},
        {{"set", "--", NULL}, 0, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 0},
        {{"unset", "-v", "missing", NULL}, 0, "one", CSH_VAR_EXPORT|CSH_VAR_READONLY, 0}
    };
    invocation.arg0 = "builtin-fixture";
    assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
    for (i = 0; i < sizeof(rows)/sizeof(*rows); ++i) {
        size_t argc = 0;
        while (rows[i].args[argc]) ++argc;
        assert(csh_state_builtin_run(state, argc, rows[i].args) == rows[i].status);
        assert(csh_state_get_variable(state, "X", &v) == CSH_STATE_OK);
        assert(v.value && !strcmp(v.value, rows[i].value) && v.attributes == rows[i].attrs);
        csh_state_get_info(state, &info);
        assert(info.argument_count == rows[i].count);
        assert(!strcmp(csh_state_parameter(state, 0), "builtin-fixture"));
        if (i == 10) assert(!strcmp(csh_state_parameter(state, 1), "b"));
    }
    {
        char *args[] = {":", NULL};
        struct csh_assignment a = {"PERSIST", "yes"};
        struct csh_command command = {0};
        struct csh_redirect redirection = {0};
        command.argv = args; command.argc = 1; command.assignments = &a; command.assignment_count = 1;
        assert(csh_execute_command(state, &command, &result, &error) == 0);
        assert(result.category == CSH_EXEC_SPECIAL_BUILTIN && !result.special_builtin_error);
        csh_state_get_variable(state, "PERSIST", &v); assert(!strcmp(v.value, "yes"));
        a.value = "after-error";
        redirection.kind = CSH_REDIRECT_READ; redirection.fd = 0; redirection.path = "/nonexistent-cshell-029/input";
        command.redirections = &redirection; command.redirection_count = 1;
        assert(csh_execute_command(state, &command, &result, &error) == -1);
        assert(result.special_builtin_error);
        csh_state_get_variable(state, "PERSIST", &v); assert(!strcmp(v.value, "after-error"));
        {
            char *bad_args[] = {"export", "X=changed", NULL};
            command.redirection_count = 0;
            command.argv = bad_args; command.argc = 2;
            a.value = "builtin-error";
            assert(csh_execute_command(state, &command, &result, &error) == 0);
            assert(result.status == 1 && result.special_builtin_error);
            csh_state_get_variable(state, "PERSIST", &v);
            assert(!strcmp(v.value, "builtin-error"));
        }
        command.argv = args; command.argc = 1;
        a.name = "X";
        assert(csh_execute_command(state, &command, &result, &error) == -1);
        csh_state_get_variable(state, "X", &v); assert(!strcmp(v.value, "one"));
    }
    csh_state_destroy(state);
    puts("builtin API checks passed");
    return 0;
}
