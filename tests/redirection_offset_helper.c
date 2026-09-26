/* CSH-043: bounded descriptor probes, compiled with the shell's off_t ABI. */
#ifdef __APPLE__
#define _DARWIN_C_SOURCE 1 /* fstatfs metadata; off_t remains the native ABI. */
#endif
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#ifdef __APPLE__
#include <sys/mount.h>
#else
#include <sys/vfs.h>
#endif
#include <unistd.h>

#define BOUNDARY ((off_t)2147487744LL)
#define CHECK(test) do { if (!(test)) { \
    fprintf(stderr, "offset-helper: line %d: %s (errno %d)\n", \
        __LINE__, #test, errno); return 2; } } while (0)

/* No writes/truncation at these offsets: seek alone does not extend a file.
 * Supported systems use a signed off_t without padding bits. */
static off_t offset_max(void)
{
    return (off_t)((UINTMAX_C(1) << (sizeof(off_t) * CHAR_BIT - 1)) - 1);
}

static off_t seek_max(int fd)
{
    off_t low = 0, high = offset_max();
    while (low < high) {
        off_t middle = low + (high - low) / 2 + 1;
        if (lseek(fd, middle, SEEK_SET) == middle) low = middle;
        else {
            if (errno != EINVAL && errno != EOVERFLOW) return -1;
            high = middle - 1;
        }
    }
    return low;
}

int main(int argc, char **argv)
{
    struct rlimit limit;
    CHECK(argc >= 2);
    CHECK(sizeof(off_t) * CHAR_BIT <= sizeof(uintmax_t) * CHAR_BIT);
    CHECK((off_t)-1 < 0);
    CHECK(getrlimit(RLIMIT_FSIZE, &limit) == 0);
    if (!strcmp(argv[1], "info")) {
        int fd, failure;
        long bits;
        off_t maximum;
        struct statfs fs;
        CHECK(argc == 3);
        CHECK((fd = open(argv[2], O_RDWR)) >= 0);
        CHECK(fstatfs(fd, &fs) == 0);
        errno = 0;
        bits = fpathconf(fd, _PC_FILESIZEBITS);
        CHECK(bits != -1 || errno == 0);
        CHECK((maximum = seek_max(fd)) >= BOUNDARY);
        CHECK(lseek(fd, maximum, SEEK_SET) == maximum);
        errno = 0;
        CHECK(lseek(fd, 1, SEEK_CUR) == (off_t)-1);
        failure = errno;
        printf("off_t_bits=%zu off_t_max=%jd FILESIZEBITS=%ld "
               "seek_max=%jd next_seek_errno=%d (%s) block_size=%ld ",
            sizeof(off_t) * CHAR_BIT, (intmax_t)offset_max(), bits,
            (intmax_t)maximum, failure, strerror(failure), (long)fs.f_bsize);
#ifdef __APPLE__
        printf("filesystem=%s\n", fs.f_fstypename);
#else
        printf("filesystem_magic=0x%lx\n", (unsigned long)fs.f_type);
#endif
        CHECK(close(fd) == 0);
        return 0;
    }
    /* Detect a pre-existing runner limit that would invalidate the oracle. */
    CHECK(limit.rlim_cur == (rlim_t)BOUNDARY);
    if (!strcmp(argv[1], "write") || !strcmp(argv[1], "native-append")) {
        size_t sent = 0, length;
        CHECK(argc == 3);
        if (!strcmp(argv[1], "native-append")) {
            int fd;
            CHECK(signal(SIGXFSZ, SIG_IGN) != SIG_ERR);
            CHECK((fd = open("data", O_WRONLY | O_APPEND)) >= 0);
            CHECK(dup2(fd, 1) == 1);
            CHECK(close(fd) == 0);
        }
        length = strlen(argv[2]);
        while (sent < length) {
            ssize_t count = write(1, argv[2] + sent, length - sent);
            if (count < 0 && errno == EINTR) continue;
            if (count < 0 && errno == EFBIG) {
                fputs("offset-helper: write: EFBIG\n", stderr);
                return 23;
            }
            CHECK(count > 0);
            sent += (size_t)count;
        }
    } else if (!strcmp(argv[1], "seek")) {
        CHECK(lseek(3, BOUNDARY - 1, SEEK_SET) == BOUNDARY - 1);
    } else if (!strcmp(argv[1], "read")) {
        char byte;
        CHECK(lseek(0, BOUNDARY - 1, SEEK_SET) == BOUNDARY - 1);
        CHECK(read(0, &byte, 1) == 1 && byte == 'Q');
        CHECK(read(0, &byte, 1) == 0);
        puts("read boundary byte and EOF");
    } else if (!strcmp(argv[1], "boundary")) {
        struct stat before, after;
        off_t maximum;
        CHECK(fstat(3, &before) == 0);
        CHECK((maximum = seek_max(3)) >= BOUNDARY);
        CHECK(lseek(3, maximum, SEEK_SET) == maximum);
        errno = 0;
        CHECK(lseek(3, 1, SEEK_CUR) == (off_t)-1);
        CHECK(errno == EINVAL || errno == EOVERFLOW);
        CHECK(lseek(3, 0, SEEK_CUR) == maximum);
        CHECK(fstat(3, &after) == 0);
        CHECK(before.st_size == after.st_size && before.st_blocks == after.st_blocks);
        puts("seek boundary and unchanged file verified");
    } else return 2;
    return 0;
}
