/* CSH-077 opt-in adapters for selected host utility contract failures.
 * These executables are never linked into cshell or installed on the host.
 * TERMINAL_PROVIDER is an absolute build-time vendor path, never PATH lookup.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <signal.h>
#include <fcntl.h>
#include <locale.h>
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

/* stty reports depend on stdin, so relay stdout through a bounded buffer.
 * Catch real write/flush failures even when a vendor ignores its stdio error. */
static int report(char **args)
{
    int descriptors[2], status, failed = 0;
    pid_t pid;
    char bytes[4096];
    ssize_t count;
    if (pipe(descriptors) < 0)
        return diagnostic(strerror(errno), 1);
    pid = fork();
    if (pid < 0) {
        close(descriptors[0]);
        close(descriptors[1]);
        return diagnostic("cannot launch report provider", 1);
    }
    if (pid == 0) {
        close(descriptors[0]);
        if (dup2(descriptors[1], STDOUT_FILENO) < 0)
            _exit(1);
        close(descriptors[1]);
        execv(TERMINAL_PROVIDER, args);
        perror(TERMINAL_PROVIDER);
        _exit(1);
    }
    close(descriptors[1]);
    for (;;) {
        size_t offset = 0;
        count = read(descriptors[0], bytes, sizeof(bytes));
        if (count < 0 && errno == EINTR)
            continue;
        if (count <= 0) {
            failed = count < 0;
            break;
        }
        while (offset < (size_t)count) {
            ssize_t written = write(STDOUT_FILENO, bytes + offset, (size_t)count - offset);
            if (written < 0 && errno == EINTR)
                continue;
            if (written <= 0) {
                failed = 1;
                break;
            }
            offset += (size_t)written;
        }
        if (failed)
            break;
    }
    close(descriptors[0]);
    if (failed)
        (void)kill(pid, SIGKILL);
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR)
            return diagnostic("report provider wait failed", 1);
    }
    if (failed)
        return diagnostic("report output failed", 1);
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}

int main(int argc, char **argv)
{
    int i;
    (void)setlocale(LC_ALL, "");
    if (strcmp(TERMINAL_UTILITY, "tty") == 0) {
        const char *name;
        int terminal;
        if (argc > 1 && !(argc == 2 && !strcmp(argv[1], "--")))
            return diagnostic("expected no operands", 2);
        terminal = isatty(STDIN_FILENO);
        if (!terminal && errno == EBADF)
            return diagnostic("invalid standard input", 2);
        name = terminal ? ttyname(STDIN_FILENO) : "not a tty";
        if (!name)
            return diagnostic(strerror(errno), 2);
        if (puts(name) == EOF || fflush(stdout) == EOF)
            return diagnostic("standard output failed", 2);
        return terminal ? 0 : 1;
    } else if (strcmp(TERMINAL_UTILITY, "stty") == 0) {
        char **args;
        int n = 0;
        if (argc == 1 || (argc == 2 && (!strcmp(argv[1], "-a") || !strcmp(argv[1], "-g"))))
            return report(argv);
        args = calloc((size_t)argc * 3 + 1, sizeof(*args));
        if (!args)
            return diagnostic(strerror(errno), 1);
        for (i = 0; i < argc; ++i) {
            args[n++] = argv[i];
            /* Darwin's -nl enables ICRNL but leaves these flags unchanged. */
            if (i && !strcmp(argv[i], "-nl")) {
                args[n++] = "-inlcr";
                args[n++] = "-igncr";
            }
        }
        execv(TERMINAL_PROVIDER, args);
        free(args);
        return diagnostic(strerror(errno), 1);
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
        /* POSIX leaves the unset/null TERM default unspecified. Pin it to
         * dumb, including init/reset, rather than treating it as usage error. */
        if (!type && (!getenv("TERM") || !*getenv("TERM")))
            type = "dumb";
        for (; i < argc; ++i) {
            /* This profile exposes the POSIX operands; terminfo capability
             * query extensions are deliberately outside its interface. */
            if (strcmp(argv[i], "clear") && strcmp(argv[i], "init") && strcmp(argv[i], "reset"))
                return diagnostic("invalid operand", 4);
#ifdef TERMINAL_TPUT
            {
                static char *const initialize[] = {"is1", "is2", "is3"};
                static char *const reset[] = {"rs1", "rs2", "rs3"};
                int error, phase, failed = 0;
                int count = !strcmp(argv[i], "clear") ? 1 : 3;
                /* The profile's init/reset policy emits the three strings in
                 * order. Each absent reset phase falls back to its init phase.
                 * No terminal modes, files or programs are changed/executed. */
                if (setupterm(type, STDOUT_FILENO, &error) != OK)
                    return diagnostic("terminal type is unavailable", error < 0 ? 5 : 3);
                for (phase = 0; phase < count; ++phase) {
                    char *name = count == 1 ? "clear" :
                        (!strcmp(argv[i], "init") ? initialize[phase] : reset[phase]);
                    char *capability = tigetstr(name);
                    if (!capability && !strcmp(argv[i], "reset"))
                        capability = tigetstr(initialize[phase]);
                    if (capability == (char *)-1) {
                        failed = 1;
                        break;
                    }
                    if (capability && (tputs(capability, 1, putchar) == ERR || ferror(stdout))) {
                        failed = 1;
                        break;
                    }
                }
                if (fflush(stdout) == EOF)
                    failed = 1;
                del_curterm(cur_term);
                if (failed)
                    return diagnostic("terminal output failed", 5);
            }
#else
            return diagnostic("terminal capability support unavailable", 5);
#endif
        }
        return 0;
    }
    execv(TERMINAL_PROVIDER, argv);
    return diagnostic(strerror(errno), 5);
}
