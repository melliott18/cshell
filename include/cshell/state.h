#ifndef CSHELL_STATE_H
#define CSHELL_STATE_H

#include <stddef.h>
#include <sys/types.h>
#include "cshell/invocation.h"

struct csh_state;
struct csh_aliases;
/* Lazily allocated, state-owned tables; borrowed until state replacement/destruction. */
struct csh_aliases *csh_state_aliases(struct csh_state *state);

size_t csh_state_getopts_offset(const struct csh_state *state);
void csh_state_set_getopts_offset(struct csh_state *state, size_t offset);
struct csh_state_checkpoint;
/* Executor-owned immutable payload. State owns references, and invokes destroy
 * at the final release, keeping state independent of parser/executor modules.
 * Initialize references to 1 and destroy to a non-NULL finalizer. Retain/release
 * accept NULL. A payload must remain immutable while shared. */
struct csh_function {
    size_t references;
    void (*destroy)(struct csh_function *function);
};
void csh_function_retain(struct csh_function *function);
void csh_function_release(struct csh_function *function);
struct csh_function *csh_state_function(const struct csh_state *state, const char *name);

struct csh_variable_save;

enum csh_state_result {
    CSH_STATE_OK,
    CSH_STATE_INVALID,
    CSH_STATE_NOMEM,
    CSH_STATE_READONLY
};

/* Command path cache, independently copied with shell state. Names/path are copied. */
void csh_state_hash_clear(struct csh_state *state);
const char *csh_state_hash_get(const struct csh_state *state, const char *name);
enum csh_state_result csh_state_hash_set(struct csh_state *state, const char *name, const char *path);
enum csh_state_result csh_state_hash_names(const struct csh_state *state, char ***out);
/* set retains its input; NULL removes a definition. Lookup borrows a value. */
enum csh_state_result csh_state_set_function(struct csh_state *state,
    const char *name, struct csh_function *function);
/* Move caller parameters aside only after new parameters have been copied.
 * Save must be empty on push; pop consumes a successful push exactly once.
 * Restore is allocation-free and preserves $0 and unrelated state. */
struct csh_parameter_save { char **arguments; size_t count; };
enum csh_state_result csh_state_push_parameters(struct csh_state *state,
    size_t count, const char *const arguments[], struct csh_parameter_save *save);
void csh_state_pop_parameters(struct csh_state *state, struct csh_parameter_save *save);

enum csh_variable_attribute {
    CSH_VAR_EXPORT = 1u << 0,
    CSH_VAR_READONLY = 1u << 1
};

struct csh_variable_view {
    /* NULL is unset; "" is set and empty. A missing name has attributes 0. */
    const char *value;
    unsigned attributes;
};

struct csh_state_info {
    unsigned source_depth;      /* Active dot scripts; inherited by subshells. */
    unsigned function_depth;    /* Active calls; inherited by subshell copies. */
    size_t argument_count;       /* $#; excludes $0 */
    int last_status;             /* $?; initially 0, no wait-status conversion */
    pid_t shell_pid;             /* $$; captured once, preserved by copies */
    pid_t background_pid;        /* $!; 0 means no background command yet */
    enum csh_input_mode mode;    /* Original invocation source selection */
    unsigned options;           /* Invocation choices and runtime set state. */
    unsigned errexit_ignored;   /* Nested tested-command contexts, inherited by copies. */
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
/* Opt the active runtime into libc locale updates on locale-variable mutation
 * and rollback. Uses shell values (export is irrelevant), preserves errno,
 * silently falls back to C on unsupported names. Only one active state per
 * process; clones inherit the flag but do not activate until mutated/restored.
 * Lexer syntax recognition is independent of these runtime category updates.
 * Libc may allocate internally when refreshing the locale. */
void csh_state_manage_locale(struct csh_state *state);

enum csh_state_result csh_state_get_variable(const struct csh_state *state,
    const char *name, struct csh_variable_view *out);
/* Assign a non-NULL value, preserving attributes; allexport adds export. */
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

void csh_state_set_errexit_ignored(struct csh_state *state, unsigned depth);

void csh_state_set_source_depth(struct csh_state *state, unsigned depth);
void csh_state_set_function_depth(struct csh_state *state, unsigned depth);

/* Copies share immutable function payloads with independent name tables.
 * Deep copies preserve every value, attribute, parameter, and metadata field.
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
