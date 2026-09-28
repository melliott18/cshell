#define _GNU_SOURCE
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
#include <grp.h>

/* A rejected exec is a kernel boundary, not a utility failure or maximum.
 * Cap allocation independently of the queried system limit. No child is
 * needed: if exec unexpectedly succeeds, the expected E2BIG marker is absent. */
static int exec_size(const char *path, int single)
{
    long ceiling = sysconf(_SC_ARG_MAX);
    size_t bytes, count, index;
    char *operand, **args;
    char *env[] = {"LC_ALL=C", NULL};
    FILE *record;
    int saved;
    if (ceiling < 1 || ceiling > 16 * 1024 * 1024) return 2;
    bytes = single ? (size_t)ceiling + 65536 : 1024;
    count = single ? 1 : (size_t)ceiling / bytes + 65;
    operand = malloc(bytes + 1);
    args = calloc(count + 2, sizeof(*args));
    if (!operand || !args) { free(operand); free(args); return 2; }
    memset(operand, 'x', bytes);
    operand[bytes] = '\0';
    args[0] = (char *)path;
    for (index = 1; index <= count; index++) args[index] = operand;
    record = fopen("exec-boundary.json", "w");
    if (!record) { free(args); free(operand); return 2; }
    fprintf(record, "{\"ARG_MAX\":%ld,\"operand_bytes\":%zu,\"operand_count\":%zu,"
            "\"operand_string_bytes_with_nuls\":%zu,\"environment_bytes_with_nuls\":9}\n",
            ceiling, bytes, count, (bytes + 1) * count);
    if (fclose(record)) { free(args); free(operand); return 2; }
    execve(path, args, env);
    saved = errno;
    free(args);
    free(operand);
    if (saved != E2BIG) { errno = saved; perror("exec-size"); return 2; }
    puts("E2BIG");
    return 0;
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "acl-executed")) {
        puts("executed");
        return 0;
    }
    if (argc == 3 && !strcmp(argv[1], "acl-write")) {
        int fd = open(argv[2], O_WRONLY | O_APPEND);
        if (fd < 0) { perror("acl-write"); return 1; }
        if (write(fd, "written\n", 8) != 8) { close(fd); return 2; }
        return close(fd) ? 2 : 0;
    }
#ifdef __linux__
    if (argc == 3 && !strcmp(argv[1], "acl-probe")) {
        int legacy, kernel, fd;
        legacy = euidaccess(argv[2], R_OK);
        kernel = faccessat(AT_FDCWD, argv[2], R_OK, AT_EACCESS);
        fd = open(argv[2], O_RDONLY);
        printf("euidaccess=%d faccessat=%d open=%d\n", legacy, kernel, fd < 0 ? -1 : 0);
        if (fd >= 0) close(fd);
        return 0;
    }
#endif
    if (argc == 4 && !strcmp(argv[1], "exec-size") &&
        (!strcmp(argv[2], "single") || !strcmp(argv[2], "aggregate")))
        return exec_size(argv[3], !strcmp(argv[2], "single"));
    if (argc >= 3 && !strcmp(argv[1], "small-file")) {
        struct rlimit limit = {1024, 1024};
        if (setrlimit(RLIMIT_FSIZE, &limit) || signal(SIGXFSZ, SIG_IGN) == SIG_ERR)
            return 2;
        execvp(argv[2], argv + 2);
        perror("small-file exec");
        return 2;
    }
#ifdef __linux__
    if (argc >= 5 && (!strcmp(argv[1], "identity") || !strcmp(argv[1], "identity-group"))) {
        /* Explicit Linux-root fixtures: replace inherited groups with the
         * requested set and drop saved root credentials before utility exec. */
        uid_t real, effective;
        gid_t group = 10003, observed_group;
        int groups = !strcmp(argv[1], "identity-group");
        if (geteuid() != 0 ||
            (strcmp(argv[2], "10001") && strcmp(argv[2], "10002")) ||
            (strcmp(argv[3], "10001") && strcmp(argv[3], "10002"))) return 2;
        real = (uid_t)strtoul(argv[2], NULL, 10);
        effective = (uid_t)strtoul(argv[3], NULL, 10);
        if (setgroups(groups, groups ? &group : NULL) || setresgid(real, effective, effective) ||
            setresuid(real, effective, effective)) return 2;
        if (getuid() != real || geteuid() != effective || getgid() != real ||
            getegid() != effective || getgroups(0, NULL) != groups ||
            (groups && (getgroups(1, &observed_group) != 1 || observed_group != group))) return 2;
        printf("uid=%lu euid=%lu gid=%lu egid=%lu groups=%s\n",
               (unsigned long)getuid(), (unsigned long)geteuid(),
               (unsigned long)getgid(), (unsigned long)getegid(), groups ? "1:10003" : "0");
        if (fflush(stdout)) return 2;
        execvp(argv[4], argv + 4);
        perror("identity exec");
        return 2;
    }
#endif
    if (argc == 2 && !strcmp(argv[1], "limits")) {
        const int kinds[] = {RLIMIT_CORE, RLIMIT_CPU, RLIMIT_FSIZE, RLIMIT_NOFILE};
        const char *names[] = {"core_bytes", "cpu_seconds", "file_size_bytes", "open_files"};
        size_t index;
        if (printf("{") < 0) return 1;
        for (index = 0; index < sizeof(kinds) / sizeof(kinds[0]); index++) {
            struct rlimit limit;
            if (getrlimit(kinds[index], &limit)) return 1;
            if (printf("%s\"%s\": [%lld, %lld]", index ? "," : "", names[index],
                       limit.rlim_cur == RLIM_INFINITY ? -1LL : (long long)limit.rlim_cur,
                       limit.rlim_max == RLIM_INFINITY ? -1LL : (long long)limit.rlim_max) < 0) return 1;
        }
        return printf(",\"ARG_MAX\": %ld, \"OPEN_MAX\": %ld}\n",
                      sysconf(_SC_ARG_MAX), sysconf(_SC_OPEN_MAX)) < 0;
    }
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
            do { count = write(ready[1], "x", 1); } while (count < 0 && errno == EINTR);
            if (count != 1) _exit(126);
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
