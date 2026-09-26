#define CSHELL_EXECUTE_FAULT_IMPLEMENTATION
#include "execute_faults.h"
#include "cshell/execute.h"
#include "cshell/parser.h"
#include "cshell/jobs.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>

static void *allocations[4096];
static size_t live, allocation_calls, fail_allocation;
static int fail_open, fail_dup, fail_dup2, fail_temp, fail_fork, interrupt_wait;
static unsigned wait_calls;
static int fail_pipe, fail_wait, fail_setfd, fork_calls, fail_read, interrupt_read;
static int target_stage, child_fault;
static int fail_group, fail_terminal, fail_modes, launch_signal;
static pid_t fault_owner;
static pid_t launched[16];
static size_t launched_count;
static size_t pipeline_baseline;

static size_t slot(void *pointer)
{
    size_t index;
    for (index = 0; index < sizeof(allocations) / sizeof(allocations[0]); ++index)
        if (allocations[index] == pointer) return index;
    return sizeof(allocations) / sizeof(allocations[0]);
}

static int allocation_fails(void)
{
    ++allocation_calls;
    if (allocation_calls != fail_allocation) return 0;
    errno = ENOMEM;
    return 1;
}

static void remember(void *pointer)
{
    size_t index;
    if (pointer == NULL) return;
    index = slot(NULL);
    assert(index < sizeof(allocations) / sizeof(allocations[0]));
    allocations[index] = pointer;
    ++live;
}

void *csh_execute_fault_malloc(size_t size)
{
    void *pointer;
    if (allocation_fails()) return NULL;
    pointer = malloc(size);
    remember(pointer);
    return pointer;
}

void *csh_execute_fault_calloc(size_t count, size_t size)
{
    void *pointer;
    if (allocation_fails()) return NULL;
    pointer = calloc(count, size);
    remember(pointer);
    return pointer;
}

void *csh_execute_fault_realloc(void *pointer, size_t size)
{
    size_t index = pointer == NULL ? sizeof(allocations) / sizeof(allocations[0]) : slot(pointer);
    void *replacement;
    if (allocation_fails()) return NULL;
    replacement = realloc(pointer, size);
    if (replacement == NULL && size != 0) return NULL;
    if (index < sizeof(allocations) / sizeof(allocations[0])) {
        allocations[index] = NULL;
        --live;
    }
    remember(replacement);
    return replacement;
}

void csh_execute_fault_free(void *pointer)
{
    size_t index;
    if (pointer == NULL) return;
    index = slot(pointer);
    /* Strings may be transferred from uninjected parser/quote modules. */
    if (index < sizeof(allocations) / sizeof(allocations[0])) {
        allocations[index] = NULL;
        assert(live != 0);
        --live;
    }
    free(pointer);
}

int csh_execute_fault_open(const char *path, int flags, ...)
{
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list arguments;
        va_start(arguments, flags);
        mode = (mode_t)va_arg(arguments, int);
        va_end(arguments);
    }
    if (fail_open && --fail_open == 0) { errno = EIO; return -1; }
    return open(path, flags, mode);
}

int csh_execute_fault_mkstemp(char *template_name)
{
    if (fail_temp && --fail_temp == 0) { errno = EMFILE; return -1; }
    return mkstemp(template_name);
}

int csh_execute_fault_dup2(int old_fd, int new_fd)
{
    if (fail_dup2 && --fail_dup2 == 0) { errno = EMFILE; return -1; }
    return dup2(old_fd, new_fd);
}

int csh_execute_fault_fcntl(int fd, int operation, ...)
{
    int argument;
    va_list arguments;
    if (operation == F_GETFD || operation == F_GETFL)
        return fcntl(fd, operation);
    va_start(arguments, operation);
    argument = va_arg(arguments, int);
    va_end(arguments);
    if ((operation == F_DUPFD || operation == F_DUPFD_CLOEXEC) &&
        fail_dup && --fail_dup == 0) { errno = EMFILE; return -1; }
    if (operation == F_SETFD && fail_setfd && --fail_setfd == 0) {
        errno = EIO;
        return -1;
    }
    return fcntl(fd, operation, argument);
}

int csh_execute_fault_pipe(int ends[2])
{
    if (fail_pipe && --fail_pipe == 0) { errno = EMFILE; return -1; }
    return pipe(ends);
}

pid_t csh_execute_fault_fork(void)
{
    pid_t child;
    ++fork_calls;
    if (fail_fork && --fail_fork == 0) { errno = EAGAIN; return -1; }
    child = fork();
    if (child > 0) {
        assert(launched_count < sizeof(launched) / sizeof(launched[0]));
        launched[launched_count++] = child;
    } else if (child == 0) {
        /* Parent allocation sweeps stop at fork; child setup has its own
         * explicitly selected failure point below. */
        fail_allocation = 0;
        fail_wait = interrupt_wait = fail_read = interrupt_read = 0;
        if (fork_calls == target_stage) {
            int null_fd = open("/dev/null", O_WRONLY);
            assert(null_fd >= 0 && dup2(null_fd, 2) == 2);
            close(null_fd);
            if (child_fault == 1) fail_open = 1;
            if (child_fault == 2) fail_dup2 = 1;
            if (child_fault == 3) fail_dup = 1;
            if (child_fault == 4) fail_temp = 1;
            if (child_fault == 5) fail_allocation = allocation_calls + 1;
            if (child_fault == 6)
                fail_dup2 = (fork_calls == 1 || fork_calls == 5 ? 1 : 2) + 1;
        }
    }
    if (child == 0 && launch_signal) {
        /* Join the new, non-orphaned job group before generating TSTP. */
        assert(setpgid(0, 0) == 0);
        raise(launch_signal);
    }
    return child;
}

