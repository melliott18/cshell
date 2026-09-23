#define CSHELL_STATE_FAULT_IMPLEMENTATION
#include "state_faults.h"
#include "cshell/state.h"

/* Keep setup and checks active when the caller supplies release CFLAGS. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define SWEEP_LIMIT 256

static void *allocations[4096];
static size_t live_allocations;
static size_t allocation_calls;
static size_t fail_allocation;

static char *initial_arguments[] = {"alpha", "", "omega", NULL};
static char *initial_environment[] = {
    "KEEP=kept", "DUP=old", "not valid=ignored", "DUP=imported", "EMPTY=",
    "READONLY=fixed", "9BAD=ignored", "NO_EQUALS", "=ignored", NULL
};

static size_t allocation_slot(void *pointer)
{
    size_t index;
    for (index = 0; index < sizeof(allocations) / sizeof(allocations[0]); ++index) {
        if (allocations[index] == pointer)
            return index;
    }
    assert(!"untracked allocation or exhausted allocation table");
    return 0;
}

void *csh_state_fault_malloc(size_t size)
{
    void *pointer;
    ++allocation_calls;
    if (allocation_calls == fail_allocation) {
        errno = ENOMEM;
        return NULL;
    }
    pointer = malloc(size);
    assert(pointer != NULL);
    allocations[allocation_slot(NULL)] = pointer;
    ++live_allocations;
    return pointer;
}

void csh_state_fault_free(void *pointer)
{
    if (pointer == NULL)
        return;
    allocations[allocation_slot(pointer)] = NULL;
    assert(live_allocations != 0);
    --live_allocations;
    free(pointer);
}

static void reset_faults(void)
{
    assert(live_allocations == 0);
    allocation_calls = 0;
    fail_allocation = 0;
}

static void arm_fault(size_t point)
{
    allocation_calls = 0;
    fail_allocation = point;
}

static struct csh_invocation invocation(void)
{
    struct csh_invocation result = {0};
    result.mode = CSH_MODE_STRING;
    result.interactive = true;
    result.arg0 = "fault-shell";
    result.argument_count = 3;
    result.arguments = initial_arguments;
    return result;
}

static void check_variable(const struct csh_state *state, const char *name,
    const char *value, unsigned attributes)
{
    struct csh_variable_view view;
    assert(csh_state_get_variable(state, name, &view) == CSH_STATE_OK);
    assert(view.attributes == attributes);
    if (value == NULL)
        assert(view.value == NULL);
    else
        assert(view.value != NULL && strcmp(view.value, value) == 0);
}

static const char *variable_value(const struct csh_state *state, const char *name)
{
    struct csh_variable_view view;
    assert(csh_state_get_variable(state, name, &view) == CSH_STATE_OK);
    assert(view.value != NULL);
    return view.value;
}

static void check_info(const struct csh_state *state, size_t count, int status,
    pid_t background, unsigned options)
{
    struct csh_state_info info;
    assert(csh_state_get_info(state, &info) == CSH_STATE_OK);
    assert(info.argument_count == count);
    assert(info.last_status == status);
    assert(info.shell_pid == getpid());
    assert(info.background_pid == background);
    assert(info.mode == CSH_MODE_STRING);
    assert(info.options == options);
    assert(strcmp(csh_state_parameter(state, 0), "fault-shell") == 0);
    assert(csh_state_parameter(state, count + 1) == NULL);
}

static void check_parameters(const struct csh_state *state)
{
    size_t index;
    for (index = 0; index < 3; ++index)
        assert(strcmp(csh_state_parameter(state, index + 1),
            initial_arguments[index]) == 0);
}

static void check_import(const struct csh_state *state, int has_environment)
{
    check_variable(state, "KEEP", has_environment ? "kept" : NULL,
        has_environment ? CSH_VAR_EXPORT : 0);
    check_variable(state, "DUP", has_environment ? "imported" : NULL,
        has_environment ? CSH_VAR_EXPORT : 0);
    check_variable(state, "EMPTY", has_environment ? "" : NULL,
        has_environment ? CSH_VAR_EXPORT : 0);
    check_variable(state, "READONLY", has_environment ? "fixed" : NULL,
        has_environment ? CSH_VAR_EXPORT : 0);
    check_variable(state, "NO_EQUALS", NULL, 0);
}

static void check_baseline(const struct csh_state *state)
{
    check_variable(state, "KEEP", "kept", CSH_VAR_EXPORT);
    check_variable(state, "DUP", "imported", CSH_VAR_EXPORT);
    check_variable(state, "EMPTY", "", CSH_VAR_EXPORT);
    check_variable(state, "READONLY", "fixed", CSH_VAR_EXPORT | CSH_VAR_READONLY);
    check_variable(state, "HIDDEN", "private", 0);
    check_variable(state, "ALIAS_NAME", "ALIAS_NAME", 0);
    check_variable(state, "UNSET", NULL, CSH_VAR_EXPORT | CSH_VAR_READONLY);
    check_variable(state, "PENDING", NULL, CSH_VAR_EXPORT);
    check_variable(state, "LOCKED", NULL, CSH_VAR_READONLY);
    check_variable(state, "NEW", NULL, 0);
    check_variable(state, "DECLARED", NULL, 0);
    check_info(state, 3, 37, (pid_t)1234,
        CSH_OPT_INTERACTIVE | CSH_OPT_NOUNSET | CSH_OPT_XTRACE);
    check_parameters(state);
}

static struct csh_state *make_baseline(void)
{
    struct csh_invocation input = invocation();
    struct csh_state *state = NULL;
    assert(csh_state_create(&state, &input, initial_environment) == CSH_STATE_OK);
    assert(csh_state_update_attributes(state, "READONLY", CSH_VAR_READONLY, 0)
        == CSH_STATE_OK);
    assert(csh_state_set_variable(state, "HIDDEN", "private") == CSH_STATE_OK);
    assert(csh_state_set_variable(state, "ALIAS_NAME", "ALIAS_NAME") == CSH_STATE_OK);
    assert(csh_state_update_attributes(state, "UNSET",
        CSH_VAR_EXPORT | CSH_VAR_READONLY, 0) == CSH_STATE_OK);
    assert(csh_state_update_attributes(state, "LOCKED", CSH_VAR_READONLY, 0)
        == CSH_STATE_OK);
    assert(csh_state_update_attributes(state, "PENDING", CSH_VAR_EXPORT, 0)
        == CSH_STATE_OK);
    assert(csh_state_set_status(state, 37) == CSH_STATE_OK);
    assert(csh_state_set_background(state, (pid_t)1234) == CSH_STATE_OK);
    assert(csh_state_update_options(state, CSH_OPT_NOUNSET | CSH_OPT_XTRACE, 0)
        == CSH_STATE_OK);
    check_baseline(state);
    return state;
}

static void check_create_failures(void)
{
    unsigned variant;
    for (variant = 0; variant < 4; ++variant) {
        size_t point;
        for (point = 1; point < SWEEP_LIMIT; ++point) {
            struct csh_invocation input = invocation();
            /* A non-NULL sentinel ensures failure actually clears the output. */
            struct csh_state *state = (struct csh_state *)&input;
            enum csh_state_result result;
            int has_environment = (variant & 1u) != 0;
            if ((variant & 2u) == 0) {
                input.argument_count = 0;
                input.arguments = NULL;
            }
            reset_faults();
            arm_fault(point);
            result = csh_state_create(&state, &input,
                has_environment ? initial_environment : NULL);
            if (result == CSH_STATE_NOMEM) {
                assert(state == NULL);
                assert(allocation_calls >= point);
            } else {
                assert(result == CSH_STATE_OK && state != NULL);
                assert(allocation_calls < point);
                check_import(state, has_environment);
                check_info(state, input.argument_count, 0, 0, CSH_OPT_INTERACTIVE);
                if (input.argument_count != 0)
                    check_parameters(state);
            }
            csh_state_destroy(state);
            assert(live_allocations == 0);
            if (result == CSH_STATE_OK)
                break;
        }
        assert(point < SWEEP_LIMIT);
    }
}

