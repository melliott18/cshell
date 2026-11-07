/* Darwin-only test interposition at real allocator call sites.
 * The helper arms this library only around the selected formatter call.
 * Never link this library into a production provider. */
#ifndef __APPLE__
#error This fixture requires Darwin dyld interposition
#endif
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int armed, target, calls, trace = -1;

static void trace_write(const char *bytes, size_t size)
{
    while (size) {
        ssize_t n = write(trace, bytes, size);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) _Exit(125);
        bytes += n;
        size -= (size_t)n;
    }
}

void csh_libc_arm(int ordinal)
{
    if (trace >= 0) _Exit(125); /* One conversion per process. */
    trace = open("libc-alloc.trace", O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (trace < 0 || ordinal < 0 || ordinal > 64) _Exit(125);
    target = ordinal;
    calls = 0;
    armed = 1;
}

void csh_libc_disarm(void)
{
    armed = 0;
    if (trace < 0 || close(trace)) _Exit(125);
    trace = -1;
}

static int fail(const char *kind, size_t size, const void *caller)
{
    if (!armed) return 0;
    int saved_errno = errno;
    int selected = ++calls == target;
    if (calls > 64) _Exit(125);
    /* Symbol resolution and tracing must not recursively inject faults. The
     * event is persisted BEFORE NULL is returned, including if libc crashes. */
    armed = 0;
    Dl_info info = {0};
    dladdr(caller, &info);
    char line[4096];
    int length = snprintf(line, sizeof line, "%d\t%s\t%zu\t%d\t%s\t%s\n",
                          calls, kind, size, selected,
                          info.dli_fname ? info.dli_fname : "?",
                          info.dli_sname ? info.dli_sname : "?");
    if (length < 0 || (size_t)length >= sizeof line) _Exit(125);
    trace_write(line, (size_t)length);
    armed = 1;
    errno = selected ? ENOMEM : saved_errno;
    return selected;
}

static void *probe_malloc(size_t size)
{
    return fail("malloc", size, __builtin_return_address(0)) ? NULL : malloc(size);
}

static void *probe_calloc(size_t count, size_t size)
{
    /* Keep overflow handling with the real allocator. */
    if (size && count > (size_t)-1 / size) return calloc(count, size);
    return fail("calloc", count * size, __builtin_return_address(0)) ? NULL : calloc(count, size);
}

static void *probe_realloc(void *pointer, size_t size)
{
    return fail("realloc", size, __builtin_return_address(0)) ? NULL : realloc(pointer, size);
}

#define INTERPOSE(replacement, original) \
    __attribute__((used)) static struct { const void *a, *b; } pair_##original \
    __attribute__((section("__DATA,__interpose"))) = \
    {(const void *)(replacement), (const void *)(original)}
INTERPOSE(probe_malloc, malloc);
INTERPOSE(probe_calloc, calloc);
INTERPOSE(probe_realloc, realloc);