ssize_t csh_execute_fault_read(int fd, void *bytes, size_t length)
{
    if (interrupt_read) { interrupt_read = 0; errno = EINTR; return -1; }
    if (fail_read && --fail_read == 0) { errno = EIO; return -1; }
    return read(fd, bytes, length);
}

pid_t csh_execute_fault_waitpid(pid_t pid, int *status, int options)
{
    assert(pid > 0); /* Never consume children owned by another subsystem. */
    ++wait_calls;
    if (interrupt_wait) { interrupt_wait = 0; errno = EINTR; return -1; }
    if (fail_wait && --fail_wait == 0) { errno = EIO; return -1; }
    return waitpid(pid, status, options);
}

int csh_execute_fault_setpgid(pid_t pid, pid_t group)
{
    if (getpid() == fault_owner && fail_group && --fail_group == 0) { errno = EIO; return -1; }
    return setpgid(pid, group);
}

int csh_execute_fault_tcsetpgrp(int fd, pid_t group)
{
    if (fail_terminal && --fail_terminal == 0) { errno = EIO; return -1; }
    return tcsetpgrp(fd, group);
}

int csh_execute_fault_tcsetattr(int fd, int action, const struct termios *modes)
{
    if (fail_modes && --fail_modes == 0) { errno = EIO; return -1; }
    return tcsetattr(fd, action, modes);
}

static void arm(size_t allocation)
{
    allocation_calls = 0;
    fault_owner = getpid();
    fail_group = fail_terminal = fail_modes = launch_signal = 0;
    fail_allocation = allocation;
    fail_open = fail_dup = fail_dup2 = fail_temp = fail_fork = interrupt_wait = 0;
    wait_calls = 0;
    fail_pipe = fail_wait = fail_setfd = fork_calls = 0;
    target_stage = child_fault = fail_read = interrupt_read = 0;
    launched_count = 0;
}

static int fd_count(void)
{
    int fd, count = 0;
    for (fd = 0; fd < 256; ++fd)
        if (fcntl(fd, F_GETFD) >= 0) ++count;
    return count;
}

static struct csh_ast *parse(const char *script)
{
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *tree = NULL;
    struct csh_error error;
    assert(csh_input_from_string(&input, script, "faults", &error) == 0);
    assert(csh_parser_create(&parser, input, &error) == 0);
    assert(csh_parser_next(parser, &tree, &error) == CSH_PARSE_TREE);
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    return tree;
}

static void adapter_faults(void)
{
    struct csh_state *state = NULL;
    struct csh_invocation invocation = {0};
    size_t baseline;
    invocation.arg0 = "faults";
    assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
    baseline = live;
    const char *scripts[] = {
        "cd 'two words' '' \\\" $'line\\n' >target 3<&0 4>&-\n",
        "A=one B='' A=two cd . <<'ONE' <<'TWO'\nfirst\nONE\nsecond\nTWO\n"
    };
    size_t variant;
    for (variant = 0; variant < sizeof(scripts) / sizeof(scripts[0]); ++variant) {
        struct csh_ast *tree = parse(scripts[variant]);
        size_t point;
        for (point = 1; point < 2048; ++point) {
            struct csh_command command = {0};
            struct csh_error error;
            int returned;
            assert(live == baseline);
            arm(point);
            returned = csh_command_from_ast(state, tree, &command, &error);
            if (returned == -1) {
                assert(error.message != NULL);
                assert(allocation_calls >= point);
                assert(command.argc == 0 && command.argv == NULL);
                assert(command.redirection_count == 0 && command.redirections == NULL);
            } else {
                assert(returned == 0 && allocation_calls < point);
                assert(command.argc > 0 && strcmp(command.argv[0], "cd") == 0);
            }
            csh_command_destroy(&command);
            csh_command_destroy(&command);
            assert(live == baseline);
            if (returned == 0) break;
        }
        assert(point < 2048);
        csh_ast_destroy(tree);
    }
    arm(0);
    csh_state_destroy(state);
    assert(live == 0);
}

static void check_temporary_variables(struct csh_state *state)
{
    struct csh_variable_view view;
    assert(csh_state_get_variable(state, "TEMP", &view) == CSH_STATE_OK);
    assert(view.value == NULL && view.attributes == 0);
    assert(csh_state_get_variable(state, "UNSET", &view) == CSH_STATE_OK);
    assert(view.value == NULL && view.attributes == 0);
}

static int successful_handler(struct csh_state *state,
    const struct csh_command *command, struct csh_execution *result,
    struct csh_error *error, void *context)
{
    (void)state;
    (void)command;
    (void)error;
    (void)context;
    result->status = 0;
    return 0;
}

