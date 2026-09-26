#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc == 3 && !strcmp(argv[1], "env")) {
        const char *value = getenv(argv[2]);
        return value && printf("%s\n", value) >= 0 ? 0 : 1;
    }
    if (argc == 2 && !strcmp(argv[1], "file-limit")) {
        struct rlimit limit;
        if (getrlimit(RLIMIT_FSIZE, &limit)) return 1;
        return printf("%llu\n", (unsigned long long)limit.rlim_cur) < 0;
    }
    if (argc == 2 && !strcmp(argv[1], "signal-child")) {
        for (;;) pause();
    }
    if (argc >= 3 && !strcmp(argv[1], "closed-stdout")) {
        close(STDOUT_FILENO);
        execvp(argv[2], argv + 2);
        perror("execvp");
        return 127;
    }
    if (argc >= 3 && !strcmp(argv[1], "interrupt")) {
        int ready[2], status;
        pid_t child, waited;
        char failed;
        ssize_t count;
        if (pipe(ready) || fcntl(ready[1], F_SETFD, FD_CLOEXEC)) return 2;
        child = fork();
        if (child < 0) return 2;
        if (child == 0) {
            close(ready[0]);
            execvp(argv[2], argv + 2);
            (void)write(ready[1], "x", 1);
            _exit(127);
        }
        close(ready[1]);
        do { count = read(ready[0], &failed, 1); } while (count < 0 && errno == EINTR);
        close(ready[0]);
        /* EOF means exec closed the descriptor; signal only this owned child. */
        if (kill(child, SIGTERM) < 0) return 2;
        do { waited = waitpid(child, &status, 0); } while (waited < 0 && errno == EINTR);
        if (count != 0 || waited != child) return 2;
        return WIFSIGNALED(status) ? 128 + WTERMSIG(status) : 2;
    }
    return 2;
}
