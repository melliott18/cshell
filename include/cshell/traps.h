#ifndef CSHELL_TRAPS_H
#define CSHELL_TRAPS_H

#include <stddef.h>
#include <signal.h>

struct csh_traps;
#define CSH_TRAP_LIMIT 128

/* One active trap table per shell process. Actions are copied before dispatch,
 * so an action may replace or remove itself. Signal handlers only set flags. */
int csh_traps_create(struct csh_traps **out, int interactive);
struct csh_traps *csh_traps_active(void);
void csh_traps_destroy(struct csh_traps *traps);
int csh_traps_builtin(struct csh_traps *traps, size_t argc, char *const argv[]);
int csh_traps_pending(void);
int csh_traps_first_pending(void);
void csh_traps_add_caught(const struct csh_traps *traps, sigset_t *set);
/* Returns a signal number, zero when none, or -1 on allocation failure.
 * The caller owns *action. EXIT is obtained separately at shell shutdown. */
int csh_traps_take(struct csh_traps *traps, char **action);
char *csh_traps_exit_action(struct csh_traps *traps);
/* In a subshell, caught actions reset; ignored actions remain ignored. */
void csh_traps_after_fork(struct csh_traps *traps, int asynchronous,
    int preserve_listing);
/* Reset caught dispositions for exec, and restore them if exec fails. */
void csh_traps_exec_signals(struct csh_traps *traps, int recover);

#endif