static void dispatch_faults(struct csh_state *state)
{
    struct csh_command command = {0};
    struct csh_redirect redirs[2] = {{0}};
    struct csh_execution result;
    struct csh_error error;
    char *arguments[] = {"test-regular", NULL};
    size_t point, baseline = live;
    struct csh_assignment prefix[] = {{"TEMP", "one"}, {"TEMP", "two"}, {"UNSET", ""}};
    int before, original = open("/dev/null", O_RDWR), variant;
    assert(original >= 0 && dup2(original, 40) == 40);
    assert(fcntl(40, F_SETFD, FD_CLOEXEC) == 0);
    close(41);
    before = fd_count();
    redirs[0].kind = CSH_REDIRECT_WRITE;
    redirs[0].fd = 40;
    redirs[0].path = "fault-output";
    redirs[1].kind = CSH_REDIRECT_WRITE;
    redirs[1].fd = 41;
    redirs[1].path = "fault-output-two";
    command.argv = arguments;
    command.argc = 1;
    command.assignments = prefix;
    command.assignment_count = 3;
    command.redirections = redirs;
    command.redirection_count = 2;
    for (point = 1; point < 256; ++point) {
        int returned;
        arm(point);
        returned = csh_execute_resolved(state, &command,
            CSH_EXEC_REGULAR_BUILTIN, successful_handler, NULL, &result,
            &error);
        if (returned < 0) {
            assert(error.message != NULL && allocation_calls >= point);
            assert(result.status != 0);
        } else {
            assert(returned == 0);
            if (result.status == 0) assert(allocation_calls < point);
            else assert(allocation_calls >= point);
        }
        assert(live == baseline && fd_count() == before);
        check_temporary_variables(state);
        assert(fcntl(40, F_GETFD) == FD_CLOEXEC);
        assert(fcntl(41, F_GETFD) == -1 && errno == EBADF);
        if (returned == 0 && result.status == 0) break;
    }
    assert(point < 256);
    for (variant = 0; variant < 6; ++variant) {
        arm(0);
        if (variant == 0) fail_open = 1;
        if (variant == 1) fail_open = 2;
        if (variant == 2) fail_dup = 1;
        if (variant == 3) fail_dup2 = 1;
        if (variant == 4) fail_dup2 = 2;
        if (variant == 5) {
            fail_temp = 1;
            redirs[0].kind = CSH_REDIRECT_HEREDOC;
            redirs[0].path = NULL;
            redirs[0].data = (unsigned char *)"body\n";
            redirs[0].length = 5;
        }
        assert(csh_execute_resolved(state, &command,
            CSH_EXEC_REGULAR_BUILTIN, successful_handler, NULL, &result,
            &error) == -1);
        assert(result.status != 0 && !result.exit_requested && error.message != NULL);
        assert(live == baseline && fd_count() == before);
        check_temporary_variables(state);
        assert(fcntl(40, F_GETFD) == FD_CLOEXEC);
        assert(fcntl(41, F_GETFD) == -1 && errno == EBADF);
    }
    close(40);
    close(original);
    arm(0);
}

static void process_faults(struct csh_state *state)
{
    struct csh_command command = {0};
    struct csh_execution result;
    struct csh_error error;
    char *arguments[] = {"/bin/sh", "-c", "exit 7", NULL};
    int before = fd_count();
    unsigned variant;
    size_t baseline;
    struct csh_assignment prefix[] = {{"TEMP", "one"}, {"PATH", "/bin:/usr/bin"}};
    command.argv = arguments;
    command.argc = 3;
    command.assignments = prefix;
    command.assignment_count = 2;
    for (variant = 0; variant < 2; ++variant) {
        size_t point;
        arguments[0] = variant == 0 ? "/bin/sh" : "sh";
        arm(0);
        assert(csh_state_set_variable(state, "PATH", "absent::/bin:/usr/bin") == CSH_STATE_OK);
        baseline = live;
        for (point = 1; point < 256; ++point) {
            int returned;
            arm(point);
            returned = csh_execute_command(state, &command, &result, &error);
            if (returned == -1) {
                assert(allocation_calls >= point && error.system_errno == ENOMEM);
                assert(result.status != 0 && error.message != NULL);
                assert(wait_calls == 0);
            } else {
                assert(returned == 0 && allocation_calls < point);
                assert(result.status == 7 && error.message == NULL);
            }
            assert(live == baseline && fd_count() == before);
            check_temporary_variables(state);
            if (returned == 0) break;
        }
        assert(point < 256);
    }
    arm(0);
    fail_fork = 1;
    assert(csh_execute_command(state, &command, &result, &error) == -1);
    assert(result.status != 0 && error.message != NULL && wait_calls == 0);
    assert(live == baseline && fd_count() == before);
    check_temporary_variables(state);
    arm(0);
    interrupt_wait = 1;
    assert(csh_execute_command(state, &command, &result, &error) == 0);
    assert(result.status == 7 && result.category == CSH_EXEC_EXTERNAL);
    assert(wait_calls >= 2 && error.message == NULL);
    assert(live == baseline && fd_count() == before);
    check_temporary_variables(state);
}

