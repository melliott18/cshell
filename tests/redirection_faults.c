/* Only redirect.c is instrumented. Public main, parsing and execution remain
 * unchanged. Named errors avoid filling a disk or modifying mounts/credentials. */
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int interrupted, observed = -1;

int csh_redirection_open(const char *path, int flags, ...)
{
    const char *fault = getenv("CSH_REDIRECT_FAULT");
    mode_t mode = 0;
    int fd;
    if (flags & O_CREAT) {
        va_list args;
        va_start(args, flags);
        mode = (mode_t)va_arg(args, int);
        va_end(args);
    }
    if (fault && strcmp(path, "fault-target") == 0) {
        static const struct { const char *name; int number; } errors[] = {
            {"EACCES", EACCES}, {"ENOSPC", ENOSPC}, {"EROFS", EROFS},
            {"EMFILE", EMFILE}, {"ENFILE", ENFILE}, {"EIO", EIO}
        };
        size_t i;
        for (i = 0; i < sizeof(errors) / sizeof(errors[0]); ++i) {
            if (strcmp(fault, errors[i].name) == 0) {
                errno = errors[i].number;
                return -1;
            }
        }
        if (!strcmp(fault, "EINTR") && !interrupted++) {
            errno = EINTR;
            return -1;
        }
        if (!strcmp(fault, "replace") && !(flags & O_EXCL)) {
            /* The preceding stat saw a FIFO. Replace it at the open boundary
             * to test the actual-fd check, without timing a competing process. */
            if (unlink(path) < 0) return -1;
            fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
            if (fd < 0) return -1;
            if (write(fd, "preserved\n", 10) != 10) { close(fd); return -1; }
            if (close(fd) < 0) return -1;
        }
    }
    fd = open(path, flags, mode);
    if (fault && !strcmp(fault, "fstat") && !strcmp(path, "fault-target"))
        observed = fd;
    return fd;
}

int csh_redirection_fstat(int fd, struct stat *result)
{
    if (fd == observed && observed >= 0) {
        observed = -1;
        errno = EIO;
        return -1;
    }
    return fstat(fd, result);
}
