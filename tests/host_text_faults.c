/* Test-only syscall boundary faults; never linked into a provider or cshell. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static const char *mode;
static int trace_fd = -1, injected;
#ifdef __APPLE__
#define REAL_READ read
#define REAL_WRITE write
#define REAL_REALLOC realloc
#define FAULT_READ fault_read
#define FAULT_WRITE fault_write
#define FAULT_REALLOC fault_realloc
#define INTERPOSE(replacement, original) \
    __attribute__((used)) static struct { const void *a, *b; } pair_##original \
    __attribute__((section("__DATA,__interpose"))) = \
    {(const void *)(replacement), (const void *)(original)}
#else
static ssize_t (*next_read)(int, void *, size_t);
static ssize_t (*next_write)(int, const void *, size_t);
static void *(*next_realloc)(void *, size_t);
#define REAL_READ next_read
#define REAL_WRITE next_write
#define REAL_REALLOC next_realloc
#define FAULT_READ read
#define FAULT_WRITE write
#define FAULT_REALLOC realloc
#endif

__attribute__((constructor)) static void initialize(void)
{
#ifndef __APPLE__
    next_read = dlsym(RTLD_NEXT, "read");
    next_write = dlsym(RTLD_NEXT, "write");
    next_realloc = dlsym(RTLD_NEXT, "realloc");
    if (!next_read || !next_write || !next_realloc) _exit(125);
#endif
    mode = getenv("CSH_TEXT_FAULT");
    const char *path = getenv("CSH_TEXT_TRACE");
    if (mode && path) trace_fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (mode && trace_fd < 0) _exit(125);
}

static int selected(const char *name)
{
    return !injected && mode && !strcmp(mode, name);
}

static void mark(void)
{
    if (REAL_WRITE(trace_fd, "fault\n", 6) != 6) _exit(125);
    injected = 1;
}

ssize_t FAULT_READ(int fd, void *buffer, size_t size)
{
    if (fd == STDIN_FILENO && size && selected("read-eintr")) {
        mark(); errno = EINTR; return -1;
    }
    if (fd == STDIN_FILENO && size && selected("read-eio")) {
        mark(); errno = EIO; return -1;
    }
    if (fd == STDIN_FILENO && size > 7 && selected("read-short")) {
        mark(); size = 7;
    }
    return REAL_READ(fd, buffer, size);
}

ssize_t FAULT_WRITE(int fd, const void *buffer, size_t size)
{
    if (fd == STDOUT_FILENO && size && selected("write-eintr")) {
        mark(); errno = EINTR; return -1;
    }
    if (fd == STDOUT_FILENO && size > 7 && selected("write-short")) {
        mark(); size = 7;
    }
    return REAL_WRITE(fd, buffer, size);
}

void *FAULT_REALLOC(void *pointer, size_t size)
{
    if (size >= 65536 && selected("realloc-enomem")) {
        mark(); errno = ENOMEM; return NULL;
    }
    return REAL_REALLOC(pointer, size);
}

#ifdef __APPLE__
INTERPOSE(fault_read, read);
INTERPOSE(fault_write, write);
INTERPOSE(fault_realloc, realloc);
#else
/* Exercise the read/write fallback on kernels with zero-copy cat support.
 * These capability failures are part of the explicitly instrumented fixture. */
ssize_t copy_file_range(int in, off_t *inoff, int out, off_t *outoff, size_t n, unsigned flags)
{
    (void)in; (void)inoff; (void)out; (void)outoff; (void)n; (void)flags;
    errno = ENOSYS; return -1;
}
ssize_t splice(int in, off_t *inoff, int out, off_t *outoff, size_t n, unsigned flags)
{
    (void)in; (void)inoff; (void)out; (void)outoff; (void)n; (void)flags;
    errno = EINVAL; return -1;
}
#endif