enum mutation {
    NEW_VARIABLE,
    REPLACE_VARIABLE,
    REPLACE_EMPTY,
    ASSIGN_UNSET,
    ALIASED_NEW_VALUE,
    ALIASED_REPLACEMENT_VALUE,
    ALIASED_SELF_VALUE,
    ALIASED_NAME,
    DECLARE_ATTRIBUTES,
    REPLACE_PARAMETERS,
    ALIASED_PARAMETERS,
    CLEAR_PARAMETERS,
    MUTATION_COUNT
};

static enum csh_state_result mutate(struct csh_state *state, enum mutation kind)
{
    const char *arguments[] = {"new first", "", "new last", "fourth"};
    const char *aliases[] = {
        csh_state_parameter(state, 3), csh_state_parameter(state, 1),
        variable_value(state, "HIDDEN"), csh_state_parameter(state, 0),
        csh_state_parameter(state, 1)
    };
    switch (kind) {
    case NEW_VARIABLE:
        return csh_state_set_variable(state, "NEW", "new value");
    case REPLACE_VARIABLE:
        return csh_state_set_variable(state, "KEEP", "replacement");
    case REPLACE_EMPTY:
        return csh_state_set_variable(state, "EMPTY", "now filled");
    case ASSIGN_UNSET:
        return csh_state_set_variable(state, "PENDING", "");
    case ALIASED_NEW_VALUE:
        return csh_state_set_variable(state, "NEW", variable_value(state, "HIDDEN"));
    case ALIASED_REPLACEMENT_VALUE:
        return csh_state_set_variable(state, "KEEP", variable_value(state, "HIDDEN"));
    case ALIASED_SELF_VALUE:
        return csh_state_set_variable(state, "KEEP", variable_value(state, "KEEP"));
    case ALIASED_NAME:
        return csh_state_set_variable(state, variable_value(state, "ALIAS_NAME"),
            "name changed");
    case DECLARE_ATTRIBUTES:
        return csh_state_update_attributes(state, "DECLARED",
            CSH_VAR_EXPORT | CSH_VAR_READONLY, 0);
    case REPLACE_PARAMETERS:
        return csh_state_set_parameters(state, 4, arguments);
    case ALIASED_PARAMETERS:
        return csh_state_set_parameters(state, 5, aliases);
    case CLEAR_PARAMETERS:
        return csh_state_set_parameters(state, 0, NULL);
    default:
        assert(!"invalid mutation fixture");
        return CSH_STATE_INVALID;
    }
}

