/* CSH-077 opt-in adapters for selected host utility contract failures.
 * These executables are never linked into cshell or installed on the host.
 * TERMINAL_PROVIDER is an absolute build-time vendor path, never PATH lookup.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
#ifdef TERMINAL_TPUT
#include <curses.h>
#include <term.h>
#endif

static int diagnostic(const char *message, int status)
{
    fprintf(stderr, "%s: %s\n", TERMINAL_UTILITY, message);
    return status;
}

static int invoke(char **args)
{
    pid_t pid = fork();
    int status;
    if (pid < 0)
        return diagnostic(strerror(errno), 5);
    if (pid == 0) {
        execv(TERMINAL_PROVIDER, args);
        perror(TERMINAL_PROVIDER);
        _exit(5);
    }
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR)
            return diagnostic(strerror(errno), 5);
    }
    return WIFEXITED(status) ? WEXITSTATUS(status) : 5;
}

int main(int argc, char **argv)
{
    int i;
    if (strcmp(TERMINAL_UTILITY, "tabs") == 0) {
        /* POSIX list separators include blanks within a single argument.
         * Normalize only a list; leave type names and other operands alone. */
        for (i = 1; i < argc; ++i) {
            if (strcmp(argv[i], "-T") == 0 && i + 1 < argc) {
                ++i;
            } else if (argv[i][0] >= '0' && argv[i][0] <= '9') {
                char *src = argv[i], *dst = argv[i];
                while (*src) {
                    if (*src == ' ' || *src == '\t') {
                        while (*src == ' ' || *src == '\t')
                            ++src;
                        if (*src && dst > argv[i] && dst[-1] != ',' && *src != ',')
                            *dst++ = ',';
                    } else {
                        *dst++ = *src++;
                    }
                }
                *dst = '\0';
            }
        }
    } else if (strcmp(TERMINAL_UTILITY, "mesg") == 0) {
        if (argc > 2 || (argc == 2 && strcmp(argv[1], "y") && strcmp(argv[1], "n")))
            return diagnostic("expected y or n", 2);
        if (!isatty(STDIN_FILENO) && !isatty(STDOUT_FILENO) && !isatty(STDERR_FILENO))
            return diagnostic("no terminal on standard input, output or error", 2);
    } else if (strcmp(TERMINAL_UTILITY, "who") == 0) {
        /* Check a supplied database before vendors silently treat open failure
         * as an empty database. am i / am I are not database operands. */
        if (argc > 1 && argv[argc - 1][0] != '-' &&
            !(argc >= 3 && strcmp(argv[argc - 2], "am") == 0 &&
              (!strcmp(argv[argc - 1], "i") || !strcmp(argv[argc - 1], "I")))) {
            int fd = open(argv[argc - 1], O_RDONLY);
            if (fd < 0)
                return diagnostic(strerror(errno), 1);
            close(fd);
        }
    } else if (strcmp(TERMINAL_UTILITY, "tput") == 0) {
        char *type = NULL;
        int result = 0;
        i = 1;
        while (i < argc && !strncmp(argv[i], "-T", 2)) {
            if (argv[i][2]) {
                type = argv[i++] + 2;
            } else {
                if (++i == argc)
                    return diagnostic("-T needs a terminal type", 2);
                type = argv[i++];
            }
        }
        if (i < argc && !strcmp(argv[i], "--"))
            ++i;
        if (i == argc)
            return diagnostic("expected clear, init or reset", 2);
        if (argv[i][0] == '-')
            return diagnostic("invalid option", 2);
        for (; i < argc; ++i) {
            char *args[5];
            int n = 0, status;
            /* This profile exposes the POSIX operands; terminfo capability
             * query extensions are deliberately outside its interface. */
            if (strcmp(argv[i], "clear") && strcmp(argv[i], "init") && strcmp(argv[i], "reset"))
                return diagnostic("invalid operand", 4);
            args[n++] = argv[0];
            if (type) {
                args[n++] = "-T";
                args[n++] = type;
            }
            args[n++] = argv[i];
            args[n] = NULL;
#ifdef TERMINAL_TPUT
            if (!strcmp(argv[i], "clear")) {
                int error;
                char *capability;
                /* A vendor status can mean either missing capability or I/O
                 * failure. Inspect the capability, never waive an exit code. */
                if (setupterm(type, STDOUT_FILENO, &error) != OK)
                    return diagnostic("terminal type is unavailable", 3);
                capability = tigetstr("clear");
                if (capability == (char *)-1) {
                    del_curterm(cur_term);
                    return diagnostic("clear capability lookup failed", 5);
                }
                if (capability == NULL) {
                    del_curterm(cur_term);
                    continue;
                }
                del_curterm(cur_term);
            }
#endif
            status = invoke(args);
            if (status != 0)
                result = status;

        }
        return result;
    }
    execv(TERMINAL_PROVIDER, argv);
    return diagnostic(strerror(errno), 5);
}
