#include "cshell/execute.h"
#include "cshell/quote.h"
#include "cshell/builtin.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static int fail(struct csh_error *error, const char *message, int number, int status)
{
    memset(error, 0, sizeof(*error));
    error->message = message;
    error->system_errno = number;
    error->status = status;
    return -1;
}

void csh_command_destroy(struct csh_command *command)
{
    size_t i;
    if (command == NULL) return;
    for (i = 0; i < command->argc; ++i) free(command->argv[i]);
    free(command->argv);
    for (i = 0; i < command->assignment_count; ++i) {
        free(command->assignments[i].name);
        free(command->assignments[i].value);
    }
    free(command->assignments);
    for (i = 0; i < command->redirection_count; ++i) {
        free(command->redirections[i].path);
        free(command->redirections[i].data);
    }
    free(command->redirections);
    memset(command, 0, sizeof(*command));
}

/* The adapter intentionally does not call expansion: all active expansion
 * fragments fail here, including those nested within double quotes. Flatten
 * only text/escaped bytes; quote containers themselves contribute no bytes. */
static int literal(const struct csh_ast_word *word, char **out,
    struct csh_error *error)
{
    const struct csh_token *token = &word->token;
    size_t i, used = 0;
    char *text;
    *out = NULL;
    if (word->substitution_count != 0)
        return fail(error, "command substitution is not supported by literal execution", 0, 2);
    if (token->length == SIZE_MAX || token->raw == NULL ||
        (token->fragment_count != 0 && token->fragments == NULL) ||
        memchr(token->raw, 0, token->length) != NULL)
        return fail(error, "invalid literal word", 0, 2);
    text = malloc(token->length + 1);
    if (text == NULL) return fail(error, "cannot allocate literal word", ENOMEM, 1);
    for (i = 0; i < token->fragment_count; ++i) {
        const struct csh_fragment *f = &token->fragments[i];
        size_t begin = f->begin, length;
        if (f->end > token->length || f->end < begin) goto invalid;
        length = f->end - begin;
        switch (f->kind) {
        case CSH_FRAGMENT_CONTINUATION:
            continue;
        case CSH_FRAGMENT_QUOTED:
            if (f->quote == CSH_QUOTE_DOLLAR_SINGLE) {
                char *decoded = NULL;
                size_t decoded_length, opening = begin + 1;
                enum csh_quote_result decoded_result;
                /* The lexer permits physical continuations between $ and '. */
                while (opening + 1 < f->end && token->raw[opening] == '\\' &&
                       token->raw[opening + 1] == '\n') opening += 2;
                if (length < 3 || opening + 1 >= f->end ||
                    token->raw[begin] != '$' || token->raw[opening] != '\'' ||
                    token->raw[f->end - 1] != '\'') goto invalid;
                decoded_result = csh_quote_decode(token->raw + opening + 1,
                    f->end - opening - 2, &decoded, &decoded_length);
                if (decoded_result != CSH_QUOTE_OK) {
                    free(text);
                    return fail(error, "cannot decode quoted literal",
                        decoded_result == CSH_QUOTE_NOMEM ? ENOMEM : 0,
                        decoded_result == CSH_QUOTE_NOMEM ? 1 : 2);
                }
                if (decoded_length > token->length - used) {
                    free(decoded);
                    goto invalid;
                }
                memcpy(text + used, decoded, decoded_length);
                used += decoded_length;
                free(decoded);
                while (i + 1 < token->fragment_count &&
                       token->fragments[i + 1].begin < f->end) ++i;
            } else if (f->quote != CSH_QUOTE_SINGLE && f->quote != CSH_QUOTE_DOUBLE)
                goto invalid;
            continue;
        case CSH_FRAGMENT_TEXT:
            if (f->quote == CSH_QUOTE_NONE) {
                size_t j;
                for (j = begin; j < f->end; ++j)
                    if (strchr("*?[~", token->raw[j]) != NULL) goto unsupported;
            }
            break;
        case CSH_FRAGMENT_ESCAPE:
            if (length != 2 || token->raw[begin] != '\\') goto invalid;
            ++begin;
            --length;
            break;
        default:
            goto unsupported;
        }
        if (length > token->length - used) goto invalid;
        memcpy(text + used, token->raw + begin, length);
        used += length;
    }
    text[used] = '\0';
    *out = text;
    return 0;
unsupported:
    free(text);
    return fail(error, "expansion is not supported by literal execution", 0, 2);
invalid:
    free(text);
    return fail(error, "invalid literal fragment", 0, 2);
}

