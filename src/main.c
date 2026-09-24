/* Shell invocation, complete-command execution, and final status. */
#include "cshell/execute.h"
#include "cshell/parser.h"

#include <stdio.h>
#include <string.h>
#include <unistd.h>

extern char **environ;

static void diagnose(const struct csh_error *error, const char *source)
{
    fputs("cshell: ", stderr);
    if (source != NULL) {
        fprintf(stderr, "%s: ", source);
        if (error->position.line != 0)
            fprintf(stderr, "%zu:%zu: ", error->position.line, error->position.column);
    }
    fputs(error->message, stderr);
    if (error->system_errno != 0)
        fprintf(stderr, ": %s", strerror(error->system_errno));
    fputc('\n', stderr);
}

static void prompt(void *context, int continuation)
{
    const struct csh_invocation *invocation = context;
    const char *text = csh_invocation_prompt(invocation, continuation, "$ ", "> ");
    if (text != NULL) {
        fputs(text, stderr);
        fflush(stderr);
    }
}

int main(int argc, char **argv)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state = NULL;
    struct csh_execution_context context = {0};
    struct csh_parser *parser = NULL;
    struct csh_error error;
    struct csh_state_info info;
    int status = 0;

    if (csh_invocation_parse(&invocation, argc, argv, STDIN_FILENO,
            STDERR_FILENO, &error) == -1) {
        diagnose(&error, error.argument_index != 0 ? argv[error.argument_index] : NULL);
        return error.status;
    }
    if (csh_state_create(&state, &invocation, environ) != CSH_STATE_OK) {
        fputs("cshell: cannot allocate shell state\n", stderr);
        status = 1;
        goto done;
    }
    if (csh_parser_create(&parser, invocation.input, &error) == -1) {
        diagnose(&error, csh_input_name(invocation.input));
        csh_state_set_status(state, error.status);
        goto done;
    }
    context.state = state;
    csh_parser_set_read_hook(parser, prompt, &invocation);
    for (;;) {
        struct csh_ast *tree = NULL;
        struct csh_execution execution;
        int executed;
        enum csh_parse_result parsed = csh_parser_next(parser, &tree, &error);
        if (parsed == CSH_PARSE_EOF) break;
        if (parsed != CSH_PARSE_TREE) {
            diagnose(&error, csh_parser_source_name(parser));
            csh_state_set_status(state, error.status);
            break; /* Parser errors are sticky; recovery belongs to CSH-011. */
        }
        executed = csh_execute_context_ast(&context, tree, &execution, &error);
        csh_ast_destroy(tree);
        if (executed == -1)
            diagnose(&error, NULL);
        if (execution.exit_requested ||
            (execution.special_builtin_error && !invocation.interactive)) break;
        if (executed == -1 && !invocation.interactive &&
            execution.category == CSH_EXEC_PIPELINE) break;
    }
done:
    if (state != NULL) {
        csh_state_get_info(state, &info);
        status = info.last_status;
    }
    csh_execution_context_destroy(&context);
    csh_parser_destroy(parser);
    csh_state_destroy(state);
    csh_invocation_destroy(&invocation);
    return status;
}