static void assignment_batch_faults(void)
{
    int category;
    for (category = CSH_EXEC_EMPTY; category <= CSH_EXEC_SPECIAL_BUILTIN; ++category) {
        size_t point;
        for (point = 1; point < 256; ++point) {
            struct csh_invocation invocation = {0};
            struct csh_state *state = NULL;
            struct csh_assignment prefixes[] = {{"OLD", "changed"}, {"NEW", ""}, {"OLD", "last"}};
            struct csh_command command = {0};
            struct csh_execution result;
            struct csh_error error;
            struct csh_variable_view view;
            char *args[] = {category == CSH_EXEC_SPECIAL_BUILTIN ? "exit" :
                category == CSH_EXEC_REGULAR_BUILTIN ? "test-regular" : "/bin/sh",
                category == CSH_EXEC_SPECIAL_BUILTIN ? "0" :
                category == CSH_EXEC_REGULAR_BUILTIN ? NULL : "-c", "exit 0", NULL};
            int rc;
            arm(0);
            invocation.mode = CSH_MODE_STRING;
            invocation.arg0 = "batch-faults";
            assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
            assert(csh_state_set_variable(state, "OLD", "original") == CSH_STATE_OK);
            command.assignments = prefixes;
            command.assignment_count = 3;
            if (category != CSH_EXEC_EMPTY) {
                command.argv = args;
                command.argc = category == CSH_EXEC_EXTERNAL ? 3 :
                    category == CSH_EXEC_REGULAR_BUILTIN ? 1 : 2;
                args[command.argc] = NULL;
            }
            arm(point);
            rc = category == CSH_EXEC_REGULAR_BUILTIN ?
                csh_execute_resolved(state, &command,
                    CSH_EXEC_REGULAR_BUILTIN, successful_handler, NULL,
                    &result, &error) :
                csh_execute_command(state, &command, &result, &error);
            assert(csh_state_get_variable(state, "OLD", &view) == CSH_STATE_OK);
            if (rc == -1 || category == CSH_EXEC_EXTERNAL || category == CSH_EXEC_REGULAR_BUILTIN) {
                assert(strcmp(view.value, "original") == 0 && view.attributes == 0);
                assert(csh_state_get_variable(state, "NEW", &view) == CSH_STATE_OK);
                assert(view.value == NULL && view.attributes == 0);
            } else assert(strcmp(view.value, "last") == 0 && view.attributes == 0);
            if (rc == -1)
                assert(error.system_errno == ENOMEM && allocation_calls >= point);
            else if (result.status != 0)
                assert(allocation_calls >= point);
            else
                assert(allocation_calls < point);
            csh_state_destroy(state);
            assert(live == 0);
            if (rc == 0 && result.status == 0) break;
        }
        assert(point < 256);
    }
    arm(0);
}

static void pipeline_clean(struct csh_pipeline_result *result, int before)
{
    size_t i;
    int status;
    for (i = 0; i < launched_count; ++i) {
        assert(result->stages != NULL && result->stages[i].pid == launched[i]);
        assert(result->stages[i].completed && result->stages[i].reaped);
        assert(waitpid(launched[i], &status, WNOHANG) == -1 && errno == ECHILD);
    }
    csh_pipeline_result_destroy(result);
    csh_pipeline_result_destroy(result);
    assert(live == pipeline_baseline && fd_count() == before);
}