static int descriptor(const unsigned char *text, size_t length, int *out)
{
    size_t i;
    int value = 0, digits = 0;
    for (i = 0; i < length; ++i) {
        int digit;
        if (text[i] == '\\' && i + 1 < length && text[i + 1] == '\n') {
            ++i;
            continue;
        }
        digit = text[i] - '0';
        if (digit < 0 || digit > 9 || value > (INT_MAX - digit) / 10) return -1;
        value = value * 10 + digit;
        digits = 1;
    }
    if (!digits) return -1;
    *out = value;
    return 0;
}

static int prepare_redirect(const struct csh_ast_redirection *source,
    struct csh_redirect *out, struct csh_error *error)
{
    char *operand = NULL;
    int input = 0;
    switch (source->operator_kind) {
    case CSH_TOKEN_LESS: out->kind = CSH_REDIRECT_READ; input = 1; break;
    case CSH_TOKEN_GREAT: out->kind = CSH_REDIRECT_WRITE; break;
    case CSH_TOKEN_DGREAT: out->kind = CSH_REDIRECT_APPEND; break;
    case CSH_TOKEN_LESS_GREAT: out->kind = CSH_REDIRECT_READ_WRITE; input = 1; break;
    case CSH_TOKEN_CLOBBER: out->kind = CSH_REDIRECT_CLOBBER; break;
    case CSH_TOKEN_LESS_AND: out->kind = CSH_REDIRECT_DUP_READ; input = 1; break;
    case CSH_TOKEN_GREAT_AND: out->kind = CSH_REDIRECT_DUP_WRITE; break;
    case CSH_TOKEN_DLESS:
    case CSH_TOKEN_DLESS_DASH: out->kind = CSH_REDIRECT_HEREDOC; input = 1; break;
    default: return fail(error, "unsupported redirection operator", 0, 2);
    }
    out->fd = input ? STDIN_FILENO : STDOUT_FILENO;
    if (source->has_io_number && descriptor(source->io_number.raw,
        source->io_number.length, &out->fd) == -1)
        return fail(error, "invalid redirection descriptor", 0, 2);
    if (out->kind == CSH_REDIRECT_HEREDOC) {
        size_t i;
        if (source->body == NULL)
            return fail(error, "here-document body has not been collected", 0, 2);
        if (!source->delimiter_quoted)
            for (i = 0; i < source->body_length; ++i)
                if (source->body[i] == '$' || source->body[i] == '`' || source->body[i] == '\\')
                    return fail(error, "here-document expansion is not supported by literal execution", 0, 2);
        out->data = malloc(source->body_length ? source->body_length : 1);
        if (out->data == NULL)
            return fail(error, "cannot allocate here-document body", ENOMEM, 1);
        memcpy(out->data, source->body, source->body_length);
        out->length = source->body_length;
        return 0;
    }
    if (literal(&source->operand, &operand, error) == -1) return -1;
    if (out->kind == CSH_REDIRECT_DUP_READ || out->kind == CSH_REDIRECT_DUP_WRITE) {
        if (strcmp(operand, "-") == 0) out->kind = CSH_REDIRECT_CLOSE;
        else if (descriptor((const unsigned char *)operand, strlen(operand), &out->source_fd) == -1) {
            free(operand);
            return fail(error, "descriptor operand must be digits or '-'", 0, 2);
        }
        free(operand);
    } else out->path = operand;
    return 0;
}

