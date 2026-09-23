#define CSHELL_ARITHMETIC_FAULT_IMPLEMENTATION
#include "arithmetic_faults.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>

#include "cshell/arithmetic.h"
#include "cshell/state.h"

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #condition); \
        exit(1); \
    } \
} while (0)

static void *allocations[4096];
static size_t live_allocations;
static size_t allocation_calls;
static size_t fail_allocation;

static size_t slot(void *pointer)
{
    size_t index;
    for (index = 0; index < sizeof(allocations) / sizeof(allocations[0]); ++index) {
        if (allocations[index] == pointer)
            return index;
    }
    CHECK(!"untracked allocation or exhausted allocation table");
    return 0;
}

void *csh_arith_fault_malloc(size_t size)
{
    void *pointer;
    ++allocation_calls;
    if (allocation_calls == fail_allocation) {
        errno = ENOMEM;
        return NULL;
    }
    pointer = malloc(size);
    CHECK(pointer != NULL);
    allocations[slot(NULL)] = pointer;
    ++live_allocations;
    return pointer;
}

void csh_arith_fault_free(void *pointer)
{
    if (pointer == NULL)
        return;
    allocations[slot(pointer)] = NULL;
    CHECK(live_allocations != 0);
    --live_allocations;
    free(pointer);
}

static struct csh_state *new_state(void)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state = NULL;
    char *arguments[] = {"one", "", "three"};
    char *environment[] = {"x=7", "locked=5", "unchanged=value", NULL};
    CHECK(live_allocations == 0);
    allocation_calls = 0;
    fail_allocation = 0;
    invocation.mode = CSH_MODE_STDIN;
    invocation.arg0 = "arithmetic-faults";
    invocation.argument_count = 3;
    invocation.arguments = arguments;
    CHECK(csh_state_create(&state, &invocation, environment) == CSH_STATE_OK);
    CHECK(csh_state_update_attributes(state, "locked", CSH_VAR_READONLY, 0) ==
        CSH_STATE_OK);
    CHECK(csh_state_update_attributes(state, "unset", CSH_VAR_EXPORT, 0) ==
        CSH_STATE_OK);
    CHECK(csh_state_update_options(state, CSH_OPT_ALLEXPORT | CSH_OPT_NOUNSET, 0) ==
        CSH_STATE_OK);
    CHECK(csh_state_set_status(state, 19) == CSH_STATE_OK);
    CHECK(csh_state_set_background(state, (pid_t)321) == CSH_STATE_OK);
    return state;
}

static void variable_is(struct csh_state *state, const char *name,
    const char *expected, unsigned attributes)
{
    struct csh_variable_view view;
    CHECK(csh_state_get_variable(state, name, &view) == CSH_STATE_OK);
    CHECK(expected == NULL ? view.value == NULL :
        view.value != NULL && strcmp(view.value, expected) == 0);
    CHECK(view.attributes == attributes);
}

static void original_state(struct csh_state *state, struct csh_state_info saved)
{
    struct csh_state_info info;
    variable_is(state, "x", "7", CSH_VAR_EXPORT);
    variable_is(state, "locked", "5", CSH_VAR_EXPORT | CSH_VAR_READONLY);
    variable_is(state, "unchanged", "value", CSH_VAR_EXPORT);
    variable_is(state, "unset", NULL, CSH_VAR_EXPORT);
    variable_is(state, "fresh", NULL, 0);
    variable_is(state, "nested", NULL, 0);
    CHECK(strcmp(csh_state_parameter(state, 0), "arithmetic-faults") == 0);
    CHECK(strcmp(csh_state_parameter(state, 1), "one") == 0);
    CHECK(strcmp(csh_state_parameter(state, 2), "") == 0);
    CHECK(strcmp(csh_state_parameter(state, 3), "three") == 0);
    CHECK(csh_state_get_info(state, &info) == CSH_STATE_OK);
    CHECK(info.argument_count == saved.argument_count);
    CHECK(info.last_status == saved.last_status);
    CHECK(info.shell_pid == saved.shell_pid);
    CHECK(info.background_pid == saved.background_pid);
    CHECK(info.mode == saved.mode);
    CHECK(info.options == saved.options);
}

static void sweep(const char *expression, enum csh_arith_result final_result)
{
    size_t point;
    for (point = 1; point < 256; ++point) {
        struct csh_state *state = new_state();
        struct csh_state_info saved;
        size_t original_allocations = live_allocations;
        size_t used;
        long number = 9876;
        enum csh_arith_result result;
        CHECK(csh_state_get_info(state, &saved) == CSH_STATE_OK);
        allocation_calls = 0;
        fail_allocation = point;
        result = csh_arith_eval(state, expression, &number);
        used = allocation_calls;
        fail_allocation = 0;
        if (used >= point) {
            CHECK(result == CSH_ARITH_NOMEM);
            CHECK(number == 9876);
            CHECK(live_allocations == original_allocations);
            original_state(state, saved);
        } else {
            CHECK(result == final_result);
            if (result != CSH_ARITH_OK) {
                CHECK(number == 9876);
                CHECK(live_allocations == original_allocations);
                original_state(state, saved);
            } else {
                CHECK(number == 3);
                variable_is(state, "x", "33", CSH_VAR_EXPORT);
                variable_is(state, "fresh", "22", CSH_VAR_EXPORT);
                variable_is(state, "nested", "3", CSH_VAR_EXPORT);
            }
        }
        csh_state_destroy(state);
        CHECK(live_allocations == 0);
        if (used < point)
            break;
    }
    CHECK(point < 256);
}

int main(void)
{
    sweep("x=11, (fresh=x*2), x+=fresh, x ? (nested=3) : 0", CSH_ARITH_OK);
    sweep("x=11, (fresh=x*2), locked=3", CSH_ARITH_READONLY);
    sweep("x=11, (fresh=x*2), (1/0+2)", CSH_ARITH_RANGE);
    sweep("x=11, (fresh=x*2), 1 ? (nested=3) : (2+)", CSH_ARITH_SYNTAX);
    puts("arithmetic allocation failure fixtures passed");
    return 0;
}