static void pipeline_faults(struct csh_state *state)
{
    struct csh_pipeline_result result = {0};
    struct csh_error error;
    struct csh_ast *tree = parse("/usr/bin/true | : | /usr/bin/true | exit 3 | /usr/bin/true\n");
    struct csh_command commands[5] = {{0}};
    struct csh_redirect input = {0};
    char *sleep_args[] = {"/bin/sleep", "30", NULL};
    char *true_args[] = {"/usr/bin/true", NULL};
    char *cat_args[] = {"/bin/cat", NULL};
    char *cd_args[] = {"cd", ".", NULL};
    size_t point, i;
    int kind, before = fd_count(), status;
    pid_t unrelated = fork();
    siginfo_t child_info;
    pipeline_baseline = live;
    assert(unrelated >= 0);
    if (unrelated == 0) _exit(37);
    assert(waitid(P_PID, (id_t)unrelated, &child_info, WEXITED | WNOWAIT) == 0);
    /* Sweep adapter, stage-vector, and all external launch allocations. */
    for (point = 1; point < 512; ++point) {
        int returned;
        arm(point);
        returned = csh_execute_pipeline_ast(state, tree, &result, &error);
        if (returned == -1) {
            assert(error.system_errno == ENOMEM && allocation_calls >= point);
            assert(launched_count == 0);
        } else {
            assert(returned == 0 && allocation_calls < point);
            assert(result.execution.status == 0 && result.stages[3].status == 3);
        }
        pipeline_clean(&result, before);
        if (returned == 0) break;
    }
    assert(point < 512);
    csh_ast_destroy(tree);
    /* No consumers need to be cooperative for partial launch cancellation. */
    for (i = 0; i < 5; ++i) {
        commands[i].argv = sleep_args;
        commands[i].argc = 2;
    }
    for (kind = 0; kind < 3; ++kind) {
        size_t limit = kind == 0 ? 4 : kind == 1 ? 5 : 8;
        for (point = 1; point <= limit; ++point) {
            arm(0);
            if (kind == 0) fail_pipe = (int)point;
            if (kind == 1) fail_fork = (int)point;
            if (kind == 2) fail_setfd = (int)point;
            assert(csh_execute_pipeline(state, commands, 5, 1, &result, &error) == -1);
            assert(error.message != NULL && result.execution.status == 1);
            assert(launched_count == (kind == 2 ? (point - 1) / 2 : point - 1));
            pipeline_clean(&result, before);
        }
    }
    /* Pipe relocation must unwind both ends if F_DUPFD_CLOEXEC fails. */
    for (point = 1; point <= 8; ++point) {
        int saved_in = fcntl(0, F_DUPFD_CLOEXEC, 40);
        int saved_out = fcntl(1, F_DUPFD_CLOEXEC, 40);
        assert(saved_in >= 40 && saved_out >= 40);
        assert(close(0) == 0 && close(1) == 0);
        arm(0);
        fail_dup = (int)point;
        assert(csh_execute_pipeline(state, commands, 5, 0, &result, &error) == -1);
        assert(launched_count == (point - 1) / 2);
        pipeline_clean(&result, before);
        assert(fcntl(0, F_GETFD) == -1 && errno == EBADF);
        assert(fcntl(1, F_GETFD) == -1 && errno == EBADF);
        assert(dup2(saved_in, 0) == 0 && dup2(saved_out, 1) == 1);
        close(saved_in); close(saved_out);
        assert(fd_count() == before);
    }
    for (i = 0; i < 5; ++i) { commands[i].argv = true_args; commands[i].argc = 1; }
    for (point = 1; point <= 5; ++point) {
        arm(0);
        fail_wait = (int)point;
        assert(csh_execute_pipeline(state, commands, 5, 0, &result, &error) == -1);
        assert(error.system_errno == EIO && result.execution.status == 1);
        pipeline_clean(&result, before);
    }
    arm(0);
    fail_wait = 1;
    assert(csh_execute_pipeline(state, commands, 1, 0, &result, &error) == -1);
    pipeline_clean(&result, before);
    arm(0);
    interrupt_wait = 1;
    assert(csh_execute_pipeline(state, commands, 5, 0, &result, &error) == 0);
    assert(wait_calls == 6 && result.execution.status == 0);
    pipeline_clean(&result, before);
    /* Inject child setup errors in every position, including builtin stages.
     * Other stages get EOF/SIGPIPE normally; errors remain stage statuses. */
    input.fd = 0;
    for (i = 0; i < 5; ++i) {
        commands[i].argv = cat_args; commands[i].argc = 1;
        commands[i].redirections = &input; commands[i].redirection_count = 1;
    }
    for (kind = 1; kind <= 6; ++kind) {
        input.kind = kind == 4 ? CSH_REDIRECT_HEREDOC : CSH_REDIRECT_READ;
        input.path = kind == 4 ? NULL : "/dev/null";
        for (point = 1; point <= 5; ++point) {
            arm(0);
            target_stage = (int)point;
            child_fault = kind;
            assert(csh_execute_pipeline(state, commands, 5, 0, &result, &error) == 0);
            assert(result.stages[point - 1].status == 1);
            assert(result.execution.status == (point == 5 ? 1 : 0));
            pipeline_clean(&result, before);
        }
    }
    {
        input.kind = CSH_REDIRECT_READ;
        input.path = "/dev/null";
        for (i = 0; i < 5; ++i) { commands[i].argv = cd_args; commands[i].argc = 2; }
        for (point = 1; point <= 5; ++point) {
            arm(0);
            target_stage = (int)point;
            child_fault = 1;
            assert(csh_execute_pipeline(state, commands, 5, 0, &result, &error) == 0);
            assert(result.stages[point - 1].status == 1);
            pipeline_clean(&result, before);
        }
    }
    /* All validation precedes side effects, even for prepared API clients. */
    input.kind = CSH_REDIRECT_WRITE; input.fd = 1; input.path = "forbidden-preflight";
    commands[4].argv = NULL;
    arm(0);
    assert(csh_execute_pipeline(state, commands, 5, 0, &result, &error) == -1);
    assert(launched_count == 0 && access(input.path, F_OK) == -1);
    pipeline_clean(&result, before);
    assert(csh_execute_pipeline(state, NULL, 0, 0, &result, &error) == -1);
    pipeline_clean(&result, before);
    assert(waitpid(unrelated, &status, 0) == unrelated);
    assert(WIFEXITED(status) && WEXITSTATUS(status) == 37);
    assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
    arm(0);
}

static void substitution_faults(struct csh_state *state)
{
    struct csh_execution_context context = {0};
    struct csh_ast *tree = parse("CAPTURE=$(printf payload)\n");
    struct csh_execution result;
    struct csh_error error;
    struct csh_variable_view view;
    size_t point, baseline = live, i;
    int before = fd_count(), status, kind;
    context.state = state;
    for (point = 1; point < 2048; ++point) {
        int rc;
        arm(point);
        rc = csh_execute_context_ast(&context, tree, &result, &error);
        if (rc == 0) {
            assert(allocation_calls < point && result.status == 0);
            csh_state_get_variable(state, "CAPTURE", &view);
            assert(view.value && !strcmp(view.value, "payload"));
            assert(csh_state_unset_variable(state, "CAPTURE") == CSH_STATE_OK);
        } else {
            assert(error.system_errno == ENOMEM && result.status == 1);
            csh_state_get_variable(state, "CAPTURE", &view);
            assert(view.value == NULL);
        }
        for (i = 0; i < launched_count; ++i)
            assert(waitpid(launched[i], &status, WNOHANG) == -1 && errno == ECHILD);
        assert(fd_count() == before && live == baseline && context.child_count == 0);
        if (rc == 0) break;
    }
    assert(point < 2048);
    for (kind = 0; kind < 5; ++kind) {
        arm(0);
        if (kind == 0) fail_pipe = 1;
        if (kind == 1) fail_fork = 1;
        if (kind == 2) fail_setfd = 1;
        if (kind == 3) fail_wait = 1;
        if (kind == 4) fail_read = 1;
        assert(csh_execute_context_ast(&context, tree, &result, &error) == -1);
        csh_state_get_variable(state, "CAPTURE", &view);
        assert(view.value == NULL);
        for (i = 0; i < launched_count; ++i)
            assert(waitpid(launched[i], &status, WNOHANG) == -1 && errno == ECHILD);
        assert(fd_count() == before && live == baseline);
    }
    arm(0);
    interrupt_read = interrupt_wait = 1;
    assert(csh_execute_context_ast(&context, tree, &result, &error) == 0);
    assert(csh_state_unset_variable(state, "CAPTURE") == CSH_STATE_OK);
    assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
    assert(fd_count() == before && live == baseline);
    csh_ast_destroy(tree);
    csh_execution_context_destroy(&context);
    arm(0);
}