int csh_command_from_ast(const struct csh_ast *tree, struct csh_command *out,
    struct csh_error *error)
{
    size_t i;
    memset(out, 0, sizeof(*out));
    memset(error, 0, sizeof(*error));
    /* The parser wraps even a single command in a list. Do not accidentally
     * execute a prefix of a compound construct which this adapter cannot run. */
    if (tree != NULL && tree->kind == CSH_AST_LIST && tree->redirection_count == 0 &&
        tree->data.list.item_count == 1 &&
        tree->data.list.items[0].separator != CSH_AST_AMPERSAND)
        tree = tree->data.list.items[0].command;
    if (tree == NULL || tree->kind != CSH_AST_SIMPLE)
        return fail(error, "only a single foreground simple command is supported", 0, 2);
    if (tree->data.simple.word_count >= SIZE_MAX / sizeof(*out->argv) ||
        tree->redirection_count > SIZE_MAX / sizeof(*out->redirections) ||
        tree->data.simple.word_count > SIZE_MAX / sizeof(*out->assignments))
        return fail(error, "command is too large", ENOMEM, 1);
    if (tree->data.simple.word_count != 0) {
        out->argv = calloc(tree->data.simple.word_count + 1, sizeof(*out->argv));
        if (out->argv == NULL) goto nomem;
        out->assignments = calloc(tree->data.simple.word_count, sizeof(*out->assignments));
        if (out->assignments == NULL) goto nomem;
    }
    for (i = 0; i < tree->data.simple.word_count; ++i) {
        char *text = NULL;
        if (literal(&tree->data.simple.words[i].word, &text, error) == -1) {
            error->position = tree->data.simple.words[i].word.token.start;
            goto failure;
        }
        if (tree->data.simple.words[i].assignment) {
            char *equals = strchr(text, '=');
            struct csh_assignment *assignment;
            if (equals == NULL) {
                free(text);
                fail(error, "invalid literal assignment", 0, 2);
                goto failure;
            }
            assignment = &out->assignments[out->assignment_count++];
            assignment->name = text;
            assignment->value = malloc(strlen(equals + 1) + 1);
            if (assignment->value != NULL) strcpy(assignment->value, equals + 1);
            *equals = '\0';
            if (assignment->value == NULL) goto nomem;
        } else out->argv[out->argc++] = text;
    }
    if (tree->redirection_count != 0) {
        out->redirections = calloc(tree->redirection_count, sizeof(*out->redirections));
        if (out->redirections == NULL) goto nomem;
    }
    for (i = 0; i < tree->redirection_count; ++i) {
        ++out->redirection_count;
        if (prepare_redirect(tree->redirections[i], &out->redirections[i], error) == -1) {
            error->position = tree->redirections[i]->start;
            goto failure;
        }
    }
    if (csh_redirect_validate(out->redirections, out->redirection_count, error) == -1) goto failure;
    return 0;
nomem:
    fail(error, "cannot allocate command", ENOMEM, 1);
failure:
    csh_command_destroy(out);
    return -1;
}

struct launch {
    char **paths;
    size_t count;
    char **environment;
    char **fallback;
};

static void launch_destroy(struct launch *launch)
{
    size_t i;
    for (i = 0; i < launch->count; ++i) free(launch->paths[i]);
    free(launch->paths);
    free(launch->fallback);
    csh_state_environment_destroy(launch->environment);
}

static int launch_prepare(struct csh_state *state, const struct csh_command *command,
    struct launch *launch, struct csh_error *error)
{
    struct csh_variable_view variable;
    const char *path, *start;
    size_t count = 1, i, name_length = strlen(command->argv[0]);
    int direct = strchr(command->argv[0], '/') != NULL;
    memset(launch, 0, sizeof(*launch));
    csh_state_get_variable(state, "PATH", &variable);
    path = variable.value != NULL ? variable.value : "/bin:/usr/bin";
    if (!direct)
        for (start = path; *start; ++start) if (*start == ':') ++count;
    if (count > SIZE_MAX / sizeof(*launch->paths) ||
        command->argc > SIZE_MAX / sizeof(*launch->fallback) - 2) goto nomem;
    launch->paths = calloc(count, sizeof(*launch->paths));
    launch->fallback = calloc(command->argc + 2, sizeof(*launch->fallback));
    if (launch->paths == NULL || launch->fallback == NULL) goto nomem;
    launch->fallback[0] = (char *)"sh";
    for (i = 1; i < command->argc; ++i) launch->fallback[i + 1] = command->argv[i];
    if (csh_state_environment(state, &launch->environment) != CSH_STATE_OK) goto nomem;
    start = path;
    for (i = 0; i < count; ++i) {
        const char *end = direct ? start : strchr(start, ':');
        size_t component = direct ? 0 : (end != NULL ? (size_t)(end - start) : strlen(start));
        size_t length = direct ? 0 : (component != 0 ? component + 1 : 2);
        char *candidate;
        if (name_length > SIZE_MAX - 3 || length > SIZE_MAX - name_length - 3) goto nomem;
        candidate = malloc(length + name_length + 3);
        if (candidate == NULL) goto nomem;
        if (!direct) {
            if (component != 0) memcpy(candidate, start, component);
            else candidate[0] = '.';
            candidate[length - 1] = '/';
        }
        memcpy(candidate + length, command->argv[0], name_length + 1);
        /* Relative PATH directories and direct relative operands can also
         * start with '-'. Keep the fallback shell's file operand unambiguous. */
        if (candidate[0] == '-') {
            memmove(candidate + 2, candidate, length + name_length + 1);
            candidate[0] = '.';
            candidate[1] = '/';
        }
        launch->paths[launch->count++] = candidate;
        if (end != NULL) start = end + 1;
    }
    return 0;
nomem:
    launch_destroy(launch);
    return fail(error, "cannot prepare external command", ENOMEM, 1);
}

