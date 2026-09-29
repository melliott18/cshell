/* Instrument pathname.c only; retain the public main/parser/executor.
 * Fail after returning a real matching entry, independent of readdir order.
 * A marker proves injection happened; closedir still closes the real stream. */
#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static DIR *target;
static int seen;

static int fault(void)
{
    const char *mode = getenv("CSH_PATH_FAULT");
    if (!mode) return 0;
    if (!strcmp(mode, "EACCES")) return EACCES;
    if (!strcmp(mode, "ENOENT")) return ENOENT;
    if (!strcmp(mode, "EIO")) return EIO;
    return 0;
}

static void mark(void)
{
    FILE *file = fopen("injected", "w");
    if (!file || fputs("injected\n", file) < 0 || fclose(file)) abort();
}

DIR *csh_path_test_opendir(const char *path)
{
    DIR *result = opendir(path);
    if (result && !strcmp(path, "paths/fault/") && fault()) {
        target = result;
        seen = 0;
    }
    return result;
}

struct dirent *csh_path_test_readdir(DIR *directory)
{
    struct dirent *entry;
    if (directory == target && seen) {
        int error = fault();
        mark();
        errno = error;
        return NULL;
    }
    entry = readdir(directory);
    if (directory == target && entry && !strcmp(entry->d_name, "match")) seen = 1;
    return entry;
}

int csh_path_test_closedir(DIR *directory)
{
    if (directory == target) target = NULL;
    return closedir(directory);
}
