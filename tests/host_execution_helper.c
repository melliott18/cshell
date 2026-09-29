/* Independent syscall/argument oracles for CSH-075. Never installed in PATH. */
#define _DEFAULT_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

int main(int argc, char **argv)
{
    int i;
    if (argc < 2) return 2;
#ifdef __linux__
    if (!strcmp(argv[1], "fork-limit")) {
        struct rlimit bound = {0, 0};
        pid_t child;
        int error, status;
        if (setgroups(0, NULL) || setgid(60003) || setuid(60003) ||
            setrlimit(RLIMIT_NPROC, &bound)) return 2;
        child = fork();
        error = errno;
        if (!child) _exit(0);
        if (child > 0) {
            while (waitpid(child, &status, 0) < 0) if (errno != EINTR) return 2;
        }
        printf("{\"uid\":%ld,\"euid\":%ld,\"fork_rejected\":%s,\"errno\":%d}\n",
               (long)getuid(), (long)geteuid(), child < 0 ? "true" : "false", child < 0 ? error : 0);
        return child < 0 && error == EAGAIN ? 0 : 1;
    }
    if (!strcmp(argv[1], "drop-exec") && argc >= 4) {
        uid_t uid = (uid_t)strtoul(argv[2], NULL, 10);
        FILE *file = fopen("caller.json", "w");
        if (!file) return 2;
        if (setgroups(0, NULL) || setgid(uid) || setuid(uid)) return 2;
        fprintf(file, "{\"uid\":%ld,\"euid\":%ld,\"gid\":%ld,\"egid\":%ld,\"groups\":%d}\n",
                (long)getuid(), (long)geteuid(), (long)getgid(), (long)getegid(), getgroups(0, NULL));
        if (fclose(file)) return 2;
        execv(argv[3], argv + 3);
        perror("drop-exec");
        return 2;
    }
#endif
    if (!strcmp(argv[1], "exit") && argc == 3) return atoi(argv[2]);
    if (!strcmp(argv[1], "args")) {
        for (i = 2; i < argc; ++i) printf("%zu:%s\n", strlen(argv[i]), argv[i]);
        return 0;
    }
    if (!strcmp(argv[1], "getenv") && argc == 3) {
        const char *value = getenv(argv[2]);
        puts(value ? value : "missing");
        return 0;
    }
    if (!strcmp(argv[1], "env")) {
        for (i = 0; environ[i]; ++i) puts(environ[i]);
        return 0;
    }
    if (!strcmp(argv[1], "nice")) {
        int value;
        errno = 0;
        value = getpriority(PRIO_PROCESS, 0);
        if (errno) return 2;
        printf("%d\n", value);
        return 0;
    }
    if (!strcmp(argv[1], "hup")) {
        struct sigaction action;
        if (sigaction(SIGHUP, NULL, &action)) return 2;
        puts(action.sa_handler == SIG_IGN ? "ignored" : "not-ignored");
        return 0;
    }
    if (!strcmp(argv[1], "park") || !strcmp(argv[1], "timed-park") ||
        !strcmp(argv[1], "timed-ignore-term")) {
        if (!strcmp(argv[1], "timed-ignore-term") && signal(SIGTERM, SIG_IGN) == SIG_ERR) return 2;
        if (strncmp(argv[1], "timed-", 6) == 0) {
            FILE *file = fopen("child.pid", "w");
            if (!file) return 2;
            fprintf(file, "%ld\n", (long)getpid());
            if (fclose(file)) return 2;
        }
        puts("ready");
        fflush(stdout);
        for (;;) pause();
    }
    if (!strcmp(argv[1], "loader") && argc == 3) {
        /* CLOEXEC pipe independently separates execve rejection from image entry.
           Only this disposable child loses descriptor access. */
        int pipefd[2], status, error = 0;
        ssize_t count;
        pid_t child;
        if (pipe(pipefd) || fcntl(pipefd[1], F_SETFD, FD_CLOEXEC)) return 2;
        child = fork();
        if (child < 0) return 2;
        if (!child) {
            struct rlimit bound = {0, 0};
            char *arguments[] = {argv[2], NULL};
            char *environment[] = {"LC_ALL=C", NULL};
            close(pipefd[0]);
            if (setrlimit(RLIMIT_NOFILE, &bound)) _exit(120);
            execve(argv[2], arguments, environment);
            error = errno;
            if (write(pipefd[1], &error, sizeof error) != sizeof error) _exit(121);
            _exit(122);
        }
        close(pipefd[1]);
        do count = read(pipefd[0], &error, sizeof error); while (count < 0 && errno == EINTR);
        close(pipefd[0]);
        while (waitpid(child, &status, 0) < 0) if (errno != EINTR) return 2;
        if (count != 0 && count != sizeof error) return 2;
        printf("{\"exec_errno\":%d,\"exit\":%d,\"signal\":%d}\n", error,
               WIFEXITED(status) ? WEXITSTATUS(status) : -1,
               WIFSIGNALED(status) ? WTERMSIG(status) : 0);
        return 0;
    }
    return 2;
}
