#ifndef CSHELL_EXECUTE_H
#define CSHELL_EXECUTE_H

#include "cshell/ast.h"
#include "cshell/redirect.h"
#include "cshell/state.h"
#include <sys/types.h>

struct csh_assignment { char *name; char *value; };
struct csh_traps;

/* All pointers are owned; argv is NULL-terminated when argc > 0. Counts
 * describe initialized entries. Zero initialization is an empty command.
 * Values are already expanded; this module owns lifetime. */
struct csh_command {
    char **argv;
    size_t argc;
    int default_path; /* command -p search, without changing the environment. */
    struct csh_assignment *assignments;
    size_t assignment_count;
    struct csh_redirect *redirections;
    size_t redirection_count;
    int substitution_status; /* Last substitution, or zero if none occurred. */
};

enum csh_execution_category {
    CSH_EXEC_EMPTY, CSH_EXEC_EXTERNAL, CSH_EXEC_REGULAR_BUILTIN,
    CSH_EXEC_SPECIAL_BUILTIN, CSH_EXEC_FUNCTION, CSH_EXEC_PIPELINE, CSH_EXEC_UNRESOLVED
};

enum csh_control_transfer { CSH_CONTROL_NONE, CSH_CONTROL_BREAK,
    CSH_CONTROL_CONTINUE, CSH_CONTROL_RETURN };

struct csh_execution {
    enum csh_control_transfer control;
    unsigned levels; /* Remaining loop boundaries to unwind. */
    int status;
    int retain_redirects; /* exec without a command commits this command's fds. */
    int redirection_failed; /* Parent command could not apply redirections. */
    int special_builtin_error; /* Runtime applies context-dependent error policy. */
    int errexit_ignored; /* Failure originated in an exempt command context. */
    int exit_requested; /* Caller leaves its input loop; library never exits. */
    enum csh_execution_category category;
};

/* One entry per stage in source order. pid is zero for an unlaunched stage or
 * a singleton parent builtin. completed makes status valid; reaped makes the
 * raw wait_status valid. Positive PIDs are historical identities after return,
 * never permission to signal/wait again. Prepared APIs report resolved category;
 * AST multi-stage pipelines use UNRESOLVED because resolution occurs in children. */
struct csh_pipeline_stage {
    pid_t pid;
    int status;
    int wait_status;
    int completed;
    int reaped;
    enum csh_execution_category category;
};

struct csh_pipeline_result {
    struct csh_execution execution;
    struct csh_pipeline_stage *stages; /* Owned; destroy even on failure. */
    size_t count;
};

void csh_pipeline_result_destroy(struct csh_pipeline_result *result);
/* Borrow prepared commands and state; out must be empty on entry. Preflight
 * the entire pipeline, then launch all stages before waiting for owned PIDs.
 * Multi-stage commands (including builtins) run in separate children. A single
 * stage uses ordinary dispatch in the current environment. All stage statuses
 * are retained; execution.status uses the last stage or rightmost nonzero
 * stage when pipefail was enabled at entry, logically inverted for !
 * unless a singleton exit requests termination (its requested status is kept).
 * Setup failures return -1 without negation, close pipes, kill and reap started
 * children. Child redirection/exec failures are ordinary stage statuses (0 API
 * return). No process groups/job control in this prepared API. Callers must serialize
 * descriptor mutation and must not reap these children or ignore SIGCHLD.
 * On return no live child ownership is transferred to the caller. */
int csh_execute_pipeline(struct csh_state *state,
    const struct csh_command *commands, size_t count, int negated,
    struct csh_pipeline_result *out, struct csh_error *error);
/* Foreground simple command or pipeline, including compound stages. Preflight
 * syntax, then expand each stage in its execution environment. Honor noexec
 * (no stages are launched) and contextual errexit, including negation. */
int csh_execute_pipeline_ast(struct csh_state *state, const struct csh_ast *tree,
    struct csh_pipeline_result *out, struct csh_error *error);

void csh_command_destroy(struct csh_command *command);
/* Materialize one simple AST in the supplied environment. Expand arguments,
 * redirect operands and assignment values without applying descriptors or
 * dispatching the command. Output is owned and empty on failure. Substitution
 * callbacks can execute. Runtime AST APIs use phased preparation instead, so
 * redirects are active during subsequent redirection/assignment expansion. */
int csh_command_from_ast(struct csh_state *state, const struct csh_ast *tree, struct csh_command *out,
    struct csh_error *error);
