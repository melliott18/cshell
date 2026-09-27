/* CSH-058 U-026: controlled EPERM interposition, never arbitrary targets. */
#include "cshell/jobs.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int calls;
static pid_t denied;
static volatile sig_atomic_t delivered;
static void caught(int n) { delivered = n; }
int csh_permission_kill(pid_t pid, int sig)
{
    ++calls;
    assert(sig == SIGUSR1);
    if (pid == denied) { errno = EPERM; return -1; }
    assert(pid == getpid());
    return kill(pid, sig);
}
int main(int argc, char **argv)
{
    struct csh_invocation inv = {0};
    struct csh_state *state;
    struct csh_jobs *jobs;
    struct csh_command command = {0};
    struct sigaction a = {0};
    char own[32];
    char *args[] = {"kill", "-s", "USR1", "--", NULL, own};
    assert(argc == 2);
    denied = (pid_t)strtol(argv[1], NULL, 10);
    assert(denied == 123456789 || denied == -123456789 || denied == 0);
    assert(denied != getpid());
    inv.arg0 = "kill-permission";
    assert(csh_state_create(&state, &inv, NULL) == CSH_STATE_OK);
    assert(csh_jobs_create(&jobs, state, -1) == 0);
    a.sa_handler = caught;
    sigemptyset(&a.sa_mask);
    assert(sigaction(SIGUSR1, &a, NULL) == 0);
    snprintf(own, sizeof(own), "%ld", (long)getpid());
    args[4] = argv[1];
    command.argc = 6;
    command.argv = args;
    assert(csh_jobs_builtin(jobs, &command) == 1);
    assert(calls == 2 && delivered == SIGUSR1);
    puts("EPERM; continued; delivered");
    csh_jobs_destroy(jobs);
    csh_state_destroy(state);
    return 0;
}
