/* Deterministic terminal handshakes for the real shell PTY cases. */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>
#include <sys/wait.h>

static int continue_tty = -1;
static void continued(int number)
{
    int saved = errno;
    (void)number;
    while (write(continue_tty, "reader-continued\n", 17) < 0 && errno == EINTR) {}
    errno = saved;
}

int main(int argc, char **argv)
{
    struct termios modes;
    int tty;
    char byte;
    if (argc < 2) return 2;
    if (strcmp(argv[1], "status") == 0) return argc > 2 ? atoi(argv[2]) : 0;
    if (strcmp(argv[1], "gate") == 0) {
        int fd = open(argv[2], O_RDONLY);
        if (fd < 0) return 2;
        if (read(fd, &byte, 1) != 1) return 3;
        close(fd);
        return argc > 3 ? atoi(argv[3]) : 0;
    }
    tty = open("/dev/tty", O_RDWR);
    if (tty < 0 || tcgetattr(tty, &modes) < 0) return 3;
    /* CSH-057 / JOB-001: exec preserves the controlling session leader.
     * Another live group owns the terminal before cshell starts. */
    if (strcmp(argv[1], "session-start") == 0) {
        int ready[2];
        pid_t child;
        if (argc != 3 || getsid(0) != getpid() || pipe(ready) < 0) return 21;
        child = fork();
        if (child < 0) return 22;
        if (child == 0) {
            if (setpgid(0, 0) < 0 || write(ready[1], "r", 1) != 1) _exit(23);
            for (;;) pause();
        }
        if (read(ready[0], &byte, 1) != 1 || tcsetpgrp(tty, child) < 0 ||
            tcgetpgrp(tty) != child) return 24;
        close(ready[0]); close(ready[1]); close(tty);
        execl(argv[2], argv[2], (char *)NULL);
        return 25;
    }
    /* SIGSTOP is delivered by kill itself while a builtin executes in the
     * current shell. The parent observes WIFSTOPPED before sending CONT. */
    if (strcmp(argv[1], "child-stop") == 0) {
        raise(SIGSTOP);
        if (tcgetpgrp(tty) != getpgrp()) return 37;
        return 23;
    }
    if (strcmp(argv[1], "builtin-stop") == 0) {
        pid_t child;
        int status;
        struct termios stopped_modes;
        if (argc != 3 && argc != 4) return 2;
        child = fork();
        if (child < 0) return 26;
        if (!child) {
            char script[512];
            if (argc == 4) snprintf(script, sizeof(script),
                "{ \"$1\" child-stop & wait %%1; } 2>/dev/null; "
                "kill -s STOP $$; wait %%1; case $? in %d) ;; *) exit 38;; esac; "
                "fg %%1 >/dev/null; case $? in 23) ;; *) exit 39;; esac; "
                "echo builtin-resumed; \"$1\" check", 128 + SIGSTOP);
            else snprintf(script, sizeof(script),
                "kill -s STOP $$; echo builtin-resumed; \"$1\" check");
            execl(argv[2], argv[2], "-ic", script,
                "builtin-stop", argv[0], (char *)NULL);
            _exit(27);
        }
        /* The nested foreground shell makes its own group at startup. */
        pid_t got;
        do { got = waitpid(child, &status, WUNTRACED); } while (got < 0 && errno == EINTR);
        if (got != child || !WIFSTOPPED(status) || WSTOPSIG(status) != SIGSTOP ||
            getpgid(child) != child || tcgetpgrp(tty) != child ||
            tcgetattr(tty, &stopped_modes) < 0 ||
            stopped_modes.c_lflag != modes.c_lflag) return 28;
        puts("builtin-stopped"); fflush(stdout);
        if (kill(child, SIGCONT) < 0) return 29;
        do { got = waitpid(child, &status, 0); } while (got < 0 && errno == EINTR);
        signal(SIGTTOU, SIG_IGN);
        if (got != child || !WIFEXITED(status) || WEXITSTATUS(status) != 0 ||
            tcsetpgrp(tty, getpgrp()) < 0 || tcgetattr(tty, &stopped_modes) < 0 ||
            stopped_modes.c_lflag != modes.c_lflag) return 30;
        return 0;
    }
    if (strcmp(argv[1], "stop") == 0) {
        int number = argc > 2 ? atoi(argv[2]) : SIGTSTP;
        if (tcgetpgrp(tty) != getpgrp()) return 31;
        raise(number);
        if (tcgetpgrp(tty) != getpgrp()) return 32;
        puts("stop-resumed");
        return 23;
    }
    /* PID/PGID assertions are inside the helper, never normalized out of a
     * transcript. The producer's group is checked by the pipeline consumer. */
    if (strcmp(argv[1], "background-producer") == 0) {
        pid_t group = getpgrp();
        if (tcgetpgrp(tty) == group || getpid() != group ||
            write(STDOUT_FILENO, &group, sizeof(group)) != sizeof(group)) return 33;
        return 0;
    }
    if (strcmp(argv[1], "background-pipeline") == 0) {
        pid_t group;
        if (tcgetpgrp(tty) == getpgrp() ||
            read(STDIN_FILENO, &group, sizeof(group)) != sizeof(group) ||
            group != getpgrp()) return 34;
        puts("background-pipeline-ok");
        return 0;
    }
    if (strcmp(argv[1], "compound-group") == 0) {
        if (getpgrp() != getppid() || tcgetpgrp(tty) == getpgrp()) return 35;
        puts("compound-group-ok");
        return 0;
    }
    /* CSH-050 / JOB-001: exercise a nested shell both in the inherited
     * foreground group (not its leader) and in a separate background group.
     * The PTY runner bounds and cleans the whole session on any failure. */
    if (strcmp(argv[1], "startup") == 0) {
        pid_t child;
        int status, background;
        if (argc != 4) return 2;
        background = strcmp(argv[2], "background") == 0;
        child = fork();
        if (child < 0) return 11;
        if (child == 0) {
            if (background && setpgid(0, 0) < 0) _exit(12);
            execl(argv[3], argv[3], "-ic",
                "case $- in *m*) ;; *) exit 19;; esac; exec \"$1\" startup-check \"$$\"",
                "startup", argv[0], (char *)NULL);
            _exit(13);
        }
        if (background) {
            pid_t result;
            do { result = waitpid(child, &status, WUNTRACED); } while (result < 0 && errno == EINTR);
            if (result != child || !WIFSTOPPED(status) || WSTOPSIG(status) != SIGTTIN ||
                tcgetpgrp(tty) != getpgrp()) return 14;
            puts("startup-stopped");
            fflush(stdout);
            if (tcsetpgrp(tty, child) < 0 || kill(child, SIGCONT) < 0) return 15;
        }
        while (waitpid(child, &status, 0) < 0) if (errno != EINTR) return 16;
        signal(SIGTTOU, SIG_IGN);
        if (tcsetpgrp(tty, getpgrp()) < 0) return 17;
        return WIFEXITED(status) ? WEXITSTATUS(status) : 18;
    }
    if (strcmp(argv[1], "startup-check") == 0) {
        if (argc != 3 || getpgrp() != (pid_t)strtol(argv[2], NULL, 10) ||
            tcgetpgrp(tty) != getpgrp()) return 20;
        puts("startup-foreground");
        return 0;
    }
    if (strcmp(argv[1], "check") == 0) {
        if (tcgetpgrp(tty) != getpgrp() || !(modes.c_lflag & ICANON) ||
            (modes.c_lflag & ECHO)) return 4;
        puts("terminal-ok"); return 0;
    }
    if (strcmp(argv[1], "reader") == 0 || strcmp(argv[1], "compound-reader") == 0) {
        if (!strcmp(argv[1], "compound-reader")) {
            struct sigaction action = {0};
            continue_tty = tty;
            action.sa_handler = continued;
            sigemptyset(&action.sa_mask);
            if (sigaction(SIGCONT, &action, NULL) < 0) return 36;
        }
        /* Opening the terminal is harmless in the background; reading stops
         * with TTIN until fg returns ownership to this process group. */
        dprintf(STDOUT_FILENO, "reader-ready\n");
        do {
            ssize_t count;
            do { count = read(tty, &byte, 1); } while (count < 0 && errno == EINTR);
            if (count != 1) return 5;
        } while (byte != '\n');
        dprintf(STDOUT_FILENO, "reader-done\n");
        return 0;
    }
    if (strcmp(argv[1], "modes") == 0) {
        modes.c_lflag &= ~ICANON;
        if (tcsetattr(tty, TCSANOW, &modes) == -1) return 6;
        dprintf(STDOUT_FILENO, "modes-ready\n");
        raise(SIGTSTP);
        if (tcgetattr(tty, &modes) == -1 || (modes.c_lflag & ICANON)) return 7;
        dprintf(STDOUT_FILENO, "modes-resumed\n");
        return 0;
    }
    if (tcgetpgrp(tty) != getpgrp()) return 8;
    if (strcmp(argv[1], "pipeline") == 0) {
        pid_t group;
        if (read(STDIN_FILENO, &group, sizeof(group)) != sizeof(group) || group != getpgrp()) return 9;
        dprintf(STDOUT_FILENO, "pipeline-ready\n");
    } else if (strcmp(argv[1], "producer") == 0) {
        pid_t group = getpgrp();
        if (write(STDOUT_FILENO, &group, sizeof(group)) != sizeof(group)) return 10;
    } else if (strcmp(argv[1], "hold") == 0) {
        sigset_t mask;
        /* These controlled terminal cases start with INT/CHLD unblocked.
         * Diagnose a leaked shell bookkeeping mask before waiting for input. */
        if (sigprocmask(SIG_SETMASK, NULL, &mask) < 0) return 40;
        if (sigismember(&mask, SIGINT) || sigismember(&mask, SIGCHLD)) {
            dprintf(STDERR_FILENO, "jobs_helper: inherited blocked INT/CHLD\n");
            return 41;
        }
        dprintf(STDOUT_FILENO, "ready\n");
    }
    else return 2;
    for (;;) pause();
}