static void context_faults(struct csh_state *state)
{
    struct csh_execution_context context = {0};
    struct csh_execution result;
    struct csh_error error;
    struct csh_ast *tree;
    size_t baseline = live, point, i;
    int before = fd_count(), status, descriptors[2];
    char script[256];
    context.state = state;
    /* Sweep plan construction, nested redirect saves and ordinary dispatch.
     * Every allocation failure leaves all parent descriptors recoverable. */
    tree = parse("{ :; { :; } >context-fault-output; } >context-fault-outer\n");
    for (point = 1; point < 512; ++point) {
        int rc;
        arm(point);
        rc = csh_execute_context_ast(&context, tree, &result, &error);
        assert(rc == -1 || rc == 0);
        assert(live == baseline && fd_count() == before);
        if (allocation_calls < point) { assert(rc == 0 && result.status == 0); break; }
        assert(result.status == 1);
    }
    assert(point < 512);
    csh_ast_destroy(tree);
    tree = parse("exit 0 &\n");
    for (point = 1; point < 512; ++point) {
        int rc;
        size_t calls;
        arm(point);
        rc = csh_execute_context_ast(&context, tree, &result, &error);
        calls = allocation_calls;
        assert(rc == 0 || (error.system_errno == ENOMEM && launched_count == 0));
        assert(csh_execution_context_reap(&context, 1, &error) == 0);
        for (i = 0; i < launched_count; ++i)
            assert(waitpid(launched[i], &status, WNOHANG) == -1 && errno == ECHILD);
        assert(context.child_count == 0 && live == baseline && fd_count() == before);
        if (calls < point) break;
    }
    assert(point < 512);
    arm(0);
    fail_fork = 1;
    assert(csh_execute_context_ast(&context, tree, &result, &error) == -1);
    assert(context.child_count == 0 && live == baseline && fd_count() == before);
    csh_ast_destroy(tree);

    /* No timing assumption: head cannot exit until its parent writes a byte. */
    assert(pipe(descriptors) == 0);
    snprintf(script, sizeof(script), "/usr/bin/head -c 1 <&%d >/dev/null &\n", descriptors[0]);
    tree = parse(script);
    arm(0);
    assert(csh_execute_context_ast(&context, tree, &result, &error) == 0);
    assert(context.child_count == 1);
    fail_wait = 1;
    assert(csh_execution_context_reap(&context, 0, &error) == -1 && error.system_errno == EIO);
    assert(context.child_count == 1); /* Error retains ownership for retry. */
    interrupt_wait = 1;
    assert(write(descriptors[1], "x", 1) == 1);
    assert(csh_execution_context_reap(&context, 1, &error) == 0);
    assert(context.child_count == 0);
    assert(waitpid(launched[0], &status, WNOHANG) == -1 && errno == ECHILD);
    close(descriptors[0]); close(descriptors[1]);
    csh_ast_destroy(tree);

    tree = parse("(:)\n");
    arm(0);
    interrupt_wait = 1;
    assert(csh_execute_context_ast(&context, tree, &result, &error) == 0);
    assert(wait_calls >= 2 && result.status == 0);
    arm(0);
    fail_wait = 1;
    assert(csh_execute_context_ast(&context, tree, &result, &error) == -1);
    assert(waitpid(launched[0], &status, WNOHANG) == -1 && errno == ECHILD);
    csh_ast_destroy(tree);
    for (int asynchronous = 0; asynchronous < 2; ++asynchronous) {
    tree = parse(asynchronous ? "{ :; } | { :; } | { :; } &\n" : "{ :; } | { :; } | { :; }\n");
    for (int kind = 0; kind < 3; ++kind) {
        for (point = 1; point <= (kind == 0 ? 2u : 3u); ++point) {
            arm(0);
            if (kind == 0) fail_pipe = (int)point;
            if (kind == 1) fail_fork = (int)point;
            if (kind == 2) fail_wait = (int)point;
            assert(csh_execute_context_ast(&context, tree, &result, &error) == -1);
            assert(csh_execution_context_reap(&context, 1, &error) == 0);
            for (i = 0; i < launched_count; ++i)
                assert(waitpid(launched[i], &status, WNOHANG) == -1 && errno == ECHILD);
            assert(fd_count() == before && live == baseline);
        }
    }
    csh_ast_destroy(tree);
    }
    arm(0);
    csh_execution_context_destroy(&context);
    assert(fd_count() == before && live == baseline);
    assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
}

