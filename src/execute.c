#include "cshell/execute.h"
#include "prepare.h"
#include "cshell/builtin.h"
#include "cshell/jobs.h"
#include "cshell/traps.h"
#include "cshell/parser.h"
#include "cshell/alias.h"
#include "cshell/output.h"

#include <errno.h>
#include <fcntl.h>
#include <fnmatch.h>
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
    memset(launch, 0, sizeof(*launch));
}

static int launch_prepare(struct csh_state *state, const struct csh_command *command,
    struct launch *launch, struct csh_error *error)
{
    struct csh_variable_view variable;
    const char *path, *start, *prefix_path = NULL;
    char *standard = NULL;
    size_t count = 1, i, name_length = strlen(command->argv[0]);
    int direct = strchr(command->argv[0], '/') != NULL;
    memset(launch, 0, sizeof(*launch));
    csh_state_get_variable(state, "PATH", &variable);
    if (command->default_path) {
        size_t length = confstr(_CS_PATH, NULL, 0);
        if (!length || !(standard = malloc(length))) goto nomem;
        if (!confstr(_CS_PATH, standard, length)) goto nomem;
    }
    /* Prefixes are already expanded. The last PATH value also controls
     * category lookup before the command's assignment scope is installed. */
    for (i = 0; i < command->assignment_count; ++i)
        if (!strcmp(command->assignments[i].name, "PATH"))
            prefix_path = command->assignments[i].value;
    path = standard ? standard : prefix_path ? prefix_path :
        variable.value != NULL ? variable.value : "/bin:/usr/bin";
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
    if (!direct && !command->default_path && prefix_path == NULL) {
        const char *cached = csh_state_hash_get(state, command->argv[0]);
        struct stat st;
        if (cached && stat(cached, &st) == 0 && S_ISREG(st.st_mode) && access(cached, X_OK) == 0) {
            char *copy = strdup(cached);
            if (!copy) goto nomem;
            for (i = 0; i < launch->count; ++i) free(launch->paths[i]);
            launch->paths[0] = copy; launch->count = 1;
        }
    }
    free(standard);
    return 0;
nomem:
    free(standard);
    launch_destroy(launch);
    return fail(error, "cannot prepare external command", ENOMEM, 1);
}

static void diagnose(const char *name, const char *message, int number)
{
    if (number) dprintf(STDERR_FILENO, "cshell: %s: %s: %s\n", name, message, strerror(number));
    else dprintf(STDERR_FILENO, "cshell: %s: %s\n", name, message);
}

