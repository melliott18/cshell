#define CSHELL_FAULT_IMPLEMENTATION
#include "prompt_faults.h"

#include <errno.h>
#include <string.h>

static unsigned interruptions, short_writes;
static int retrying;

static int is_prompt(const void *bytes, size_t length)
{
    const char *text = bytes;
    return length == 2 && (text[0] == '$' || text[0] == '>') && text[1] == ' ';
}

int csh_prompt_fault_fputs(const char *text, FILE *stream)
{
    if (stream == stderr && is_prompt(text, strlen(text)) && !retrying) {
        retrying = 1;
        ++interruptions;
        errno = EINTR;
        return EOF;
    }
    retrying = 0;
    return fputs(text, stream);
}

ssize_t csh_prompt_fault_write(int fd, const void *bytes, size_t length)
{
    if (fd == STDERR_FILENO && is_prompt(bytes, length)) {
        if (!retrying) {
            retrying = 1;
            ++interruptions;
            errno = EINTR;
            return -1;
        }
        retrying = 0;
        ++short_writes;
        return write(fd, bytes, 1);
    }
    return write(fd, bytes, length);
}

int main(int argc, char **argv)
{
    int status = csh_prompt_fault_main(argc, argv);
    /* Do not accept a passing transcript if the injected main output path
     * was bypassed. Every interrupted descriptor write is then shortened. */
    if (interruptions == 0 || short_writes != interruptions) {
        fputs("prompt output fault injection was not exercised\n", stderr);
        return 1;
    }
    return status;
}