static void job_faults(struct csh_state *state)
{
    struct csh_execution_context context = {0};
    struct csh_execution result;
    struct csh_error error;
    struct csh_ast *tree;
    size_t baseline = live, point, i;
    int before = fd_count(), status;
    context.state = state;
    alarm(20);
    tree = parse("/bin/echo unsafe >/dev/null | /bin/cat | /bin/cat\n");
    /* Preparation and registration fail before releasing the launch barrier.
     * Each launched direct child must be dead/reaped after every failed fork,
     * pipe, allocation or wait. No descriptor or registered job leaks. */
    for (int kind = 0; kind < 4; ++kind) {
        for (point = 1; point < (kind == 0 ? 512u : 5u); ++point) {
            int rc;
            size_t calls;
            arm(0);
            assert(csh_jobs_create(&context.jobs, state, -1) == 0);
            arm(kind == 0 ? point : 0);
            if (kind == 1) fail_fork = (int)point;
            if (kind == 2) fail_pipe = (int)point;
            if (kind == 3) fail_wait = (int)point;
            rc = csh_execute_context_ast(&context, tree, &result, &error);
            calls = allocation_calls;
            assert(rc == 0 || rc == -1);
            fail_allocation = 0;
            fail_fork = fail_pipe = fail_wait = 0;
            csh_jobs_destroy(context.jobs);
            context.jobs = NULL;
            for (i = 0; i < launched_count; ++i)
                assert(waitpid(launched[i], &status, WNOHANG) == -1 && errno == ECHILD);
            assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
            assert(live == baseline && fd_count() == before);
            if (kind == 0 && calls < point) break;
        }
    }
    csh_ast_destroy(tree);
    arm(0);
    csh_execution_context_destroy(&context);
    assert(live == baseline && fd_count() == before);
}

static void terminal_job_faults(struct csh_state *state)
{
    struct csh_execution_context context = {0};
    struct csh_execution result;
    struct csh_error error;
    struct csh_ast *tree;
    struct termios original, after;
    size_t baseline = live;
    int before = fd_count(), status;
    context.state = state;
    alarm(10);
    assert(tcgetattr(0, &original) == 0);
    tree = parse("/bin/echo unsafe >/dev/null | /bin/cat | /bin/cat\n");
    for (int kind = 0; kind < 4; ++kind) {
        for (int point = 1; point <= (kind == 0 ? 3 : kind == 1 ? 2 : kind == 2 ? 1 : 3); ++point) {
            arm(0);
            assert(csh_jobs_create(&context.jobs, state, 0) == 0);
            assert(csh_jobs_monitor(context.jobs));
            arm(0);
            if (kind == 0) fail_group = point;
            if (kind == 1) fail_terminal = point;
            if (kind == 2) fail_modes = point;
            if (kind == 3) fail_wait = point;
            assert(csh_execute_context_ast(&context, tree, &result, &error) == -1);
            assert(tcgetpgrp(0) == getpgrp());
            assert(tcgetattr(0, &after) == 0);
            assert(original.c_lflag == after.c_lflag);
            assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
            arm(0);
            csh_jobs_destroy(context.jobs);
            context.jobs = NULL;
            assert(live == baseline && fd_count() == before);
        }
    }
    csh_ast_destroy(tree);
    tree = parse("/usr/bin/true\n");
    /* Deliver terminal signals inside the fork wrapper, before the child can
     * reset inherited shell handlers. They must remain pending until reset. */
    for (int i = 0; i < 2; ++i) {
        sigset_t original_mask, after_mask;
        int sent = i == 0 ? SIGINT : SIGTSTP;
        arm(0);
        assert(csh_jobs_create(&context.jobs, state, 0) == 0);
        assert(sigprocmask(SIG_SETMASK, NULL, &original_mask) == 0);
        launch_signal = sent;
        assert(csh_execute_context_ast(&context, tree, &result, &error) == 0);
        if (result.status != 128 + sent)
            fprintf(stderr, "launch signal %d returned %d\n", sent, result.status);
        assert(result.status == 128 + sent);
        assert(tcgetpgrp(0) == getpgrp());
        assert(sigprocmask(SIG_SETMASK, NULL, &after_mask) == 0);
        assert(sigismember(&original_mask, sent) == sigismember(&after_mask, sent));
        if (sent == SIGTSTP) {
            char *kill_args[] = {"kill", "-KILL", "%1", NULL};
            char *wait_args[] = {"wait", NULL};
            struct csh_command kill_command = {0}, wait_command = {0};
            kill_command.argc = 3; kill_command.argv = kill_args;
            wait_command.argc = 1; wait_command.argv = wait_args;
            assert(csh_jobs_builtin(context.jobs, &kill_command) == 0);
            assert(csh_jobs_builtin(context.jobs, &wait_command) == 0);
        }
        arm(0);
        csh_jobs_destroy(context.jobs);
        context.jobs = NULL;
        assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
        assert(live == baseline && fd_count() == before);
    }
    csh_ast_destroy(tree);
    puts("terminal job failure cleanup passed");
}

