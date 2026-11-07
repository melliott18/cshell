/* Standalone provider formatting interface; not linked into cshell. */
#ifndef CSH_HOST_FORMAT_H
#define CSH_HOST_FORMAT_H
#include <stdarg.h>
int csh_vprintf(const char *format, va_list arguments);
#endif
