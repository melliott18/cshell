#include "cshell/execute.h"
#include "cshell/parser.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static struct csh_execution run(struct csh_execution_context *context, const char *text)
{
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *tree = NULL;
    struct csh_error error;
    struct csh_execution result;
    struct csh_state_info info;
    assert(csh_input_from_string(&input, text, "contexts", &error) == 0);
    assert(csh_parser_create(&parser, input, &error) == 0);
    assert(csh_parser_next(parser, &tree, &error) == CSH_PARSE_TREE);
    assert(csh_execute_context_ast(context, tree, &result, &error) == 0);
    assert(error.message == NULL);
    csh_state_get_info(context->state, &info);
    assert(info.last_status == result.status);
    csh_ast_destroy(tree);
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    return result;
}

static int fd_count(void)
{
    int fd, count = 0;
    for (fd = 0; fd < 256; ++fd) if (fcntl(fd, F_GETFD) >= 0) ++count;
    return count;
}

int main(int argc, char **argv)
{
    struct csh_invocation invocation = {0};
    struct csh_execution_context context = {0};
    struct csh_state_info info;
    struct csh_variable_view view;
    struct csh_execution result;
    struct csh_error error;
    int ready[2], release[2], status, before;
    char script[8192];
    pid_t unrelated, background, reported;
    siginfo_t child_info;
    struct stat saved, after;
    assert(argc == 2);
    invocation.arg0 = "context-fixture";
    invocation.mode = CSH_MODE_STRING;
    assert(csh_state_create(&context.state, &invocation, NULL) == CSH_STATE_OK);
    before = fd_count();
    result = run(&context, "A=parent; { A=brace; }; (A=child; exit 23); exit\n");
    assert(result.status == 23 && result.exit_requested);
    csh_state_get_variable(context.state, "A", &view);
    assert(strcmp(view.value, "brace") == 0);
    result = run(&context, "{ exit 17; }; A=never\n");
    assert(result.status == 17 && result.exit_requested);
    csh_state_get_variable(context.state, "A", &view);
    assert(strcmp(view.value, "brace") == 0);
    assert(fd_count() == before);

    /* Group backup descriptors cannot satisfy originally closed operands in
     * nested commands. Cover both target clobbering and source duplication. */
    assert(fstat(1, &saved) == 0);
    for (int fd = 40; fd < 46; ++fd) {
        close(fd);
        snprintf(script, sizeof(script), "{ { : %d>&-; }; : 1>&%d; } >group-output\n", fd, fd);
        result = run(&context, script);
        assert(result.status == 1);
        assert(fstat(1, &after) == 0 && saved.st_dev == after.st_dev && saved.st_ino == after.st_ino);
        assert(fcntl(fd, F_GETFD) == -1 && errno == EBADF);
    }
    result = run(&context, "{ { A=never; } >created 0<missing-context-input; } >outer || A=recovered\n");
    assert(result.status == 0 && fd_count() == before);
    csh_state_get_variable(context.state, "A", &view);
    assert(strcmp(view.value, "recovered") == 0);

    assert(pipe(ready) == 0 && pipe(release) == 0);
    assert(dup2(ready[1], 40) == 40 && dup2(release[0], 41) == 41);
    close(ready[1]); close(release[0]);
    unrelated = fork();
    assert(unrelated >= 0);
    if (unrelated == 0) _exit(37);
    assert(waitid(P_PID, (id_t)unrelated, &child_info, WEXITED | WNOWAIT) == 0);
    snprintf(script, sizeof(script), "'%s' gate 40 41 &\n", argv[1]);
    result = run(&context, script);
    assert(result.status == 0 && !result.exit_requested && context.child_count == 1);
    csh_state_get_info(context.state, &info);
    background = info.background_pid;
    assert(background > 0 && background != unrelated);
    /* Receiving readiness proves the background helper reached its gate.
     * The executor returned before the parent releases that gate. */
    assert(read(ready[0], &reported, sizeof(reported)) == sizeof(reported));
    assert(reported == background);
    assert(csh_execution_context_reap(&context, 0, &error) == 0);
    assert(context.child_count == 1);
    run(&context, "exit 29\n");
    assert(write(release[1], "x", 1) == 1);
    assert(csh_execution_context_reap(&context, 1, &error) == 0);
    assert(context.child_count == 0);
    csh_state_get_info(context.state, &info);
    assert(info.last_status == 29 && info.background_pid == background);
    assert(waitpid(background, &status, WNOHANG) == -1 && errno == ECHILD);
    assert(waitpid(unrelated, &status, 0) == unrelated && WEXITSTATUS(status) == 37);
    snprintf(script, sizeof(script), ": | '%s' gate 40 41 &\n", argv[1]);
    result = run(&context, script);
    assert(result.status == 0);
    csh_state_get_info(context.state, &info);
    assert(read(ready[0], &reported, sizeof(reported)) == sizeof(reported));
    assert(reported == info.background_pid);
    assert(write(release[1], "x", 1) == 1);
    assert(csh_execution_context_reap(&context, 1, &error) == 0);
    assert(context.child_count == 0);
    close(ready[0]); close(release[1]); close(40); close(41);
    assert(fd_count() == before);

    result = run(&context, "(A=async; exit 3) & (exit 4) & exit\n");
    assert(result.status == 0 && result.exit_requested);
    assert(csh_execution_context_reap(&context, 1, &error) == 0);
    assert(context.child_count == 0);
    csh_state_get_variable(context.state, "A", &view);
    assert(strcmp(view.value, "recovered") == 0);
    /* Automatic polling at the next execution boundary consumes a zombie. */
    run(&context, "exit 12 &\n");
    csh_state_get_info(context.state, &info);
    assert(waitid(P_PID, (id_t)info.background_pid, &child_info, WEXITED | WNOWAIT) == 0);
    run(&context, ":\n");
    assert(context.child_count == 0);
    assert(waitpid(info.background_pid, &status, WNOHANG) == -1 && errno == ECHILD);
    assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
    {
        struct csh_state *state = context.state;
        csh_execution_context_destroy(&context);
        csh_state_destroy(state);
    }
    assert(fd_count() == before);
    puts("context API checks passed");
    return 0;
}
