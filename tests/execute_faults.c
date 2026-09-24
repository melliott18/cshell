#define CSHELL_EXECUTE_FAULT_IMPLEMENTATION
#include "execute_faults.h"
#include "cshell/execute.h"
#include "cshell/parser.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static void *allocations[4096];
static size_t live, allocation_calls, fail_allocation;
static int fail_open, fail_dup, fail_dup2, fail_temp, fail_fork, interrupt_wait;
static unsigned wait_calls;

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
    return fcntl(fd, operation, argument);
}

pid_t csh_execute_fault_fork(void)
{
    if (fail_fork && --fail_fork == 0) { errno = EAGAIN; return -1; }
    return fork();
}

pid_t csh_execute_fault_waitpid(pid_t pid, int *status, int options)
{
    assert(pid > 0); /* Never consume children owned by another subsystem. */
    ++wait_calls;
    if (interrupt_wait) { interrupt_wait = 0; errno = EINTR; return -1; }
    return waitpid(pid, status, options);
}

static void arm(size_t allocation)
{
    allocation_calls = 0;
    fail_allocation = allocation;
    fail_open = fail_dup = fail_dup2 = fail_temp = fail_fork = interrupt_wait = 0;
    wait_calls = 0;
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
    const char *scripts[] = {
        "cd 'two words' '' \\\" $'line\\n' >target 3<&0 4>&-\n",
        "A=one B='' A=two cd . <<'ONE' <<'TWO'\nfirst\nONE\nsecond\nTWO\n"
    };
    size_t variant;
    for (variant = 0; variant < sizeof(scripts) / sizeof(scripts[0]); ++variant) {
        struct csh_ast *tree = parse(scripts[variant]);
        size_t point;
        for (point = 1; point < 256; ++point) {
            struct csh_command command = {0};
            struct csh_error error;
            int returned;
            assert(live == 0);
            arm(point);
            returned = csh_command_from_ast(tree, &command, &error);
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
            assert(live == 0);
            if (returned == 0) break;
        }
        assert(point < 256);
        csh_ast_destroy(tree);
    }
    arm(0);
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

int main(void)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state = NULL;
    invocation.mode = CSH_MODE_STRING;
    invocation.arg0 = "execute-faults";
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
