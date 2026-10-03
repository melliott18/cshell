/* Test-only allocation interposition in the standalone source, not libc.
 * Keep the production adapter/source byte-for-byte shared with the profile. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdlib.h>
#include <string.h>

static int fail_call(const char *kind, const char *site)
{
    const char *selected = getenv("CSH_PRINTF_FAIL");
    const char *selected_site = getenv("CSH_PRINTF_FAIL_SITE");
    if (selected && !strcmp(selected, kind) &&
        (!selected_site || !*selected_site || !strcmp(selected_site, site))) {
        errno = ENOMEM;
        return 1;
    }
    return 0;
}

static char *fault_strdup(const char *text, const char *site)
{
    return fail_call("strdup", site) ? NULL : strdup(text);
}

static void *fault_realloc(void *pointer, size_t size, const char *site)
{
    return fail_call("realloc", site) ? NULL : realloc(pointer, size);
}

#define strdup(text) fault_strdup((text), __func__)
#define realloc(pointer, size) fault_realloc((pointer), (size), __func__)
#include "../tools/host-profile/printf.c"
