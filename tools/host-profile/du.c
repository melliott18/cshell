/* Configure the selected Linux GNU du process in its documented POSIX mode.
 * GNU coreutils retains all traversal, formatting and utility implementation.
 * No argument, output or exit-status translation is performed.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    int error;
    (void)argc;
    if (setenv("POSIXLY_CORRECT", "1", 1) < 0) {
        perror("du: POSIXLY_CORRECT");
        return 125;
    }
    execv("/usr/bin/du", argv);
    error = errno;
    perror("du: /usr/bin/du");
    return error == ENOENT ? 127 : 126;
}
