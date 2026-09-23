#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cshell/arithmetic.h"
#include "cshell/state.h"

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #condition); \
        exit(1); \
    } \
} while (0)

static struct csh_state *new_state(void)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state = NULL;
    invocation.mode = CSH_MODE_STDIN;
    invocation.arg0 = "arithmetic-fixture";
    CHECK(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
    return state;
}

static void value_is(struct csh_state *state, const char *text, long expected)
{
    long actual = 42;
    enum csh_arith_result result = csh_arith_eval(state, text, &actual);
    if (result != CSH_ARITH_OK || actual != expected) {
        fprintf(stderr, "%s: result %d, value %ld; expected %ld\n", text,
            (int)result, actual, expected);
        exit(1);
    }
    CHECK(csh_arith_probe(text) == CSH_ARITH_OK);
}

static void error_is(struct csh_state *state, const char *text,
    enum csh_arith_result expected)
{
    long number = 1234;
    CHECK(csh_arith_eval(state, text, &number) == expected);
    CHECK(number == 1234);
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

static void operators(void)
{
    static const struct { const char *text; long expected; } cases[] = {
        {"", 0}, {" \t\n", 0}, {"0", 0}, {"077 + 0X10 + 0xff", 334},
        {"2+3*4", 14}, {"(2+3)*4", 20}, {"23 / 5", 4},
        {"-23 / 5", -4}, {"-23 % 5", -3}, {"23 % -5", 3},
        {"10-3-2", 5}, {"+ - + 3", -3}, {"!9 + !0", 1},
        {"~0", -1}, {"1<<3+1", 16}, {"40 >> 2", 10},
        {"-5 >> 1", -3}, {"1<2 == 3>=3", 1},
        {"2<=2 && 3>2 && 3!=4", 1}, {"3==3 || 0", 1},
        {"2<1 || 5<=4", 0}, {"6&3", 2}, {"6^3", 5}, {"6|3", 7},
        {"1 | 2 ^ 3 & 4", 3}, {"1 || 0 && 0", 1},
        {"1?2:3", 2}, {"0?2:3", 3}, {"0?2:0?4:5", 5},
        {"1?0?2:3:4", 3}, {"1?2,3:4", 3}, {"1,2,3", 3},
        {"unset_name+1", 1}
    };
    struct csh_state *state = new_state();
    size_t index;
    for (index = 0; index < sizeof(cases) / sizeof(cases[0]); ++index)
        value_is(state, cases[index].text, cases[index].expected);
    csh_state_destroy(state);
}

static void assignments_and_variables(void)
{
    struct csh_state *state = new_state();
    struct csh_variable_view view;
    struct csh_state_info info;
    long aliased_result = 0;
    CHECK(csh_state_set_variable(state, "x", "not-a-number") == CSH_STATE_OK);
    value_is(state, "x=y=7", 7);
    variable_is(state, "x", "7", 0);
    variable_is(state, "y", "7", 0);
    value_is(state, "x+=3", 10);
    value_is(state, "x-=2", 8);
    value_is(state, "x*=3", 24);
    value_is(state, "x/=4", 6);
    value_is(state, "x%=4", 2);
    value_is(state, "x<<=3", 16);
    value_is(state, "x>>=2", 4);
    value_is(state, "x|=3", 7);
    value_is(state, "x^=2", 5);
    value_is(state, "x&=3", 1);
    value_is(state, "(x)=9", 9);
    value_is(state, "x=2, x+3", 5);
    variable_is(state, "x", "2", 0);
    CHECK(csh_state_set_variable(state, "signed", "-0xA") == CSH_STATE_OK);
    value_is(state, "signed", -10);
    CHECK(csh_state_set_variable(state, "signed", "+077") == CSH_STATE_OK);
    value_is(state, "signed", 63);
    CHECK(csh_state_set_variable(state, "empty", "") == CSH_STATE_OK);
    value_is(state, "empty+1", 1);
    CHECK(csh_state_set_variable(state, "bad", "2+3") == CSH_STATE_OK);
    error_is(state, "bad", CSH_ARITH_SYNTAX);
    CHECK(csh_state_set_variable(state, "bad", " 2") == CSH_STATE_OK);
    error_is(state, "bad", CSH_ARITH_SYNTAX);
    CHECK(csh_state_set_variable(state, "bad", "08") == CSH_STATE_OK);
    error_is(state, "bad", CSH_ARITH_SYNTAX);
    CHECK(csh_state_set_variable(state, "expression", "expression=3,expression+1") ==
        CSH_STATE_OK);
    CHECK(csh_state_get_variable(state, "expression", &view) == CSH_STATE_OK);
    CHECK(csh_arith_eval(state, view.value, &aliased_result) == CSH_ARITH_OK);
    CHECK(aliased_result == 4);
    variable_is(state, "expression", "3", 0);
    CHECK(csh_state_update_options(state, CSH_OPT_ALLEXPORT, 0) == CSH_STATE_OK);
    value_is(state, "exported=2", 2);
    variable_is(state, "exported", "2", CSH_VAR_EXPORT);
    CHECK(csh_state_update_options(state, CSH_OPT_NOUNSET, 0) == CSH_STATE_OK);
    error_is(state, "missing", CSH_ARITH_SYNTAX);
    value_is(state, "missing=4", 4);
    value_is(state, "empty", 0);
    CHECK(csh_state_get_info(state, &info) == CSH_STATE_OK);
    CHECK(info.last_status == 0);
    csh_state_destroy(state);
}

static void short_circuit_and_rollback(void)
{
    struct csh_state *state = new_state();
    CHECK(csh_state_set_variable(state, "x", "4") == CSH_STATE_OK);
    CHECK(csh_state_set_variable(state, "bad", "not arithmetic") == CSH_STATE_OK);
    CHECK(csh_state_set_variable(state, "locked", "8") == CSH_STATE_OK);
    CHECK(csh_state_update_attributes(state, "locked", CSH_VAR_READONLY, 0) ==
        CSH_STATE_OK);
    value_is(state, "0 && (x=5)", 0);
    value_is(state, "1 || (x=5)", 1);
    value_is(state, "1 ? 9 : (x=5)", 9);
    value_is(state, "0 ? (x=5) : 9", 9);
    variable_is(state, "x", "4", 0);
    value_is(state, "0 && 1/0", 0);
    value_is(state, "1 || 1/0", 1);
    value_is(state, "1 ? 3 : bad", 3);
    value_is(state, "0 ? bad : 3", 3);
    value_is(state, "0 && (locked=1)", 0);
    value_is(state, "1 && (x=5)", 1);
    value_is(state, "0 || (x=6)", 1);
    variable_is(state, "x", "6", 0);
    error_is(state, "x=7,1/0", CSH_ARITH_RANGE);
    variable_is(state, "x", "6", 0);
    error_is(state, "new_name=7,1+", CSH_ARITH_SYNTAX);
    variable_is(state, "new_name", NULL, 0);
    error_is(state, "x=9, locked=10", CSH_ARITH_READONLY);
    variable_is(state, "x", "6", 0);
    variable_is(state, "locked", "8", CSH_VAR_READONLY);
    error_is(state, "0 && (1+)", CSH_ARITH_SYNTAX);
    error_is(state, "1 ? 2 : (3=4)", CSH_ARITH_SYNTAX);
    csh_state_destroy(state);
}

static void boundaries(void)
{
    struct csh_state *state = new_state();
    char buffer[256];
    unsigned bits = (unsigned)(sizeof(long) * CHAR_BIT);
    (void)snprintf(buffer, sizeof(buffer), "%ld", LONG_MAX);
    value_is(state, buffer, LONG_MAX);
    CHECK(csh_state_set_variable(state, "max", buffer) == CSH_STATE_OK);
    (void)snprintf(buffer, sizeof(buffer), "%ld", LONG_MIN);
    value_is(state, buffer, LONG_MIN);
    CHECK(csh_state_set_variable(state, "min", buffer) == CSH_STATE_OK);
    value_is(state, "min", LONG_MIN);
    value_is(state, "min+max", -1);
    value_is(state, "max*0", 0);
    value_is(state, "min*1", LONG_MIN);
    value_is(state, "min/1", LONG_MIN);
    value_is(state, "min%1", 0);
    value_is(state, "min-min", 0);
    value_is(state, "-max", -LONG_MAX);
    value_is(state, "-1 * -max", LONG_MAX);
    value_is(state, "max + min", -1);
    value_is(state, "min - min", 0);
    error_is(state, "max+1", CSH_ARITH_RANGE);
    error_is(state, "(max+1+2)", CSH_ARITH_RANGE);
    error_is(state, "1 ? max+1+2 : 4", CSH_ARITH_RANGE);
    error_is(state, "min-1", CSH_ARITH_RANGE);
    error_is(state, "max-min", CSH_ARITH_RANGE);
    error_is(state, "min-max", CSH_ARITH_RANGE);
    error_is(state, "max*2", CSH_ARITH_RANGE);
    error_is(state, "min*2", CSH_ARITH_RANGE);
    error_is(state, "min * -1", CSH_ARITH_RANGE);
    error_is(state, "-1 * min", CSH_ARITH_RANGE);
    error_is(state, "min / -1", CSH_ARITH_RANGE);
    error_is(state, "min % -1", CSH_ARITH_RANGE);
    error_is(state, "-min", CSH_ARITH_RANGE);
    error_is(state, "1/0", CSH_ARITH_RANGE);
    error_is(state, "1%0", CSH_ARITH_RANGE);
    error_is(state, "1 << -1", CSH_ARITH_RANGE);
    error_is(state, "1 >> -1", CSH_ARITH_RANGE);
    error_is(state, "-1 << 0", CSH_ARITH_RANGE);
    error_is(state, "max << 1", CSH_ARITH_RANGE);
    (void)snprintf(buffer, sizeof(buffer), "1 << %u", bits);
    error_is(state, buffer, CSH_ARITH_RANGE);
    (void)snprintf(buffer, sizeof(buffer), "1 >> %u", bits);
    error_is(state, buffer, CSH_ARITH_RANGE);
    (void)snprintf(buffer, sizeof(buffer), "min >> %u", bits - 1);
    value_is(state, buffer, -1);
    error_is(state, "9999999999999999999999999999999999999", CSH_ARITH_RANGE);
    CHECK(csh_arith_probe("9999999999999999999999999999999999999") == CSH_ARITH_OK);
    CHECK(csh_arith_probe("1/0") == CSH_ARITH_OK);
    CHECK(csh_arith_probe("missing+=1") == CSH_ARITH_OK);
    csh_state_destroy(state);
}

static void syntax(void)
{
    static const char *const invalid[] = {
        "1+", "1 2", "()", "(1", "1)", "0x", "08", "12junk", "1L",
        "x++", "++x", "--x", "1 ** 2", "2#10", "'x'", "sizeof(1)",
        "x[1]", "1=2", "x+y=2", "(x=1)=2", "(1?x:y)=2", "1?2", "1?:2",
        "1?2:", "1:2", "=1", "1;2", "x?y:z=1", "1,", "1.2", "x@"
    };
    struct csh_state *state = new_state();
    size_t index;
    char nested[520];
    long result;
    for (index = 0; index < sizeof(invalid) / sizeof(invalid[0]); ++index) {
        error_is(state, invalid[index], CSH_ARITH_SYNTAX);
        CHECK(csh_arith_probe(invalid[index]) == CSH_ARITH_SYNTAX);
    }
    memset(nested, '(', 256);
    nested[256] = '1';
    memset(nested + 257, ')', 256);
    nested[513] = '\0';
    error_is(state, nested, CSH_ARITH_SYNTAX);
    CHECK(csh_arith_probe(nested) == CSH_ARITH_SYNTAX);
    CHECK(csh_arith_probe(NULL) == CSH_ARITH_SYNTAX);
    CHECK(csh_arith_eval(NULL, "1", &result) == CSH_ARITH_SYNTAX);
    CHECK(csh_arith_eval(state, NULL, &result) == CSH_ARITH_SYNTAX);
    CHECK(csh_arith_eval(state, "1", NULL) == CSH_ARITH_SYNTAX);
    csh_state_destroy(state);
}

int main(void)
{
    operators();
    assignments_and_variables();
    short_circuit_and_rollback();
    boundaries();
    syntax();
    puts("arithmetic fixtures passed");
    return 0;
}