static void diagnose(const char *name, const char *message, int number)
{
    if (number) dprintf(STDERR_FILENO, "cshell: %s: %s: %s\n", name, message, strerror(number));
    else dprintf(STDERR_FILENO, "cshell: %s: %s\n", name, message);
}

/* This routine is called only after fork. Every route terminates with exec
 * or _exit, never by returning to the caller's input loop. */
static void launch_child(const struct csh_command *command, struct launch *launch)
{
    struct csh_redirect_save *save = NULL;
    struct csh_error error;
    size_t i;
    int remembered = 0;
    if (csh_redirect_apply(command->redirections, command->redirection_count, &save, &error) == -1) {
        diagnose(command->argv[0], error.message, error.system_errno);
        _exit(error.status);
    }
    if (command->argv[0][0] == '\0') {
        diagnose("", "command not found", 0);
        _exit(127);
    }
    for (i = 0; i < launch->count; ++i) {
        int number;
        execve(launch->paths[i], command->argv, launch->environment);
        number = errno;
        if (number == ENOEXEC) {
            launch->fallback[1] = launch->paths[i];
            execve("/bin/sh", launch->fallback, launch->environment);
            diagnose(command->argv[0], "cannot execute command interpreter", errno);
            _exit(126);
        }
        if (number != ENOENT && number != ENOTDIR) remembered = number;
        else {
            struct stat information;
            /* ENOENT can mean a present script has a missing #! interpreter.
             * Continue PATH search, but retain found/unexecutable status. */
            if (stat(launch->paths[i], &information) == 0) remembered = number;
        }
    }
    diagnose(command->argv[0], remembered ? "cannot execute" : "command not found", remembered);
    _exit(remembered ? 126 : 127);
}

static void builtin_exit(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result)
{
    struct csh_state_info info;
    size_t first = 1;
    csh_state_get_info(state, &info);
    result->status = info.last_status;
    if (first < command->argc && strcmp(command->argv[first], "--") == 0) ++first;
    if (command->argc - first > 1) {
        diagnose("exit", "too many arguments", 0);
        result->status = 2;
        result->exit_requested = !(info.options & CSH_OPT_INTERACTIVE);
        return;
    }
    if (command->argc > first) {
        char *end;
        const char *operand = command->argv[first], *digits = operand;
        long value;
        if (*digits == '+' || *digits == '-') ++digits;
        while (*digits >= '0' && *digits <= '9') ++digits;
        errno = 0;
        value = strtol(operand, &end, 10);
        if (errno == ERANGE || end == operand || *end != '\0' || *digits != '\0') {
            diagnose("exit", "numeric status required", 0);
            result->status = 2;
            result->exit_requested = !(info.options & CSH_OPT_INTERACTIVE);
            return;
        }
        result->status = (int)((unsigned long)value & 255u);
    }
    result->exit_requested = 1;
}

/* Validate the entire prefix before any mutations or filesystem effects.
 * The selective save also makes allocation failures during a batch atomic. */
static int assignments_apply(struct csh_state *state,
    const struct csh_command *command, enum csh_execution_category category,
    struct csh_variable_save **save, struct csh_execution *result,
    struct csh_error *error)
{
    struct csh_state_info info;
    const char **names;
    size_t i;
    int temporary = category == CSH_EXEC_EXTERNAL ||
        category == CSH_EXEC_REGULAR_BUILTIN || category == CSH_EXEC_FUNCTION;
    enum csh_state_result status;
    if (command->assignment_count == 0) return 0;
    if (command->assignments == NULL)
        return fail(error, "invalid assignment vector", 0, 2);
    csh_state_get_info(state, &info);
    for (i = 0; i < command->assignment_count; ++i) {
        struct csh_variable_view view;
        const struct csh_assignment *assignment = &command->assignments[i];
        if (assignment->value == NULL || csh_state_get_variable(state,
            assignment->name, &view) != CSH_STATE_OK)
            return fail(error, "invalid assignment name or value", 0, 2);
        if (view.attributes & CSH_VAR_READONLY) {
            result->exit_requested = !(info.options & CSH_OPT_INTERACTIVE);
            return fail(error, "cannot assign to readonly variable", 0, 1);
        }
    }
    if (command->assignment_count > SIZE_MAX / sizeof(*names))
        return fail(error, "too many assignments", ENOMEM, 1);
    names = malloc(command->assignment_count * sizeof(*names));
    if (names == NULL) return fail(error, "cannot save assignment variables", ENOMEM, 1);
    for (i = 0; i < command->assignment_count; ++i)
        names[i] = command->assignments[i].name;
    status = csh_state_save_variables(state, command->assignment_count, names, save);
    free(names);
    if (status != CSH_STATE_OK)
        return fail(error, "cannot save assignment variables", ENOMEM, 1);
    for (i = 0; i < command->assignment_count; ++i) {
        const struct csh_assignment *assignment = &command->assignments[i];
        status = csh_state_set_variable(state, assignment->name, assignment->value);
        if (status == CSH_STATE_OK && (temporary || (info.options & CSH_OPT_ALLEXPORT)))
            status = csh_state_update_attributes(state, assignment->name, CSH_VAR_EXPORT, 0);
        if (status != CSH_STATE_OK) {
            csh_state_restore_variables(state, save);
            return fail(error, "cannot apply assignment variables", ENOMEM, 1);
        }
    }
    if (!temporary) {
        csh_state_variable_save_destroy(*save);
        *save = NULL;
    }
    return 0;
}

