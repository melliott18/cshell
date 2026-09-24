#include "cshell/redirect.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

struct saved_descriptor {
    int target;
    int backup;
    int flags;
    size_t argument_index;
};

struct csh_redirect_save {
    struct csh_redirect_save *next;
    size_t count;
    struct saved_descriptor entries[];
};

/* Descriptor operations are serialized. Track private backups across nested
 * apply calls so newly expanded operands cannot see or overwrite them. */
static struct csh_redirect_save *active_saves;

static int fail(struct csh_error *error, const char *message, int number,
    size_t index)
{
    *error = (struct csh_error){0};
    error->message = message;
    error->system_errno = number;
    error->status = 1;
    error->argument_index = index;
    return -1;
}

static int descriptor_flags(int fd, int command)
{
    int result;
    do {
        result = fcntl(fd, command);
    } while (result == -1 && errno == EINTR);
    return result;
}

static int set_descriptor_flags(int fd, int flags)
{
    int result;
    do {
        result = fcntl(fd, F_SETFD, flags);
    } while (result == -1 && errno == EINTR);
    return result;
}

static int duplicate_to(int source, int target)
{
    int result;
    do {
        result = dup2(source, target);
    } while (result == -1 && errno == EINTR);
    return result;
}

/* Descriptor mutation is serialized by the caller. No descriptor can be
 * acquired between interrupted close attempts, including in signal handlers. */
static int close_descriptor(int fd)
{
    int result;
    do {
        result = close(fd);
    } while (result == -1 && errno == EINTR);
    return result == -1 && errno != EBADF ? -1 : 0;
}

int csh_redirect_validate(const struct csh_redirect *items, size_t count,
    struct csh_error *error)
{
    size_t index;
    *error = (struct csh_error){0};
    if (count != 0 && items == NULL)
        return fail(error, "missing redirection operands", EINVAL, 0);
    if (count > (SIZE_MAX - sizeof(struct csh_redirect_save)) /
            sizeof(struct saved_descriptor))
        return fail(error, "too many redirections", EOVERFLOW, 0);
    for (index = 0; index < count; ++index) {
        const struct csh_redirect *item = &items[index];
        if (item->fd < 0)
            return fail(error, "invalid redirection descriptor", EBADF,
                index + 1);
        switch (item->kind) {
        case CSH_REDIRECT_READ:
        case CSH_REDIRECT_WRITE:
        case CSH_REDIRECT_APPEND:
        case CSH_REDIRECT_READ_WRITE:
        case CSH_REDIRECT_CLOBBER:
            if (item->path == NULL)
                return fail(error, "missing redirection path", EINVAL,
                    index + 1);
            break;
        case CSH_REDIRECT_DUP_READ:
        case CSH_REDIRECT_DUP_WRITE:
            if (item->source_fd < 0)
                return fail(error, "invalid source descriptor", EBADF,
                    index + 1);
            break;
        case CSH_REDIRECT_CLOSE:
            break;
        case CSH_REDIRECT_HEREDOC:
            if (item->length != 0 && item->data == NULL)
                return fail(error, "missing here-document data", EINVAL,
                    index + 1);
            break;
        default:
            return fail(error, "invalid redirection kind", EINVAL, index + 1);
        }
    }
    return 0;
}

static int is_operand(int fd, const struct csh_redirect *items, size_t count)
{
    size_t index;
    for (index = 0; index < count; ++index) {
        if (fd == items[index].fd ||
            ((items[index].kind == CSH_REDIRECT_DUP_READ ||
              items[index].kind == CSH_REDIRECT_DUP_WRITE) &&
             fd == items[index].source_fd))
            return 1;
    }
    return 0;
}

/* A closed source operand must stay closed: merely using a conventional high
 * descriptor range would make, for example, 1>&10 accidentally succeed. */
static int save_descriptor(int fd, const struct csh_redirect *items,
    size_t count, const int *reserved, size_t reserved_count)
{
    int minimum = 3;
    for (;;) {
        int result;
        size_t index;
        do {
            result = fcntl(fd, F_DUPFD_CLOEXEC, minimum);
        } while (result == -1 && errno == EINTR);
        if (result == -1) return -1;
        for (index = 0; index < reserved_count; ++index)
            if (reserved[index] == result) break;
        if (index == reserved_count && !is_operand(result, items, count))
            return result;
        if (close_descriptor(result) == -1)
            return -1;
        if (result == INT_MAX) {
            errno = EMFILE;
            return -1;
        }
        minimum = result + 1;
    }
}

