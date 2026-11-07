#ifndef CSH_TEST_RETENTION_TRACE_H
#define CSH_TEST_RETENTION_TRACE_H

#include <sys/types.h>

/* Test-only observer. None of these functions changes masks, dispositions,
 * alarms or errno. The fork wrapper preserves the real fork result/errno. */
void csh_retention_trace_init(void);
int csh_retention_trace_enabled(void);
void csh_retention_trace_context(int capacity, int round, int item);
void csh_retention_trace_event(const char *event, pid_t child);
void csh_retention_trace_close(void);
pid_t csh_retention_fork(void);

#ifdef CSH_RETENTION_INTERPOSE_FORK
#define fork csh_retention_fork
#endif

#endif
