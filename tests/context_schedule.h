#ifndef CSHELL_CONTEXT_SCHEDULE_H
#define CSHELL_CONTEXT_SCHEDULE_H
#include <sys/types.h>
#include <sys/wait.h>

/* Test-only scheduling hook; never linked into cshell. */
pid_t csh_context_waitpid(pid_t pid, int *status, int options);
#define waitpid csh_context_waitpid
#endif