static void check_mutation(const struct csh_state *state, enum mutation kind)
{
    const char *parameters[] = {"new first", "", "new last", "fourth"};
    const char *aliases[] = {"omega", "alpha", "private", "fault-shell", "alpha"};
    size_t index;
    if (kind == REPLACE_PARAMETERS || kind == ALIASED_PARAMETERS ||
        kind == CLEAR_PARAMETERS) {
        size_t count = kind == REPLACE_PARAMETERS ? 4 :
            kind == ALIASED_PARAMETERS ? 5 : 0;
        const char *const *expected = kind == REPLACE_PARAMETERS ? parameters : aliases;
        check_info(state, count, 37, (pid_t)1234,
            CSH_OPT_INTERACTIVE | CSH_OPT_NOUNSET | CSH_OPT_XTRACE);
        for (index = 0; index < count; ++index)
            assert(strcmp(csh_state_parameter(state, index + 1), expected[index]) == 0);
    } else {
        check_info(state, 3, 37, (pid_t)1234,
            CSH_OPT_INTERACTIVE | CSH_OPT_NOUNSET | CSH_OPT_XTRACE);
        check_parameters(state);
    }
    check_variable(state, "KEEP", kind == REPLACE_VARIABLE ? "replacement" :
        kind == ALIASED_REPLACEMENT_VALUE ? "private" : "kept", CSH_VAR_EXPORT);
    check_variable(state, "NEW", kind == NEW_VARIABLE ? "new value" :
        kind == ALIASED_NEW_VALUE ? "private" : NULL, 0);
    check_variable(state, "ALIAS_NAME", kind == ALIASED_NAME ? "name changed" :
        "ALIAS_NAME", 0);
    check_variable(state, "DECLARED", NULL, kind == DECLARE_ATTRIBUTES ?
        CSH_VAR_EXPORT | CSH_VAR_READONLY : 0);
    check_variable(state, "HIDDEN", "private", 0);
    check_variable(state, "DUP", "imported", CSH_VAR_EXPORT);
    check_variable(state, "EMPTY", kind == REPLACE_EMPTY ? "now filled" : "",
        CSH_VAR_EXPORT);
    check_variable(state, "READONLY", "fixed", CSH_VAR_EXPORT | CSH_VAR_READONLY);
    check_variable(state, "UNSET", NULL, CSH_VAR_EXPORT | CSH_VAR_READONLY);
    check_variable(state, "PENDING", kind == ASSIGN_UNSET ? "" : NULL, CSH_VAR_EXPORT);
    check_variable(state, "LOCKED", NULL, CSH_VAR_READONLY);
}

