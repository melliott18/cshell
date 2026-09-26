#ifndef CSHELL_REDIRECT_H
#define CSHELL_REDIRECT_H

#include "cshell/input.h"

enum csh_redirect_kind {
    CSH_REDIRECT_READ, CSH_REDIRECT_WRITE, CSH_REDIRECT_APPEND,
    CSH_REDIRECT_READ_WRITE, CSH_REDIRECT_CLOBBER,
    CSH_REDIRECT_DUP_READ, CSH_REDIRECT_DUP_WRITE, CSH_REDIRECT_CLOSE,
    CSH_REDIRECT_NOCLOBBER, /* Captured option for a prepared > operation. */
    CSH_REDIRECT_HEREDOC
};

/* Prepared, owned operands. Only path for file operations and data for
 * HEREDOC are populated; source_fd is used by DUP operations. Here-document
 * data is already expanded, may contain NUL, and has exactly length bytes. */
struct csh_redirect {
    enum csh_redirect_kind kind;
    int fd;
    int source_fd;
    char *path;
    unsigned char *data;
    size_t length;
};

struct csh_redirect_save;

/* Borrow inputs. validate has no descriptor/filesystem side effects. apply
 * saves each target's original open/closed state and descriptor flags, then
 * applies operations in order. Private saved fds cannot alias any operand.
 * On failure apply restores and clears *save. On success the caller MUST
 * restore, even when command execution fails. Restore consumes *save.
 * Do not overwrite an outstanding save token with another apply call.
 * Descriptor mutation must be serialized, including signal handlers.
 * Restore attempts every target on error and reports the first failure.
 * Restore cannot undo filesystem creation/truncation or shared file offsets.
 * File opens use the native off_t/open offset maximum, with no lower shell
 * limit. Duplications retain the source open description and shared offset.
 * Filesystem and resource-limit enforcement remain host responsibilities.
 * All errors are returned without printing. error and save are required.
 * Callers serialize descriptor mutation, including signal handlers; no
 * concurrent descriptor acquisition is allowed during interrupted closes. */
int csh_redirect_validate(const struct csh_redirect *items, size_t count,
    struct csh_error *error);
int csh_redirect_apply(const struct csh_redirect *items, size_t count,
    struct csh_redirect_save **save, struct csh_error *error);
/* Group bodies can refer to descriptors beyond the group's own operands.
 * Exclude those descriptors from private backups for the group's lifetime. */
int csh_redirect_apply_reserved(const struct csh_redirect *items, size_t count,
    const int *reserved, size_t reserved_count,
    struct csh_redirect_save **save, struct csh_error *error);
int csh_redirect_restore(struct csh_redirect_save **save,
    struct csh_error *error);

/* After fork, before any child shell work: close inherited private backups.
 * The parent retains its own restoration tokens. */
void csh_redirect_child(void);
/* Consume backups without restoring targets (exec without a command). */
void csh_redirect_commit(struct csh_redirect_save **save);

#endif
