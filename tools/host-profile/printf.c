/* Standalone FreeBSD printf, with GNU getopt and output-error adapters.
 * The upstream implementation and its BSD license remain unchanged in vendor/.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <unistd.h>

#ifdef __linux__
static int host_getopt(int argc, char *const argv[], const char *options)
{
    (void)options;
    /* FreeBSD getopt stops at the format operand; GNU defaults to permutation. */
    return getopt(argc, argv, "+");
}
#define getopt host_getopt
#endif
#define main freebsd_printf_main
#include "vendor/printf.c"
#undef main

int main(int argc, char **argv)
{
    int status = freebsd_printf_main(argc, argv);
    /* Include buffered write failures in the external utility's exit status. */
    if (fflush(stdout) == EOF || ferror(stdout)) {
        warn("write error");
        return 1;
    }
    return status;
}
