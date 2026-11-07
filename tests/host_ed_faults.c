/* CSH-074: controlled backing-store failures in a separately built editor. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#undef tmpfile
#undef fwrite
static FILE *backing;
static int requested(const char *name)
{
    const char *value = getenv("CSH_ED_FAULT");
    return value && strcmp(value, name) == 0;
}
FILE *csh_ed_tmpfile(void)
{
    if (requested("create")) { errno = EMFILE; return NULL; }
    backing = tmpfile();
    return backing;
}
size_t csh_ed_fwrite(const void *data, size_t size, size_t count, FILE *stream)
{
    if (stream == backing && requested("write")) { errno = ENOSPC; return 0; }
    return fwrite(data, size, count, stream);
}
