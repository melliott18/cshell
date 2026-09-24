#define CSHELL_ALIAS_FAULT_IMPLEMENTATION
#include "alias_faults.h"
#include "cshell/alias.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

static void *allocations[128];
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
    assert(!"untracked allocation or exhausted table");
    return 0;
}

void *csh_alias_fault_malloc(size_t size)
{
    void *pointer;
    ++allocation_calls;
    if (allocation_calls == fail_allocation) {
        errno = ENOMEM;
        return NULL;
    }
    pointer = malloc(size);
    assert(pointer != NULL);
    allocations[slot(NULL)] = pointer;
    ++live_allocations;
    return pointer;
}

void csh_alias_fault_free(void *pointer)
{
    if (pointer == NULL)
        return;
    allocations[slot(pointer)] = NULL;
    assert(live_allocations != 0);
    --live_allocations;
    free(pointer);
}

static void arm(size_t point)
{
    allocation_calls = 0;
    fail_allocation = point;
}

static struct csh_aliases *baseline(void)
{
    struct csh_aliases *aliases;
    struct csh_error error;
    assert(live_allocations == 0);
    arm(0);
    assert(csh_aliases_create(&aliases, &error) == 0);
    assert(csh_aliases_set(aliases, "old", "original", &error) == 0);
    assert(csh_aliases_set(aliases, "name", "new", &error) == 0);
    return aliases;
}

static void value_is(const struct csh_aliases *aliases, const char *name,
    const char *expected)
{
    const char *value = csh_aliases_get(aliases, name);
    if (expected == NULL)
        assert(value == NULL);
    else
        assert(value != NULL && strcmp(value, expected) == 0);
}

static void constructor(void)
{
    size_t point;
    for (point = 1; point < 4; ++point) {
        struct csh_error error;
        struct csh_aliases *aliases = (struct csh_aliases *)&error;
        int result;
        arm(point);
        result = csh_aliases_create(&aliases, &error);
        if (result < 0) {
            assert(aliases == NULL);
            assert(error.system_errno == ENOMEM && error.status == 1);
        } else {
            assert(aliases != NULL && error.message == NULL);
            assert(allocation_calls < point);
        }
        csh_aliases_destroy(aliases);
        assert(live_allocations == 0);
        if (result == 0)
            break;
    }
    assert(point < 4);
}

static void mutations(void)
{
    unsigned variant;
    for (variant = 0; variant < 5; ++variant) {
        size_t point;
        for (point = 1; point < 8; ++point) {
            struct csh_aliases *aliases = baseline();
            struct csh_error error;
            size_t before = live_allocations;
            const char *name = variant == 0 ? "fresh" : "old";
            const char *value = variant == 1 ? "replacement" :
                variant == 2 ? "" : csh_aliases_get(aliases, "old");
            const char *expected = value;
            int result;
            if (variant == 4)
                name = csh_aliases_get(aliases, "name");
            arm(point);
            result = csh_aliases_set(aliases, name, value, &error);
            if (result < 0) {
                assert(error.system_errno == ENOMEM && error.status == 1);
                assert(live_allocations == before);
                value_is(aliases, "old", "original");
                value_is(aliases, "fresh", NULL);
                value_is(aliases, "new", NULL);
            } else {
                assert(allocation_calls < point && error.message == NULL);
                value_is(aliases, variant == 4 ? "new" : name,
                    variant == 1 || variant == 2 ? expected : "original");
            }
            value_is(aliases, "name", "new");
            csh_aliases_destroy(aliases);
            assert(live_allocations == 0);
            if (result == 0)
                break;
        }
        assert(point < 8);
    }
}

static void handlers(void)
{
    size_t point;
    for (point = 1; point < 12; ++point) {
        const char *argv[] = {"alias", "fresh=new", "old=replacement", "after=later"};
        struct csh_aliases *aliases = baseline();
        FILE *out = tmpfile();
        FILE *err = tmpfile();
        int status;
        assert(out != NULL && err != NULL);
        arm(point);
        status = csh_builtin_alias(aliases, 4, argv, out, err);
        if (status == 0) {
            assert(allocation_calls < point);
            value_is(aliases, "fresh", "new");
            value_is(aliases, "old", "replacement");
            value_is(aliases, "after", "later");
        } else {
            assert(status == 1 && allocation_calls >= point);
            /* Every failed operand leaves that definition unchanged, while
             * subsequent independent definitions still take effect. */
            value_is(aliases, "fresh", point <= 3 ? NULL : "new");
            value_is(aliases, "old", point == 4 ? "original" : "replacement");
            value_is(aliases, "after", point >= 5 ? NULL : "later");
        }
        value_is(aliases, "name", "new");
        assert(fclose(out) == 0 && fclose(err) == 0);
        csh_aliases_destroy(aliases);
        assert(live_allocations == 0);
        if (status == 0)
            break;
    }
    assert(point < 12);
}

static void no_allocation(void)
{
    const char *list[] = {"alias"};
    const char *remove[] = {"unalias", "old"};
    const char *all[] = {"unalias", "-a"};
    struct csh_aliases *aliases = baseline();
    struct csh_error error;
    FILE *out = tmpfile();
    FILE *err = tmpfile();
    assert(out != NULL && err != NULL);
    arm(1);
    value_is(aliases, "old", "original");
    assert(csh_builtin_alias(aliases, 1, list, out, err) == 0);
    assert(csh_aliases_unset(aliases, "absent", &error) == 0);
    assert(csh_builtin_unalias(aliases, 2, remove, out, err) == 0);
    assert(csh_builtin_unalias(aliases, 2, all, out, err) == 0);
    assert(allocation_calls == 0 && live_allocations == 1);
    assert(fclose(out) == 0 && fclose(err) == 0);
    csh_aliases_destroy(aliases);
    assert(live_allocations == 0);
}

int main(void)
{
    constructor();
    mutations();
    handlers();
    no_allocation();
    puts("ok");
    return 0;
}
