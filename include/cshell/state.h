#ifndef CSHELL_STATE_H
#define CSHELL_STATE_H

#include <stddef.h>
#include <sys/types.h>
#include "cshell/invocation.h"

struct csh_state;
struct csh_state_checkpoint;
struct csh_variable_save;

enum csh_state_result {
    CSH_STATE_OK,
    CSH_STATE_INVALID,
    CSH_STATE_NOMEM,
    CSH_STATE_READONLY
};

enum csh_variable_attribute {
    CSH_VAR_EXPORT = 1u << 0,
    CSH_VAR_READONLY = 1u << 1
};

/* Storage flags only: parsing and option effects belong to later tickets. */
enum csh_shell_option {
    CSH_OPT_INTERACTIVE = 1u << 0,
    CSH_OPT_ALLEXPORT = 1u << 1,
    CSH_OPT_ERREXIT = 1u << 2,
    CSH_OPT_NOGLOB = 1u << 3,
    CSH_OPT_NOEXEC = 1u << 4,
    CSH_OPT_NOUNSET = 1u << 5,
    CSH_OPT_VERBOSE = 1u << 6,
    CSH_OPT_XTRACE = 1u << 7,
    CSH_OPT_NOCLOBBER = 1u << 8,
    CSH_OPT_PIPEFAIL = 1u << 9,
    CSH_OPT_MONITOR = 1u << 10,
    CSH_OPT_NOTIFY = 1u << 11
};

struct csh_variable_view {
    /* NULL is unset; "" is set and empty. A missing name has attributes 0. */
    const char *value;
    unsigned attributes;
};

struct csh_state_info {
    size_t argument_count;       /* $#; excludes $0 */
    int last_status;             /* $?; initially 0, no wait-status conversion */
    pid_t shell_pid;             /* $$; captured once, preserved by copies */
    pid_t background_pid;        /* $!; 0 means no background command yet */
    enum csh_input_mode mode;    /* Original invocation source selection */
    unsigned options;           /* Initially only invocation.interactive */
};

/* All retained strings are copied. No operation uses getenv/setenv/environ.
 * Failed mutations leave state unchanged. Errors are returned without printing,
 * exiting, or changing last_status. Names use [A-Za-z_][A-Za-z0-9_]*,
 * independent of locale.
 * Borrowed views/parameters expire on successful mutation, restore, or destroy.
 * Objects are not thread-safe; all pointers must designate valid live objects.
 * Constructors set *out to NULL on failure; out must not own an earlier object.
 * NULL envp means empty environment. Invalid entries are ignored; for duplicate
 * valid names the last entry wins. Imported variables have the export attribute.
 * Invocation input is neither retained nor consumed. */
enum csh_state_result csh_state_create(struct csh_state **out,
    const struct csh_invocation *invocation, char *const envp[]);
void csh_state_destroy(struct csh_state *state); /* NULL accepted */

enum csh_state_result csh_state_get_variable(const struct csh_state *state,
    const char *name, struct csh_variable_view *out);
/* Assign a non-NULL value, preserving attributes; new names start unexported. */
enum csh_state_result csh_state_set_variable(struct csh_state *state,
    const char *name, const char *value);
/* Set/clear masks must be disjoint and contain only known attribute bits.
 * May declare an unset variable. Readonly cannot be cleared once established;
 * export may still be changed on a readonly variable. */
enum csh_state_result csh_state_update_attributes(struct csh_state *state,
    const char *name, unsigned set, unsigned clear);
/* Removes both value and attributes; an absent name succeeds. */
enum csh_state_result csh_state_unset_variable(struct csh_state *state,
    const char *name);

/* Owned NULL-terminated snapshot of all declared variable names, in unspecified
 * order. Survives state changes/destruction; free with environment_destroy. */
enum csh_state_result csh_state_names(const struct csh_state *state, char ***out);

/* Owned NULL-terminated name=value vector, including exported set values only.
 * Ordering is unspecified. Snapshot survives every state mutation/destruction. */
enum csh_state_result csh_state_environment(const struct csh_state *state,
    char ***out);
void csh_state_environment_destroy(char **environment); /* NULL accepted */

/* Selective rollback: copy the named variables (duplicates allowed), including
 * absence and attributes. Restore consumes *save without allocating, bypasses
 * readonly, and preserves all unrelated variables and metadata. Nested scopes
 * on one state must be restored in reverse order. Output must be empty. */
enum csh_state_result csh_state_save_variables(const struct csh_state *state,
    size_t count, const char *const names[], struct csh_variable_save **out);
enum csh_state_result csh_state_restore_variables(struct csh_state *state,
    struct csh_variable_save **save);
void csh_state_variable_save_destroy(struct csh_variable_save *save);

/* Index 0 is $0; indices 1..$# are positional parameters. NULL indicates an
 * out-of-range index or NULL state. Replacing positionals never changes $0.
 * arguments may be NULL only when count is zero; no NULL terminator required.
 * Elements may alias existing borrowed parameter/variable strings. */
const char *csh_state_parameter(const struct csh_state *state, size_t index);
enum csh_state_result csh_state_set_parameters(struct csh_state *state,
    size_t count, const char *const arguments[]);
enum csh_state_result csh_state_get_info(const struct csh_state *state,
    struct csh_state_info *out);
/* Status accepts nonnegative ints, including encoded signal statuses above 255.
 * Background accepts a positive ID or 0 to clear; negative inputs are invalid. */
enum csh_state_result csh_state_set_status(struct csh_state *state, int status);
enum csh_state_result csh_state_set_background(struct csh_state *state, pid_t pid);
enum csh_state_result csh_state_update_options(struct csh_state *state,
    unsigned set, unsigned clear);

/* Deep copies preserve every value, attribute, parameter, and metadata field.
 * Save makes an independent full-state checkpoint. Restore replaces the entire
 * state, consumes *checkpoint and sets it to NULL, without allocating. It is an
 * internal rollback primitive, including for readonly attributes, not a shell
 * assignment. Checkpoints can be discarded or restored exactly once. Nested
 * save/restore order is caller-controlled. External resources (cwd, fds, jobs)
 * are not included. Use clone for an independently mutable execution context. */
enum csh_state_result csh_state_clone(const struct csh_state *state,
    struct csh_state **out);
enum csh_state_result csh_state_save(const struct csh_state *state,
    struct csh_state_checkpoint **out);
enum csh_state_result csh_state_restore(struct csh_state *state,
    struct csh_state_checkpoint **checkpoint);
void csh_state_checkpoint_destroy(struct csh_state_checkpoint *checkpoint);

#endif
