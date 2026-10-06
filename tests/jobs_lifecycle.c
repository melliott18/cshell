/* CSH-057: EXEC-009, JOB-003, U-032. Production jobs.c with only its
 * sysconf call interposed: exhaust a known, bounded CHILD_MAX with real,
 * sequential children, independent of host limits of millions of processes. */
#include "cshell/jobs.h"
#include "cshell/parser.h"
#include "retention_trace.h"
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
#include <time.h>
#include <unistd.h>

/* Preserve assertion diagnostics while the test captures stdout/stderr. */
static int diagnostic_fd = STDERR_FILENO;
#undef assert
#define assert(test) do { if (!(test)) { \
    dprintf(diagnostic_fd, "lifecycle assertion at line %d: %s (errno=%d)\n", \
        __LINE__, #test, errno); abort(); } } while (0)

static long capacity = 32;
static int queries;
static void trace(const char *event, pid_t child)
{
    int saved = errno;
    csh_retention_trace_event(event, child);
    assert(errno == saved);
}
long csh_lifecycle_sysconf(int name)
{
    assert(name == _SC_CHILD_MAX);
    ++queries;
    return capacity;
}
static struct csh_execution run(struct csh_execution_context *ctx, const char *s)
{
    struct csh_input *in = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *tree = NULL;
    struct csh_error error;
    struct csh_execution result;
    assert(csh_input_from_string(&in, s, "lifecycle", &error) == 0);
    assert(csh_parser_create(&parser, in, &error) == 0);
    assert(csh_parser_next(parser, &tree, &error) == CSH_PARSE_TREE);
    assert(csh_execute_context_ast(ctx, tree, &result, &error) == 0);
    csh_ast_destroy(tree); csh_parser_destroy(parser); csh_input_destroy(in);
    return result;
}
static struct csh_execution traced_run(struct csh_execution_context *ctx,
    const char *source, const char *begin, const char *end, pid_t child)
{
    struct csh_execution result;
    trace(begin, child);
    result = run(ctx, source);
    trace(end, child);
    return result;
}
static int traced_reap(struct csh_jobs *jobs, pid_t child)
{
    int rc;
    trace("reap+", child);
    rc = csh_jobs_reap(jobs, 1);
    trace("reap-", child);
    return rc;
}
static void destroy(struct csh_execution_context *ctx)
{
    /* Context destruction clears borrowed pointers; retain the state owner. */
    struct csh_state *state = ctx->state;
    trace("cleanup+", 0);
    csh_execution_context_destroy(ctx);
    csh_state_destroy(state);
    trace("cleanup-", 0);
}
static void retention(void)
{
    for (int fallback = 0; fallback < 2; ++fallback) {
        struct csh_invocation inv = {0};
        struct csh_execution_context ctx = {0};
        struct csh_state_info info;
        pid_t ids[257];
        char script[256];
        int n = fallback ? 256 : 32;
        capacity = fallback ? -1 : n;
        inv.arg0 = "retention";
        assert(csh_state_create(&ctx.state, &inv, NULL) == CSH_STATE_OK);
        assert(csh_jobs_create(&ctx.jobs, ctx.state, -1) == 0);
        assert(queries == fallback + 1);
        for (int round = 0; round < 2; ++round) {
            csh_retention_trace_context(n, round + 1, 0);
            trace("round+", 0);
            printf("retention capacity=%d round=%d completed=0\n", n, round + 1);
            assert(fflush(stdout) == 0);
            /* Alternate saved $! and IDs read by the observer only. cshell
             * creates optional unmonitored jobs, so unsaved IDs also stay
             * known until reporting, wait, or capacity permits eviction. */
            for (int i = 0; i < n; ++i) {
                csh_retention_trace_context(n, round + 1, i + 1);
                alarm(5);
                snprintf(script, sizeof(script), "exit %d & %s\n", i % 100 + 1,
                    i % 2 ? ":" : "saved=$!");
                assert(traced_run(&ctx, script, "run+", "run-", 0).status == 0);
                csh_state_get_info(ctx.state, &info);
                ids[i] = info.background_pid;
                assert(traced_reap(ctx.jobs, ids[i]) == 0);
                /* Unbuffered checkpoints localize an outer-runner timeout;
                 * they do not reset or extend either deadline. */
                if ((i + 1) % 64 == 0 || i + 1 == n) {
                    printf("retention capacity=%d round=%d completed=%d\n", n, round + 1, i + 1);
                    assert(fflush(stdout) == 0);
                }
            }
            /* Foreground utility registration must not evict a known ID. */
            csh_retention_trace_context(n, round + 1, 0);
            assert(traced_run(&ctx, "/usr/bin/true\n", "fg+", "fg-", 0).status == 0);
            if (round) {
                csh_retention_trace_context(n, round + 1, n + 1);
                assert(traced_run(&ctx, "exit 117 & saved=$!\n", "overflow+", "overflow-", 0).status == 0);
                csh_state_get_info(ctx.state, &info); ids[n] = info.background_pid;
                assert(traced_reap(ctx.jobs, ids[n]) == 0);
                snprintf(script, sizeof(script), "wait %ld 2>/dev/null\n", (long)ids[0]);
                assert(traced_run(&ctx, script, "wait+", "wait-", ids[0]).status == 127); /* selected oldest eviction */
            }
            for (int i = round; i < n + round; ++i) {
                csh_retention_trace_context(n, round + 1, i + 1);
                snprintf(script, sizeof(script), "wait %ld\n", (long)ids[i]);
                assert(traced_run(&ctx, script, "wait+", "wait-", ids[i]).status == (i == n ? 117 : i % 100 + 1));
            }
            assert(traced_run(&ctx, "wait\n", "wait_all+", "wait_all-", 0).status == 0);
            trace("round-", 0);
        }
        destroy(&ctx);
    }
    puts("CHILD_MAX=32 and fallback=256: capacity, saved/unsaved IDs, foreground preservation, oldest eviction passed");
}
static void live_retention(void)
{
    struct csh_invocation inv = {0};
    struct csh_execution_context ctx = {0};
    struct csh_job *live[2];
    struct csh_state_info info;
    pid_t ids[33];
    char script[80];
    siginfo_t event;
    inv.arg0 = "live-retention"; capacity = 32;
    csh_retention_trace_context(32, 0, 0);
    trace("live+", 0);
    assert(csh_state_create(&ctx.state, &inv, NULL) == CSH_STATE_OK);
    assert(csh_jobs_create(&ctx.jobs, ctx.state, -1) == 0);
    for (int i = 0; i < 2; ++i) {
        csh_retention_trace_context(32, 0, i + 1);
        live[i] = csh_jobs_add(ctx.jobs, 1, "live", 1, 0); assert(live[i]);
        live[i]->processes[0].pid = csh_retention_fork(); assert(live[i]->processes[0].pid >= 0);
        if (!live[i]->processes[0].pid) {
            if (i) raise(SIGSTOP);
            for (;;) pause();
        }
        live[i]->pgid = live[i]->processes[0].pid;
    }
    trace("live_stop+", live[1]->pgid);
    while (waitid(P_PID, (id_t)live[1]->pgid, &event, WSTOPPED | WNOWAIT) < 0)
        assert(errno == EINTR);
    assert(csh_jobs_poll(ctx.jobs) == 0 && live[1]->processes[0].stopped);
    trace("live_stop-", live[1]->pgid);
    for (int i = 0; i < 33; ++i) {
        csh_retention_trace_context(32, 0, i + 1);
        alarm(5);
        assert(traced_run(&ctx, "exit 23 & saved=$!\n", "run+", "run-", 0).status == 0);
        csh_state_get_info(ctx.state, &info); ids[i] = info.background_pid;
        int observed;
        trace("reap+", ids[i]);
        do { observed = waitid(P_PID, (id_t)ids[i], &event, WEXITED | WNOWAIT); }
        while (observed < 0 && errno == EINTR);
        /* The executor polls between list entries: a fast child may already
         * be reaped into the registry before run returns. Its exact retained
         * result is still checked by the later numeric wait. */
        assert(observed == 0 || errno == ECHILD);
        assert(csh_jobs_poll(ctx.jobs) == 0);
        trace("reap-", ids[i]);
    }
    for (int i = 1; i < 33; ++i) {
        csh_retention_trace_context(32, 0, i + 1);
        snprintf(script, sizeof(script), "wait %ld\n", (long)ids[i]);
        assert(traced_run(&ctx, script, "wait+", "wait-", ids[i]).status == 23);
    }
    snprintf(script, sizeof(script), "wait %ld 2>/dev/null\n", (long)ids[0]);
    assert(traced_run(&ctx, script, "wait+", "wait-", ids[0]).status == 127);
    /* These borrowed records must survive eviction. Cancel reaps both. */
    assert(kill(live[0]->pgid, 0) == 0 && kill(live[1]->pgid, 0) == 0);
    assert(live[1]->processes[0].stopped);
    trace("cancel+", live[0]->pgid);
    csh_jobs_cancel(ctx.jobs, live[0]);
    trace("cancel-", 0);
    trace("cancel+", live[1]->pgid);
    csh_jobs_cancel(ctx.jobs, live[1]);
    trace("cancel-", 0);
    destroy(&ctx);
    trace("live-", 0);
}
static void formats(void)
{
    struct csh_invocation inv = {0};
    struct csh_execution_context ctx = {0};
    struct csh_job *job;
    int output[2], saved;
    char actual[512], expected[512], script[80];
    inv.arg0 = "formats";
    csh_retention_trace_context(0, 0, 0);
    trace("formats+", 0);
    assert(csh_state_create(&ctx.state, &inv, NULL) == CSH_STATE_OK);
    assert(csh_jobs_create(&ctx.jobs, ctx.state, -1) == 0);
    /* Real two-stage pipeline, held until all three formats are asserted. */
    job = csh_jobs_add(ctx.jobs, 2, "pipeline", 1, 0); assert(job);
    for (size_t i = 0; i < 2; ++i) {
        job->processes[i].pid = csh_retention_fork(); assert(job->processes[i].pid >= 0);
        if (!job->processes[i].pid) for (;;) pause();
    }
    job->pgid = job->processes[0].pid;
    for (int grouped = 0; grouped < 2; ++grouped) {
      job->grouped = grouped;
      pid_t displayed = job->processes[grouped ? 0 : 1].pid;
      pid_t additional = job->processes[grouped ? 1 : 0].pid;
      for (int mode = 0; mode < 3; ++mode) {
        assert(pipe(output) == 0); saved = dup(STDOUT_FILENO); assert(saved >= 0);
        assert(dup2(output[1], STDOUT_FILENO) == STDOUT_FILENO); close(output[1]);
        snprintf(script, sizeof(script), "jobs %s %%1\n", mode == 1 ? "-l" : mode == 2 ? "-p" : "");
        assert(run(&ctx, script).status == 0);
        assert(dup2(saved, STDOUT_FILENO) == STDOUT_FILENO); close(saved);
        if (mode == 0) snprintf(expected, sizeof(expected), "[1] + Running pipeline\n");
        else if (mode == 1) snprintf(expected, sizeof(expected), "[1] + %ld Running pipeline\n%ld pipeline\n",
            (long)displayed, (long)additional);
        else snprintf(expected, sizeof(expected), "%ld\n", (long)displayed);
        ssize_t length = read(output[0], actual, sizeof(actual));
        assert(length == (ssize_t)strlen(expected) && !memcmp(actual, expected, (size_t)length));
        close(output[0]);
      }
    }
    job->grouped = 0; /* The formatting fixture's children share our group. */
    trace("cancel+", job->pgid);
    csh_jobs_cancel(ctx.jobs, job);
    trace("cancel-", 0);
    destroy(&ctx);
    trace("formats-", 0);
}
static void notification(int notify, int outcome)
{
    struct csh_invocation inv = {0};
    struct csh_execution_context ctx = {0};
    struct csh_job *bg, *fg;
    int messages[2], release[2], launch[2], saved, status;
    char expected[128];
    inv.arg0 = "notifications"; inv.options = CSH_OPT_INTERACTIVE;
    assert(csh_state_create(&ctx.state, &inv, NULL) == CSH_STATE_OK);
    assert(csh_jobs_create(&ctx.jobs, ctx.state, STDIN_FILENO) == 0);
    assert(csh_jobs_monitor(ctx.jobs));
    if (notify) csh_state_update_options(ctx.state, CSH_OPT_NOTIFY, 0);
    assert(pipe(messages) == 0 && pipe(release) == 0 && pipe(launch) == 0);
    saved = dup(STDERR_FILENO); assert(saved >= 0);
    assert(dup2(messages[1], STDERR_FILENO) == STDERR_FILENO); close(messages[1]);
    bg = csh_jobs_add(ctx.jobs, 1, "background", 1, 0); assert(bg);
    bg->processes[0].pid = csh_retention_fork(); assert(bg->processes[0].pid >= 0);
    if (!bg->processes[0].pid) {
        char byte;
        signal(SIGTERM, SIG_DFL);
        signal(SIGTSTP, SIG_DFL); signal(SIGTTIN, SIG_DFL); signal(SIGTTOU, SIG_DFL);
        assert(read(release[0], &byte, 1) == 1);
        if (outcome < 0) raise(SIGTERM);
        if (outcome >= 128) { raise(outcome - 128); _exit(0); }
        _exit(outcome);
    }
    bg->pgid = bg->processes[0].pid;
    assert(setpgid(bg->pgid, bg->pgid) == 0);
    if (outcome >= 128) {
        siginfo_t stopped;
        assert(write(release[1], "x", 1) == 1);
        /* Observe the kernel stop without consuming jobs.c's wait status. */
        while (waitid(P_PID, (id_t)bg->pgid, &stopped, WSTOPPED | WNOWAIT) < 0)
            assert(errno == EINTR);
        assert(stopped.si_code == CLD_STOPPED && stopped.si_status == outcome - 128);
        if (outcome == 128 + SIGTSTP)
            snprintf(expected, sizeof(expected), "[1] + Stopped background\n");
        else snprintf(expected, sizeof(expected), "[1] + Stopped (SIG%s) background\n",
            csh_jobs_signal_name(outcome - 128));
    } else snprintf(expected, sizeof(expected), "[1]   %s background\n",
        outcome < 0 ? "Terminated (SIGTERM)" : outcome ? "Done(17)" : "Done");
    fg = csh_jobs_add(ctx.jobs, 1, "foreground", 0, 0); assert(fg);
    fg->processes[0].pid = csh_retention_fork(); assert(fg->processes[0].pid >= 0);
    if (!fg->processes[0].pid) {
        char output[128], ready;
        struct timespec tick = {0, 1000000};
        alarm(5);
        /* Match production's launch barrier: the foreground child cannot
         * exit before its parent assigns the group and transfers the tty. */
        assert(read(launch[0], &ready, 1) == 1);
        if (outcome < 128) assert(write(release[1], "x", 1) == 1);
        /* ESRCH is proof that the foreground wait reaped the background
         * child. Polling delay throttles the predicate, never proves it. */
        if (outcome < 128) {
            while (kill(bg->pgid, 0) == 0) nanosleep(&tick, NULL);
            assert(errno == ESRCH);
        }
        if (notify) {
            size_t offset = 0, length = strlen(expected);
            while (offset < length) {
                ssize_t count = read(messages[0], output + offset, length - offset);
                if (count < 0 && errno == EINTR) continue;
                assert(count > 0); offset += (size_t)count;
            }
            assert(memcmp(output, expected, length) == 0);
        } else {
            assert(fcntl(messages[0], F_SETFL, O_NONBLOCK) == 0);
            assert(read(messages[0], output, sizeof(output)) == -1 && errno == EAGAIN);
        }
        _exit(0);
    }
    fg->pgid = fg->processes[0].pid;
    assert(setpgid(fg->pgid, fg->pgid) == 0);
    assert(csh_jobs_give_terminal(ctx.jobs, fg, 0) == 0);
    assert(write(launch[1], "r", 1) == 1);
    assert(csh_jobs_foreground(ctx.jobs, fg, 0, &status, NULL) == 0 && status == 0);
    assert(tcgetpgrp(STDIN_FILENO) == getpgrp());
    if (!notify) {
        char output[128];
        csh_jobs_notify(ctx.jobs);
        ssize_t length = read(messages[0], output, sizeof(output));
        assert(length == (ssize_t)strlen(expected) && !memcmp(output, expected, (size_t)length));
    }
    assert(run(&ctx, "wait %1\n").status == (outcome < 0 ? 128 + SIGTERM : outcome));
    if (outcome >= 128)
        assert(run(&ctx, "bg %1 >/dev/null; wait %1\n").status == 0);
    assert(dup2(saved, STDERR_FILENO) == STDERR_FILENO); close(saved);
    close(messages[0]); close(release[0]); close(release[1]);
    close(launch[0]); close(launch[1]);
    destroy(&ctx);
}
static void diagnostic_stall(void)
{
    int ready[2], status;
    pid_t child, observed;
    char byte;
    ssize_t count;
    assert(csh_retention_trace_enabled());
    assert(pipe(ready) == 0);
    child = csh_retention_fork(); assert(child >= 0);
    if (child == 0) {
        close(ready[0]);
        do { count = write(ready[1], "r", 1); } while (count < 0 && errno == EINTR);
        assert(count == 1);
        close(ready[1]);
        for (;;) pause();
    }
    close(ready[1]);
    do { count = read(ready[0], &byte, 1); } while (count < 0 && errno == EINTR);
    assert(count == 1 && byte == 'r');
    close(ready[0]);
    trace("stall_ready", child);
    /* Exercise the existing alarm's real disposition. Observation installs
     * no handler and neither unblocks nor consumes an inherited SIGALRM. */
    alarm(5);
    trace("stall_wait+", child);
    do { observed = waitpid(child, &status, 0); } while (observed < 0 && errno == EINTR);
    trace("stall_wait-", child);
    assert(!"diagnostic stalled child unexpectedly finished");
}
int main(int argc, char **argv)
{
    int trace_errno;
    diagnostic_fd = dup(STDERR_FILENO);
    assert(diagnostic_fd >= 0);
    trace_errno = errno;
    csh_retention_trace_init();
    assert(errno == trace_errno);
    trace("start", 0);
    alarm(20);
    trace("alarm_armed", 0);
    if (argc == 2 && !strcmp(argv[1], "diagnostic-stall")) diagnostic_stall();
    else if (argc == 2 && !strcmp(argv[1], "notify")) {
        const int outcomes[] = {-1, 0, 17, 128 + SIGSTOP, 128 + SIGTSTP,
            128 + SIGTTIN, 128 + SIGTTOU};
        for (int notify = 0; notify <= 1; ++notify)
            for (size_t i = 0; i < sizeof(outcomes) / sizeof(*outcomes); ++i) {
                alarm(10);
                notification(notify, outcomes[i]);
            }
        puts("foreground notifications: notify off/on, zero/nonzero/signal bytes and retained results passed");
    } else {
        retention();
        puts("retention live records"); assert(fflush(stdout) == 0);
        live_retention();
        puts("retention formatting"); assert(fflush(stdout) == 0);
        formats();
        puts("retention complete"); assert(fflush(stdout) == 0);
    }
    /* No forgotten direct children survive either phase. */
    int status;
    csh_retention_trace_context(0, 0, 0);
    trace("cleanup+", 0);
    assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
    trace("cleanup-", 0);
    alarm(0);
    trace("finish", 0);
    csh_retention_trace_close();
    close(diagnostic_fd);
    return 0;
}
