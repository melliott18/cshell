/* CSH-074 portability adapter; project license. */
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include "compat.h"

long long csh_strtonum(const char *text, long long minimum, long long maximum,
                      const char **error)
{
    char *end;
    long long value;
    int saved_errno = errno;
    errno = 0;
    value = strtoll(text, &end, 10);
    *error = NULL;
    if (text == end || *end || minimum > maximum)
        *error = "invalid";
    else if ((errno == ERANGE && value < 0) || value < minimum)
        *error = "too small";
    else if (errno == ERANGE || value > maximum)
        *error = "too large";
    errno = saved_errno;
    return *error ? 0 : value;
}

size_t csh_strlcpy(char *dst, const char *src, size_t capacity)
{
    size_t length = strlen(src);
    if (capacity) {
        size_t copied = length < capacity ? length : capacity - 1;
        memcpy(dst, src, copied);
        dst[copied] = '\0';
    }
    return length;
}

size_t csh_strlcat(char *dst, const char *src, size_t capacity)
{
    size_t used = strnlen(dst, capacity);
    if (used == capacity)
        return used + strlen(src);
    return used + csh_strlcpy(dst + used, src, capacity - used);
}
