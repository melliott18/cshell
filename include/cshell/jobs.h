#ifndef CSHELL_JOBS_H
#define CSHELL_JOBS_H

#include "cshell/execute.h"
#include <termios.h>

struct csh_jobs;
struct csh_job_process {
    pid_t pid;
    int status;
    int done;
    int stopped;
};
/* A job owns all direct stage PIDs. The executor fills them before release;
 * only jobs.c collects their statuses, including during launch cancellation. */
struct csh_job {
    struct csh_job *next;
    unsigned id;
    pid_t pgid;
    struct csh_job_process *processes;
    size_t count;
    char *text;
    int grouped;
    int background;
    int changed;
    int reported;
    int negated;
    int modes_valid;
    struct termios modes;
};
/* One signal-owning manager per process; create only at a runtime boundary.
 * fd is a borrowed terminal candidate, or -1 for scripts/subshells. Missing
 * terminal capabilities leave monitor off. Destroy restores dispositions. */
int csh_jobs_create(struct csh_jobs **out, struct csh_state *state, int fd);
void csh_jobs_destroy(struct csh_jobs *jobs);
/* Child-only: restore dispositions, close tty, free the copied manager
 * without touching its parent-owned PIDs, and clear interactive/monitor bits. */
void csh_jobs_after_fork(struct csh_jobs *jobs, int asynchronous);
int csh_jobs_monitor(const struct csh_jobs *jobs);
/* Relocate the private tty away from all redirection operands. */
int csh_jobs_reserve(struct csh_jobs *jobs, const int *fds, size_t count);
/* Register preallocated stages before fork. The returned pointer is borrowed
 * from the manager; executor fills PIDs and uses cancel on launch failure. */
struct csh_job *csh_jobs_add(struct csh_jobs *jobs, size_t count,
    const char *text, int asynchronous, int negated);
/* Free a finished record (or a copied parent record after fork). */
void csh_jobs_remove(struct csh_jobs *jobs, struct csh_job *job);
void csh_jobs_cancel(struct csh_jobs *jobs, struct csh_job *job);
/* Give the terminal before opening the launch barrier. */
int csh_jobs_give_terminal(struct csh_jobs *jobs, struct csh_job *job, int resume);
/* Wait and reclaim the terminal. Success consumes a completed job; a stopped
 * job remains owned. Errors retain ownership for cancellation or retry. */
int csh_jobs_foreground(struct csh_jobs *jobs, struct csh_job *job, int resume,
    int *status);
/* Collection preserves shell status/$!. wait=1 also waits until completion
 * or a monitored stop; statuses remain available for the wait builtin. */
int csh_jobs_poll(struct csh_jobs *jobs);
int csh_jobs_reap(struct csh_jobs *jobs, int wait);
void csh_jobs_announce(struct csh_jobs *jobs, const struct csh_job *job);
void csh_jobs_notify(struct csh_jobs *jobs);
/* Input wait hook: pselect atomically unblocks SIGCHLD, reaps while idle, and
 * reports changes immediately only when notify is enabled. No read-ahead. */
int csh_jobs_read_ready(void *jobs, int fd);
int csh_jobs_is_builtin(const char *name);
int csh_jobs_builtin(struct csh_jobs *jobs, const struct csh_command *command);
/* Temporarily restore inherited signal actions around exec; recover on failure. */
void csh_jobs_exec_signals(struct csh_jobs *jobs, int recover);
#endif
