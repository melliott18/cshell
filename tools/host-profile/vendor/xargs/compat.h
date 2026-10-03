/* CSH-074 portability adapter; project license. */
#ifndef CSH_XARGS_COMPAT_H
#define CSH_XARGS_COMPAT_H
#include <stddef.h>
size_t csh_strlcpy(char *, const char *, size_t);
size_t csh_strlcat(char *, const char *, size_t);
long long csh_strtonum(const char *, long long, long long, const char **);
#define strtonum csh_strtonum
#endif