static int command_validate(struct csh_state *state,
    const struct csh_command *command, enum csh_execution_category *category,
    struct csh_error *error)
{
    size_t i;
    if (state == NULL || command == NULL)
        return fail(error, "invalid execution input", 0, 2);
    if (command->argc != 0 && command->argv == NULL)
        return fail(error, "invalid command argument vector", 0, 2);
    for (i = 0; i < command->argc; ++i)
        if (command->argv[i] == NULL)
            return fail(error, "invalid command argument", 0, 2);
    if (command->argc != 0 && command->argv[command->argc] != NULL)
        return fail(error, "command argument vector is not terminated", 0, 2);
    if (command->assignment_count != 0 && command->assignments == NULL)
        return fail(error, "invalid assignment vector", 0, 2);
    for (i = 0; i < command->assignment_count; ++i) {
        struct csh_variable_view view;
        if (command->assignments[i].value == NULL ||
            csh_state_get_variable(state, command->assignments[i].name,
                &view) != CSH_STATE_OK)
            return fail(error, "invalid assignment name or value", 0, 2);
    }
    if (csh_redirect_validate(command->redirections,
        command->redirection_count, error) == -1) return -1;
    if (command->argc == 0) *category = CSH_EXEC_EMPTY;
    else if (strcmp(command->argv[0], "exit") == 0)
        *category = CSH_EXEC_SPECIAL_BUILTIN;
    else *category = csh_state_builtin_category(command->argv[0]);
    return 0;
}

static int child_status(int status)
{
    return WIFEXITED(status) ? WEXITSTATUS(status) :
        WIFSIGNALED(status) ? 128 + WTERMSIG(status) : 1;
}

static int execute_resolved(struct csh_state *state,
    const struct csh_command *command,
    enum csh_execution_category category, csh_command_handler handler,
    void *context, struct csh_execution *result,
    struct csh_pipeline_stage *stage, struct csh_error *error)
{
    struct csh_redirect_save *save = NULL;
    struct csh_variable_save *variables = NULL;
    size_t i;
    int rc = -1;
    memset(result, 0, sizeof(*result));
    memset(error, 0, sizeof(*error));
    if (state == NULL || command == NULL) {
        fail(error, "invalid execution input", 0, 2);
        goto done;
    }
    if (command->argc != 0 && command->argv == NULL) {
        fail(error, "invalid command argument vector", 0, 2);
        goto done;
    }
    for (i = 0; i < command->argc; ++i)
        if (command->argv[i] == NULL) {
            fail(error, "invalid command argument", 0, 2);
            goto done;
        }
    if (command->argc != 0 && command->argv[command->argc] != NULL) {
        fail(error, "command argument vector is not terminated", 0, 2);
        goto done;
    }
    if (csh_redirect_validate(command->redirections, command->redirection_count, error) == -1) goto done;
    if (category < CSH_EXEC_EMPTY || category > CSH_EXEC_FUNCTION ||
        (category == CSH_EXEC_EMPTY) != (command->argc == 0) ||
        ((category == CSH_EXEC_EMPTY || category == CSH_EXEC_EXTERNAL) ?
            handler != NULL : handler == NULL)) {
        fail(error, "invalid resolved command category or handler", 0, 2);
        goto done;
    }
    result->category = category;
    if (assignments_apply(state, command, category, &variables, result, error) == -1)
        goto done;
    if (result->category == CSH_EXEC_EXTERNAL) {
        struct launch launch;
        pid_t child, waited;
        int status;
        if (launch_prepare(state, command, &launch, error) == -1) goto done;
        csh_state_restore_variables(state, &variables);
        child = fork();
        if (child == -1) {
            int number = errno;
            launch_destroy(&launch);
            fail(error, "cannot fork command", number, 1);
            goto done;
        }
        if (child == 0) launch_child(command, &launch);
        if (stage != NULL) stage->pid = child;
        do { waited = waitpid(child, &status, 0); } while (waited == -1 && errno == EINTR);
        if (waited == -1) {
            int number = errno;
            launch_destroy(&launch);
            fail(error, "cannot wait for command", number, 1);
            goto done;
        }
        launch_destroy(&launch);
        result->status = child_status(status);
        if (stage != NULL) {
            stage->reaped = 1;
            stage->wait_status = status;
        }
        rc = 0;
    } else {
        struct csh_error restore_error;
        if (csh_redirect_apply(command->redirections, command->redirection_count, &save, error) == -1) goto done;
        rc = handler == NULL ? 0 : handler(state, command, result, error, context);
        if (csh_redirect_restore(&save, &restore_error) == -1) {
            *error = restore_error;
            rc = -1;
            result->exit_requested = 0;
            goto done;
        }
    }
done:
    csh_state_restore_variables(state, &variables);
    if (rc == -1) result->status = error->status;
    if (result->category == CSH_EXEC_SPECIAL_BUILTIN && result->status != 0 && !result->exit_requested)
        result->special_builtin_error = 1;
    if (state != NULL) csh_state_set_status(state, result->status);
    return rc;
}

