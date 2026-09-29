#ifndef CSHELL_STACK_H
#define CSHELL_STACK_H

#include <stddef.h>

/* Native recursion consumes a real, finite resource. Return an errno value
 * when the current thread's stack cannot be measured or has insufficient
 * headroom for another call and diagnostic/cleanup work; zero on success.
 * Does not install signal handlers or change process-wide resource limits.
 * Like the shell's other stateful module APIs, calls must be serialized. */
int csh_stack_check(void);

/* Remaining bytes after the cleanup reserve. Also used by resource fixtures.
 * Bounds are thread-local, refreshed when RLIMIT_STACK changes, and are
 * inherited across fork without treating the child's existing frames as free. */
int csh_stack_available(size_t *bytes);

#endif
