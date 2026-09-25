#ifndef CSHELL_OUTPUT_H
#define CSHELL_OUTPUT_H

#include <errno.h>
#include <stddef.h>
#include <string.h>
#include <unistd.h>

/* Allocation-free descriptor output, including closed/read-only descriptors.
 * Retry EINTR and partial writes; callers decide the diagnostic/status policy. */
static inline int csh_write_bytes(int fd, const void *data, size_t length)
{
    const unsigned char *bytes = data;
    size_t sent = 0;
    while (sent < length) {
        ssize_t count = write(fd, bytes + sent, length - sent);
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) { if (count == 0) errno = EIO; return -1; }
        sent += (size_t)count;
    }
    return 0;
}

static inline int csh_write_text(int fd, const char *text)
{
    return csh_write_bytes(fd, text, strlen(text));
}

#endif