static void check_mutation_failures(void)
{
    enum mutation kind;
    for (kind = NEW_VARIABLE; kind < MUTATION_COUNT; ++kind) {
        size_t point;
        for (point = 1; point < SWEEP_LIMIT; ++point) {
            struct csh_state *state;
            enum csh_state_result result;
            size_t before;
            reset_faults();
            state = make_baseline();
            before = live_allocations;
            arm_fault(point);
            result = mutate(state, kind);
            if (result == CSH_STATE_NOMEM) {
                assert(allocation_calls >= point);
                assert(live_allocations == before);
                check_baseline(state);
            } else {
                assert(result == CSH_STATE_OK);
                assert(allocation_calls < point);
                check_mutation(state, kind);
            }
            csh_state_destroy(state);
            assert(live_allocations == 0);
            if (result == CSH_STATE_OK)
                break;
        }
        assert(point < SWEEP_LIMIT);
    }
}

static void check_environment(char *const environment[])
{
    const char *expected[] = {"KEEP=kept", "DUP=imported", "EMPTY=", "READONLY=fixed"};
    unsigned seen = 0;
    size_t index;
    assert(environment != NULL);
    for (index = 0; environment[index] != NULL; ++index) {
        size_t match;
        assert(index < 4);
        for (match = 0; match < 4; ++match) {
            if (strcmp(environment[index], expected[match]) == 0)
                break;
        }
        assert(match < 4);
        assert((seen & (1u << match)) == 0);
        seen |= 1u << match;
    }
    assert(index == 4 && seen == 15u);
}

static void check_environment_failures(void)
{
    size_t point;
    for (point = 1; point < SWEEP_LIMIT; ++point) {
        struct csh_state *state;
        char **environment = (char **)&state;
        enum csh_state_result result;
        size_t before;
        reset_faults();
        state = make_baseline();
        before = live_allocations;
        arm_fault(point);
        result = csh_state_environment(state, &environment);
        if (result == CSH_STATE_NOMEM) {
            assert(environment == NULL);
            assert(allocation_calls >= point);
            assert(live_allocations == before);
        } else {
            assert(result == CSH_STATE_OK && allocation_calls < point);
            check_environment(environment);
        }
        check_baseline(state);
        csh_state_destroy(state);
        if (result == CSH_STATE_OK)
            check_environment(environment);
        csh_state_environment_destroy(environment);
        assert(live_allocations == 0);
        if (result == CSH_STATE_OK)
            break;
    }
    assert(point < SWEEP_LIMIT);
}

