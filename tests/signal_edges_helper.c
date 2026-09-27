/* CSH-058: actual dispositions/delivery, isolated groups and API resets. */
#include "cshell/jobs.h"
#include "cshell/traps.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static volatile sig_atomic_t received;
static void caught(int n) { received = n; }
static void disposition(int n, void (*handler)(int))
{
    struct sigaction a = {0};
    a.sa_handler = handler;
    sigemptyset(&a.sa_mask);
    assert(sigaction(n, &a, NULL) == 0);
}
static int await(pid_t pid, int flags)
{
    int status;
    pid_t result;
    do { result = waitpid(pid, &status, flags); } while (result < 0 && errno == EINTR);
    assert(result == pid);
    return status;
}
static void trap(struct csh_traps *t, int n, char *action)
{
    char number[24];
    char *args[] = {"trap", action, number};
    snprintf(number, sizeof(number), "%d", n);
    assert(csh_traps_builtin(t, 3, args) == 0);
}
static void check(int n, int expected)
{
    struct sigaction a;
    int actual;
    assert(sigaction(n, NULL, &a) == 0);
    actual = a.sa_handler == SIG_DFL ? 0 : a.sa_handler == SIG_IGN ? 1 : 2;
    if (actual != expected) fprintf(stderr, "signal %d: disposition %d expected %d\n", n, actual, expected);
    assert(actual == expected);
}
static void api(int n, int interactive, int inherited, int action, int shape)
{
    struct csh_invocation inv = {0};
    struct csh_state *state;
    struct csh_jobs *jobs;
    struct csh_traps *traps;
    int locked = inherited && !interactive;
    int explicit_ignore = !locked && (action == 2 || action == 3);
    int explicit_catch = !locked && action == 1;
    int expected, status;
    char *text = NULL;
    pid_t child;
    disposition(n, inherited ? SIG_IGN : SIG_DFL);
    inv.arg0 = "signal-edges";
    inv.options = interactive ? CSH_OPT_INTERACTIVE : 0;
    assert(csh_state_create(&state, &inv, NULL) == CSH_STATE_OK);
    assert(csh_traps_create(&traps, interactive) == 0);
    assert(csh_jobs_create(&jobs, state, -1) == 0);
    if (action == 1 || action == 3) trap(traps, n, ":");
    if (action >= 2) trap(traps, n, "");
    if (action == 4) trap(traps, n, "-");
    expected = explicit_catch ? 2 : explicit_ignore ? (n == SIGCHLD ? 2 : 1) :
        n == SIGCHLD ? 2 : inherited ? 1 : !interactive ? 0 :
        (n == SIGINT || n == SIGHUP) ? 2 : 1;
    check(n, expected);
    if (explicit_catch) {
        assert(raise(n) == 0);
        assert(csh_traps_take(traps, &text) == n);
        assert(text && !strcmp(text, ":"));
        free(text);
    } else if (expected == 1 || explicit_ignore) {
        assert(raise(n) == 0);
        assert(csh_traps_first_pending() == 0);
    }
    child = fork();
    assert(child >= 0);
    if (!child) {
        int asynchronous = shape == 1;
        int forced = asynchronous && (n == SIGINT || n == SIGQUIT);
        csh_jobs_after_fork(jobs, asynchronous);
        csh_traps_after_fork(traps, asynchronous, shape == 2);
        expected = forced ? 1 : explicit_ignore ? (n == SIGCHLD ? 2 : 1) :
            explicit_catch ? 0 : inherited ? (n == SIGCHLD ? 2 : 1) : 0;
        check(n, expected);
        assert(csh_traps_first_pending() == 0);
        /* Reset an inherited ignored action in every fork shape. The previous
         * action must be the child's baseline, never a parent-only handler. */
        trap(traps, n, "-");
        expected = forced ? 1 : inherited && !explicit_catch ? (n == SIGCHLD ? 2 : 1) :
            explicit_ignore && n == SIGCHLD ? 2 : 0;
        check(n, expected);
        trap(traps, n, "");
        trap(traps, n, "-");
        check(n, expected);
        if (n == SIGCHLD) {
            pid_t grandchild = fork();
            assert(grandchild >= 0);
            if (!grandchild) _exit(23);
            status = await(grandchild, 0);
            assert(WIFEXITED(status) && WEXITSTATUS(status) == 23);
        }
        _exit(0);
    }
    status = await(child, 0);
    assert(WIFEXITED(status) && WEXITSTATUS(status) == 0);
    csh_jobs_destroy(jobs);
    csh_traps_destroy(traps);
    csh_state_destroy(state);
}
static void probe(int n)
{
    struct sigaction a;
    pid_t child;
    int status;
    assert(sigaction(n, NULL, &a) == 0);
    printf("%s:", a.sa_handler == SIG_IGN ? "ignored" : a.sa_handler == SIG_DFL ? "default" : "caught");
    fflush(stdout);
    /* Parent stays in this session so default terminal-stop delivery in the
     * child's new group is not suppressed by the orphaned-group rule. */
    disposition(SIGCHLD, SIG_DFL);
    child = fork();
    assert(child >= 0);
    if (!child) {
        assert(setpgid(0, 0) == 0);
        assert(sigaction(n, &a, NULL) == 0);
        assert(raise(n) == 0);
        _exit(0);
    }
    status = await(child, WUNTRACED);
    if (WIFSTOPPED(status)) {
        assert(WSTOPSIG(status) == n);
        assert(kill(child, SIGCONT) == 0);
        assert(await(child, 0) == 0);
        puts("stopped");
    } else if (WIFSIGNALED(status)) {
        assert(WTERMSIG(status) == n);
        puts("terminated");
    } else {
        assert(WIFEXITED(status) && WEXITSTATUS(status) == 0);
        puts("survived");
    }
}
static void group(const char *binary, int negative)
{
    int ready[2], ack[2], i, status;
    pid_t members[2], shell;
    char bytes[2], script[160];
    sigset_t blocked, old;
    assert(getpgrp() == getpid()); /* bounded_run owns this new session */
    disposition(SIGUSR1, SIG_IGN);
    assert(pipe(ready) == 0 && pipe(ack) == 0);
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGUSR1);
    assert(sigprocmask(SIG_BLOCK, &blocked, &old) == 0);
    for (i = 0; i < 2; ++i) {
        members[i] = fork();
        assert(members[i] >= 0);
        if (!members[i]) {
            char id = (char)('A' + i);
            disposition(SIGUSR1, caught);
            assert(write(ready[1], &id, 1) == 1);
            while (!received) sigsuspend(&old);
            assert(received == SIGUSR1);
            assert(write(ack[1], &id, 1) == 1);
            _exit(0);
        }
    }
    for (i = 0; i < 2; ++i) assert(read(ready[0], bytes + i, 1) == 1);
    assert(bytes[0] != bytes[1]);
    shell = fork();
    assert(shell >= 0);
    if (!shell) {
        assert(sigprocmask(SIG_SETMASK, &old, NULL) == 0);
        snprintf(script, sizeof(script), "kill -s USR1 -- %ld", negative ? -(long)getpgrp() : 0L);
        execl(binary, binary, "-c", script, (char *)NULL);
        _exit(99);
    }
    status = await(shell, 0);
    assert(status == 0);
    for (i = 0; i < 2; ++i) assert(read(ack[0], bytes + i, 1) == 1);
    assert((bytes[0] == 'A' && bytes[1] == 'B') || (bytes[0] == 'B' && bytes[1] == 'A'));
    for (i = 0; i < 2; ++i) assert(await(members[i], 0) == 0);
    puts("delivered:A,B");
}
int main(int argc, char **argv)
{
    assert(argc >= 2);
    alarm(4);
    if (!strcmp(argv[1], "api")) {
        assert(argc == 7);
        api(atoi(argv[2]), atoi(argv[3]), atoi(argv[4]), atoi(argv[5]), atoi(argv[6]));
    } else if (!strcmp(argv[1], "launch")) {
        assert(argc == 7);
        disposition(atoi(argv[2]), atoi(argv[3]) ? SIG_IGN : SIG_DFL);
        execl(argv[4], argv[4], argv[5], argv[6], (char *)NULL);
        return 99;
    } else if (!strcmp(argv[1], "probe")) {
        assert(argc == 3);
        probe(atoi(argv[2]));
    } else if (!strcmp(argv[1], "group")) {
        assert(argc == 4);
        group(argv[2], atoi(argv[3]));
    } else if (!strcmp(argv[1], "conditions")) {
        struct sigaction a;
        int n;
        /* Query all host signal numbers, including beyond the runtime table. */
        for (n = 1; n < 1024; ++n)
            if (n != SIGKILL && n != SIGSTOP && sigaction(n, NULL, &a) == 0)
                printf("%d\n", n);
    } else return 98;
    return 0;
}