int csh_execute_resolved(struct csh_state *state,
    const struct csh_command *command,
    enum csh_execution_category category, csh_command_handler handler,
    void *context, struct csh_execution *result, struct csh_error *error)
{
    return execute_resolved(state, command, category, handler, context,
        result, NULL, error);
}

static int bootstrap_handler(struct csh_state *state,
    const struct csh_command *command, struct csh_execution *result,
    struct csh_error *error, void *context)
{
    (void)error;
    (void)context;
    if (strcmp(command->argv[0], "exit") == 0)
        builtin_exit(state, command, result);
    else
        result->status = csh_state_builtin_run(state, command->argc,
            command->argv);
    return 0;
}

int csh_execute_command(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result, struct csh_error *error)
{
    enum csh_execution_category category = CSH_EXEC_EMPTY;
    csh_command_handler handler = NULL;
    if (command != NULL && command->argc != 0 && command->argv != NULL &&
        command->argv[0] != NULL) {
        if (strcmp(command->argv[0], "exit") == 0)
            category = CSH_EXEC_SPECIAL_BUILTIN;
        else category = csh_state_builtin_category(command->argv[0]);
        if (category != CSH_EXEC_EXTERNAL) handler = bootstrap_handler;
    }
    return execute_resolved(state, command, category, handler, NULL,
        result, NULL, error);
}

void csh_pipeline_result_destroy(struct csh_pipeline_result *result)
{
    if (result == NULL) return;
    free(result->stages);
    memset(result, 0, sizeof(*result));
}

/* Like redirection close, this requires serialized descriptor mutation. */
static void pipe_close(int fd)
{
    if (fd >= 0) while (close(fd) == -1 && errno == EINTR) {}
}

/* Keep pipes off standard descriptors even when those descriptors were closed
 * by the caller. Children close every private end before applying redirects,
 * so a closed user dup operand can never refer to a private pipe. */
static int pipeline_pipe(int ends[2])
{
    int i, number;
    if (pipe(ends) == -1) return -1;
    for (i = 0; i < 2; ++i) {
        int moved;
        if (ends[i] < 3) {
            do { moved = fcntl(ends[i], F_DUPFD_CLOEXEC, 3); }
            while (moved == -1 && errno == EINTR);
            if (moved == -1) goto failure;
            pipe_close(ends[i]);
            ends[i] = moved;
        } else {
            do { moved = fcntl(ends[i], F_SETFD, FD_CLOEXEC); }
            while (moved == -1 && errno == EINTR);
            if (moved == -1) goto failure;
        }
    }
    return 0;
failure:
    number = errno;
    pipe_close(ends[0]);
    pipe_close(ends[1]);
    ends[0] = ends[1] = -1;
    errno = number;
    return -1;
}

static int pipeline_connect(int source, int target)
{
    int rc;
    if (source < 0) return 0;
    do { rc = dup2(source, target); } while (rc == -1 && errno == EINTR);
    return rc;
}