static void check_copy_failures(void)
{
    unsigned save;
    for (save = 0; save < 2; ++save) {
        size_t point;
        for (point = 1; point < SWEEP_LIMIT; ++point) {
            struct csh_state *state;
            struct csh_state *copy = (struct csh_state *)&state;
            struct csh_state_checkpoint *checkpoint =
                (struct csh_state_checkpoint *)&state;
            enum csh_state_result result;
            size_t before;
            reset_faults();
            state = make_baseline();
            before = live_allocations;
            arm_fault(point);
            result = save ? csh_state_save(state, &checkpoint) :
                csh_state_clone(state, &copy);
            if (result == CSH_STATE_NOMEM) {
                assert(save ? checkpoint == NULL : copy == NULL);
                assert(allocation_calls >= point);
                assert(live_allocations == before);
            } else {
                assert(result == CSH_STATE_OK && allocation_calls < point);
                if (save) {
                    fail_allocation = 0;
                    assert(csh_state_set_variable(state, "KEEP", "changed")
                        == CSH_STATE_OK);
                    assert(csh_state_restore(state, &checkpoint) == CSH_STATE_OK);
                    assert(checkpoint == NULL);
                } else {
                    check_baseline(copy);
                    assert(csh_state_parameter(state, 0) != csh_state_parameter(copy, 0));
                    assert(csh_state_parameter(state, 1) != csh_state_parameter(copy, 1));
                    assert(variable_value(state, "KEEP") != variable_value(copy, "KEEP"));
                    fail_allocation = 0;
                    assert(csh_state_set_variable(copy, "KEEP", "changed")
                        == CSH_STATE_OK);
                    csh_state_destroy(copy);
                }
            }
            check_baseline(state);
            csh_state_destroy(state);
            assert(live_allocations == 0);
            if (result == CSH_STATE_OK)
                break;
        }
        assert(point < SWEEP_LIMIT);
    }
}

static void check_allocation_free_restore(void)
{
    struct csh_state *state;
    struct csh_state_checkpoint *checkpoint = NULL;
    struct csh_state_checkpoint *discard = NULL;
    const char *arguments[] = {"changed"};
    reset_faults();
    state = make_baseline();
    assert(csh_state_save(state, &checkpoint) == CSH_STATE_OK);
    assert(csh_state_save(state, &discard) == CSH_STATE_OK);
    assert(csh_state_unset_variable(state, "KEEP") == CSH_STATE_OK);
    assert(csh_state_set_variable(state, "HIDDEN", "changed") == CSH_STATE_OK);
    assert(csh_state_update_attributes(state, "HIDDEN",
        CSH_VAR_READONLY | CSH_VAR_EXPORT, 0) == CSH_STATE_OK);
    assert(csh_state_set_variable(state, "NEW", "discard me") == CSH_STATE_OK);
    assert(csh_state_set_parameters(state, 1, arguments) == CSH_STATE_OK);
    assert(csh_state_set_status(state, 126) == CSH_STATE_OK);
    assert(csh_state_set_background(state, 0) == CSH_STATE_OK);
    assert(csh_state_update_options(state, CSH_OPT_ERREXIT,
        CSH_OPT_INTERACTIVE | CSH_OPT_NOUNSET | CSH_OPT_XTRACE) == CSH_STATE_OK);
    arm_fault(1);
    assert(csh_state_restore(state, &checkpoint) == CSH_STATE_OK);
    assert(checkpoint == NULL);
    assert(allocation_calls == 0);
    check_baseline(state);
    csh_state_checkpoint_destroy(discard);
    csh_state_checkpoint_destroy(NULL);
    csh_state_environment_destroy(NULL);
    csh_state_destroy(state);
    csh_state_destroy(NULL);
    assert(allocation_calls == 0 && live_allocations == 0);
}

int main(void)
{
    check_create_failures();
    check_mutation_failures();
    check_environment_failures();
    check_copy_failures();
    check_allocation_free_restore();
    puts("state allocation faults passed");
    return 0;
}
