/* Test-only allocation interposition in the standalone source, not libc.
 * Keep the production adapter/source byte-for-byte shared with the profile. */
#define _GNU_SOURCE
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdio.h>

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

/* Inject the documented libc API failure result, without claiming an
 * internal libc allocation failed. In particular ferror(stdout) stays clear. */
static int fault_vprintf(const char *format, va_list arguments)
{
    const char *error = getenv("CSH_PRINTF_API_ERROR");
    if (error && strcmp(error, "control")) {
        if (!strcmp(error, "ENOMEM")) errno = ENOMEM;
        else if (!strcmp(error, "EINTR")) errno = EINTR;
        else if (!strcmp(error, "EOVERFLOW")) errno = EOVERFLOW;
        else if (!strcmp(error, "zero")) errno = 0;
        else return vprintf(format, arguments);
        return -1;
    }
    return vprintf(format, arguments);
}

#define vprintf fault_vprintf
#define strdup(text) fault_strdup((text), __func__)
#define realloc(pointer, size) fault_realloc((pointer), (size), __func__)
#include "../tools/host-profile/printf.c"
