/* CSH-050 U-026/JOB-003/U-032: partial kill failures must not poison later
 * successful deliveries. Only EPERM is interposed; stopped children are real. */
#include "cshell/jobs.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int trace_fd = -1;
static void trace(const char *phase) {
    int saved = errno; sigset_t mask; sigprocmask(SIG_SETMASK, NULL, &mask);
    dprintf(trace_fd, "%ld %s mask CHLD=%d INT=%d\n", (long)getpid(), phase, sigismember(&mask,SIGCHLD), sigismember(&mask,SIGINT));
    errno = saved;
}
static pid_t children[2], refused;
static int delivery_signal, calls, grouped;

int csh_permission_kill(pid_t pid, int sig)
{
    assert(sig == delivery_signal);
    assert(grouped ? pid == -children[0] :
        (pid == children[0] || pid == children[1]));
    ++calls;
    if (pid == refused) { errno = EPERM; return -1; }
    return kill(pid, sig);
}

static void transfer(int fd, int writing, size_t count)
{
    char bytes[2] = {'x', 'x'};
    size_t offset = 0;
    while (offset < count) {
        ssize_t n = writing ? write(fd, bytes + offset, count - offset) :
            read(fd, bytes + offset, count - offset);
        if (n < 0 && errno == EINTR) continue;
        assert(n > 0);
        offset += (size_t)n;
    }
}

int main(int argc, char **argv)
{
    struct csh_invocation inv = {0};
    struct csh_state *state;
    struct csh_jobs *jobs;
    struct csh_job *job;
    struct csh_command command = {0};
    int gate[2], release[2], status;
    assert(argc == 4);
    grouped = !strcmp(argv[1], "grouped");
    delivery_signal = !strcmp(argv[2], "CONT") ? SIGCONT : SIGKILL;
    trace_fd = open(getenv("CSH_TRACE"), O_WRONLY|O_CREAT|O_APPEND, 0600);
    assert(trace_fd>=0); trace("start"); alarm(4);
    inv.arg0 = "kill-job-state";
    assert(csh_state_create(&state, &inv, NULL) == CSH_STATE_OK);
    assert(csh_jobs_create(&jobs, state, -1) == 0);
    job = csh_jobs_add(jobs, 2, "partial-delivery", 1, 0);
    assert(job && job->id == 1 && pipe(gate) == 0 && pipe(release) == 0);
    job->grouped = grouped;
    for (int i = 0; i < 2; ++i) {
        children[i] = fork();
        assert(children[i] >= 0);
        if (!children[i]) {
            close(gate[1]); close(release[1]);
            trace("child gate enter"); transfer(gate[0], 0, 1); trace("child gate exit");
            trace("child STOP enter"); assert(raise(SIGSTOP) == 0); trace("child STOP exit");
            trace("child release enter"); transfer(release[0], 0, 1); trace("child release exit");
            _exit(23 + i);
        }
        job->processes[i].pid = children[i];
        if (grouped) assert(setpgid(children[i], children[0]) == 0);
    }
    job->pgid = children[0];
    trace("parent gate"); transfer(gate[1], 1, 2);
    close(gate[0]); close(gate[1]);
    for (int i = 0; i < 2; ++i) {
        siginfo_t event;
        int rc;
        trace(i ? "waitid 1 enter" : "waitid 0 enter");
        do { rc = waitid(P_PID, (id_t)children[i], &event, WSTOPPED | WNOWAIT); }
        while (rc < 0 && errno == EINTR);
        trace(i ? "waitid 1 exit" : "waitid 0 exit");
        assert(rc == 0 && event.si_code == CLD_STOPPED && event.si_status == SIGSTOP);
    }
    trace("poll enter"); assert(csh_jobs_poll(jobs) == 0); trace("poll exit");
    assert(job->processes[0].stopped && job->processes[1].stopped);
    char *args[] = {"kill", "-s", argv[2], "%1", NULL, NULL};
    command.argc = 4;
    if (!strcmp(argv[3], "before")) {
        args[3] = "%missing"; args[4] = "%1"; command.argc = 5;
    } else if (!strcmp(argv[3], "after")) {
        args[4] = "%missing"; command.argc = 5;
    } else {
        assert(!strcmp(argv[3], "first") || (!grouped && !strcmp(argv[3], "last")));
        refused = grouped ? -children[0] : children[!strcmp(argv[3], "last")];
    }
    command.argv = args;
    trace("kill enter"); assert(csh_jobs_builtin(jobs, &command, NULL) == 1); trace("kill exit");
    assert(calls == (grouped ? 1 : 2));
    for (int i = 0; i < 2; ++i) {
        int denied = refused == (grouped ? -children[0] : children[i]);
        /* No poll occurs after delivery: this checks the manager's immediate
         * state, independently of when the kernel publishes WCONTINUED. */
        assert(job->processes[i].stopped == denied);
        if (denied) assert(kill(children[i], SIGKILL) == 0);
    }
    trace("parent release enter"); if (delivery_signal == SIGCONT) transfer(release[1], 1, 2); trace("parent release exit");
    close(release[0]); close(release[1]);
    char *wait_args[] = {"wait", "%1", NULL};
    command.argc = 2; command.argv = wait_args;
    int last_denied = refused == (grouped ? -children[0] : children[1]);
    /* The explicit cleanup KILL must also clear a retained stop before wait. */
    for (int i = 0; i < 2; ++i)
        if (refused == (grouped ? -children[0] : children[i]))
            job->processes[i].stopped = 0;
    trace("wait enter");
    assert(csh_jobs_builtin(jobs, &command, NULL) ==
        (delivery_signal == SIGKILL || last_denied ? 128 + SIGKILL : 24));
    trace("wait exit");
    assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
    csh_jobs_destroy(jobs);
    csh_state_destroy(state);
    puts("partial delivery: state and final wait status passed");
    return 0;
}
