/* Independent syscall/argument oracles for CSH-075. Never installed in PATH. */
#define _DEFAULT_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

static double seconds(struct timespec value)
{
    return (double)value.tv_sec + (double)value.tv_nsec / 1000000000.0;
}

static int burn_cpu(void)
{
    struct timespec start, now;
    volatile unsigned long value = 1;
    unsigned long j;
    if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &start)) return 2;
    do {
        for (j = 0; j < 10000; ++j) value = value * 1664525UL + 1013904223UL;
        if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &now)) return 2;
    } while (seconds(now) - seconds(start) < 0.12);
    return 0;
}

static void exit_on_term(int sig)
{
    (void)sig;
    _exit(143);
}

int main(int argc, char **argv)
{
    int i;
    if (argc < 2) return 2;
    if (!strcmp(argv[1], "measure") && argc == 3) {
        struct timespec start, end, delay = {0, 150000000};
        struct rusage own, children;
        FILE *record;
        int status = 0;
        if (clock_gettime(CLOCK_MONOTONIC, &start)) return 2;
        if (!strcmp(argv[2], "wall")) {
            while (nanosleep(&delay, &delay)) if (errno != EINTR) return 2;
        } else if (!strcmp(argv[2], "cpu")) {
            if (burn_cpu()) return 2;
        } else if (!strcmp(argv[2], "child")) {
            pid_t child = fork();
            if (child < 0) return 2;
            if (!child) _exit(burn_cpu());
            while (waitpid(child, &status, 0) < 0) if (errno != EINTR) return 2;
            if (!WIFEXITED(status) || WEXITSTATUS(status)) return 2;
        } else return 2;
        if (clock_gettime(CLOCK_MONOTONIC, &end) || getrusage(RUSAGE_SELF, &own) ||
            getrusage(RUSAGE_CHILDREN, &children)) return 2;
        record = fopen("measurement.json", "w");
        if (!record) return 2;
        fprintf(record, "{\"real\":%.9f,\"user\":%.9f,\"sys\":%.9f}\n",
                seconds(end) - seconds(start),
                (double)own.ru_utime.tv_sec + (double)children.ru_utime.tv_sec +
                ((double)own.ru_utime.tv_usec + (double)children.ru_utime.tv_usec) / 1000000.0,
                (double)own.ru_stime.tv_sec + (double)children.ru_stime.tv_sec +
                ((double)own.ru_stime.tv_usec + (double)children.ru_stime.tv_usec) / 1000000.0);
        return fclose(record) ? 2 : 0;
    }
    if (!strcmp(argv[1], "copy-input")) {
        char data[1024];
        ssize_t count;
        while ((count = read(STDIN_FILENO, data, sizeof data)) != 0) {
            ssize_t offset = 0;
            if (count < 0) { if (errno == EINTR) continue; return 2; }
            while (offset < count) {
                ssize_t written = write(STDOUT_FILENO, data + offset, (size_t)(count - offset));
                if (written < 0) { if (errno == EINTR) continue; return 2; }
                offset += written;
            }
        }
        return 0;
    }
    if (!strcmp(argv[1], "exec-error") && argc == 3) {
        char *arguments[] = {argv[2], NULL};
        char *environment[] = {"LC_ALL=C", NULL};
        execve(argv[2], arguments, environment);
        printf("%d\n", errno);
        return 0;
    }
    if (!strcmp(argv[1], "fd-exhaustion")) {
        int descriptors[64], count = 0, error, control;
        struct rlimit bound = {32, 32}, measured;
        if (setrlimit(RLIMIT_NOFILE, &bound) || getrlimit(RLIMIT_NOFILE, &measured)) return 2;
        while (count < 64) {
            int descriptor = open("/dev/null", O_RDONLY);
            if (descriptor < 0) break;
            descriptors[count++] = descriptor;
        }
        error = errno;
        while (count > 0) close(descriptors[--count]);
        control = open("/dev/null", O_RDONLY);
        if (control < 0) return 2;
        close(control);
        printf("{\"errno\":%d,\"soft\":%lu,\"restored\":true}\n",
               error, (unsigned long)measured.rlim_cur);
        return error == EMFILE ? 0 : 1;
    }
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
    if (!strcmp(argv[1], "raise-term")) {
        raise(SIGTERM);
        return 2;
    }
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
    if (!strcmp(argv[1], "nice-ceiling")) {
        int value;
        if (setpriority(PRIO_PROCESS, 0, INT_MAX)) return 2;
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
        !strcmp(argv[1], "timed-ignore-term") || !strcmp(argv[1], "timed-exit-term")) {
        if (!strcmp(argv[1], "timed-ignore-term") && signal(SIGTERM, SIG_IGN) == SIG_ERR) return 2;
        if (!strcmp(argv[1], "timed-exit-term") && signal(SIGTERM, exit_on_term) == SIG_ERR) return 2;
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