static int stage_wait(struct csh_pipeline_stage *stage)
{
    pid_t waited;
    int status;
    do { waited = waitpid(stage->pid, &status, 0); }
    while (waited == -1 && errno == EINTR);
    if (waited == -1) return -1;
    stage->wait_status = status;
    stage->status = child_status(status);
    stage->reaped = stage->completed = 1;
    return 0;
}

static void pipeline_cancel(struct csh_pipeline_result *result)
{
    size_t i;
    /* Close parent pipes before this call; kill all before waiting for any.
     * SIGKILL bounds cleanup even when a stage ignores TERM or never uses its
     * pipe. These are our direct, unreaped children, never process groups. */
    for (i = 0; i < result->count; ++i) {
        struct csh_pipeline_stage *stage = &result->stages[i];
        if (stage->pid > 0 && !stage->reaped) kill(stage->pid, SIGKILL);
    }
    for (i = 0; i < result->count; ++i) {
        struct csh_pipeline_stage *stage = &result->stages[i];
        if (stage->pid > 0 && !stage->reaped) stage_wait(stage);
    }
}

static void pipeline_child(struct csh_state *state,
    const struct csh_command *command, struct launch *launch,
    enum csh_execution_category category, int previous, int ends[2])
{
    struct csh_execution result;
    struct csh_error error;
    if (pipeline_connect(previous, STDIN_FILENO) == -1 ||
        pipeline_connect(ends[1], STDOUT_FILENO) == -1) {
        diagnose("pipeline", "cannot connect pipe", errno);
        _exit(1);
    }
    pipe_close(previous);
    pipe_close(ends[0]);
    pipe_close(ends[1]);
    /* Explicit redirections override the pipe connections. External commands
     * exec directly in this child; no wrapper/grandchild obscures ownership. */
    if (category == CSH_EXEC_EXTERNAL) launch_child(command, launch);
    if (csh_execute_command(state, command, &result, &error) == -1)
        diagnose("pipeline", error.message, error.system_errno);
    _exit(result.status);
}

static int pipeline_launch_prepare(struct csh_state *state,
    const struct csh_command *command, struct launch *launch,
    struct csh_error *error)
{
    struct csh_variable_save *variables = NULL;
    struct csh_execution result = {0};
    int rc;
    if (assignments_apply(state, command, CSH_EXEC_EXTERNAL, &variables,
        &result, error) == -1) return -1;
    rc = launch_prepare(state, command, launch, error);
    csh_state_restore_variables(state, &variables);
    return rc;
}

int csh_execute_pipeline(struct csh_state *state,
    const struct csh_command *commands, size_t count, int negated,
    struct csh_pipeline_result *out, struct csh_error *error)
{
    struct launch *launches = NULL;
    size_t i;
    int previous = -1, ends[2] = {-1, -1}, rc = -1;
    memset(out, 0, sizeof(*out));
    memset(error, 0, sizeof(*error));
    out->execution.category = CSH_EXEC_PIPELINE;
    if (state == NULL || commands == NULL || count == 0) {
        fail(error, "invalid pipeline input", 0, 2);
        goto done;
    }
    if (count > SIZE_MAX / sizeof(*out->stages) ||
        count > SIZE_MAX / sizeof(*launches)) {
        fail(error, "pipeline is too large", ENOMEM, 1);
        goto done;
    }
    out->stages = calloc(count, sizeof(*out->stages));
    if (out->stages == NULL) {
        fail(error, "cannot allocate pipeline stages", ENOMEM, 1);
        goto done;
    }
    out->count = count;
    for (i = 0; i < count; ++i)
        if (command_validate(state, &commands[i], &out->stages[i].category, error) == -1)
            goto done;
    if (count == 1) {
        enum csh_execution_category category = out->stages[0].category;
        csh_command_handler handler = category == CSH_EXEC_EMPTY ||
            category == CSH_EXEC_EXTERNAL ? NULL : bootstrap_handler;
        rc = execute_resolved(state, commands, category, handler, NULL,
            &out->execution, out->stages, error);
        out->stages[0].status = out->execution.status;
        out->stages[0].completed = rc == 0;
        if (rc == -1) pipeline_cancel(out);
        goto done;
    }
    launches = calloc(count, sizeof(*launches));
    if (launches == NULL) {
        fail(error, "cannot allocate pipeline launches", ENOMEM, 1);
        goto done;
    }
    /* All preparation completes before the first child or filesystem effect. */
    for (i = 0; i < count; ++i) {
        if (out->stages[i].category == CSH_EXEC_EXTERNAL &&
            pipeline_launch_prepare(state, &commands[i], &launches[i],
                error) == -1) {
            /* launch_prepare already destroyed the failed entry. */
            memset(&launches[i], 0, sizeof(launches[i]));
            goto done;
        }
    }
    for (i = 0; i < count; ++i) {
        pid_t child;
        if (i + 1 < count && pipeline_pipe(ends) == -1) {
            fail(error, "cannot create pipeline pipe", errno, 1);
            goto cancel;
        }
        child = fork();
        if (child == -1) {
            fail(error, "cannot fork pipeline stage", errno, 1);
            goto cancel;
        }
        if (child == 0)
            pipeline_child(state, &commands[i], &launches[i],
                out->stages[i].category, previous, ends);
        out->stages[i].pid = child;
        pipe_close(previous);
        pipe_close(ends[1]);
        previous = ends[0];
        ends[0] = ends[1] = -1;
    }
    /* The last launch closes previous, leaving no pipe end in the parent. */
    for (i = 0; i < count; ++i) {
        if (stage_wait(&out->stages[i]) == -1) {
            fail(error, "cannot wait for pipeline stage", errno, 1);
            goto cancel;
        }
    }
    out->execution.status = out->stages[count - 1].status;
    rc = 0;
    goto done;
cancel:
    pipe_close(previous);
    pipe_close(ends[0]);
    pipe_close(ends[1]);
    pipeline_cancel(out);
done:
    if (launches != NULL) {
        for (i = 0; i < count; ++i) launch_destroy(&launches[i]);
        free(launches);
    }
    if (rc == -1) out->execution.status = error->status;
    else if (negated && !out->execution.exit_requested)
        out->execution.status = out->execution.status == 0 ? 1 : 0;
    if (state != NULL) csh_state_set_status(state, out->execution.status);
    return rc;
}

