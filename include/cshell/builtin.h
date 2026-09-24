#ifndef CSHELL_BUILTIN_H
#define CSHELL_BUILTIN_H
#include "cshell/execute.h"
/* Lookup is pure; EXTERNAL means this module does not own the name.
 * Run borrows validated argv/state, uses current fds/cwd, prints diagnostics,
 * returns shell status, and never exits. Caller owns redirection lifetimes. */
enum csh_execution_category csh_state_builtin_category(const char *name);
int csh_state_builtin_run(struct csh_state *state, size_t argc, char *const argv[]);
#endif
