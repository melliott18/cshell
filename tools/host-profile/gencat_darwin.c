/* Standalone driver for the Alfalfa/Apple catalog engine. The included files
 * retain the upstream permissive license. Catalog bytes remain libc-native. */
#define _DARWIN_C_SOURCE
#include <sys/types.h>
#include <errno.h>
#include <fcntl.h>
#include <locale.h>
#include <stdio.h>
#include <strings.h>
#include <stdlib.h>
#include <unistd.h>
#include <err.h>

static ssize_t checked_write(int fd, const void *data, size_t length)
{
    size_t done = 0;
    while (done < length) {
        ssize_t n = write(fd, (const char *)data + done, length - done);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) err(1, "gencat: write");
        done += (size_t)n;
    }
    return (ssize_t)done;
}
static off_t checked_seek(int fd, off_t offset, int whence)
{
    off_t result = lseek(fd, offset, whence);
    if (result == (off_t)-1) err(1, "gencat: seek");
    return result;
}
static ssize_t checked_read(int fd, void *data, size_t length)
{
    ssize_t result;
    do result = read(fd, data, length); while (result < 0 && errno == EINTR);
    if (result < 0) err(1, "gencat: read");
    return result;
}
#define bzero(pointer, size) memset(pointer, 0, size)
#define bcopy(source, destination, size) memmove(destination, source, size)
#define write checked_write
#define lseek checked_seek
#define read checked_read
#include "vendor/gencat-darwin/genlib.c"
#undef write
#undef lseek
#undef read

int main(int argc, char **argv)
{
    int input, output, index;
    FILE *temporary = NULL;
    char buffer[8192];
    ssize_t count;
    setlocale(LC_ALL, "");
    if (argc < 3 || (argv[1][0] == '-' && argv[1][1]))
        errx(1, "usage: gencat catfile msgfile ...");
    /* Do not let tmpfile/open reuse a closed standard descriptor that a
     * later '-' operand denotes. Diagnose before allocating catalog storage. */
    if (!strcmp(argv[1], "-") && fcntl(STDOUT_FILENO, F_GETFD) < 0)
        err(1, "gencat: stdout");
    for (index = 2; index < argc; ++index)
        if (!strcmp(argv[index], "-") && fcntl(STDIN_FILENO, F_GETFD) < 0)
            err(1, "gencat: stdin");
    if (!strcmp(argv[1], "-")) {
        /* The native file format has backpatched offsets; use an anonymous
         * seekable file, then copy to stdout. No named temporary survives. */
        temporary = tmpfile();
        if (!temporary) err(1, "gencat: temporary output");
        output = fileno(temporary);
    } else {
        input = open(argv[1], O_RDONLY);
        if (input >= 0) { MCReadCat(input); close(input); }
        else if (errno != ENOENT) err(1, "gencat: %s", argv[1]);
        output = -1;
    }
    for (index = 2; index < argc; ++index) {
        input = !strcmp(argv[index], "-") ? STDIN_FILENO : open(argv[index], O_RDONLY);
        if (input < 0) err(1, "gencat: %s", argv[index]);
        MCParse(input);
        if (input != STDIN_FILENO && close(input)) err(1, "gencat: close input");
    }
    if (output < 0) {
        output = open(argv[1], O_WRONLY | O_CREAT | O_TRUNC, 0666);
        if (output < 0) err(1, "gencat: %s", argv[1]);
    }
    MCWriteCat(output);
    if (temporary) {
        checked_seek(output, 0, SEEK_SET);
        while ((count = checked_read(output, buffer, sizeof(buffer))) > 0)
            checked_write(STDOUT_FILENO, buffer, (size_t)count);
        if (fclose(temporary)) err(1, "gencat: close temporary output");
    } else if (close(output)) err(1, "gencat: close output");
    return 0;
}
