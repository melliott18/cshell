/* Standalone FreeBSD printf with local output, getopt and catalog adapters.
 * The upstream BSD license is retained in vendor/.
 */
#define _GNU_SOURCE
#include <err.h>
#include <errno.h>
#include <locale.h>
#include <nl_types.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static nl_catd messages = (nl_catd)-1;
static int formatting_error;

/* Stable set 1 message IDs; catalogs use the same printf argument types. */
static const char *host_message(int id, const char *fallback)
{
    return catgets(messages, 1, id, fallback);
}

static int host_printf(const char *format, ...)
{
    va_list args;
    int result;
    va_start(args, format);
    result = vprintf(format, args);
    va_end(args);
    if (result < 0 && !formatting_error)
        formatting_error = errno ? errno : EIO;
    return result;
}

#ifdef __linux__
static int host_getopt(int argc, char *const argv[], const char *options)
{
    (void)options;
    /* FreeBSD getopt stops at the format operand; GNU defaults to permutation. */
    return getopt(argc, argv, "+");
}
#define getopt host_getopt
#endif
#define printf host_printf
#define main freebsd_printf_main
#include "vendor/printf.c"
#undef main
#undef printf

#ifndef HOST_PRINTF_MAIN
#define HOST_PRINTF_MAIN main
#endif
int HOST_PRINTF_MAIN(int argc, char **argv)
{
    int status;
    (void)setlocale(LC_ALL, "");
    messages = catopen("cshell-printf", NL_CAT_LOCALE);
    status = freebsd_printf_main(argc, argv);
    free(conversion_format);
    conversion_format = NULL;
    conversion_capacity = 0;
    /* vprintf may fail without setting the stream's error indicator (ENOMEM). */
    if (fflush(stdout) == EOF || ferror(stdout) || formatting_error) {
        if (formatting_error) errno = formatting_error;
        warn("%s", host_message(10, "write or formatting error"));
        status = 1;
    }
    if (messages != (nl_catd)-1) (void)catclose(messages);
    return status;
}
