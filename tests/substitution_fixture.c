/* CSH-026: lifecycle checks that output-only runtime fixtures cannot observe. */
#include "cshell/execute.h"
#include "cshell/parser.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
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

static struct csh_ast *parse(const char *text)
{
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *tree = NULL;
    struct csh_error error;
    assert(csh_input_from_string(&input, text, "substitution-api", &error) == 0);
    assert(csh_parser_create(&parser, input, &error) == 0);
    assert(csh_parser_next(parser, &tree, &error) == CSH_PARSE_TREE);
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    return tree;
}

static void value_is(struct csh_state *state, const char *name, const char *expected)
{
    struct csh_variable_view view;
    assert(csh_state_get_variable(state, name, &view) == CSH_STATE_OK);
    assert(expected == NULL ? view.value == NULL : view.value && !strcmp(view.value, expected));
}

int main(void)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state = NULL;
    struct csh_execution_context context = {0};
    struct csh_execution result;
    struct csh_pipeline_result pipeline = {0};
    struct csh_error error;
    struct csh_ast *tree;
    struct csh_state_info info;
    int before = fd_count(), i, status;
    pid_t unrelated;
    siginfo_t child;
    invocation.arg0 = "substitution-api";
    assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
    context.state = state;
    unrelated = fork();
    assert(unrelated >= 0);
    if (unrelated == 0) _exit(37);
    assert(waitid(P_PID, (id_t)unrelated, &child, WEXITED | WNOWAIT) == 0);
    tree = parse("VALUE=$(INNER=child; cd /; printf 'a\\nb\\n\\n'; exit 17)\n");
    for (i = 0; i < 30; ++i) {
        assert(csh_execute_context_ast(&context, tree, &result, &error) == 0);
        assert(result.status == 17 && !result.exit_requested);
        value_is(state, "VALUE", "a\nb");
        value_is(state, "INNER", NULL);
        assert(context.child_count == 0 && fd_count() == before);
    }
    csh_ast_destroy(tree);
    tree = parse("printf '%s' \"${MUTATED:=value}${missing:?required}\" >forbidden\n");
    for (i = 0; i < 10; ++i) {
        assert(csh_execute_context_ast(&context, tree, &result, &error) == -1);
        assert(result.status == 2 && result.exit_requested);
        assert(!strcmp(csh_error_message(&error), "required"));
        value_is(state, "MUTATED", NULL);
        assert(access("forbidden", F_OK) == -1);
        assert(fd_count() == before && context.child_count == 0);
    }
    csh_ast_destroy(tree);
    assert(csh_state_update_options(state, CSH_OPT_INTERACTIVE | CSH_OPT_NOUNSET, 0) == CSH_STATE_OK);
    tree = parse("printf '%s' \"$missing\"\n");
    assert(csh_execute_context_ast(&context, tree, &result, &error) == -1);
    assert(result.status == 2 && !result.exit_requested);
    assert(!strcmp(csh_error_message(&error), "missing"));
    csh_ast_destroy(tree);
    assert(csh_state_update_options(state, CSH_OPT_NOGLOB, CSH_OPT_NOUNSET) == CSH_STATE_OK);
    tree = parse("FLAGS=$(printf '%s' \"$-\")\n");
    assert(csh_execute_context_ast(&context, tree, &result, &error) == 0);
    value_is(state, "FLAGS", "f"); /* Substitutions are noninteractive. */
    csh_state_get_info(state, &info);
    assert(info.options == (CSH_OPT_INTERACTIVE | CSH_OPT_NOGLOB));
    csh_ast_destroy(tree);
    tree = parse("VALUE=changed | exit 9\n");
    assert(csh_execute_pipeline_ast(state, tree, &pipeline, &error) == 0);
    assert(pipeline.execution.status == 9 && pipeline.count == 2);
    assert(!pipeline.execution.exit_requested);
    for (i = 0; i < 2; ++i) {
        assert(pipeline.stages[i].pid > 0 && pipeline.stages[i].reaped);
        assert(waitpid(pipeline.stages[i].pid, &status, WNOHANG) == -1 && errno == ECHILD);
    }
    value_is(state, "VALUE", "a\nb");
    csh_pipeline_result_destroy(&pipeline);
    csh_ast_destroy(tree);
    assert(waitpid(unrelated, &status, 0) == unrelated);
    assert(WIFEXITED(status) && WEXITSTATUS(status) == 37);
    assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
    tree = parse("VALUE=$(printf bytes)\n");
    for (i = 1; i < 8; ++i) {
        int saved[3], fd, after_close;
        for (fd = 0; fd < 3; ++fd) {
            saved[fd] = fcntl(fd, F_DUPFD_CLOEXEC, 40);
            assert(saved[fd] >= 40);
            if (i & (1 << fd)) assert(close(fd) == 0);
        }
        after_close = fd_count();
        assert(csh_execute_context_ast(&context, tree, &result, &error) == 0);
        assert(result.status == 0 && fd_count() == after_close);
        value_is(state, "VALUE", "bytes");
        for (fd = 0; fd < 3; ++fd) {
            if (i & (1 << fd)) assert(fcntl(fd, F_GETFD) == -1 && errno == EBADF);
            assert(dup2(saved[fd], fd) == fd);
            close(saved[fd]);
        }
    }
    csh_ast_destroy(tree);
    csh_execution_context_destroy(&context);
    csh_state_destroy(state);
    assert(fd_count() == before);
    puts("substitution ownership checks passed");
    return 0;
}
