/* Test-only scope around the selected portable formatter, never an injected API return. */
#include <dlfcn.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include "../tools/host-profile/format.h"

static int scoped_vprintf(const char *format, va_list arguments)
{
    void (*arm)(int) = (void (*)(int))dlsym(RTLD_DEFAULT, "csh_libc_arm");
    void (*disarm)(void) = (void (*)(void))dlsym(RTLD_DEFAULT, "csh_libc_disarm");
    const char *selected = getenv("CSH_LIBC_FAIL");
    if (!arm || !disarm || !selected) _Exit(125);
    arm(atoi(selected));
    int result = csh_vprintf(format, arguments);
    int saved_errno = errno;
    disarm();
    errno = saved_errno;
    return result;
}

#define HOST_VPRINTF scoped_vprintf
#include "../tools/host-profile/printf.c"