static void discard_save(struct csh_redirect_save *save)
{
    size_t index;
    for (index = 0; index < save->count; ++index) {
        if (save->entries[index].backup != -1)
            close_descriptor(save->entries[index].backup);
    }
    free(save);
}

int csh_redirect_restore(struct csh_redirect_save **save,
    struct csh_error *error)
{
    struct csh_redirect_save *saved;
    size_t index;
    int result = 0;
    *error = (struct csh_error){0};
    if (save == NULL)
        return fail(error, "missing redirection save", EINVAL, 0);
    saved = *save;
    *save = NULL;
    if (saved == NULL) return 0;
    {
        struct csh_redirect_save **link = &active_saves;
        while (*link != NULL && *link != saved) link = &(*link)->next;
        if (*link == saved) *link = saved->next;
    }
    for (index = 0; index < saved->count; ++index) {
        const struct saved_descriptor *entry = &saved->entries[index];
        int restored;
        if (entry->backup == -1) {
            restored = close_descriptor(entry->target);
        } else {
            restored = duplicate_to(entry->backup, entry->target);
            if (restored != -1)
                restored = set_descriptor_flags(entry->target, entry->flags);
        }
        if (restored == -1 && result == 0)
            result = fail(error, "cannot restore redirection descriptor",
                errno, entry->argument_index);
        if (entry->backup != -1 && close_descriptor(entry->backup) == -1 &&
            result == 0)
            result = fail(error, "cannot close saved descriptor", errno,
                entry->argument_index);
    }
    free(saved);
    return result;
}

static int here_document(const struct csh_redirect *item)
{
    char path[] = "/tmp/cshell-heredoc-XXXXXX";
    int fd;
    int result;
    int number;
    size_t offset = 0;
    do {
        memcpy(path, "/tmp/cshell-heredoc-XXXXXX", sizeof(path));
        fd = mkstemp(path);
    } while (fd == -1 && errno == EINTR);
    if (fd == -1)
        return -1;
    do {
        result = unlink(path);
    } while (result == -1 && errno == EINTR);
    if (result == -1) {
        number = errno;
        close_descriptor(fd);
        /* Make one cleanup attempt even if the first unlink failed. */
        unlink(path);
        errno = number;
        return -1;
    }
    if (set_descriptor_flags(fd, FD_CLOEXEC) == -1)
        goto failure;
    while (offset < item->length) {
        size_t amount = item->length - offset;
        ssize_t written;
        if (amount > 16384)
            amount = 16384;
        do {
            written = write(fd, item->data + offset, amount);
        } while (written == -1 && errno == EINTR);
        if (written == -1)
            goto failure;
        if (written == 0) {
            errno = EIO;
            goto failure;
        }
        offset += (size_t)written;
    }
    do {
        result = lseek(fd, 0, SEEK_SET) == (off_t)-1 ? -1 : 0;
    } while (result == -1 && errno == EINTR);
    if (result == -1)
        goto failure;
    return fd;
failure:
    number = errno;
    close_descriptor(fd);
    errno = number;
    return -1;
}