/* Borrow command/state. Runs state builtins and exit in parent with reversible fds;
 * external execution owns exactly one forked child and waitpid targets it.
 * Return 0 when dispatch completed, including command failure statuses and
 * child redirection/exec errors; -1 for preparation, parent redirection,
 * fork/wait/internal errors.
 * The exec builtin replaces the calling process on success; its no-command
 * form commits descriptors. Other builtins return through this interface.
 * Always initialize result and update state's last_status. error contains a
 * diagnostic only on -1; use csh_error_message and print unless reported.
 * Child failures print once in the child.
 * Signal termination maps to 128 + signal number. No process-global environ
 * mutation; exec uses the state's exported environment and PATH variable.
 * exit [--] [status] preserves last_status when omitted (or the pre-action
 * status when ending a trap action); otherwise accepts a
 * signed decimal long and uses its low eight bits. Operand errors set status
 * 2 and request exit only in non-interactive state, as do special-builtin
 * redirection errors with their own failure status. */
int csh_execute_command(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result, struct csh_error *error);
/* Resolved parent dispatch for builtin/function consumers. Handler borrows all
 * inputs, returns 0 with status/exit_requested or -1 with an error. It must
 * return normally so descriptors and temporary variables can be restored.
 * EMPTY/EXTERNAL require a NULL handler; parent categories require a handler.
 * Regular builtin/function prefixes are exported temporarily and selectively
 * restored, including attributes. Special prefixes persist, preserving export
 * attributes unless allexport is enabled. Unrelated handler mutations persist.
 * Readonly prefixes fail before side effects, status 1, with exit_requested in
 * noninteractive contexts; caller prints error once and honors that flag even
 * on -1. A copied/subshell context must honor it only within that context. */
typedef int (*csh_command_handler)(struct csh_state *state,
    const struct csh_command *command, struct csh_execution *result,
    struct csh_error *error, void *context);
int csh_execute_resolved(struct csh_state *state, const struct csh_command *command,
    enum csh_execution_category category, csh_command_handler handler,
    void *context, struct csh_execution *result, struct csh_error *error);
/* Simple command or foreground pipeline; discards stage details. Use
 * csh_execute_pipeline_ast when the caller needs the full stage vector. */
int csh_execute_ast(struct csh_state *state, const struct csh_ast *tree,
    struct csh_execution *result, struct csh_error *error);

/* Input observer used by the runtime and eval/dot for verbose mode. */
void csh_execute_input_line(void *state, const unsigned char *bytes, size_t length);

struct csh_background_child;
struct csh_jobs;
/* Initialize with {0}, then set state to a borrowed, live shell state. One
 * context owns its registered direct children; do not copy it or reap those
 * PIDs elsewhere. Destroy before state. Without jobs, no signal handler is installed. */
struct csh_execution_context {
    struct csh_state *state;
    unsigned loop_depth;
    unsigned evaluation_depth;
    struct csh_background_child *children; /* Private owned registry. */
    size_t child_count;
    struct csh_jobs *jobs; /* Optional owned runtime job manager; see jobs.h. */
    struct csh_traps *traps; /* Borrowed process trap table; see traps.h. */
    int dispatching_traps;
    int in_trap;
    int trap_status; /* Status before the current action, for an omitted exit. */
};
/* Lists, AND/OR, compounds, functions, and pipelines with compound stages.
 * Preflight supported syntax before effects; expand only commands reached.
 * Background items return status 0 after registration and publish $!.
 * Reap completed background children at execution boundaries. */
int csh_execute_context_ast(struct csh_execution_context *context,
    const struct csh_ast *tree, struct csh_execution *result,
    struct csh_error *error);
/* Dispatch pending actions at a command boundary; save and restore the status
 * seen before each action. Propagate an exit requested by an action. */
int csh_execute_pending_traps(struct csh_execution_context *context,
    struct csh_execution *result, struct csh_error *error);
/* Run EXIT once with the current status, retaining it unless the action exits
 * explicitly. The caller must have completed command execution first. */
int csh_execute_exit_trap(struct csh_execution_context *context,
    struct csh_error *error);
/* wait=0 polls; wait=1 waits for all registered children, retrying EINTR.
 * Neither changes last status or $!. Errors retain unreaped ownership for a
 * retry. An attached jobs manager instead retains statuses, and wait=1 returns
 * on a monitored stop; see jobs.h for the runtime wait builtin. */
int csh_execution_context_reap(struct csh_execution_context *context, int wait,
    struct csh_error *error);
/* Poll then release the registry. Running children are detached, not killed
 * or waited for: use reap(wait=1) first when a library host must retain/reap
 * every child. A shell exiting normally must not wait for background jobs. */
void csh_execution_context_destroy(struct csh_execution_context *context);

#endif
