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
    if (strcmp(argv[1], "reader") == 0) {
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
    } else if (strcmp(argv[1], "hold") == 0) dprintf(STDOUT_FILENO, "ready\n");
    else return 2;
    for (;;) pause();
}
