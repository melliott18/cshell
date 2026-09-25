#ifndef CSHELL_BUILTIN_H
#define CSHELL_BUILTIN_H
#include "cshell/execute.h"
/* Builtin classification is pure; EXTERNAL means no registered state/evaluation
 * builtin. Evaluation/control/job handlers are dispatched by execute.c.
 * Run borrows validated argv/state, uses current fds/cwd, prints diagnostics,
 * returns shell status, and never exits. Caller owns redirection lifetimes. */
enum csh_execution_category csh_state_builtin_category(const char *name);
int csh_state_builtin_run(struct csh_state *state, size_t argc, char *const argv[]);
/* Job-aware set validates monitor capability before changing options/parameters. */
int csh_builtin_set(struct csh_state *state, size_t argc, char *const argv[], int monitor_available);
int csh_utility_run(struct csh_state *state, size_t argc, char *const argv[]);
#endif
