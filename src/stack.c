#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#ifndef _DARWIN_C_SOURCE
#define _DARWIN_C_SOURCE
#endif

#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <sys/resource.h>

#include "cshell/stack.h"

/* This is byte headroom, not a grammar-depth limit. It covers the bounded
 * native call paths between checks, libc diagnostics and signal delivery.
 * Tree/lexer/plan destruction is iterative and does not consume this reserve
 * in proportion to the input depth. Use a real frame address: ASan may move
 * ordinary automatic variables to its separate fake stack. */
#define STACK_RESERVE ((size_t)64 * 1024)

int csh_stack_available(size_t *bytes)
{
    /* GNU/Clang TLS is available in the supported C99 builds. Thread IDs
     * can be reused with a different stack; a process-global cache keyed only
     * by pthread_t would then be unsafe even with serialized API calls. */
    static __thread uintptr_t low, high;
    static __thread rlim_t saved_limit;
    static __thread int initialized;
    struct rlimit limit;
    pthread_t self = pthread_self();
    uintptr_t current = (uintptr_t)__builtin_frame_address(0);
    int saved_errno = errno;
    *bytes = 0;
    if (getrlimit(RLIMIT_STACK, &limit) == -1)
        return errno;
    if (!initialized || saved_limit != limit.rlim_cur) {
        uintptr_t bottom, top;
        size_t size;
#if defined(__APPLE__)
        top = (uintptr_t)pthread_get_stackaddr_np(self);
        size = pthread_get_stacksize_np(self);
        if (size == 0 || size > top) return ENOMEM;
        bottom = top - size;
#elif defined(__linux__)
        pthread_attr_t attributes;
        void *address;
        int result = pthread_getattr_np(self, &attributes);
        if (result != 0) return result;
        result = pthread_attr_getstack(&attributes, &address, &size);
        pthread_attr_destroy(&attributes);
        if (result != 0) return result;
        bottom = (uintptr_t)address;
        if (size == 0 || size > UINTPTR_MAX - bottom) return ENOMEM;
        top = bottom + size;
#else
#error "Stack bounds need a platform implementation"
#endif
        /* A lowered main-thread soft limit may be smaller than the pthread
         * mapping. Clamping also conservatively respects it for API threads. */
        if (limit.rlim_cur != RLIM_INFINITY && limit.rlim_cur < top - bottom)
            bottom = top - (uintptr_t)limit.rlim_cur;
        low = bottom;
        high = top;
        saved_limit = limit.rlim_cur;
        initialized = 1;
    }
    errno = saved_errno;
    if (current < low || current >= high || current - low <= STACK_RESERVE)
        return ENOMEM;
    *bytes = current - low - STACK_RESERVE;
    return 0;
}

int csh_stack_check(void)
{
    size_t bytes;
    return csh_stack_available(&bytes);
}