static int apply_one(const struct csh_redirect *item)
{
    int fd;
    int flags;
    int result;
    int number;
    switch (item->kind) {
    case CSH_REDIRECT_CLOSE:
        return close_descriptor(item->fd);
    case CSH_REDIRECT_DUP_READ:
    case CSH_REDIRECT_DUP_WRITE:
        flags = descriptor_flags(item->source_fd, F_GETFL);
        if (flags == -1)
            return -1;
        if ((item->kind == CSH_REDIRECT_DUP_READ &&
                (flags & O_ACCMODE) == O_WRONLY) ||
            (item->kind == CSH_REDIRECT_DUP_WRITE &&
                (flags & O_ACCMODE) == O_RDONLY)) {
            errno = EBADF;
            return -1;
        }
        if (duplicate_to(item->source_fd, item->fd) == -1)
            return -1;
        /* dup2(fd, fd) is a no-op, but explicit redirection must also make
         * this descriptor available to the command across exec. */
        return set_descriptor_flags(item->fd, 0);
    case CSH_REDIRECT_HEREDOC:
        fd = here_document(item);
        break;
    default:
        switch (item->kind) {
        case CSH_REDIRECT_READ:
            flags = O_RDONLY;
            break;
        case CSH_REDIRECT_APPEND:
            flags = O_WRONLY | O_CREAT | O_APPEND;
            break;
        case CSH_REDIRECT_READ_WRITE:
            flags = O_RDWR | O_CREAT;
            break;
        default:
            flags = O_WRONLY | O_CREAT | O_TRUNC;
            break;
        }
        do {
            fd = open(item->path, flags | O_CLOEXEC, 0666);
        } while (fd == -1 && errno == EINTR);
        break;
    }
    if (fd == -1)
        return -1;
    if (fd == item->fd)
        result = set_descriptor_flags(fd, 0);
    else {
        result = duplicate_to(fd, item->fd);
        number = errno;
        if (close_descriptor(fd) == -1 && result != -1)
            return -1;
        errno = number;
    }
    return result == -1 ? -1 : 0;
}

int csh_redirect_apply(const struct csh_redirect *items, size_t count,
    struct csh_redirect_save **save, struct csh_error *error)
{
    return csh_redirect_apply_reserved(items, count, NULL, 0, save, error);
}

int csh_redirect_apply_reserved(const struct csh_redirect *items, size_t count,
    const int *reserved, size_t reserved_count,
    struct csh_redirect_save **save, struct csh_error *error)
{
    struct csh_redirect_save *saved;
    size_t index;
    *error = (struct csh_error){0};
    if (save == NULL)
        return fail(error, "missing redirection save", EINVAL, 0);
    *save = NULL;
    if (csh_redirect_validate(items, count, error) == -1)
        return -1;
    if (count == 0)
        return 0;
    saved = malloc(sizeof(*saved) + count * sizeof(*saved->entries));
    if (saved == NULL)
        return fail(error, "cannot allocate redirection save", ENOMEM, 0);
    saved->count = 0;
    saved->next = NULL;
    {
        struct csh_redirect_save *outer;
        for (outer = active_saves; outer != NULL; outer = outer->next) {
            for (index = 0; index < outer->count; ++index) {
                int old = outer->entries[index].backup, moved;
                if (old < 0 || !is_operand(old, items, count)) continue;
                moved = save_descriptor(old, items, count, reserved, reserved_count);
                if (moved == -1) {
                    int number = errno;
                    free(saved);
                    return fail(error, "cannot relocate private descriptor", number, 0);
                }
                close_descriptor(old);
                outer->entries[index].backup = moved;
            }
        }
    }
    /* Take the complete snapshot first. An allocation or descriptor-save
     * failure therefore cannot leave any target partially redirected. */
    for (index = 0; index < count; ++index) {
        struct saved_descriptor entry;
        size_t previous;
        int number;
        for (previous = 0; previous < saved->count; ++previous) {
            if (saved->entries[previous].target == items[index].fd)
                break;
        }
        if (previous != saved->count)
            continue;
        entry.target = items[index].fd;
        entry.argument_index = index + 1;
        entry.flags = descriptor_flags(entry.target, F_GETFD);
        entry.backup = -1;
        if (entry.flags == -1) {
            if (errno != EBADF)
                goto save_failure;
        } else {
            entry.backup = save_descriptor(entry.target, items, count, reserved, reserved_count);
            if (entry.backup == -1)
                goto save_failure;
        }
        saved->entries[saved->count++] = entry;
        continue;
save_failure:
        number = errno;
        discard_save(saved);
        return fail(error, "cannot save redirection descriptor", number,
            index + 1);
    }
    saved->next = active_saves;
    active_saves = saved;
    *save = saved;
    for (index = 0; index < count; ++index) {
        if (apply_one(&items[index]) == -1) {
            struct csh_error restore_error;
            int number = errno;
            if (csh_redirect_restore(save, &restore_error) == -1) {
                *error = restore_error;
                return -1;
            }
            return fail(error, "cannot apply redirection", number, index + 1);
        }
    }
    return 0;
}

void csh_redirect_child(void)
{
    while (active_saves != NULL) {
        struct csh_redirect_save *saved = active_saves;
        active_saves = saved->next;
        discard_save(saved);
    }
}
