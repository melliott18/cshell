/* Test-only allocation interposition in the standalone source, not libc.
 * Keep the production adapter/source byte-for-byte shared with the profile. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdlib.h>
#include <string.h>

static int fail_call(const char *kind)
{
    const char *selected = getenv("CSH_PRINTF_FAIL");
    if (selected && !strcmp(selected, kind)) {
        errno = ENOMEM;
        return 1;
    }
    return 0;
}

static char *fault_strdup(const char *text)
{
    return fail_call("strdup") ? NULL : strdup(text);
}

static void *fault_realloc(void *pointer, size_t size)
{
    return fail_call("realloc") ? NULL : realloc(pointer, size);
}

#define strdup fault_strdup
#define realloc fault_realloc
#include "../tools/host-profile/printf.c"
