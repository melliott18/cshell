/* Shell invocation, complete-command execution, and final status. */
#include "cshell/execute.h"
#include "cshell/character.h"
#include "cshell/builtin.h"
#include "cshell/parser.h"
#include "cshell/jobs.h"
#include "cshell/output.h"
#include "cshell/traps.h"
#include <errno.h>
#include <locale.h>

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
    fputs(csh_error_message(error), stderr);
    if (error->system_errno != 0)
        fprintf(stderr, ": %s", strerror(error->system_errno));
    fputc('\n', stderr);
}

struct prompt_context {
    struct csh_invocation *invocation;
    struct csh_jobs *jobs;
    struct csh_state *state;
    struct csh_execution_context *shell;
    int exit_requested;
};

static int input_ready(void *user, int fd)
{
    struct prompt_context *data = user;
    int dispatched = 0;
    for (;;) {
        struct csh_execution execution = {0};
        struct csh_error error;
        if (csh_jobs_read_ready(data->jobs, fd, dispatched) == 0) return 0;
        if (errno != EINTR || csh_jobs_interrupt_pending() ||
            csh_jobs_hangup_pending()) return -1;
        if (csh_traps_pending() && !dispatched) {
            if (csh_execute_pending_traps(data->shell, &execution, &error) == -1) {
                errno = ENOMEM;
                return -1;
            }
            if (execution.exit_requested) {
                data->exit_requested = 1;
                errno = EINTR;
                return -1;
            }
            /* Leave signals raised by an action for the next command
             * boundary, but accept a later independent idle delivery. */
            dispatched = csh_traps_pending();
        }
    }
}

static void prompt(void *context, int continuation)
{
    struct prompt_context *prompt_data = context;
    const struct csh_invocation *invocation = prompt_data->invocation;
    csh_jobs_poll(prompt_data->jobs);
    csh_jobs_notify(prompt_data->jobs);
    const char *text = csh_invocation_prompt(invocation, continuation, "$ ", "> ");
    /* SIGCHLD from bg can interrupt even this short terminal write. Retry
     * interrupted/partial output before entering the next input wait. */
    if (text != NULL) (void)csh_write_text(STDERR_FILENO, text);
}