int csh_execute_pipeline_ast(struct csh_state *state, const struct csh_ast *tree,
    struct csh_pipeline_result *out, struct csh_error *error)
{
    struct csh_command *commands = NULL;
    size_t i, count = 1;
    int negated = 0, rc = -1;
    memset(out, 0, sizeof(*out));
    memset(error, 0, sizeof(*error));
    out->execution.category = CSH_EXEC_PIPELINE;
    if (tree != NULL && tree->kind == CSH_AST_LIST && tree->redirection_count == 0 &&
        tree->data.list.item_count == 1 &&
        tree->data.list.items[0].separator != CSH_AST_AMPERSAND)
        tree = tree->data.list.items[0].command;
    if (tree != NULL && tree->kind == CSH_AST_PIPELINE && tree->redirection_count == 0) {
        count = tree->data.pipeline.command_count;
        negated = tree->data.pipeline.negated;
        if (count == 0 || tree->data.pipeline.commands == NULL) {
            fail(error, "invalid pipeline AST", 0, 2);
            goto done;
        }
    } else if (tree == NULL || tree->kind != CSH_AST_SIMPLE) {
        fail(error, "only a foreground simple command or pipeline is supported", 0, 2);
        goto done;
    }
    if (count > SIZE_MAX / sizeof(*commands) ||
        (commands = calloc(count, sizeof(*commands))) == NULL) {
        fail(error, "cannot allocate pipeline commands", ENOMEM, 1);
        goto done;
    }
    for (i = 0; i < count; ++i) {
        const struct csh_ast *stage = tree->kind == CSH_AST_PIPELINE ?
            tree->data.pipeline.commands[i] : tree;
        /* No nested compound/list adapter shortcuts inside a stage. */
        if (stage == NULL || stage->kind != CSH_AST_SIMPLE) {
            fail(error, "only simple pipeline stages are supported", 0, 2);
            goto done;
        }
        if (csh_command_from_ast(stage, &commands[i], error) == -1) goto done;
    }
    rc = csh_execute_pipeline(state, commands, count, negated, out, error);
done:
    if (commands != NULL) {
        for (i = 0; i < count; ++i) csh_command_destroy(&commands[i]);
        free(commands);
    }
    if (rc == -1) {
        out->execution.status = error->status;
        if (state != NULL) csh_state_set_status(state, out->execution.status);
    }
    return rc;
}

int csh_execute_ast(struct csh_state *state, const struct csh_ast *tree,
    struct csh_execution *result, struct csh_error *error)
{
    struct csh_pipeline_result pipeline = {0};
    int rc = csh_execute_pipeline_ast(state, tree, &pipeline, error);
    *result = pipeline.execution;
    csh_pipeline_result_destroy(&pipeline);
    return rc;
}
