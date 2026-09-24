/* Deterministic terminal handshakes for the real shell PTY cases. */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

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
