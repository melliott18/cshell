#include "cshell/execute.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int fd_count(void)
{
    int fd, count = 0;
    for (fd = 0; fd < 256; ++fd) if (fcntl(fd, F_GETFD) >= 0) ++count;
    return count;
}

static void check_stages(struct csh_pipeline_result *result, const int *expected)
{
    size_t i;
    for (i = 0; i < result->count; ++i) {
        struct csh_pipeline_stage *stage = &result->stages[i];
        int status;
        assert(stage->pid > 0 && stage->completed && stage->reaped);
        if (expected != NULL) assert(stage->status == expected[i]);
        assert(WIFEXITED(stage->wait_status) || WIFSIGNALED(stage->wait_status));
        assert(waitpid(stage->pid, &status, WNOHANG) == -1 && errno == ECHILD);
    }
}

int main(int argc, char **argv)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state = NULL;
    struct csh_pipeline_result result = {0};
    struct csh_error error;
    struct csh_state_info info;
    struct csh_command commands[3] = {{0}};
    char *first[] = {NULL, "status", "7", NULL};
    char *middle[] = {NULL, "signal", NULL};
    char *last[] = {"exit", "9", NULL};
    int expected[] = {7, 128 + SIGTERM, 9};
    int before, status, repeat, mask;
    pid_t unrelated;
    siginfo_t child_info;
    assert(argc == 2);
    first[0] = middle[0] = argv[1];
    invocation.mode = CSH_MODE_STRING;
    invocation.arg0 = "pipeline-fixture";
    assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
    commands[0].argv = first; commands[0].argc = 3;
    commands[1].argv = middle; commands[1].argc = 2;
    commands[2].argv = last; commands[2].argc = 2;
    before = fd_count();
    unrelated = fork();
    assert(unrelated >= 0);
    if (unrelated == 0) _exit(37);
    assert(waitid(P_PID, (id_t)unrelated, &child_info, WEXITED | WNOWAIT) == 0);
    for (repeat = 0; repeat < 20; ++repeat) {
        assert(csh_execute_pipeline(state, commands, 3, repeat % 2, &result, &error) == 0);
        assert(error.message == NULL && result.count == 3);
        assert(result.execution.category == CSH_EXEC_PIPELINE);
        assert(!result.execution.exit_requested);
        assert(result.execution.status == (repeat % 2 ? 0 : 9));
        assert(csh_state_get_info(state, &info) == CSH_STATE_OK);
        assert(info.last_status == result.execution.status);
        check_stages(&result, expected);
        assert(result.stages[2].category == CSH_EXEC_SPECIAL_BUILTIN);
        csh_pipeline_result_destroy(&result);
        csh_pipeline_result_destroy(&result);
        assert(result.stages == NULL && result.count == 0 && fd_count() == before);
    }
    {
        char *fds[] = {argv[1], "private-fds", NULL};
        struct csh_command probes[3] = {{0}};
        int clean[] = {0, 0, 0};
        for (repeat = 0; repeat < 3; ++repeat) {
            probes[repeat].argv = fds; probes[repeat].argc = 2;
        }
        assert(csh_execute_pipeline(state, probes, 3, 0, &result, &error) == 0);
        check_stages(&result, clean);
        csh_pipeline_result_destroy(&result);
    }
    assert(waitpid(unrelated, &status, 0) == unrelated);
    assert(WIFEXITED(status) && WEXITSTATUS(status) == 37);
    assert(csh_execute_pipeline(state, commands, 1, 1, &result, &error) == 0);
    check_stages(&result, expected);
    assert(result.execution.status == 0);
    csh_pipeline_result_destroy(&result);
    assert(csh_execute_pipeline(state, commands + 2, 1, 0, &result, &error) == 0);
    assert(result.stages[0].pid == 0 && result.stages[0].completed && !result.stages[0].reaped);
    assert(result.stages[0].status == 9 && result.execution.exit_requested);
    csh_pipeline_result_destroy(&result);
    /* All combinations of originally closed standard fds. Keep backups high
     * and CLOEXEC; verify original closures and no parent descriptor growth. */
    for (mask = 1; mask < 8; ++mask) {
        int saved[3], fd, after_close;
        char *copy[] = {argv[1], "copy", NULL};
        struct csh_redirect input = {0}, output = {0};
        input.kind = CSH_REDIRECT_READ; input.fd = 0; input.path = "/dev/null";
        output.kind = CSH_REDIRECT_WRITE; output.fd = 1; output.path = "/dev/null";
        for (fd = 0; fd < 3; ++fd) {
            saved[fd] = fcntl(fd, F_DUPFD_CLOEXEC, 40);
            assert(saved[fd] >= 40);
            if (mask & (1 << fd)) assert(close(fd) == 0);
            commands[fd].argv = copy; commands[fd].argc = 2;
        }
        commands[0].redirections = &input; commands[0].redirection_count = 1;
        commands[2].redirections = &output; commands[2].redirection_count = 1;
        after_close = fd_count();
        assert(csh_execute_pipeline(state, commands, 3, 0, &result, &error) == 0);
        assert(result.execution.status == 0);
        expected[0] = expected[1] = expected[2] = 0;
        check_stages(&result, expected);
        csh_pipeline_result_destroy(&result);
        assert(fd_count() == after_close);
        for (fd = 0; fd < 3; ++fd) {
            if (mask & (1 << fd)) assert(fcntl(fd, F_GETFD) == -1 && errno == EBADF);
            assert(dup2(saved[fd], fd) == fd);
            close(saved[fd]);
        }
        assert(fd_count() == before);
    }
    assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
    csh_state_destroy(state);
    puts("pipeline API checks passed");
    return 0;
}
