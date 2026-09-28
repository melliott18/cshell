/* Public main with targeted state/builtin/utility faults. No production hooks.
 * Every injected run verifies the selected path was actually reached. */
#define CSHELL_STATE_FAULT_IMPLEMENTATION
#include "state_builtin_faults.h"
#include <errno.h>
#include <stdio.h>

static const char *mode;
static size_t allocation, fail_at;
static int initializing, hits, interrupted;
static int selected(const char *name) { return mode && !strcmp(mode, name); }
static int allocation_failure(void)
{
    if (initializing && selected("startup-allocation") && ++allocation == fail_at) {
        ++hits; errno = ENOMEM; return 1;
    }
    return 0;
}
void *csh_state_fault_malloc(size_t size) { return allocation_failure() ? NULL : malloc(size); }
void *csh_state_fault_calloc(size_t n, size_t size) { return allocation_failure() ? NULL : calloc(n, size); }
void *csh_state_fault_realloc(void *p, size_t size) { return allocation_failure() ? NULL : realloc(p, size); }
char *csh_state_fault_strdup(const char *s) { return allocation_failure() ? NULL : strdup(s); }
char *csh_state_fault_strndup(const char *s, size_t n) { return allocation_failure() ? NULL : strndup(s, n); }
int csh_state_fault_initialize(struct csh_state *state)
{
    int rc;
    initializing = 1;
    rc = csh_builtin_initialize(state);
    initializing = 0;
    return rc;
}
char *csh_state_fault_getcwd(char *p, size_t n)
{
    if (selected("cwd")) { ++hits; errno = EACCES; return NULL; }
    return getcwd(p, n);
}
clock_t csh_state_fault_times(struct tms *t)
{
    if (selected("times")) { ++hits; errno = EIO; return (clock_t)-1; }
    return times(t);
}
long csh_state_fault_sysconf(int name)
{
    if (selected("ticks") && name == _SC_CLK_TCK) { ++hits; errno = EINVAL; return -1; }
    return sysconf(name);
}
int csh_state_fault_getrlimit(int r, struct rlimit *l)
{
    if (selected("getrlimit")) { ++hits; errno = EIO; return -1; }
    if (selected("limit-units")) { l->rlim_cur = 8192; l->rlim_max = 16384; return 0; }
    if (selected("limit-unlimited")) { l->rlim_cur = 8192; l->rlim_max = RLIM_INFINITY; return 0; }
    return getrlimit(r, l);
}
int csh_state_fault_setrlimit(int r, const struct rlimit *l)
{
    if (selected("setrlimit")) { ++hits; errno = EPERM; return -1; }
    if (selected("limit-units")) {
        unsigned unit = r == RLIMIT_CORE || r == RLIMIT_FSIZE ? 512 : r == RLIMIT_NOFILE ? 1 : 1024;
        if (l->rlim_cur != 7 * unit || l->rlim_max != 16384) { errno = EINVAL; return -1; }
        ++hits; return 0;
    }
    if (selected("limit-unlimited")) {
        if (l->rlim_cur != RLIM_INFINITY || l->rlim_max != RLIM_INFINITY) { errno = EINVAL; return -1; }
        ++hits; return 0;
    }
    return setrlimit(r, l);
}
ssize_t csh_state_fault_read(int fd, void *p, size_t n)
{
    if (fd == 0 && selected("read-eio")) { ++hits; errno = EIO; return -1; }
    if (fd == 0 && selected("read-eintr") && !interrupted) {
        interrupted = 1; ++hits; errno = EINTR; return -1;
    }
    return read(fd, p, n);
}
ssize_t csh_state_fault_write(int fd, const void *p, size_t n)
{
    if (fd == 1 && selected("write-retry")) {
        ++hits;
        if (!interrupted) { interrupted = 1; errno = EINTR; return -1; }
        if (n > 1) n = 1;
    }
    if (fd == 1 && selected("write-zero")) { ++hits; return 0; }
    return write(fd, p, n);
}
int main(int argc, char **argv)
{
    int rc;
    const char *point = getenv("CSH_STATE_FAULT_AT");
    mode = getenv("CSH_STATE_FAULT");
    fail_at = point ? (size_t)strtoul(point, NULL, 10) : 1;
    rc = csh_state_fault_main(argc, argv);
    if ((selected("limit-units") || selected("limit-unlimited")) && hits != 6) return 98;
    if (!hits) {
        /* The startup sweep stops only after a complete, uninjected run. */
        if (selected("startup-allocation") && allocation < fail_at && rc == 0) return 99;
        fputs("state fault injection was not exercised\n", stderr);
        return 98;
    }
    return rc;
}
