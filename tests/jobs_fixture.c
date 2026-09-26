#include "cshell/jobs.h"
#include "cshell/parser.h"
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

enum fixture_phase {
    OWNERSHIP, PIPELINE, IDLE_REAP, RAPID_EXIT, INTERRUPTED_WAIT, NOTIFY, CLEANUP
};
static volatile sig_atomic_t timeout_phase;
static volatile sig_atomic_t timeout_fd = STDERR_FILENO;

static void timed_out(int number)
{
    const char *message;
    size_t length;
    (void)number;
#define PHASE_MESSAGE(phase, text) \
    case phase: message = "jobs fixture timeout: " text "\n"; \
        length = sizeof("jobs fixture timeout: " text "\n") - 1; break
    switch (timeout_phase) {
        PHASE_MESSAGE(OWNERSHIP, "child ownership");
        PHASE_MESSAGE(PIPELINE, "pipeline ownership");
        PHASE_MESSAGE(IDLE_REAP, "idle reaping");
        PHASE_MESSAGE(RAPID_EXIT, "rapid-exit pipeline");
        PHASE_MESSAGE(INTERRUPTED_WAIT, "interrupted wait");
        PHASE_MESSAGE(NOTIFY, "idle notification");
        default: message = "jobs fixture timeout: cleanup\n";
            length = sizeof("jobs fixture timeout: cleanup\n") - 1; break;
    }
#undef PHASE_MESSAGE
    /* The alarm can interrupt any library operation. Keep its diagnostic
     * async-signal-safe; the Python runner cleans up the entire process group. */
    while (write(timeout_fd, message, length) < 0 && errno == EINTR) {}
    _exit(124);
}

static void begin_phase(enum fixture_phase phase)
{
    timeout_phase = phase;
    alarm(5);
}

static struct csh_execution run(struct csh_execution_context *context, const char *text)
{
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *tree = NULL;
    struct csh_error error;
    struct csh_execution result;
    assert(csh_input_from_string(&input, text, "jobs", &error) == 0);
    assert(csh_parser_create(&parser, input, &error) == 0);
    assert(csh_parser_next(parser, &tree, &error) == CSH_PARSE_TREE);
    assert(csh_execute_context_ast(context, tree, &result, &error) == 0);
    assert(error.message == NULL);
    csh_ast_destroy(tree);
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    return result;
}

static pid_t waited(pid_t pid, int *status, int options)
{
    pid_t result;
    do { result = waitpid(pid, status, options); } while (result == -1 && errno == EINTR);
    return result;
}

static int descriptors(void)
{
    int fd, count = 0;
    for (fd = 0; fd < 256; ++fd) if (fcntl(fd, F_GETFD) >= 0) ++count;
    return count;
}

