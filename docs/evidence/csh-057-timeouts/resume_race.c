/* Minimal host diagnostic: no cshell code. Run under the existing PTY harness. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>
#include <time.h>

int main(int argc, char **argv)
{
    const int extra_continue = argc > 1 && atoi(argv[1]);
    const pid_t shell = getpgrp();
    assert(signal(SIGTTOU, SIG_IGN) != SIG_ERR);
    for (int i = 0; i < 64; ++i) {
        int gate[2], status, rc;
        pid_t child, got;
        char byte;
        assert(pipe(gate) == 0);
        child = fork();
        assert(child >= 0);
        if (!child) {
            close(gate[1]);
            
            assert(read(gate[0], &byte, 1) == 0);
            close(gate[0]);
            if (argc > 2) {
                execl(argv[2], argv[2], "hold", (char *)NULL);
                _exit(127);
            }
            assert(tcgetpgrp(0) == getpgrp());
            assert(write(1, "ready\n", 6) == 6);
            for (;;) pause();
        }
        assert(setpgid(child, child) == 0);
        rc = tcsetpgrp(0, child);
        if (rc < 0) {
            int saved = errno;
            dprintf(1, "handoff errno=%d child=%ld getpgid=%ld fg=%ld\n",
                saved, (long)child, (long)getpgid(child), (long)tcgetpgrp(0));
            kill(child, SIGKILL); waitpid(child, &status, 0);
            return 1;
        }
        close(gate[0]); close(gate[1]);
        do { got = waitpid(child, &status, WUNTRACED); } while (got < 0 && errno == EINTR);
        assert(got == child && WIFSTOPPED(status) && WSTOPSIG(status) == SIGTSTP);
        assert(kill(-child, SIGCONT) == 0); /* bg */
        assert(tcsetpgrp(0, shell) == 0);
        assert(tcsetpgrp(0, child) == 0); /* fg */
        assert(write(1, "foreground\n", 11) == 11);
        if (argc > 3) {
            struct timespec delay = {0, (i % 8) * atol(argv[3]) * 1000};
            nanosleep(&delay, NULL); /* diagnostic scheduling window only */
        }
        if (extra_continue && kill(-child, SIGCONT) < 0)
            assert(errno == EPERM || errno == ESRCH); /* confirmed by wait below */
        assert(waitpid(child, &status, 0) == child);
        assert(WIFSIGNALED(status) && WTERMSIG(status) == SIGINT);
        assert(tcsetpgrp(0, shell) == 0);
        assert(write(1, "interrupted\n", 12) == 12);
    }
    return 0;
}