/* Return only when every exec attempt failed; caller decides whether to exit. */
static int launch_replace(const struct csh_command *command, struct launch *launch)
{
    size_t i;
    int remembered = 0;
    if (command->argv[0][0] == '\0') {
        diagnose("", "command not found", 0);
        return 127;
    }
    for (i = 0; i < launch->count; ++i) {
        int number;
        execve(launch->paths[i], command->argv, launch->environment);
        number = errno;
        if (number == ENOEXEC) {
            launch->fallback[1] = launch->paths[i];
            execve("/bin/sh", launch->fallback, launch->environment);
            diagnose(command->argv[0], "cannot execute command interpreter", errno);
            return 126;
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
    return remembered ? 126 : 127;
}

static void launch_child(const struct csh_command *command, struct launch *launch)
{
    struct csh_redirect_save *save = NULL;
    struct csh_error error;
    if (csh_jobs_active() != NULL) csh_jobs_after_fork(csh_jobs_active(), 0);
    csh_traps_exec_signals(csh_traps_active(), 0);
    if (csh_redirect_apply(command->redirections, command->redirection_count, &save, &error) == -1) {
        diagnose(command->argv[0], error.message, error.system_errno);
        _exit(error.status);
    }
    _exit(launch_replace(command, launch));
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

static int control_name(const char *name)
{
    return !strcmp(name, "break") || !strcmp(name, "continue") || !strcmp(name, "return");
}

static int special_name(const char *name)
{
    static const char *const names[] = {":", ".", "break", "continue", "eval",
        "exec", "exit", "export", "readonly", "return", "set", "shift",
        "times", "trap", "unset"};
    size_t i;
    for (i = 0; i < sizeof(names) / sizeof(names[0]); ++i)
        if (!strcmp(name, names[i])) return 1;
    return 0;
}

static char *lookup_path(struct csh_state *state, const char *name, int defaults,
    int readable, const struct csh_command *prefix, struct csh_error *error);

static enum csh_execution_category path_builtin_category(struct csh_state *state,
    const char *name, int defaults, const struct csh_command *prefix)
{
    enum csh_execution_category category = csh_state_builtin_category(name);
    if (!strcmp(name, "pwd")) {
        struct csh_error error;
        char *path = lookup_path(state, name, defaults, 0, prefix, &error);
        if (!path || (strcmp(path, "/bin/pwd") && strcmp(path, "/usr/bin/pwd"))) category = CSH_EXEC_EXTERNAL;
        free(path);
    }
    return category;
}

static enum csh_execution_category command_category(struct csh_state *state,
    const char *name, const struct csh_command *prefix)
{
    enum csh_execution_category category = path_builtin_category(state, name, 0, prefix);
    if (!strcmp(name, "exit") || !strcmp(name, "trap") || control_name(name))
        return CSH_EXEC_SPECIAL_BUILTIN;
    if (category != CSH_EXEC_SPECIAL_BUILTIN && csh_state_function(state, name) != NULL)
        return CSH_EXEC_FUNCTION;
    return category;
}

static void report_error(struct csh_error *error);

static int evaluation_handler(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result, struct csh_error *error, void *context);

static int flow_handler(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result, struct csh_error *error, void *context);

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
    else *category = command_category(state, command->argv[0], command);
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
            if (number != ECHILD) {
                kill(child, SIGKILL);
                do { waited = waitpid(child, &status, 0); } while (waited == -1 && errno == EINTR);
                if (waited == child && stage != NULL) {
                    stage->reaped = stage->completed = 1;
                    stage->status = child_status(status);
                    stage->wait_status = status;
                }
            }
            launch_destroy(&launch);
            fail(error, "cannot wait for command", number, 1);
            goto done;
        }
        launch_destroy(&launch);
        result->status = child_status(status);
        if (stage != NULL) {
            stage->reaped = stage->completed = 1;
            stage->status = result->status;
            stage->wait_status = status;
        }
        rc = 0;
    } else {
        struct csh_error restore_error;
        if (csh_redirect_apply(command->redirections, command->redirection_count, &save, error) == -1) {
            result->redirection_failed = 1;
            goto done;
        }
        if (handler == NULL) result->status = command->substitution_status;
        rc = handler == NULL ? 0 : handler(state, command, result, error, context);
        if (result->retain_redirects) csh_redirect_commit(&save);
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
    if (result->category == CSH_EXEC_SPECIAL_BUILTIN && result->status != 0 && !result->exit_requested &&
        result->control == CSH_CONTROL_NONE &&
        (rc == -1 || (strcmp(command->argv[0], "eval") && strcmp(command->argv[0], ".") &&
                       strcmp(command->argv[0], "trap"))))
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
    if (control_name(command->argv[0]) || result->category == CSH_EXEC_FUNCTION)
        return flow_handler(state, command, result, error, context);
    if (!strcmp(command->argv[0], ".") || !strcmp(command->argv[0], "eval") ||
        !strcmp(command->argv[0], "exec") || !strcmp(command->argv[0], "command") ||
        !strcmp(command->argv[0], "type") || !strcmp(command->argv[0], "hash") ||
        !strcmp(command->argv[0], "alias") || !strcmp(command->argv[0], "unalias"))
    {
        int rc = evaluation_handler(state, command, result, error, context);
        if (rc == -1) {
            result->status = error->status;
            if (!error->reported) report_error(error);
            if (result->category == CSH_EXEC_SPECIAL_BUILTIN) result->special_builtin_error = 1;
            return 0;
        }
        return rc;
    }
    if (!strcmp(command->argv[0], "read") || !strcmp(command->argv[0], "getopts") ||
        !strcmp(command->argv[0], "umask") || !strcmp(command->argv[0], "ulimit") ||
        !strcmp(command->argv[0], "times")) {
        result->status = csh_utility_run(state, command->argc, command->argv);
        return 0;
    }
    if (!strcmp(command->argv[0], "trap")) {
        struct csh_execution_context *shell = context;
        result->status = csh_traps_builtin(shell ? shell->traps : csh_traps_active(),
            command->argc, command->argv);
        return 0;
    }
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
    if (command_validate(state, command, &category, error) == -1) {
        memset(result, 0, sizeof(*result));
        result->status = error->status;
        if (state != NULL) csh_state_set_status(state, result->status);
        return -1;
    }
    if (category != CSH_EXEC_EMPTY && category != CSH_EXEC_EXTERNAL)
        handler = bootstrap_handler;
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
    if (csh_jobs_active() != NULL) csh_jobs_after_fork(csh_jobs_active(), 0);
    if (category == CSH_EXEC_EXTERNAL) csh_traps_exec_signals(csh_traps_active(), 0);
    else csh_traps_after_fork(csh_traps_active(), 0, 0);
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
    struct csh_state_info initial = {0};
    if (state != NULL) csh_state_get_info(state, &initial);
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
        if (!out->stages[0].reaped) out->stages[0].status = out->execution.status;
        out->stages[0].completed = out->stages[0].reaped || rc == 0;
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
    if (initial.options & CSH_OPT_PIPEFAIL)
        for (i = 0; i < count; ++i)
            if (out->stages[i].status) out->execution.status = out->stages[i].status;
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
    else if (negated && !out->execution.exit_requested && out->execution.control == CSH_CONTROL_NONE)
        out->execution.status = out->execution.status == 0 ? 1 : 0;
    if (state != NULL) csh_state_set_status(state, out->execution.status);
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

/* The context layer owns composition and asynchronous children; ordinary
 * commands and simple pipelines retain the same dispatch/assignment engine. */
struct csh_background_child {
    pid_t pid;
    struct csh_background_child *next;
};

struct execution_plan {
    enum csh_ast_kind kind;
    const struct csh_ast *tree; /* Borrowed; expansion occurs only at execution. */
    struct execution_plan *children;
    size_t count;
    int negated;
    int asynchronous;
};

struct descriptor_reservations {
    int *items;
    size_t count;
};

static void plan_destroy(struct execution_plan *plan)
{
    size_t i;
    for (i = 0; i < plan->count; ++i) plan_destroy(&plan->children[i]);
    free(plan->children);
    memset(plan, 0, sizeof(*plan));
}

static int plan_prepare(const struct csh_ast *tree, struct execution_plan *plan,
    struct descriptor_reservations *reserved, unsigned depth,
    struct csh_error *error)
{
    size_t i, count = 0;
    if (tree == NULL || depth > 256)
        return fail(error, "invalid or excessively nested execution tree", 0, 2);
    plan->kind = tree->kind;
    plan->tree = tree;
    switch (tree->kind) {
    case CSH_AST_SIMPLE:
        break;
    case CSH_AST_IF:
        count = tree->data.if_clause.branch_count * 2 + (tree->data.if_clause.else_body != NULL);
        break;
    case CSH_AST_FOR: case CSH_AST_FUNCTION: count = 1; break;
    case CSH_AST_WHILE: case CSH_AST_UNTIL: count = 2; break;
    case CSH_AST_CASE: count = tree->data.case_clause.item_count; break;
    case CSH_AST_LIST: count = tree->data.list.item_count; break;
    case CSH_AST_AND: case CSH_AST_OR: count = 2; break;
    case CSH_AST_BRACE: case CSH_AST_SUBSHELL:
        count = 1;
        break;
    case CSH_AST_PIPELINE:
        count = tree->data.pipeline.command_count;
        plan->negated = tree->data.pipeline.negated;
        if (count == 0) return fail(error, "invalid pipeline AST", 0, 2);
        break;
    default:
        return fail(error, "unsupported compound command", 0, 2);
    }
    if (tree->redirection_count && tree->kind != CSH_AST_SIMPLE &&
        tree->kind != CSH_AST_BRACE && tree->kind != CSH_AST_SUBSHELL &&
        tree->kind < CSH_AST_IF)
        return fail(error, "invalid compound redirections", 0, 2);
    for (i = 0; i < tree->redirection_count; ++i) {
        const struct csh_ast_redirection *r = tree->redirections[i];
        int *replacement, fd;
        if (r->has_io_number && csh_descriptor(r->io_number.raw, r->io_number.length, &fd) == -1)
            return fail(error, "invalid redirection descriptor", 0, 2);
        if (reserved->count > SIZE_MAX / sizeof(int) - 2)
            return fail(error, "too many descriptor operands", ENOMEM, 1);
        replacement = realloc(reserved->items, (reserved->count + 2) * sizeof(int));
        if (replacement == NULL)
            return fail(error, "cannot reserve descriptor operands", ENOMEM, 1);
        reserved->items = replacement;
        if (r->has_io_number) reserved->items[reserved->count++] = fd;
        if ((r->operator_kind == CSH_TOKEN_LESS_AND || r->operator_kind == CSH_TOKEN_GREAT_AND) &&
            csh_descriptor(r->operand.token.raw, r->operand.token.length, &fd) == 0)
            reserved->items[reserved->count++] = fd;
    }
    if (count == 0) return 0;
    if (count > SIZE_MAX / sizeof(*plan->children) ||
        (plan->children = calloc(count, sizeof(*plan->children))) == NULL)
        return fail(error, "cannot allocate execution plan", ENOMEM, 1);
    plan->count = count;
    for (i = 0; i < count; ++i) {
        const struct csh_ast *child;
        switch (tree->kind) {
        case CSH_AST_LIST:
            child = tree->data.list.items[i].command;
            plan->children[i].asynchronous =
                tree->data.list.items[i].separator == CSH_AST_AMPERSAND;
            break;
        case CSH_AST_PIPELINE: child = tree->data.pipeline.commands[i]; break;
        case CSH_AST_AND: case CSH_AST_OR:
            child = i == 0 ? tree->data.binary.left : tree->data.binary.right;
            break;
        case CSH_AST_IF:
            child = i == tree->data.if_clause.branch_count * 2 ? tree->data.if_clause.else_body :
                i % 2 ? tree->data.if_clause.branches[i / 2].body :
                tree->data.if_clause.branches[i / 2].condition;
            break;
        case CSH_AST_FOR: child = tree->data.for_clause.body; break;
        case CSH_AST_FUNCTION: child = tree->data.function.body; break;
        case CSH_AST_WHILE: case CSH_AST_UNTIL:
            child = i == 0 ? tree->data.loop.condition : tree->data.loop.body; break;
        case CSH_AST_CASE: child = tree->data.case_clause.items[i].body; break;
        default: child = tree->data.group.body; break;
        }
        if (plan_prepare(child, &plan->children[i], reserved, depth + 1, error) == -1)
            return -1;
    }
    return 0;
}

int csh_execution_context_reap(struct csh_execution_context *context, int wait,
    struct csh_error *error)
{
    struct csh_background_child **link = &context->children;
    if (context->jobs != NULL && csh_jobs_reap(context->jobs, wait) == -1)
        return fail(error, "cannot collect job status", errno, 1);
    memset(error, 0, sizeof(*error));
    while (*link != NULL) {
        struct csh_background_child *child = *link;
        int status;
        pid_t waited;
        do { waited = waitpid(child->pid, &status, wait ? 0 : WNOHANG); }
        while (waited == -1 && errno == EINTR);
        if (waited == -1)
            return fail(error, "cannot reap background child", errno, 1);
        if (waited == 0) link = &child->next;
        else {
            *link = child->next;
            free(child);
            --context->child_count;
        }
    }
    return 0;
}

void csh_execution_context_destroy(struct csh_execution_context *context)
{
    struct csh_error ignored;
    if (context == NULL) return;
    csh_execution_context_reap(context, 0, &ignored);
    while (context->children != NULL) {
        struct csh_background_child *child = context->children;
        context->children = child->next;
        free(child);
    }
    csh_jobs_destroy(context->jobs);
    memset(context, 0, sizeof(*context));
}

static int execute_plan(struct csh_execution_context *context,
    const struct execution_plan *plan, const struct descriptor_reservations *reserved,
    struct csh_execution *result, struct csh_error *error);
static void apply_errexit(struct csh_state *state, enum csh_ast_kind kind,
    struct csh_execution *result)
{
    struct csh_state_info info;
    csh_state_get_info(state, &info);
    /* A function/eval/dot call is itself a simple command. The compound
     * exception inside its body does not exempt this command's status. */
    if (kind == CSH_AST_SIMPLE) result->errexit_ignored = 0;
    if (info.errexit_ignored) result->errexit_ignored = 1;
    if ((info.options & CSH_OPT_ERREXIT) && result->status != 0 &&
        !info.errexit_ignored && !result->errexit_ignored &&
        result->control == CSH_CONTROL_NONE &&
        kind != CSH_AST_LIST && kind != CSH_AST_AND && kind != CSH_AST_OR)
        result->exit_requested = 1;
}

static int execute_test(struct csh_execution_context *context,
    const struct execution_plan *plan, const struct descriptor_reservations *reserved,
    struct csh_execution *result, struct csh_error *error)
{
    struct csh_state_info info;
    int rc;
    csh_state_get_info(context->state, &info);
    csh_state_set_errexit_ignored(context->state, info.errexit_ignored + 1);
    rc = execute_plan(context, plan, reserved, result, error);
    csh_state_set_errexit_ignored(context->state, info.errexit_ignored);
    return rc;
}

static int context_job(struct csh_execution_context *context,
    const struct execution_plan *plan, const struct descriptor_reservations *reserved,
    const struct csh_command *prepared, int asynchronous,
    struct csh_execution *result, struct csh_error *error);
static int job_handler(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result, struct csh_error *error, void *context);

static void report_error(struct csh_error *error)
{
    if (error->reported) return;
    dprintf(STDERR_FILENO, "cshell: %s", csh_error_message(error));
    if (error->system_errno) dprintf(STDERR_FILENO, ": %s", strerror(error->system_errno));
    dprintf(STDERR_FILENO, "\n");
    error->reported = 1;
}

static void expansion_failed(struct csh_state *state, struct csh_execution *result)
{
    struct csh_state_info info;
    csh_state_get_info(state, &info);
    result->exit_requested = !(info.options & CSH_OPT_INTERACTIVE);
}

static int restore_redirects(struct csh_redirect_save ***saves, size_t count,
    struct csh_error *error)
{
    int rc = 0;
    while (count) {
        struct csh_error restored;
        if (csh_redirect_restore(&(*saves)[--count], &restored) == -1) {
            *error = restored;
            rc = -1;
        }
    }
    free(*saves);
    *saves = NULL;
    return rc;
}

static int runtime_redirects(struct csh_state *state, struct csh_jobs *jobs, const struct csh_ast *tree,
    const struct descriptor_reservations *reserved, struct csh_command *command,
    struct csh_redirect_save ***saves, struct csh_execution *result,
    struct csh_error *error)
{
    size_t i;
    *saves = NULL;
    if (!tree->redirection_count) return 0;
    *saves = calloc(tree->redirection_count, sizeof(**saves));
    if (*saves == NULL) return fail(error, "cannot allocate redirection saves", ENOMEM, 1);
    for (i = 0; i < tree->redirection_count; ++i) {
        struct csh_redirect redirect = {0};
        int rc = csh_command_redirect(state, tree->redirections[i], command, &redirect, error);
        if (rc == -1) expansion_failed(state, result);
        else if (rc == -2) { result->redirection_failed = 1; rc = -1; }
        else {
            struct csh_input_reservation input_scope = {0};
            int fds[2] = {redirect.fd, redirect.source_fd};
            size_t count = redirect.kind == CSH_REDIRECT_DUP_READ ||
                redirect.kind == CSH_REDIRECT_DUP_WRITE ? 2 : 1;
            rc = csh_input_reserve_begin(&input_scope, fds, count, error);
            if (rc == 0 && jobs != NULL && csh_jobs_reserve(jobs, fds, count) == -1)
                rc = fail(error, "cannot reserve job descriptors", errno, 1);
            if (rc == 0) rc = csh_redirect_apply_reserved(&redirect, 1, reserved->items,
                reserved->count, &(*saves)[i], error);
            csh_input_reserve_end(&input_scope);
            if (rc == -1) result->redirection_failed = 1;
        }
        free(redirect.path);
        free(redirect.data);
        if (rc == -1) {
            if (i != 0) report_error(error);
            restore_redirects(saves, i, error);
            return -1;
        }
    }
    return 0;
}

/* Trace one expanded simple command. PS4 uses here-document expansion:
 * parameter/arithmetic/substitution expansion, without field splitting/globbing.
 * Recursive tracing of PS4 itself is suppressed. */
static void trace_word(const char *word)
{
    const char *p;
    if (*word && strspn(word, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./-:=+") == strlen(word)) {
        csh_write_text(2, word);
        return;
    }
    csh_write_text(2, "'");
    for (p = word; *p; ++p) {
        if (*p == '\'') csh_write_text(2, "'\\''");
        else csh_write_bytes(2, p, 1);
    }
    csh_write_text(2, "'");
}

static void trace_command(struct csh_state *state, const struct csh_command *command)
{
    static int tracing;
    struct csh_state_info info;
    struct csh_variable_view ps4;
    struct csh_ast_word word = {0};
    struct csh_fields fields = {0};
    struct csh_error error;
    const char *prefix;
    size_t i;
    int separated = 0;
    csh_state_get_info(state, &info);
    if (!(info.options & CSH_OPT_XTRACE) || tracing) return;
    tracing = 1;
    csh_state_get_variable(state, "PS4", &ps4);
    prefix = ps4.value != NULL ? ps4.value : "+ ";
    if (csh_parser_document((const unsigned char *)prefix, strlen(prefix), &word, &error) == 0 &&
        csh_prepare_word(state, &word, CSH_EXPAND_HEREDOC, &fields, &error) == 0)
        csh_write_text(2, fields.count ? fields.values[0] : "");
    else csh_write_text(2, "+ ");
    csh_ast_word_destroy(&word);
    csh_fields_destroy(&fields);
    for (i = 0; i < command->assignment_count; ++i) {
        if (separated) csh_write_text(2, " ");
        csh_write_text(2, command->assignments[i].name);
        csh_write_text(2, "=");
        trace_word(command->assignments[i].value);
        separated = 1;
    }
    for (i = 0; i < command->argc; ++i) {
        if (separated) csh_write_text(2, " ");
        trace_word(command->argv[i]);
        separated = 1;
    }
    csh_write_text(2, "\n");
    tracing = 0;
}

static int runtime_simple(struct csh_execution_context *context,
    const struct execution_plan *plan, const struct descriptor_reservations *reserved,
    int direct, struct csh_pipeline_stage *stage,
    struct csh_execution *result, struct csh_error *error)
{
    struct csh_state *state = context->state;
    const struct csh_ast *tree = plan->tree;
    struct csh_command command = {0};
    struct csh_redirect_save **saves = NULL;
    struct csh_state *redirect_state = NULL;
    enum csh_execution_category category;
    csh_command_handler handler;
    void *handler_context = context;
    int rc = -1;
    memset(result, 0, sizeof(*result));
    if (csh_command_arguments(state, tree, &command, error) == -1) {
        expansion_failed(state, result);
        goto done;
    }
    if (command_validate(state, &command, &category, error) == -1) goto done;
    result->category = category;
    if (command.argc == 0 && tree->redirection_count != 0 &&
        csh_state_clone(state, &redirect_state) != CSH_STATE_OK) {
        fail(error, "cannot copy redirection environment", ENOMEM, 1);
        goto done;
    }
    {
        int redirected = runtime_redirects(redirect_state != NULL ? redirect_state : state,
            context->jobs, tree, reserved, &command, &saves, result, error);
        /* Assignment-only redirections expand in a disposable state. Its
         * locale mutations must not escape into subsequent parent expansion,
         * including when applying the redirection fails. */
        if (redirect_state != NULL) csh_state_refresh_locale(state);
        if (redirected == -1) goto done;
    }
    if (csh_command_assignments(state, tree, &command, error) == -1) {
        expansion_failed(state, result);
        goto done;
    }
    /* Argument/redirection expansion precedes prefix expansion. Resolve again
     * with the final prefix values, without changing their lifetime/attributes. */
    if (command.argc != 0)
        category = command_category(state, command.argv[0], &command);
    result->category = category;
    trace_command(state, &command);
    handler = category == CSH_EXEC_EMPTY || category == CSH_EXEC_EXTERNAL ?
        NULL : bootstrap_handler;
    if (context->jobs != NULL && command.argc != 0 &&
        category != CSH_EXEC_FUNCTION && csh_jobs_is_builtin(command.argv[0]) &&
        (strcmp(command.argv[0], "set") != 0 ||
            (command.argc > 1 && strcmp(command.argv[1], "--") != 0))) {
        category = strcmp(command.argv[0], "set") == 0 ?
            CSH_EXEC_SPECIAL_BUILTIN : CSH_EXEC_REGULAR_BUILTIN;
        handler = job_handler;
        handler_context = context->jobs;
    }
    if (direct && category == CSH_EXEC_EXTERNAL) {
        struct launch launch;
        if (pipeline_launch_prepare(state, &command, &launch, error) == -1) goto done;
        launch_child(&command, &launch);
    }
    if (!direct && context->jobs != NULL && category == CSH_EXEC_EXTERNAL) {
        rc = context_job(context, plan, reserved, &command, 0, result, error);
    } else {
        rc = execute_resolved(state, &command, category, handler,
            handler_context, result, stage, error);
    }
done:
    if (rc == -1 && saves != NULL) report_error(error);
    if (result->retain_redirects && saves != NULL) {
        size_t i;
        for (i = 0; i < tree->redirection_count; ++i) csh_redirect_commit(&saves[i]);
    }
    result->retain_redirects = 0;
    if (saves != NULL && restore_redirects(&saves, tree->redirection_count, error) == -1) rc = -1;
    if (rc == -1) result->status = error->status;
    if (result->redirection_failed && result->category == CSH_EXEC_SPECIAL_BUILTIN)
        result->special_builtin_error = 1;
    csh_state_destroy(redirect_state);
    if (stage != NULL) {
        stage->category = result->category;
        if (!stage->reaped) stage->status = result->status;
        stage->completed = stage->reaped || rc == 0;
    }
    csh_command_destroy(&command);
    return rc;
}

static int context_noexec(const struct csh_execution_context *context)
{
    struct csh_state_info info;
    csh_state_get_info(context->state, &info);
    return (info.options & CSH_OPT_NOEXEC) != 0;
}

static int context_stopped(struct csh_execution_context *context,
    const struct csh_execution *result)
{
    struct csh_state_info info;
    csh_state_get_info(context->state, &info);
    return result->control != CSH_CONTROL_NONE || result->exit_requested || (result->special_builtin_error &&
        !(info.options & CSH_OPT_INTERACTIVE));
}

/* Lookup uses the same PATH candidate construction as execution. */
static char *lookup_path(struct csh_state *state, const char *name, int defaults,
    int readable, const struct csh_command *prefix, struct csh_error *error)
{
    char *argv[] = {(char *)name, NULL}, *path = NULL;
    struct csh_command command = {0};
    struct launch launch;
    size_t i;
    command.argc = 1; command.argv = argv; command.default_path = defaults;
    if (prefix != NULL) {
        command.assignments = prefix->assignments;
        command.assignment_count = prefix->assignment_count;
    }
    if (launch_prepare(state, &command, &launch, error) == -1) return NULL;
    for (i = 0; i < launch.count; ++i) {
        struct stat st;
        if (stat(launch.paths[i], &st) == 0 &&
            (readable ? !S_ISDIR(st.st_mode) : S_ISREG(st.st_mode)) &&
            access(launch.paths[i], readable ? R_OK : X_OK) == 0) {
            path = strdup(launch.paths[i]);
            if (!path) fail(error, "cannot allocate command path", ENOMEM, 1);
            break;
        }
    }
    launch_destroy(&launch);
    if (path && path[0] != '/') {
        size_t capacity = 256;
        char *directory = NULL, *absolute;
        for (;;) {
            directory = malloc(capacity);
            if (!directory) break;
            if (getcwd(directory, capacity)) break;
            free(directory); directory = NULL;
            if (errno != ERANGE || capacity > SIZE_MAX / 2) break;
            capacity *= 2;
        }
        if (!directory) { free(path); fail(error, "cannot resolve command directory", errno, 1); return NULL; }
        absolute = malloc(strlen(directory) + strlen(path) + 2);
        if (absolute) sprintf(absolute, "%s/%s", directory, path);
        free(directory); free(path); path = absolute;
        if (!path) fail(error, "cannot allocate command path", ENOMEM, 1);
    }
    return path;
}
static int lookup_report(struct csh_state *state, const char *name, int verbose,
    int defaults, struct csh_error *error)
{
    const char *alias = csh_aliases_get(csh_state_aliases(state), name);
    enum csh_execution_category category = command_category(state, name, NULL);
    static const char *const reserved[] = {"!", "{", "}", "case", "do", "done", "elif",
        "else", "esac", "fi", "for", "if", "in", "then", "until", "while"};
    size_t i;
    if (alias) {
        const char *argv[] = {"alias", name};
        if (verbose && printf("%s is an alias: ", name) < 0) return 1;
        if (!verbose && printf("alias ") < 0) return 1;
        return csh_builtin_alias(csh_state_aliases(state), 2, argv, stdout, stderr) || fflush(stdout) == EOF;
    }
    for (i = 0; i < sizeof(reserved)/sizeof(*reserved); ++i)
        if (!strcmp(name, reserved[i])) return dprintf(1, verbose ? "%s is a reserved word\n" : "%s\n", name) < 0;
    if ((category != CSH_EXEC_EXTERNAL || csh_jobs_is_builtin(name)) &&
        (strcmp(name, "pwd") || category == CSH_EXEC_FUNCTION)) {
        return dprintf(1, verbose ? "%s is a %s\n" : "%s\n", name,
            category == CSH_EXEC_FUNCTION ? "function" : "shell builtin") < 0;
    }
    { char *path = lookup_path(state, name, defaults, 0, NULL, error);
      int rc;
      if (!path) {
          if (verbose) diagnose(name, "not found", 0);
          return 1;
      }
      rc = (verbose ? dprintf(1, "%s is %s\n", name, path) : dprintf(1, "%s\n", path)) < 0;
      free(path); return rc;
    }
}

void csh_execute_input_line(void *state, const unsigned char *bytes, size_t length)
{
    struct csh_state_info info;
    csh_state_get_info(state, &info);
    if (info.options & CSH_OPT_VERBOSE) csh_write_bytes(STDERR_FILENO, bytes, length);
}

static int evaluate_input(struct csh_execution_context *context, struct csh_input *input,
    int sourced, struct csh_execution *result, struct csh_error *error)
{
    struct csh_parser *parser = NULL;
    int rc = 0;
    enum csh_execution_category category = result->category;
    if (context->evaluation_depth >= 128) return fail(error, "evaluation nesting limit exceeded", 0, 2);
    if (csh_parser_create(&parser, input, error) == -1) return -1;
    csh_input_set_line_hook(input, csh_execute_input_line, context->state);
    if (csh_state_aliases(context->state) == NULL) {
        csh_parser_destroy(parser); return fail(error, "cannot allocate aliases", ENOMEM, 1);
    }
    csh_parser_set_aliases(parser, csh_state_aliases(context->state));
    ++context->evaluation_depth;
    result->status = 0;
    for (;;) {
        struct csh_ast *tree = NULL;
        enum csh_parse_result parsed;
        csh_parser_set_aliases(parser, csh_state_aliases(context->state));
        parsed = csh_parser_next(parser, &tree, error);
        if (parsed == CSH_PARSE_EOF) break;
        if (parsed != CSH_PARSE_TREE) {
            struct csh_state_info info;
            csh_state_get_info(context->state, &info);
            /* A dot read failure is a utility error. Let the caller's
             * category apply the interactive / command suppression rules. */
            result->exit_requested = csh_input_failed(input) ? !sourced :
                !(info.options & CSH_OPT_INTERACTIVE);
            rc = -1; break;
        }
        rc = csh_execute_context_ast(context, tree, result, error);
        csh_ast_destroy(tree);
        if (context_stopped(context, result)) break;
        if (rc == -1) {
            report_error(error);
            /* A command status is not an error in eval/dot itself. */
            rc = 0;
        }
    }
    --context->evaluation_depth;
    csh_parser_destroy(parser);
    result->category = category;
    return rc;
}

static void evaluate_trap_action(struct csh_execution_context *context,
    const char *action, int saved, struct csh_execution *outer)
{
    struct csh_input *input = NULL;
    struct csh_execution execution = {0};
    struct csh_error error;
    csh_state_set_status(context->state, saved);
    if (csh_input_from_string(&input, action, "trap", &error) == -1 ||
        evaluate_input(context, input, 0, &execution, &error) == -1) {
        if (!error.reported) report_error(&error);
    }
    csh_input_destroy(input);
    if (execution.exit_requested) {
        outer->exit_requested = 1;
        outer->status = execution.status;
    } else if (execution.control != CSH_CONTROL_NONE) {
        outer->control = execution.control;
        outer->levels = execution.levels;
        outer->status = execution.status;
        csh_state_set_status(context->state, execution.status);
    } else csh_state_set_status(context->state, saved);
}

int csh_execute_pending_traps(struct csh_execution_context *context,
    struct csh_execution *result, struct csh_error *error)
{
    int number = 0, next;
    char *action;
    unsigned char seen[CSH_TRAP_LIMIT] = {0};
    if (context == NULL || context->traps == NULL || context->dispatching_traps) return 0;
    context->dispatching_traps = 1;
    while ((next = csh_traps_first_pending()) > 0 && !seen[next]) {
        struct csh_state_info info;
        number = csh_traps_take(context->traps, &action);
        if (number <= 0) break;
        seen[number] = 1;
        csh_state_get_info(context->state, &info);
        evaluate_trap_action(context, action, info.last_status, result);
        free(action);
        if (result->exit_requested || result->control != CSH_CONTROL_NONE) break;
    }
    context->dispatching_traps = 0;
    if (number < 0) {
        result->status = 1;
        csh_state_set_status(context->state, 1);
        return fail(error, "cannot allocate trap action", ENOMEM, 1);
    }
    return 0;
}

int csh_execute_exit_trap(struct csh_execution_context *context,
    struct csh_error *error)
{
    char *action;
    struct csh_state_info info;
    struct csh_execution result = {0};
    if (context == NULL || context->state == NULL) return 0;
    csh_state_get_info(context->state, &info);
    if (context->traps == NULL) return info.last_status;
    action = csh_traps_exit_action(context->traps);
    if (action == NULL) {
        if (errno == ENOMEM) {
            fail(error, "cannot allocate EXIT action", ENOMEM, 1);
            report_error(error);
            csh_state_set_status(context->state, 1);
            return 1;
        }
        return info.last_status;
    }
    evaluate_trap_action(context, action, info.last_status, &result);
    free(action);
    return result.exit_requested ? result.status : info.last_status;
}

static int evaluation_handler(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result, struct csh_error *error, void *user)
{
    struct csh_execution_context local = {0}, *context = user;
    const char *name = command->argv[0];
    size_t first = 1, i;
    int rc = 0;
    if (!context) { local.state = state; context = &local; }
    if (!strcmp(name, "alias") || !strcmp(name, "unalias")) {
        struct csh_aliases *aliases = csh_state_aliases(state);
        if (!aliases) return fail(error, "cannot allocate aliases", ENOMEM, 1);
        result->status = !strcmp(name, "alias") ?
            csh_builtin_alias(aliases, (int)command->argc, (const char *const *)command->argv, stdout, stderr) :
            csh_builtin_unalias(aliases, (int)command->argc, (const char *const *)command->argv, stdout, stderr);
        if (fflush(stdout) == EOF) result->status = 1;
    } else if (!strcmp(name, "eval") || !strcmp(name, ".")) {
        struct csh_input *input = NULL;
        struct csh_parameter_save parameters = {0};
        int sourced = !strcmp(name, "."), pushed = 0;
        char *text = NULL;
        if (sourced) {
            if (first < command->argc && !strcmp(command->argv[first], "--")) ++first;
            if (first == command->argc) return fail(error, "dot requires a file", 0, 2);
            text = lookup_path(state, command->argv[first++], 0, 1, NULL, error);
            if (!text) return fail(error, "cannot find readable dot file", error->system_errno, 1);
            rc = csh_input_from_file(&input, text, error);
            if (rc == 0 && first < command->argc) {
                if (csh_state_push_parameters(state, command->argc - first,
                    (const char *const *)(command->argv + first), &parameters) != CSH_STATE_OK)
                    rc = fail(error, "cannot save dot parameters", ENOMEM, 1);
                else pushed = 1;
            }
        } else {
            size_t length = 1, used = 0;
            for (i = first; i < command->argc; ++i) {
                size_t n = strlen(command->argv[i]);
                if (n >= SIZE_MAX - length) return fail(error, "eval input too large", ENOMEM, 1);
                length += n + 1;
            }
            text = malloc(length);
            if (!text) return fail(error, "cannot allocate eval input", ENOMEM, 1);
            for (i = first; i < command->argc; ++i) {
                size_t n = strlen(command->argv[i]);
                if (i != first) text[used++] = ' ';
                memcpy(text + used, command->argv[i], n); used += n;
            }
            text[used] = 0;
            rc = csh_input_from_string(&input, text, "eval", error);
        }
        free(text);
        if (rc == 0) {
            struct csh_state_info info;
            csh_state_get_info(state, &info);
            if (sourced) csh_state_set_source_depth(state, info.source_depth + 1);
            rc = evaluate_input(context, input, sourced, result, error);
            if (sourced) {
                csh_state_set_source_depth(state, info.source_depth);
                if (result->control == CSH_CONTROL_RETURN) result->control = CSH_CONTROL_NONE;
            }
        }
        if (pushed) csh_state_pop_parameters(state, &parameters);
        csh_input_destroy(input);
    } else if (!strcmp(name, "exec")) {
        struct csh_command target = *command;
        struct launch launch;
        struct csh_state_info info;
        if (first < command->argc && !strcmp(command->argv[first], "--")) ++first;
        if (first == command->argc) { result->retain_redirects = 1; result->status = 0; return 0; }
        if (first == 1 && command->argv[first][0] == '-') return fail(error, "invalid exec option", 0, 2);
        target.argv += first; target.argc -= first;
        target.redirections = NULL; target.redirection_count = 0;
        /* Build the replacement environment with exported prefixes, then
         * restore attributes so a failed interactive exec retains ordinary
         * special-builtin assignment semantics. */
        {
            struct csh_variable_save *save = NULL;
            int prepared = assignments_apply(state, command, CSH_EXEC_EXTERNAL,
                &save, result, error);
            if (prepared == 0) prepared = launch_prepare(state, &target, &launch, error);
            csh_state_restore_variables(state, &save);
            if (prepared == -1) return -1;
        }
        csh_jobs_exec_signals(context->jobs, 0);
        csh_traps_exec_signals(context->traps, 0);
        result->status = launch_replace(&target, &launch);
        csh_jobs_exec_signals(context->jobs, 1);
        csh_traps_exec_signals(context->traps, 1);
        launch_destroy(&launch);
        csh_state_get_info(state, &info);
        result->exit_requested = !(info.options & CSH_OPT_INTERACTIVE);
    } else if (!strcmp(name, "command") || !strcmp(name, "type")) {
        int verbose = !strcmp(name, "type"), report = verbose, defaults = command->default_path;
        while (first < command->argc && command->argv[first][0] == '-' && command->argv[first][1]) {
            const char *p = command->argv[first++] + 1;
            if (!strcmp(p, "-")) break;
            for (; *p; ++p) {
                if (*p == 'p' && !strcmp(name, "command")) defaults = 1;
                else if ((*p == 'v' || *p == 'V') && !strcmp(name, "command")) { report = 1; verbose = *p == 'V'; }
                else { diagnose(name, "invalid option", 0); result->status = 2; return 0; }
            }
        }
        result->status = 0;
        if (report) {
            for (i = first; i < command->argc; ++i)
                if (lookup_report(state, command->argv[i], verbose, defaults, error)) result->status = 1;
        } else if (first < command->argc) {
            struct csh_command target = *command;
            enum csh_execution_category category;
            target.argv += first; target.argc -= first;
            target.assignments = NULL; target.assignment_count = 0;
            target.redirections = NULL; target.redirection_count = 0;
            target.default_path = defaults;
            category = path_builtin_category(state, target.argv[0], defaults, NULL);
            if (!strcmp(target.argv[0], "exit") || control_name(target.argv[0])) category = CSH_EXEC_SPECIAL_BUILTIN;
            if (category == CSH_EXEC_SPECIAL_BUILTIN) category = CSH_EXEC_REGULAR_BUILTIN;
            if (context->evaluation_depth >= 128) return fail(error, "evaluation nesting limit exceeded", 0, 2);
            ++context->evaluation_depth;
            if (context->jobs && csh_jobs_is_builtin(target.argv[0]) &&
                (strcmp(target.argv[0], "set") ||
                    (target.argc > 1 && strcmp(target.argv[1], "--"))))
                result->status = csh_jobs_builtin(context->jobs, &target);
            else if (context->jobs && category == CSH_EXEC_EXTERNAL)
                rc = context_job(context, NULL, NULL, &target, 0, result, error);
            else rc = execute_resolved(state, &target, category,
                category == CSH_EXEC_EXTERNAL ? NULL : bootstrap_handler, context, result, NULL, error);
            --context->evaluation_depth;
            result->category = CSH_EXEC_REGULAR_BUILTIN;
        }
    } else { /* hash */
        int reset = 0;
        if (first < command->argc && !strcmp(command->argv[first], "-r")) { csh_state_hash_clear(state); reset = 1; ++first; }
        if (first < command->argc && !strcmp(command->argv[first], "--")) ++first;
        if (first < command->argc && command->argv[first][0] == '-') { diagnose(name, "invalid option", 0); result->status = 2; return 0; }
        result->status = 0;
        if (first == command->argc && !reset) {
            char **names;
            if (csh_state_hash_names(state, &names) != CSH_STATE_OK) return fail(error, "cannot list command cache", ENOMEM, 1);
            for (i = 0; names[i]; ++i)
                if (command_category(state, names[i], NULL) == CSH_EXEC_EXTERNAL &&
                    dprintf(1, "%s\n", csh_state_hash_get(state, names[i])) < 0) result->status = 1;
            csh_state_environment_destroy(names);
        }
        for (i = first; i < command->argc; ++i) {
            char *path;
            const char *operand = command->argv[i];
            if (command_category(state, operand, NULL) != CSH_EXEC_EXTERNAL || csh_jobs_is_builtin(operand)) continue;
            path = lookup_path(state, operand, 0, 0, NULL, error);
            if (!path) { diagnose(operand, "command not found", 0); result->status = 1; }
            else if (!strchr(operand, '/') && csh_state_hash_set(state, operand, path) != CSH_STATE_OK) result->status = 1;
            free(path);
        }
    }
    if (context == &local) csh_execution_context_destroy(&local);
    return rc;
}

static int context_pipeline(struct csh_execution_context *context,
    const struct execution_plan *plan, const struct descriptor_reservations *reserved,
    int asynchronous, struct csh_execution *result, struct csh_error *error,
    struct csh_pipeline_result *details);

static void background_setup(int redirect_input)
{
    if (redirect_input) {
        int fd;
        do { fd = open("/dev/null", O_RDONLY); } while (fd == -1 && errno == EINTR);
        if (fd == -1 || pipeline_connect(fd, STDIN_FILENO) == -1) {
            diagnose("context", "cannot redirect background input", errno);
            _exit(1);
        }
        if (fd != STDIN_FILENO) pipe_close(fd);
    }
    signal(SIGINT, SIG_IGN);
    signal(SIGQUIT, SIG_IGN);
}

static void context_child(struct csh_state *state, struct csh_traps *traps,
    const struct execution_plan *plan,
    const struct descriptor_reservations *reserved, int managed)
{
    struct csh_execution_context child = {0};
    struct csh_execution result;
    struct csh_error error;
    child.state = state; /* fork isolates state, cwd, options and descriptors. */
    child.traps = traps;
    csh_redirect_child();
    csh_state_update_options(state, 0, CSH_OPT_INTERACTIVE);
    if (managed && csh_jobs_create(&child.jobs, state, -1) == -1) {
        diagnose("context", "cannot initialize child jobs", errno);
        _exit(1);
    }
    if (plan->kind == CSH_AST_SIMPLE) {
        if (runtime_simple(&child, plan, reserved, 1, NULL,
            &result, &error) == -1 && !error.reported)
            diagnose("context", csh_error_message(&error), error.system_errno);
    } else if (execute_plan(&child, plan, reserved, &result, &error) == -1 && !error.reported)
        diagnose("context", csh_error_message(&error), error.system_errno);
    csh_execute_pending_traps(&child, &result, &error);
    csh_state_set_status(state, result.status);
    result.status = csh_execute_exit_trap(&child, &error);
    csh_execution_context_destroy(&child);
    csh_traps_destroy(traps);
    _exit(result.status);
}

static void plan_text(FILE *stream, const struct execution_plan *plan)
{
    size_t i;
    switch (plan->kind) {
    case CSH_AST_SIMPLE:
        for (i = 0; i < plan->tree->data.simple.word_count; ++i) {
            const struct csh_token *token = &plan->tree->data.simple.words[i].word.token;
            if (i) fputc(' ', stream);
            fwrite(token->raw, 1, token->length, stream);
        }
        break;
    case CSH_AST_BRACE: case CSH_AST_SUBSHELL:
        fputs(plan->kind == CSH_AST_BRACE ? "{ " : "( ", stream);
        plan_text(stream, &plan->children[0]);
        fputs(plan->kind == CSH_AST_BRACE ? "; }" : " )", stream);
        break;
    default:
        if (plan->negated) fputs("! ", stream);
        for (i = 0; i < plan->count; ++i) {
            if (i) fputs(plan->kind == CSH_AST_PIPELINE ? " | " :
                plan->kind == CSH_AST_AND ? " && " :
                plan->kind == CSH_AST_OR ? " || " : "; ", stream);
            plan_text(stream, &plan->children[i]);
        }
        break;
    }
}

/* Runtime contexts transfer each launched PID to the job manager exactly once.
 * The synchronous prepared-command APIs retain their existing ownership
 * contract. A barrier holds every stage until group creation and terminal
 * transfer succeed, including when the group leader would exit immediately. */
static int context_job(struct csh_execution_context *context,
    const struct execution_plan *plan, const struct descriptor_reservations *reserved,
    const struct csh_command *prepared, int asynchronous,
    struct csh_execution *result, struct csh_error *error)
{
    int is_pipeline = plan != NULL && plan->kind == CSH_AST_PIPELINE;
    size_t count = is_pipeline ? plan->count : 1, i;
    struct csh_job *job = NULL;
    struct launch *launches = NULL;
    int gate[2] = {-1, -1}, previous = -1, ends[2] = {-1, -1}, rc = -1;
    sigset_t launch_signals, prior_mask;
    int masked = 0;
    char *text = NULL;
    size_t text_size = 0;
    FILE *stream = NULL;
    launches = calloc(count, sizeof(*launches));
    if (launches == NULL) {
        fail(error, "cannot allocate job launches", ENOMEM, 1);
        goto done;
    }
    result->category = is_pipeline ? CSH_EXEC_PIPELINE : CSH_EXEC_EXTERNAL;
    if (prepared != NULL) {
        struct csh_variable_save *save = NULL;
        int prepared_ok = assignments_apply(context->state, prepared,
            CSH_EXEC_EXTERNAL, &save, result, error);
        if (prepared_ok == 0)
            prepared_ok = launch_prepare(context->state, prepared,
                &launches[0], error);
        csh_state_restore_variables(context->state, &save);
        if (prepared_ok == -1) goto done;
    }
    stream = open_memstream(&text, &text_size);
    if (stream == NULL) { fail(error, "cannot allocate job text", errno, 1); goto done; }
    if (plan != NULL) plan_text(stream, plan);
    else for (i = 0; i < prepared->argc; ++i) fprintf(stream, "%s%s", i ? " " : "", prepared->argv[i]);
    if (fclose(stream) == EOF) {
        stream = NULL;
        fail(error, "cannot format job text", errno, 1);
        goto done;
    }
    stream = NULL;
    job = csh_jobs_add(context->jobs, count, text, asynchronous,
        is_pipeline && plan->negated);
    if (job == NULL) { fail(error, "cannot allocate job", errno, 1); goto done; }
    if (pipeline_pipe(gate) == -1) { fail(error, "cannot create launch barrier", errno, 1); goto cancel; }
    /* A terminal signal arriving immediately after handoff must not run the
     * shell's inherited handler in a child that has not reset it yet. Keep
     * it pending across fork and the barrier, then restore the caller's mask. */
    sigemptyset(&launch_signals);
    sigaddset(&launch_signals, SIGINT);
    sigaddset(&launch_signals, SIGQUIT);
    sigaddset(&launch_signals, SIGTSTP);
    sigaddset(&launch_signals, SIGTTIN);
    sigaddset(&launch_signals, SIGTTOU);
    csh_traps_add_caught(context->traps, &launch_signals);
    if (sigprocmask(SIG_BLOCK, &launch_signals, &prior_mask) == -1) {
        fail(error, "cannot block job launch signals", errno, 1); goto cancel;
    }
    masked = 1;
    for (i = 0; i < count; ++i) {
        pid_t pid;
        const struct execution_plan *stage = is_pipeline ? &plan->children[i] : plan;
        if (i + 1 < count && pipeline_pipe(ends) == -1) {
            fail(error, "cannot create job pipe", errno, 1); goto cancel;
        }
        pid = fork();
        if (pid == -1) { fail(error, "cannot fork job stage", errno, 1); goto cancel; }
        if (pid == 0) {
            char byte;
            ssize_t received;
            int monitor = job->grouped;
            close(gate[1]);
            if (monitor && setpgid(0, job->pgid) == -1) _exit(1);
            csh_jobs_after_fork(context->jobs, asynchronous);
            if (prepared != NULL) csh_traps_exec_signals(context->traps, 0);
            else csh_traps_after_fork(context->traps, asynchronous, 0);
            if (is_pipeline && plan->negated) {
                struct csh_state_info info;
                csh_state_get_info(context->state, &info);
                csh_state_set_errexit_ignored(context->state, info.errexit_ignored + 1);
            }
            do { received = read(gate[0], &byte, 1); } while (received == -1 && errno == EINTR);
            close(gate[0]);
            if (received == -1) _exit(1);
            if (asynchronous && !monitor) background_setup(i == 0);
            if (pipeline_connect(previous, STDIN_FILENO) == -1 ||
                pipeline_connect(ends[1], STDOUT_FILENO) == -1) {
                diagnose("job", "cannot connect pipe", errno); _exit(1);
            }
            pipe_close(previous); pipe_close(ends[0]); pipe_close(ends[1]);
            sigprocmask(SIG_SETMASK, &prior_mask, NULL);
            if (prepared != NULL) launch_child(prepared, &launches[0]);
            context_child(context->state, context->traps, stage, reserved, 1);
        }
        job->processes[i].pid = pid;
        if (job->pgid == 0) job->pgid = pid;
        if (job->grouped && setpgid(pid, job->pgid) == -1) {
            fail(error, "cannot assign job process group", errno, 1); goto cancel;
        }
        pipe_close(previous); pipe_close(ends[1]);
        previous = ends[0]; ends[0] = ends[1] = -1;
    }
    if (!asynchronous && csh_jobs_give_terminal(context->jobs, job, 0) == -1) {
        fail(error, "cannot give terminal to job", errno, 1); goto cancel;
    }
    pipe_close(gate[0]); gate[0] = -1;
    pipe_close(gate[1]); gate[1] = -1;
    sigprocmask(SIG_SETMASK, &prior_mask, NULL);
    masked = 0;
    if (asynchronous) {
        csh_state_set_background(context->state, job->processes[count - 1].pid);
        csh_jobs_announce(context->jobs, job);
        result->status = 0;
    } else if (csh_jobs_foreground(context->jobs, job, 0, &result->status) == -1) {
        fail(error, "cannot wait for foreground job", errno, 1); goto cancel;
    }
    rc = 0;
    goto done;
cancel:
    /* Keep the barrier shut until all partially launched children are dead. */
    pipe_close(previous); previous = -1;
    pipe_close(ends[0]); ends[0] = -1;
    pipe_close(ends[1]); ends[1] = -1;
    csh_jobs_cancel(context->jobs, job);
done:
    if (masked) sigprocmask(SIG_SETMASK, &prior_mask, NULL);
    pipe_close(gate[0]); pipe_close(gate[1]);
    if (stream != NULL) fclose(stream);
    free(text);
    if (launches != NULL) for (i = 0; i < count; ++i) launch_destroy(&launches[i]);
    free(launches);
    return rc;
}

static int job_handler(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result, struct csh_error *error, void *context)
{
    (void)state; (void)error;
    result->status = csh_jobs_builtin(context, command);
    return 0;
}

static int context_fork(struct csh_execution_context *context,
    const struct execution_plan *plan, const struct descriptor_reservations *reserved,
    int asynchronous, struct csh_execution *result, struct csh_error *error)
{
    struct csh_background_child *entry = NULL;
    struct csh_pipeline_stage stage = {0};
    sigset_t blocked, prior;
    if (context->jobs != NULL)
        return context_job(context, plan, reserved, NULL,
            asynchronous, result, error);
    if (asynchronous && plan->kind == CSH_AST_PIPELINE && plan->count > 1)
        return context_pipeline(context, plan, reserved, 1, result, error, NULL);
    if (asynchronous && (entry = malloc(sizeof(*entry))) == NULL)
        return fail(error, "cannot allocate background child", ENOMEM, 1);
    sigemptyset(&blocked);
    csh_traps_add_caught(context->traps, &blocked);
    if (sigprocmask(SIG_BLOCK, &blocked, &prior) == -1) {
        free(entry);
        return fail(error, "cannot block execution signals", errno, 1);
    }
    stage.pid = fork();
    if (stage.pid == -1) {
        int number = errno;
        sigprocmask(SIG_SETMASK, &prior, NULL);
        free(entry);
        return fail(error, "cannot fork execution context", number, 1);
    }
    if (stage.pid == 0) {
        /* Apply the implicit input before any explicit body redirects. */
        csh_traps_after_fork(context->traps, asynchronous, 0);
        if (asynchronous) background_setup(1);
        sigprocmask(SIG_SETMASK, &prior, NULL);
        context_child(context->state, context->traps, plan, reserved, 0);
    }
    sigprocmask(SIG_SETMASK, &prior, NULL);
    if (asynchronous) {
        entry->pid = stage.pid;
        entry->next = context->children;
        context->children = entry;
        ++context->child_count;
        csh_state_set_background(context->state, stage.pid);
        result->status = 0;
        csh_state_set_status(context->state, 0);
        return 0;
    }
    if (stage_wait(&stage) == -1) {
        int number = errno;
        kill(stage.pid, SIGKILL);
        stage_wait(&stage);
        return fail(error, "cannot wait for execution context", number, 1);
    }
    result->status = stage.status;
    return 0;
}

static int context_pipeline(struct csh_execution_context *context,
    const struct execution_plan *plan, const struct descriptor_reservations *reserved,
    int asynchronous, struct csh_execution *result, struct csh_error *error,
    struct csh_pipeline_result *details)
{
    struct csh_pipeline_result pipeline = {0};
    struct csh_background_child *pending = NULL;
    size_t i;
    int rc = -1, previous = -1, ends[2] = {-1, -1};
    struct csh_state_info initial;
    csh_state_get_info(context->state, &initial);
    if (plan->count == 1) {
        rc = execute_plan(context, &plan->children[0], reserved, result, error);
        if (rc == 0 && plan->negated && !result->exit_requested && result->control == CSH_CONTROL_NONE)
            result->status = !result->status;
        return rc;
    }
    if (context->jobs != NULL)
        return context_job(context, plan, reserved, NULL,
            asynchronous, result, error);
    pipeline.stages = calloc(plan->count, sizeof(*pipeline.stages));
    if (pipeline.stages == NULL)
        return fail(error, "cannot allocate pipeline stages", ENOMEM, 1);
    pipeline.count = plan->count;
    for (i = 0; i < plan->count; ++i) pipeline.stages[i].category = CSH_EXEC_UNRESOLVED;
    for (i = 0; i < plan->count; ++i) {
        pid_t pid;
        sigset_t blocked, prior;
        if (asynchronous) {
            struct csh_background_child *entry = malloc(sizeof(*entry));
            if (entry == NULL) {
                fail(error, "cannot allocate background child", ENOMEM, 1);
                goto cancel;
            }
            entry->pid = 0;
            entry->next = pending;
            pending = entry;
        }
        if (i + 1 < plan->count && pipeline_pipe(ends) == -1) {
            fail(error, "cannot create pipeline pipe", errno, 1);
            goto cancel;
        }
        sigemptyset(&blocked);
        csh_traps_add_caught(context->traps, &blocked);
        if (sigprocmask(SIG_BLOCK, &blocked, &prior) == -1) {
            fail(error, "cannot block pipeline signals", errno, 1);
            goto cancel;
        }
        pid = fork();
        if (pid == -1) {
            int number = errno;
            sigprocmask(SIG_SETMASK, &prior, NULL);
            fail(error, "cannot fork pipeline stage", number, 1);
            goto cancel;
        }
        if (pid == 0) {
            csh_traps_after_fork(context->traps, asynchronous, 0);
            if (asynchronous) background_setup(i == 0);
            sigprocmask(SIG_SETMASK, &prior, NULL);
            if (pipeline_connect(previous, STDIN_FILENO) == -1 ||
                pipeline_connect(ends[1], STDOUT_FILENO) == -1) {
                diagnose("pipeline", "cannot connect pipe", errno);
                _exit(1);
            }
            pipe_close(previous);
            pipe_close(ends[0]);
            pipe_close(ends[1]);
            if (plan->negated) {
                struct csh_state_info info;
                csh_state_get_info(context->state, &info);
                csh_state_set_errexit_ignored(context->state, info.errexit_ignored + 1);
            }
            context_child(context->state, context->traps, &plan->children[i], reserved, 0);
        }
        sigprocmask(SIG_SETMASK, &prior, NULL);
        pipeline.stages[i].pid = pid;
        if (asynchronous) pending->pid = pid;
        pipe_close(previous);
        pipe_close(ends[1]);
        previous = ends[0];
        ends[0] = ends[1] = -1;
    }
    if (asynchronous) {
        csh_state_set_background(context->state, pipeline.stages[plan->count - 1].pid);
        while (pending != NULL) {
            struct csh_background_child *entry = pending;
            pending = entry->next;
            entry->next = context->children;
            context->children = entry;
            ++context->child_count;
        }
        result->category = CSH_EXEC_PIPELINE;
        result->status = 0; /* Even a negated asynchronous pipeline returns 0. */
        csh_state_set_status(context->state, 0);
        rc = 0;
        goto done;
    }
    for (i = 0; i < plan->count; ++i)
        if (stage_wait(&pipeline.stages[i]) == -1) {
            fail(error, "cannot wait for pipeline stage", errno, 1);
            goto cancel;
        }
    result->category = CSH_EXEC_PIPELINE;
    result->status = pipeline.stages[plan->count - 1].status;
    if (initial.options & CSH_OPT_PIPEFAIL)
        for (i = 0; i < plan->count; ++i)
            if (pipeline.stages[i].status) result->status = pipeline.stages[i].status;
    if (plan->negated) result->status = !result->status;
    rc = 0;
    goto done;
cancel:
    pipe_close(previous);
    pipe_close(ends[0]);
    pipe_close(ends[1]);
    pipeline_cancel(&pipeline);
done:
    while (pending != NULL) {
        struct csh_background_child *entry = pending;
        pending = entry->next;
        free(entry);
    }
    if (details != NULL) {
        struct csh_execution execution = *result;
        *details = pipeline;
        details->execution = execution;
    } else csh_pipeline_result_destroy(&pipeline);
    return rc;
}

struct shell_function {
    struct csh_function base;
    const struct csh_ast *tree;
};

static void function_destroy(struct csh_function *base)
{
    struct shell_function *function = (struct shell_function *)base;
    csh_ast_destroy((struct csh_ast *)function->tree);
    free(function);
}

static int define_function(struct csh_state *state, const struct csh_ast *tree,
    struct csh_error *error)
{
    struct csh_fields name = {0};
    struct shell_function *function;
    enum csh_state_result saved;
    if (csh_prepare_word(state, &tree->data.function.name, CSH_EXPAND_REDIRECTION,
        &name, error) == -1) return -1;
    if (name.count != 1 || special_name(name.values[0])) {
        csh_fields_destroy(&name);
        return fail(error, "invalid function name: special builtin names are reserved", 0, 2);
    }
    function = calloc(1, sizeof(*function));
    if (function == NULL) {
        csh_fields_destroy(&name);
        return fail(error, "cannot allocate function definition", ENOMEM, 1);
    }
    function->base.references = 1;
    function->base.destroy = function_destroy;
    function->tree = tree;
    csh_ast_retain(tree);
    saved = csh_state_set_function(state, name.values[0], &function->base);
    csh_function_release(&function->base);
    csh_fields_destroy(&name);
    if (saved != CSH_STATE_OK)
        return fail(error, "cannot store function definition", saved == CSH_STATE_NOMEM ? ENOMEM : 0, 1);
    return 0;
}

static int flow_handler(struct csh_state *state, const struct csh_command *command,
    struct csh_execution *result, struct csh_error *error, void *user)
{
    struct csh_execution_context local = {0}, *context = user;
    const char *name = command->argv[0];
    if (context == NULL) { local.state = state; context = &local; }
    if (control_name(name)) {
        struct csh_state_info info;
        size_t first = 1;
        unsigned long value = 1;
        int returning = !strcmp(name, "return");
        csh_state_get_info(state, &info);
        if (first < command->argc && !strcmp(command->argv[first], "--")) ++first;
        if (command->argc - first > 1) {
            diagnose(name, "too many arguments", 0);
            result->status = 2;
            return 0;
        }
        if (first < command->argc) {
            const char *operand = command->argv[first], *digits = operand;
            char *end;
            long number;
            if (*digits == '+' || *digits == '-') ++digits;
            if (!*digits) goto invalid_operand;
            while (*digits >= '0' && *digits <= '9') ++digits;
            errno = 0;
            number = strtol(operand, &end, 10);
            if (*digits || *end || errno == ERANGE || (!returning && number <= 0))
                goto invalid_operand;
            value = (unsigned long)number;
        } else if (returning) value = (unsigned long)info.last_status;
        if ((returning && info.function_depth == 0 && info.source_depth == 0) ||
            (!returning && context->loop_depth == 0)) {
            diagnose(name, returning ? "not in a function" : "not in a loop", 0);
            result->status = 2;
            return 0;
        }
        result->control = returning ? CSH_CONTROL_RETURN :
            !strcmp(name, "break") ? CSH_CONTROL_BREAK : CSH_CONTROL_CONTINUE;
        result->levels = returning ? 0 : value > context->loop_depth ?
            context->loop_depth : (unsigned)value;
        result->status = returning ? (int)(value & 255u) : 0;
        return 0;
invalid_operand:
        diagnose(name, returning ? "numeric status required" : "positive loop count required", 0);
        result->status = 2;
        return 0;
    } else {
        struct shell_function *function = (struct shell_function *)csh_state_function(state, name);
        struct csh_parameter_save parameters = {0};
        struct execution_plan plan = {0};
        struct descriptor_reservations reserved = {0};
        struct csh_state_info info;
        struct csh_input_reservation input_scope = {0};
        unsigned loops = context->loop_depth;
        int rc = -1;
        if (function == NULL) return fail(error, "missing function definition", 0, 1);
        csh_state_get_info(state, &info);
        if (info.function_depth >= 128)
            return fail(error, "function nesting limit exceeded", 0, 2);
        csh_function_retain(&function->base);
        if (plan_prepare(function->tree, &plan, &reserved, 0, error) == -1) goto done;
        if (csh_input_reserve_begin(&input_scope, reserved.items, reserved.count, error) == -1) goto done;
        if (context->jobs != NULL && csh_jobs_reserve(context->jobs,
            reserved.items, reserved.count) == -1) {
            fail(error, "cannot reserve function descriptors", errno, 1);
            goto done;
        }
        if (csh_state_push_parameters(state, command->argc - 1,
            (const char *const *)(command->argv + 1), &parameters) != CSH_STATE_OK) {
            fail(error, "cannot save function parameters", ENOMEM, 1);
            goto done;
        }
        csh_state_set_function_depth(state, info.function_depth + 1);
        context->loop_depth = 0;
        /* Definition redirects are evaluated on each invocation, after the
         * call's parameters and assignment environment have been established. */
        plan.kind = CSH_AST_BRACE;
        rc = execute_plan(context, &plan, &reserved, result, error);
        csh_state_set_function_depth(state, info.function_depth);
        context->loop_depth = loops;
        csh_state_pop_parameters(state, &parameters);
        if (result->control == CSH_CONTROL_RETURN) {
            result->control = CSH_CONTROL_NONE;
            result->levels = 0;
        }
done:
        csh_input_reserve_end(&input_scope);
        result->category = CSH_EXEC_FUNCTION;
        plan_destroy(&plan);
        free(reserved.items);
        csh_function_release(&function->base);
        if (context == &local) csh_execution_context_destroy(&local);
        return rc;
    }
}

/* Consume exactly this loop's boundary. Return 1 for break/unwind, 2 for a
 * local continue, and 0 for ordinary completion. */
static int loop_transfer(struct csh_execution *result)
{
    enum csh_control_transfer control = result->control;
    if (control != CSH_CONTROL_BREAK && control != CSH_CONTROL_CONTINUE) return 0;
    if (--result->levels != 0) return 1;
    result->control = CSH_CONTROL_NONE;
    return control == CSH_CONTROL_CONTINUE ? 2 : 1;
}

static int compound_body(struct csh_execution_context *context,
    const struct execution_plan *plan, const struct descriptor_reservations *reserved,
    struct csh_execution *result, struct csh_error *error)
{
    const struct csh_ast *tree = plan->tree;
    size_t i, j;
    int rc = 0;
    switch (plan->kind) {
    case CSH_AST_IF:
        for (i = 0; i < tree->data.if_clause.branch_count; ++i) {
            rc = execute_test(context, &plan->children[i * 2], reserved, result, error);
            if (rc == -1 || (context_stopped(context, result) || context_noexec(context))) return rc;
            if (result->status == 0)
                return execute_plan(context, &plan->children[i * 2 + 1], reserved, result, error);
        }
        if (tree->data.if_clause.else_body != NULL)
            return execute_plan(context, &plan->children[plan->count - 1], reserved, result, error);
        result->status = 0;
        return 0;
    case CSH_AST_WHILE: case CSH_AST_UNTIL: {
        int last = 0, last_ignored = 0;
        ++context->loop_depth;
        for (;;) {
            int transfer;
            rc = execute_test(context, &plan->children[0], reserved, result, error);
            transfer = loop_transfer(result);
            if (rc == -1 || transfer == 1 || (context_stopped(context, result) || context_noexec(context))) break;
            if (transfer == 2) continue;
            if ((result->status == 0) != (plan->kind == CSH_AST_WHILE)) {
                result->status = last;
                result->errexit_ignored = last_ignored;
                break;
            }
            rc = execute_plan(context, &plan->children[1], reserved, result, error);
            last = result->status;
            last_ignored = result->errexit_ignored;
            transfer = loop_transfer(result);
            if (rc == -1 || transfer == 1 || (context_stopped(context, result) || context_noexec(context))) break;
        }
        --context->loop_depth;
        return rc;
    }
    case CSH_AST_FOR: {
        struct csh_fields name = {0};
        struct csh_command words = {0};
        if (csh_prepare_word(context->state, &tree->data.for_clause.name,
            CSH_EXPAND_REDIRECTION, &name, error) == -1) return -1;
        if (name.count != 1) { csh_fields_destroy(&name); return fail(error, "invalid loop name", 0, 2); }
        if (tree->data.for_clause.has_in) {
            for (i = 0; i < tree->data.for_clause.words.count; ++i) {
                struct csh_fields fields = {0};
                char **grown;
                if (csh_prepare_word(context->state, &tree->data.for_clause.words.items[i],
                    CSH_EXPAND_ARGUMENT, &fields, error) == -1) { rc = -1; goto for_done; }
                if (fields.count >= SIZE_MAX / sizeof(char *) - words.argc ||
                    (grown = realloc(words.argv, (words.argc + fields.count + 1) * sizeof(char *))) == NULL) {
                    csh_fields_destroy(&fields);
                    rc = fail(error, "cannot allocate loop words", ENOMEM, 1);
                    goto for_done;
                }
                words.argv = grown;
                for (j = 0; j < fields.count; ++j) words.argv[words.argc++] = fields.values[j];
                words.argv[words.argc] = NULL;
                free(fields.values);
            }
        } else {
            struct csh_state_info info;
            csh_state_get_info(context->state, &info);
            words.argv = calloc(info.argument_count + 1, sizeof(char *));
            if (words.argv == NULL) { rc = fail(error, "cannot allocate loop words", ENOMEM, 1); goto for_done; }
            for (i = 1; i <= info.argument_count; ++i) {
                const char *parameter = csh_state_parameter(context->state, i);
                char *word = malloc(strlen(parameter) + 1);
                if (word == NULL) { rc = fail(error, "cannot copy loop word", ENOMEM, 1); goto for_done; }
                strcpy(word, parameter);
                words.argv[words.argc++] = word;
            }
        }
        ++context->loop_depth;
        for (i = 0; i < words.argc; ++i) {
            enum csh_state_result assigned = csh_state_set_variable(context->state, name.values[0], words.argv[i]);
            struct csh_state_info info;
            int transfer;
            csh_state_get_info(context->state, &info);
            if (assigned == CSH_STATE_OK && (info.options & CSH_OPT_ALLEXPORT))
                assigned = csh_state_update_attributes(context->state, name.values[0], CSH_VAR_EXPORT, 0);
            if (assigned != CSH_STATE_OK) {
                rc = fail(error, "cannot assign loop variable", assigned == CSH_STATE_NOMEM ? ENOMEM : 0, 1);
                break;
            }
            rc = execute_plan(context, &plan->children[0], reserved, result, error);
            transfer = loop_transfer(result);
            if (rc == -1 || transfer == 1 || (context_stopped(context, result) || context_noexec(context))) break;
        }
        --context->loop_depth;
for_done:
        csh_fields_destroy(&name);
        csh_command_destroy(&words);
        return rc;
    }
    case CSH_AST_CASE: {
        struct csh_fields word = {0};
        int fallthrough = 0;
        if (csh_prepare_word(context->state, &tree->data.case_clause.word,
            CSH_EXPAND_REDIRECTION, &word, error) == -1) return -1;
        for (i = 0; i < tree->data.case_clause.item_count; ++i) {
            const struct csh_ast_case_item *item = &tree->data.case_clause.items[i];
            int match = fallthrough;
            for (j = 0; !match && j < item->patterns.count; ++j) {
                struct csh_fields pattern = {0};
                rc = csh_prepare_word(context->state, &item->patterns.items[j],
                    CSH_EXPAND_PATTERN, &pattern, error);
                if (rc == -1) break;
                match = fnmatch(pattern.count ? pattern.values[0] : "",
                    word.count ? word.values[0] : "", 0) == 0;
                csh_fields_destroy(&pattern);
            }
            if (rc == -1) break;
            if (!match) continue;
            if (plan->children[i].count != 0)
                rc = execute_plan(context, &plan->children[i], reserved, result, error);
            if (rc == -1 || (context_stopped(context, result) || context_noexec(context)) || item->terminator != CSH_AST_CASE_FALLTHROUGH) break;
            fallthrough = 1;
        }
        csh_fields_destroy(&word);
        return rc;
    }
    default: return fail(error, "invalid compound command", 0, 2);
    }
}

static int execute_plan(struct csh_execution_context *context,
    const struct execution_plan *plan, const struct descriptor_reservations *reserved,
    struct csh_execution *result, struct csh_error *error)
{
    size_t i;
    int rc = 0;
    memset(result, 0, sizeof(*result));
    memset(error, 0, sizeof(*error));
    {
        struct csh_state_info info;
        csh_state_get_info(context->state, &info);
        if (info.options & CSH_OPT_NOEXEC) { result->status = info.last_status; return 0; }
    }
    switch (plan->kind) {
    case CSH_AST_SIMPLE:
        rc = runtime_simple(context, plan, reserved, 0, NULL, result, error);
        break;
    case CSH_AST_LIST:
        for (i = 0; i < plan->count; ++i) {
            if (plan->children[i].asynchronous) {
                memset(result, 0, sizeof(*result));
                rc = context_fork(context, &plan->children[i], reserved, 1, result, error);
            } else rc = execute_plan(context, &plan->children[i], reserved, result, error);
            if (rc == -1 || (context_stopped(context, result) || context_noexec(context))) break;
            if (csh_execution_context_reap(context, 0, error) == -1) { rc = -1; break; }
        }
        break;
    case CSH_AST_AND: case CSH_AST_OR:
        rc = execute_test(context, &plan->children[0], reserved, result, error);
        if (rc == 0 && !(context_stopped(context, result) || context_noexec(context)) &&
            ((plan->kind == CSH_AST_AND) == (result->status == 0)))
            rc = execute_plan(context, &plan->children[1], reserved, result, error);
        break;
    case CSH_AST_SUBSHELL: {
        /* Execute redirects inside the fork, with the group wrapper treated
         * as a brace so it does not fork itself again. */
        struct execution_plan group = *plan;
        group.kind = CSH_AST_BRACE;
        rc = context_fork(context, &group, reserved, 0, result, error);
        break;
    }
    case CSH_AST_FUNCTION:
        rc = define_function(context->state, plan->tree, error);
        if (rc == -1) expansion_failed(context->state, result);
        break;
    case CSH_AST_IF: case CSH_AST_FOR: case CSH_AST_WHILE:
    case CSH_AST_UNTIL: case CSH_AST_CASE:
    case CSH_AST_BRACE: {
        struct csh_redirect_save **saves = NULL;
        struct csh_command command = {0};
        rc = runtime_redirects(context->state, context->jobs, plan->tree, reserved, &command, &saves, result, error);
        if (rc == 0) {
            rc = plan->kind == CSH_AST_BRACE ?
                execute_plan(context, &plan->children[0], reserved, result, error) :
                compound_body(context, plan, reserved, result, error);
            if (rc == -1) {
                expansion_failed(context->state, result);
                report_error(error);
            }
            if (restore_redirects(&saves, plan->tree->redirection_count, error) == -1) rc = -1;
        }
        break;
    }
    case CSH_AST_PIPELINE: {
        struct csh_state_info before;
        csh_state_get_info(context->state, &before);
        if (plan->negated) csh_state_set_errexit_ignored(context->state, before.errexit_ignored + 1);
        rc = context_pipeline(context, plan, reserved, 0, result, error, NULL);
        csh_state_set_errexit_ignored(context->state, before.errexit_ignored);
        /* The status after inversion is still exempt, even when nonzero. */
        if (plan->negated) result->errexit_ignored = 1;
        break;
    }
    default: rc = fail(error, "unsupported compound command", 0, 2); break;
    }
    if (rc == -1) result->status = error->status;
    if (rc == -1 && result->redirection_failed) {
        /* A redirection failure is a command status for list composition.
         * Report it here, while any enclosing group's redirects are active. */
        report_error(error);
        memset(error, 0, sizeof(*error));
        result->redirection_failed = 0;
        rc = 0;
    }
    apply_errexit(context->state, plan->kind, result);
    csh_state_set_status(context->state, result->status);
    if (context->traps != NULL && !context->dispatching_traps &&
        csh_execute_pending_traps(context, result, error) == -1)
        rc = -1;
    return rc;
}

int csh_execute_context_ast(struct csh_execution_context *context,
    const struct csh_ast *tree, struct csh_execution *result, struct csh_error *error)
{
    struct execution_plan plan = {0};
    struct csh_input_reservation input_scope = {0};
    struct descriptor_reservations reserved = {0};
    int rc = -1;
    memset(result, 0, sizeof(*result));
    memset(error, 0, sizeof(*error));
    /* Preserve the candidate's fatal preflight-error classification. */
    result->category = CSH_EXEC_PIPELINE;
    if (context == NULL || context->state == NULL) {
        fail(error, "invalid execution context", 0, 2);
        goto done;
    }
    if (csh_execution_context_reap(context, 0, error) == -1 ||
        plan_prepare(tree, &plan, &reserved, 0, error) == -1) goto done;
    if (csh_input_reserve_begin(&input_scope, reserved.items, reserved.count, error) == -1) goto done;
    if (context->jobs != NULL && csh_jobs_reserve(context->jobs,
        reserved.items, reserved.count) == -1) {
        fail(error, "cannot reserve job descriptors", errno, 1);
        goto done;
    }
    rc = execute_plan(context, &plan, &reserved, result, error);
done:
    csh_input_reserve_end(&input_scope);
    plan_destroy(&plan);
    free(reserved.items);
    if (rc == -1) result->status = error->status;
    if (context != NULL && context->state != NULL)
        csh_state_set_status(context->state, result->status);
    return rc;
}

static int standalone_trap(const struct csh_ast *tree)
{
    while (tree != NULL) {
        if (tree->kind == CSH_AST_LIST && tree->data.list.item_count == 1)
            tree = tree->data.list.items[0].command;
        else if (tree->kind == CSH_AST_PIPELINE &&
            tree->data.pipeline.command_count == 1 && !tree->data.pipeline.negated)
            tree = tree->data.pipeline.commands[0];
        else break;
    }
    return tree != NULL && tree->kind == CSH_AST_SIMPLE &&
        tree->data.simple.word_count != 0 &&
        tree->data.simple.words[0].word.token.length == 4 &&
        !memcmp(tree->data.simple.words[0].word.token.raw, "trap", 4);
}

int csh_execute_substitution(struct csh_state *state, const struct csh_ast *tree,
    char **bytes, size_t *length, int *status, struct csh_error *error)
{
    static unsigned nesting;
    struct csh_pipeline_stage child = {0};
    sigset_t blocked, prior;
    int ends[2] = {-1, -1}, failed = 0;
    size_t used = 0, capacity = 0;
    char *buffer = NULL;
    *bytes = NULL;
    *length = 0;
    if (nesting >= 128) return fail(error, "command substitution nesting limit exceeded", 0, 2);
    if (pipeline_pipe(ends) == -1) return fail(error, "cannot create substitution pipe", errno, 1);
    sigemptyset(&blocked);
    csh_traps_add_caught(csh_traps_active(), &blocked);
    if (sigprocmask(SIG_BLOCK, &blocked, &prior) == -1) {
        int number = errno;
        pipe_close(ends[0]); pipe_close(ends[1]);
        return fail(error, "cannot block substitution signals", number, 1);
    }
    child.pid = fork();
    if (child.pid == -1) {
        int number = errno;
        sigprocmask(SIG_SETMASK, &prior, NULL);
        pipe_close(ends[0]); pipe_close(ends[1]);
        return fail(error, "cannot fork command substitution", number, 1);
    }
    if (child.pid == 0) {
        struct csh_execution_context context = {0};
        struct csh_execution result;
        struct csh_error failure;
        if (csh_jobs_active() != NULL) csh_jobs_after_fork(csh_jobs_active(), 0);
        csh_traps_after_fork(csh_traps_active(), 0, standalone_trap(tree));
        sigprocmask(SIG_SETMASK, &prior, NULL);
        ++nesting;
        if (pipeline_connect(ends[1], STDOUT_FILENO) == -1) {
            diagnose("substitution", "cannot connect output", errno);
            _exit(1);
        }
        pipe_close(ends[0]); pipe_close(ends[1]);
        csh_redirect_child();
        csh_state_update_options(state, 0, CSH_OPT_INTERACTIVE);
        context.state = state;
        context.traps = csh_traps_active();
        if (csh_execute_context_ast(&context, tree, &result, &failure) == -1 && !failure.reported)
            diagnose("substitution", csh_error_message(&failure), failure.system_errno);
        csh_execute_pending_traps(&context, &result, &failure);
        csh_state_set_status(state, result.status);
        result.status = csh_execute_exit_trap(&context, &failure);
        {
            struct csh_traps *traps = context.traps;
            csh_execution_context_destroy(&context);
            csh_traps_destroy(traps);
        }
        _exit(result.status);
    }
    sigprocmask(SIG_SETMASK, &prior, NULL);
    pipe_close(ends[1]);
    for (;;) {
        char chunk[8192];
        ssize_t count;
        do { count = read(ends[0], chunk, sizeof(chunk)); } while (count == -1 && errno == EINTR);
        if (count == 0) break;
        if (count < 0) {
            fail(error, "cannot read command substitution", errno, 1);
            failed = 1;
            break;
        }
        /* Even after a storage failure, drain before waiting so a producer
         * cannot block on a full pipe and all synchronous children finish. */
        if (failed) continue;
        if (memchr(chunk, 0, (size_t)count) != NULL) {
            fail(error, "NUL byte in command substitution output", 0, 2);
            failed = 1;
            continue;
        }
        if ((size_t)count >= SIZE_MAX - used) {
            fail(error, "command substitution output is too large", ENOMEM, 1);
            failed = 1;
            continue;
        }
        if (used + (size_t)count + 1 > capacity) {
            size_t grown = capacity ? capacity : sizeof(chunk) + 1;
            char *replacement;
            while (grown < used + (size_t)count + 1) {
                if (grown > SIZE_MAX / 2) { grown = used + (size_t)count + 1; break; }
                grown *= 2;
            }
            replacement = realloc(buffer, grown);
            if (replacement == NULL) {
                fail(error, "cannot allocate command substitution output", ENOMEM, 1);
                failed = 1;
                continue;
            }
            buffer = replacement;
            capacity = grown;
        }
        memcpy(buffer + used, chunk, (size_t)count);
        used += (size_t)count;
    }
    pipe_close(ends[0]);
    if (stage_wait(&child) == -1) {
        int number = errno;
        /* Retain ownership on a failed wait. Retry once before cancellation;
         * ordinary EINTR is already handled by stage_wait. */
        if (number != ECHILD && stage_wait(&child) == -1) {
            kill(child.pid, SIGKILL);
            stage_wait(&child);
        }
        if (!failed) fail(error, "cannot wait for command substitution", number, 1);
        failed = 1;
    }
    if (failed) { free(buffer); return -1; }
    if (buffer == NULL && (buffer = malloc(1)) == NULL)
        return fail(error, "cannot allocate command substitution output", ENOMEM, 1);
    while (used && buffer[used - 1] == '\n') --used;
    buffer[used] = 0;
    *bytes = buffer;
    *length = used;
    *status = child.status;
    return 0;
}

int csh_execute_pipeline_ast(struct csh_state *state, const struct csh_ast *tree,
    struct csh_pipeline_result *out, struct csh_error *error)
{
    struct execution_plan plan = {0};
    struct descriptor_reservations reserved = {0};
    struct csh_execution_context context = {0};
    const struct execution_plan *simple;
    struct csh_state_info initial = {0};
    int executing = 0;
    int rc = -1;
    memset(out, 0, sizeof(*out));
    memset(error, 0, sizeof(*error));
    out->execution.category = CSH_EXEC_PIPELINE;
    context.state = state;
    if (state != NULL) csh_state_get_info(state, &initial);
    if (tree != NULL && tree->kind == CSH_AST_LIST && tree->redirection_count == 0 &&
        tree->data.list.item_count == 1 &&
        tree->data.list.items[0].separator != CSH_AST_AMPERSAND)
        tree = tree->data.list.items[0].command;
    if (state == NULL || tree == NULL ||
        (tree->kind != CSH_AST_SIMPLE && tree->kind != CSH_AST_PIPELINE)) {
        fail(error, "only a foreground simple command or pipeline is supported", 0, 2);
        goto done;
    }
    if (plan_prepare(tree, &plan, &reserved, 0, error) == -1) goto done;
    if (initial.options & CSH_OPT_NOEXEC) {
        out->execution.status = initial.last_status;
        rc = 0;
        goto done;
    }
    executing = 1;
    if (plan.negated) csh_state_set_errexit_ignored(state, initial.errexit_ignored + 1);
    if (tree->kind == CSH_AST_PIPELINE && plan.count > 1) {
        rc = context_pipeline(&context, &plan, &reserved, 0, &out->execution, error, out);
        goto done;
    }
    out->stages = calloc(1, sizeof(*out->stages));
    if (out->stages == NULL) {
        fail(error, "cannot allocate pipeline stage", ENOMEM, 1);
        goto done;
    }
    out->count = 1;
    simple = tree->kind == CSH_AST_SIMPLE ? &plan : &plan.children[0];
    if (simple->kind == CSH_AST_SIMPLE)
        rc = runtime_simple(&context, simple, &reserved, 0,
            out->stages, &out->execution, error);
    else {
        rc = execute_plan(&context, &plan.children[0], &reserved, &out->execution, error);
        if (!out->stages[0].reaped) out->stages[0].status = out->execution.status;
        out->stages[0].completed = out->stages[0].reaped || rc == 0;
    }
    if (rc == 0 && plan.negated && !out->execution.exit_requested && out->execution.control == CSH_CONTROL_NONE)
        out->execution.status = !out->execution.status;
done:
    if (rc == -1 && out->execution.redirection_failed &&
        out->execution.category == CSH_EXEC_EXTERNAL) {
        if (!error->reported) diagnose("command", csh_error_message(error), error->system_errno);
        memset(error, 0, sizeof(*error));
        rc = 0;
    }
    if (state != NULL) csh_state_set_errexit_ignored(state, initial.errexit_ignored);
    if (rc == -1) out->execution.status = error->status;
    if (executing) {
        if (plan.negated) out->execution.errexit_ignored = 1;
        apply_errexit(state, plan.kind, &out->execution);
    }
    plan_destroy(&plan);
    free(reserved.items);
    csh_execution_context_destroy(&context);
    if (rc == -1) out->execution.status = error->status;
    if (state != NULL) csh_state_set_status(state, out->execution.status);
    return rc;
}
