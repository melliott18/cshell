/* Instrument only input.c. The real public main/parser/executor run unchanged.
 * Match the selected file identity, including duplicated/relocated input fds. */
#include <errno.h>
#include <stdlib.h>
#include <signal.h>
#include <sys/stat.h>
#include <unistd.h>

ssize_t csh_command_read(int fd, void *buffer, size_t size)
{
    const char *path = getenv("CSH_TEST_READ_FILE");
    const char *limit = getenv("CSH_TEST_READ_AFTER");
    struct stat source, target;
    if (path && limit && stat(path, &target) == 0 && fstat(fd, &source) == 0 &&
        source.st_dev == target.st_dev && source.st_ino == target.st_ino) {
        off_t offset = lseek(fd, 0, SEEK_CUR);
        off_t boundary = (off_t)strtol(limit, NULL, 10);
        if (offset >= boundary) {
            if (getenv("CSH_TEST_READ_SIGNAL")) raise(SIGUSR1);
            errno = EIO; return -1;
        }
        if (offset >= 0 && (off_t)size > boundary - offset)
            size = (size_t)(boundary - offset);
    }
    return read(fd, buffer, size);
}
