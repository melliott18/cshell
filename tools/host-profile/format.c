/* Pinned GNU vasnprintf provides checked floating-conversion allocation.
 * The source archive and licenses are retained with the M4/gnulib provider.
 * Format first, then write exact bytes; all failures retain errno for printf's
 * existing diagnostic/status adapter. No test switches exist in this file. */
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include "vasnprintf.h"
#include "format.h"

int csh_vprintf(const char *format, va_list arguments)
{
    char buffer[4096];
    size_t length = sizeof buffer;
    char *text = vasnprintf(buffer, &length, format, arguments);
    int result, saved_errno;
    if (!text) return -1;
    if (length > INT_MAX) {
        if (text != buffer) free(text);
        errno = EOVERFLOW;
        return -1;
    }
    result = fwrite(text, 1, length, stdout) == length ? (int)length : -1;
    saved_errno = errno;
    if (text != buffer) free(text);
    errno = result < 0 && !saved_errno ? EIO : saved_errno;
    return result;
}