static void control_faults(struct csh_state *state)
{
    const char *parameters[] = {"caller", "second"};
    const char *scripts[] = {
        "f child",
        "PATH=/bin:/usr/bin PATH=/usr/bin:/bin pwd >control-output",
        "PATH=absent pwd >control-output",
        "outer() { inner() { return 7; } >control-output; TEMP=child inner arg; }; TEMP=outer outer call",

        "eval 'value=shared; for x in a b; do :; done' >control-output",
        "command eval 'value=shared; :'; command -p true",
        "eval '. ./evaluation-source inner' >control-output",
        "read -r first second <evaluation-source",
        "getopts ab: option -abvalue",
        "hash printf; hash -r; :",

        "for x; do if :; then case $x in c*) :;; *) :;; esac; fi; done >control-output",
        "for x in a b; do :; done; until :; do :; done; while :; do break; done",
        "f() { f() { :; }; return 7; }; f child",
        "f() { unset -f f; return 7; }; f child",
        "f() { case ${missing:?required} in *) :;; esac; }; f child"
    };
    struct csh_execution_context context = {0};
    struct csh_execution result;
    struct csh_error error;
    struct csh_ast *definition;
    size_t baseline, i, point;
    int before = fd_count();
    assert(csh_state_set_parameters(state, 2, parameters) == CSH_STATE_OK);
    context.state = state;
    {
        FILE *source = fopen("evaluation-source", "w");
        assert(source != NULL);
        assert(fputs("value=from_source\nreturn 7\n", source) >= 0);
        assert(fclose(source) == 0);
    }
    definition = parse("f() { for x in a b; do case $x in a) continue;; b) return 7;; esac; done; } >control-output");
    assert(csh_execute_context_ast(&context, definition, &result, &error) == 0);
    csh_ast_destroy(definition); /* State must retain the definition. */
    baseline = live;
    for (i = 0; i < sizeof(scripts) / sizeof(scripts[0]); ++i) {
        struct csh_ast *tree = parse(scripts[i]);
        for (point = 1; point < 4096; ++point) {
            struct csh_state *copy = NULL;
            struct csh_state_info info;
            size_t calls;
            int rc;
            arm(0);
            assert(csh_state_clone(state, &copy) == CSH_STATE_OK);
            context.state = copy;
            arm(point);
            rc = csh_execute_context_ast(&context, tree, &result, &error);
            calls = allocation_calls;
            fail_allocation = 0;
            assert(rc == 0 || rc == -1);
            assert(strcmp(csh_state_parameter(copy, 1), "caller") == 0);
            assert(strcmp(csh_state_parameter(copy, 2), "second") == 0);
            csh_state_get_info(copy, &info);
            assert(info.argument_count == 2 && info.function_depth == 0);
            assert(context.loop_depth == 0);
            {
                struct csh_variable_view original, restored;
                assert(csh_state_get_variable(state, "PATH", &original) == CSH_STATE_OK);
                assert(csh_state_get_variable(copy, "PATH", &restored) == CSH_STATE_OK);
                assert(original.attributes == restored.attributes);
                assert(original.value == NULL ? restored.value == NULL :
                    restored.value != NULL && !strcmp(original.value, restored.value));
                assert(csh_state_get_variable(copy, "TEMP", &restored) == CSH_STATE_OK);
                assert(restored.value == NULL && restored.attributes == 0);
            }
            csh_execution_context_destroy(&context);
            csh_state_destroy(copy);
            assert(live == baseline && fd_count() == before);
            if (calls < point) break;
        }
        assert(point < 4096);
        csh_ast_destroy(tree);
    }
    arm(0);
    context.state = state;
    /* Prepared dispatch shares function lookup and parameter restoration. */
    {
        char *arguments[] = {"f", "child", NULL};
        struct csh_command command = {0};
        struct csh_pipeline_result pipeline = {0};
        command.argv = arguments;
        command.argc = 2;
        assert(csh_execute_command(NULL, &command, &result, &error) == -1);
        assert(csh_execute_command(state, &command, &result, &error) == 0);
        assert(result.status == 7 && result.category == CSH_EXEC_FUNCTION);
        assert(csh_execute_pipeline(state, &command, 1, 0, &pipeline, &error) == 0);
        assert(pipeline.execution.status == 7);
        csh_pipeline_result_destroy(&pipeline);
        assert(strcmp(csh_state_parameter(state, 1), "caller") == 0);
    }
    /* A failed definition replacement leaves the old body callable. */
    definition = parse("f() { return 9; }");
    for (point = 1; point < 4096; ++point) {
        struct csh_state *copy = NULL;
        struct csh_function *old = csh_state_function(state, "f");
        size_t calls;
        int rc;
        arm(0);
        assert(csh_state_clone(state, &copy) == CSH_STATE_OK);
        context.state = copy;
        arm(point);
        rc = csh_execute_context_ast(&context, definition, &result, &error);
        calls = allocation_calls;
        fail_allocation = 0;
        if (rc == -1) assert(csh_state_function(copy, "f") == old);
        csh_execution_context_destroy(&context);
        csh_state_destroy(copy);
        if (calls < point) break;
    }
    csh_ast_destroy(definition);
    arm(0);
}

int main(int argc, char **argv)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state = NULL;
    invocation.mode = CSH_MODE_STRING;
    invocation.arg0 = "execute-faults";
    if (argc == 2 && strcmp(argv[1], "--control") == 0) {
        assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
        control_faults(state);
        csh_state_destroy(state);
        assert(live == 0);
        puts("control flow fault checks passed");
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "--jobs-terminal") == 0) {
        invocation.interactive = 1;
        assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
        terminal_job_faults(state);
        csh_state_destroy(state);
        assert(live == 0);
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "--jobs") == 0) {
        assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
        job_faults(state);
        csh_state_destroy(state);
        assert(live == 0);
        puts("job launch and ownership fault checks passed");
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "--substitution") == 0) {
        assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
        substitution_faults(state);
        csh_state_destroy(state);
        assert(live == 0);
        puts("substitution fault checks passed");
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "--context") == 0) {
        assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
        context_faults(state);
        csh_state_destroy(state);
        assert(live == 0);
        puts("context fault checks passed");
        return 0;
    }
    if (argc == 2 && strcmp(argv[1], "--pipeline") == 0) {
        assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
        pipeline_faults(state);
        csh_state_destroy(state);
        assert(live == 0);
        puts("pipeline fault checks passed");
        return 0;
    }
    assert(argc == 1);
    adapter_faults();
    assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
    dispatch_faults(state);
    process_faults(state);
    csh_state_destroy(state);
    assert(live == 0);
    assignment_batch_faults();
    puts("execution fault checks passed");
    return 0;
}
