/* CSH-080 test-only call-site ENOMEM injection into the unchanged local provider.
 * This covers provider handling of allocation/API failure, not libc internals.
 */
#define _XOPEN_SOURCE 700
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static unsigned calls, fail_at, triggered;
static int fault(void)
{
    if (++calls == fail_at) {
        triggered = 1;
        errno = ENOMEM;
        return 1;
    }
    return 0;
}
static void *fault_malloc(size_t n) { return fault() ? NULL : malloc(n); }
static char *fault_strdup(const char *s) { return fault() ? NULL : strdup(s); }
static char *fault_getcwd(char *p, size_t n) { return fault() ? NULL : getcwd(p, n); }
static char *fault_realpath(const char *s, char *p) { return fault() ? NULL : realpath(s, p); }
#define malloc fault_malloc
#define strdup fault_strdup
#define getcwd fault_getcwd
#define realpath fault_realpath
#define main provider_main
#include "../tools/host-profile/paths.c"
#undef main
#undef malloc
#undef strdup
#undef getcwd
#undef realpath

int main(int argc, char **argv)
{
    const char *setting = getenv("CSH_PATH_FAIL_AT");
    char *end;
    unsigned long value;
    int status;
    FILE *marker;
    if (!setting) return 125;
    errno = 0;
    value = strtoul(setting, &end, 10);
    if (errno || !*setting || *end || value > 1024) return 125;
    fail_at = (unsigned)value;
    status = provider_main(argc, argv);
    marker = fopen(".allocation-fault.json", "w");
    if (!marker) return 125;
    fprintf(marker, "{\"requested\":%u,\"calls\":%u,\"triggered\":%u}\n",
            fail_at, calls, triggered);
    if (fclose(marker)) return 125;
    return status;
}
