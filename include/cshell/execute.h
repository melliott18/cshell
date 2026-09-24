#ifndef CSHELL_EXECUTE_H
#define CSHELL_EXECUTE_H

#include "cshell/ast.h"
#include "cshell/redirect.h"
#include "cshell/state.h"

struct csh_assignment { char *name; char *value; };

/* All pointers are owned; argv is NULL-terminated when argc > 0. Counts
 * describe initialized entries. Zero initialization is an empty command.
 * CSH-008 will supply expansion; CSH-023 will implement assignment lifetime.
 * Nonempty assignments currently fail before redirection/dispatch. */
struct csh_command {
    char **argv;
    size_t argc;
    struct csh_assignment *assignments;
    size_t assignment_count;
    struct csh_redirect *redirections;
    size_t redirection_count;
};

enum csh_execution_category {
    CSH_EXEC_EMPTY, CSH_EXEC_EXTERNAL, CSH_EXEC_REGULAR_BUILTIN,
    CSH_EXEC_SPECIAL_BUILTIN
};

struct csh_execution {
    int status;
    int exit_requested; /* Caller leaves its input loop; library never exits. */
    enum csh_execution_category category;
};

void csh_command_destroy(struct csh_command *command);
/* Borrow AST; produce an owned command or leave out empty on error. Accepts
 * only simple nodes (or a singleton foreground parser list). Quotes and
 * escaped literals are removed. Assignments, expansions, unquoted glob/tilde
 * syntax, compound/list/pipeline syntax are rejected before dispatch. */
int csh_command_from_ast(const struct csh_ast *tree, struct csh_command *out,
    struct csh_error *error);
/* Borrow command/state. Runs cd and exit in parent with reversible fds;
 * external execution owns exactly one forked child and waitpid targets it.
 * Return 0 when dispatch completed, including command failure statuses and
 * child redirection/exec errors; -1 for preparation, parent redirection,
 * fork/wait/internal errors.
 * Always initialize result and update state's last_status. error contains a
 * static diagnostic only on -1; child failures print once in the child.
 * Signal termination maps to 128 + signal number. No process-global environ
 * mutation; exec uses the state's exported environment and PATH variable. */
int csh_execute_command(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result, struct csh_error *error);
int csh_execute_ast(struct csh_state *state, const struct csh_ast *tree,
    struct csh_execution *result, struct csh_error *error);

#endif