static int ignore_eof(void *user)
{
    struct prompt_context *data = user;
    struct csh_state_info info;
    csh_state_get_info(data->state, &info);
    if (!(info.options & CSH_OPT_IGNOREEOF)) return 0;
    fputs("cshell: use exit to leave the shell\n", stderr);
    prompt(user, 0);
    return 1;
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
    struct prompt_context prompt_data;

    /* The process starts in the C locale. Establish the invocation locale
     * before reading shell input or expanding any words. Changes to shell
     * LC_CTYPE variables later do not change this invocation's lexer locale. */
    if (setlocale(LC_ALL, "") == NULL) (void)setlocale(LC_ALL, "C");

    if (csh_character_startup() == -1) {
        fputs("cshell: cannot preserve startup character locale\n", stderr);
        return 1;
    }

    if (csh_invocation_parse(&invocation, argc, argv, STDIN_FILENO,
            STDERR_FILENO, &error) == -1) {
        diagnose(&error, error.argument_index != 0 ? argv[error.argument_index] : NULL);
        csh_character_shutdown();
        return error.status;
    }
    if (csh_state_create(&state, &invocation, environ) != CSH_STATE_OK) {
        fputs("cshell: cannot allocate shell state\n", stderr);
        status = 1;
        goto done;
    }
    if (csh_builtin_initialize(state)) {
        fputs("cshell: cannot initialize shell variables\n", stderr);
        csh_state_set_status(state, 1);
        goto done;
    }
    csh_state_manage_locale(state);
    if (csh_parser_create(&parser, invocation.input, &error) == -1) {
        diagnose(&error, csh_input_name(invocation.input));
        csh_state_set_status(state, error.status);
        goto done;
    }
    context.state = state;
    if (csh_state_aliases(state) == NULL) {
        csh_state_set_status(state, 1); goto done;
    }
    csh_parser_set_aliases(parser, csh_state_aliases(state));
    if (csh_traps_create(&context.traps, invocation.interactive) == -1) {
        fprintf(stderr, "cshell: cannot initialize traps: %s\n", strerror(errno));
        csh_state_set_status(state, 1);
        goto done;
    }
    if (csh_jobs_create(&context.jobs, state,
        invocation.interactive ? STDIN_FILENO : -1) == -1) {
        fprintf(stderr, "cshell: cannot initialize jobs: %s\n", strerror(errno));
        csh_state_set_status(state, 1);
        goto done;
    }
    /* Job setup supplies the interactive monitor default. Explicit command
     * line choices override it, including +m, and notify survives setup. */
    csh_state_update_options(state, invocation.options & invocation.option_mask,
        invocation.option_mask & ~invocation.options);
    if ((invocation.options & CSH_OPT_MONITOR) && !csh_jobs_monitor(context.jobs)) {
        fputs("cshell: job control unavailable\n", stderr);
        csh_state_set_status(state, 2);
        goto done;
    }
    prompt_data.state = state;
    prompt_data.invocation = &invocation;
    prompt_data.jobs = context.jobs;
    prompt_data.shell = &context;
    prompt_data.exit_requested = 0;
    csh_input_set_wait_hook(invocation.input, input_ready, &prompt_data);
    csh_parser_set_read_hook(parser, prompt, &prompt_data);
    csh_input_set_line_hook(invocation.input, csh_execute_input_line, state);
    if (invocation.interactive && invocation.mode == CSH_MODE_STDIN && isatty(STDIN_FILENO))
        csh_input_set_eof_hook(invocation.input, ignore_eof, &prompt_data);
    for (;;) {
        struct csh_ast *tree = NULL;
        struct csh_execution execution;
        int executed;
        enum csh_parse_result parsed;
        csh_parser_set_aliases(parser, csh_state_aliases(state));
        parsed = csh_parser_next(parser, &tree, &error);
        if (parsed == CSH_PARSE_EOF) break;
        if (parsed == CSH_PARSE_INTERRUPTED) {
            struct csh_execution pending = {0};
            if (prompt_data.exit_requested) break;
            int signal_number = csh_jobs_take_interrupt();
            if (signal_number) csh_state_set_status(state, 128 + signal_number);
            if (csh_execute_pending_traps(&context, &pending, &error) == -1) {
                diagnose(&error, NULL);
                break;
            }
            if (csh_jobs_hangup_pending()) {
                csh_state_set_status(state, 129);
                break;
            }
            if (pending.exit_requested) break;
            continue;
        }
        if (parsed != CSH_PARSE_TREE) {
            diagnose(&error, csh_parser_source_name(parser));
            csh_state_set_status(state, error.status);
            break; /* Ordinary parser errors remain sticky. */
        }
        executed = csh_execute_context_ast(&context, tree, &execution, &error);
        csh_jobs_take_interrupt();
        csh_ast_destroy(tree);
        if (executed == -1 && !error.reported)
            diagnose(&error, NULL);
        if (execution.exit_requested ||
            (execution.special_builtin_error && !invocation.interactive)) break;
        if (csh_jobs_hangup_pending()) {
            csh_state_set_status(state, 129);
            break;
        }
        if (executed == -1 && !invocation.interactive &&
            execution.category == CSH_EXEC_PIPELINE) break;
    }
done:
    if (state != NULL) {
        if (csh_jobs_hangup_pending()) {
            csh_jobs_hangup(context.jobs);
            csh_state_set_status(state, 129);
            csh_jobs_clear_hangup();
        }
        if (context.traps != NULL) {
            struct csh_execution pending = {0};
            if (csh_execute_pending_traps(&context, &pending, &error) == -1)
                diagnose(&error, NULL);
            csh_execute_exit_trap(&context, &error);
        }
        csh_state_get_info(state, &info);
        status = info.last_status;
    }
    csh_traps_destroy(context.traps);
    csh_execution_context_destroy(&context);
    csh_parser_destroy(parser);
    csh_state_destroy(state);
    csh_invocation_destroy(&invocation);
    csh_character_shutdown();
    return status;
}