int main(int argc, char **argv)
{
    struct csh_invocation invocation = {0};
    struct csh_execution_context context = {0};
    struct csh_state *state;
    struct csh_state_info info;
    struct csh_error error;
    struct sigaction original, current, watchdog = {0};
    int input[2], release[2], before = descriptors(), status;
    pid_t unrelated, background, observer;
    siginfo_t child_info;
    char script[1024], byte;
    struct timespec tick = {0, 1000000};
    int stall = argc == 2 && strcmp(argv[1], "--stall-rapid-exit") == 0;
    assert(argc == 1 || stall);
    watchdog.sa_handler = timed_out;
    sigemptyset(&watchdog.sa_mask);
    assert(sigaction(SIGALRM, &watchdog, NULL) == 0);
    begin_phase(OWNERSHIP);
    invocation.arg0 = "job-fixture";
    invocation.mode = CSH_MODE_STRING;
    assert(sigaction(SIGCHLD, NULL, &original) == 0);
    assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
    context.state = state;
    assert(csh_jobs_create(&context.jobs, state, -1) == 0);
    assert(!csh_jobs_monitor(context.jobs));
    unrelated = fork();
    assert(unrelated >= 0);
    if (unrelated == 0) _exit(37);
    while (waitid(P_PID, (id_t)unrelated, &child_info, WEXITED | WNOWAIT) == -1) assert(errno == EINTR);
    run(&context, "exit 17 &\n");
    csh_state_get_info(state, &info);
    background = info.background_pid;
    assert(csh_execution_context_reap(&context, 1, &error) == 0);
    assert(waited(background, &status, WNOHANG) == -1 && errno == ECHILD);
    assert(waited(unrelated, &status, 0) == unrelated &&
        WIFEXITED(status) && WEXITSTATUS(status) == 37);
    run(&context, "jobs >/dev/null\n");
    snprintf(script, sizeof(script), "wait %ld\n", (long)background);
    assert(run(&context, script).status == 17);
    assert(run(&context, "wait\n").status == 0);
    /* Every stage is owned; $! is exactly the last stage, and polling does
     * not discard the pipeline result before wait consumes it. */
    begin_phase(PIPELINE);
    run(&context, "exit 4 | exit 23 &\n");
    csh_state_get_info(state, &info);
    background = info.background_pid;
    assert(csh_execution_context_reap(&context, 1, &error) == 0);
    snprintf(script, sizeof(script), "wait %ld\n", (long)background);
    assert(run(&context, script).status == 23);
    assert(waited(-1, &status, WNOHANG) == -1 && errno == ECHILD);
    /* The observer writes only after the owned child has been reaped while
     * the shell is idle waiting for descriptor input. No sleeps establish
     * correctness; all waiting is bounded and uses observable handshakes. */
    begin_phase(IDLE_REAP);
    assert(pipe(input) == 0 && pipe(release) == 0);
    snprintf(script, sizeof(script), "/usr/bin/head -c 1 <&%d >/dev/null &\n", release[0]);
    run(&context, script);
    csh_state_get_info(state, &info);
    background = info.background_pid;
    observer = fork();
    assert(observer >= 0);
    if (observer == 0) {
        alarm(5);
        assert(write(release[1], "x", 1) == 1);
        while (kill(background, 0) == 0) nanosleep(&tick, NULL);
        assert(errno == ESRCH);
        assert(write(input[1], "r", 1) == 1);
        _exit(0);
    }
    close(input[1]);
    assert(csh_jobs_read_ready(context.jobs, input[0], 0) == 0);
    assert(read(input[0], &byte, 1) == 1 && byte == 'r');
    assert(waited(observer, &status, 0) == observer &&
        WIFEXITED(status) && WEXITSTATUS(status) == 0);
    assert(run(&context, "wait\n").status == 0);
    close(input[0]); close(release[0]); close(release[1]);
    /* Rapid exits cannot race registration or lose final-stage status. Each
     * pipeline gets the same stall budget: aggregate fork/sanitizer overhead
     * must not consume the budget for a later, still-progressing iteration. */
    for (int i = 0; i < 150; ++i) {
        begin_phase(RAPID_EXIT);
        if (stall) {
            run(&context, "/bin/sleep 60 | /bin/sleep 60 &\n");
            printf("%ld\n", (long)getsid(0));
            assert(fflush(stdout) == 0);
            for (;;) pause();
        }
        run(&context, "exit 7 | exit 29 &\n");
        csh_state_get_info(state, &info);
        snprintf(script, sizeof(script), "wait %ld\n", (long)info.background_pid);
        assert(run(&context, script).status == 29);
    }
    begin_phase(CLEANUP);
    csh_execution_context_destroy(&context);
    assert(sigaction(SIGCHLD, NULL, &current) == 0 && current.sa_handler == original.sa_handler);
    assert(descriptors() == before);
    /* An interactive wait interrupted by SIGINT returns 130 and leaves its
     * child registered for a subsequent wait. No controlling tty is needed. */
    begin_phase(INTERRUPTED_WAIT);
    assert(csh_state_update_options(state, CSH_OPT_INTERACTIVE, 0) == CSH_STATE_OK);
    context.state = state;
    assert(csh_jobs_create(&context.jobs, state, -1) == 0);
    assert(pipe(release) == 0);
    snprintf(script, sizeof(script), "{ /usr/bin/head -c 1 <&%d >/dev/null & } 2>/dev/null\n", release[0]);
    run(&context, script);
    csh_state_get_info(state, &info);
    background = info.background_pid;
    observer = fork();
    assert(observer >= 0);
    if (observer == 0) {
        pid_t parent = getppid();
        alarm(5);
        for (;;) { nanosleep(&tick, NULL); kill(parent, SIGINT); }
    }
    snprintf(script, sizeof(script), "wait %ld\n", (long)background);
    assert(run(&context, script).status == 128 + SIGINT);
    assert(kill(observer, SIGKILL) == 0);
    while (waitpid(observer, &status, 0) == -1 && errno == EINTR) {}
    assert(kill(background, 0) == 0);
    assert(write(release[1], "x", 1) == 1);
    assert(run(&context, script).status == 0);
    close(release[0]); close(release[1]);
    /* Notify reports completion while idle and still leaves the status for
     * wait. Capture stderr independently of nondeterministic launch PIDs. */
    begin_phase(NOTIFY);
    {
        int messages[2], saved_error = dup(STDERR_FILENO);
        char output[256];
        ssize_t length;
        assert(saved_error >= 0 && pipe(messages) == 0 && pipe(input) == 0);
        timeout_fd = saved_error;
        assert(dup2(messages[1], STDERR_FILENO) == STDERR_FILENO);
        close(messages[1]);
        run(&context, "set -b; { exit 17 & } 2>/dev/null\n");
        csh_state_get_info(state, &info);
        background = info.background_pid;
        observer = fork();
        assert(observer >= 0);
        if (observer == 0) {
            alarm(5);
            while (kill(background, 0) == 0) nanosleep(&tick, NULL);
            assert(errno == ESRCH);
            assert(write(input[1], "r", 1) == 1);
            _exit(0);
        }
        close(input[1]);
        assert(csh_jobs_read_ready(context.jobs, input[0], 0) == 0);
        assert(read(input[0], &byte, 1) == 1 && byte == 'r');
        assert(waited(observer, &status, 0) == observer &&
            WIFEXITED(status) && WEXITSTATUS(status) == 0);
        assert(dup2(saved_error, STDERR_FILENO) == STDERR_FILENO);
        timeout_fd = STDERR_FILENO;
        close(saved_error);
        length = read(messages[0], output, sizeof(output) - 1);
        assert(length > 0);
        output[length] = '\0';
        assert(strcmp(output, "[2]  Done(17) exit 17\n") == 0);
        assert(run(&context, "wait %2\n").status == 17);
        close(messages[0]); close(input[0]);
    }
    begin_phase(CLEANUP);
    csh_execution_context_destroy(&context);
    csh_state_destroy(state);
    assert(waited(-1, &status, WNOHANG) == -1 && errno == ECHILD);
    assert(descriptors() == before);
    alarm(0);
    puts("job ownership, idle reaping, retained statuses and interrupted wait passed");
    return 0;
}
