/* Deliberately links only replacement modules; this is not the shell runtime. */
#include "cshell/execute.h"
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
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;

static struct csh_state *make_state(void)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state = NULL;
    invocation.mode = CSH_MODE_STRING;
    invocation.arg0 = "execute-fixture";
    assert(csh_state_create(&state, &invocation, environ) == CSH_STATE_OK);
    return state;
}

static int run_script(struct csh_state *state, const char *text)
{
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_error error;
    struct csh_ast *tree = NULL;
    struct csh_execution result = {0};
    enum csh_parse_result parsed;
    int status = 0;
    assert(csh_input_from_string(&input, text, "execute-fixture", &error) == 0);
    assert(csh_parser_create(&parser, input, &error) == 0);
    while ((parsed = csh_parser_next(parser, &tree, &error)) == CSH_PARSE_TREE) {
        struct csh_state_info info;
        int dispatched = csh_execute_ast(state, tree, &result, &error);
        csh_ast_destroy(tree);
        tree = NULL;
        assert(csh_state_get_info(state, &info) == CSH_STATE_OK);
        assert(info.last_status == result.status);
        status = result.status;
        if (dispatched < 0) {
            assert(error.message != NULL);
            if (!error.reported) fprintf(stderr, "execute-fixture: %s\n", csh_error_message(&error));
            break;
        }
        assert(error.message == NULL);
        if (result.exit_requested) break;
    }
    if (parsed == CSH_PARSE_ERROR || parsed == CSH_PARSE_INCOMPLETE) {
        fprintf(stderr, "parse-fixture: %s\n", error.message);
        status = 2;
    }
    csh_ast_destroy(tree);
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    return status;
}

static int fd_count(void)
{
    int fd, count = 0;
    for (fd = 0; fd < 256; ++fd)
        if (fcntl(fd, F_GETFD) >= 0) ++count;
    return count;
}

static void api_checks(struct csh_state *state)
{
    struct csh_error error;
    struct csh_execution result;
    struct csh_command command = {0};
    struct csh_assignment assignment = {"9NAME", "value"};
    struct csh_redirect redirs[3] = {{0}};
    struct csh_redirect_save *save = NULL;
    char *cd_args[] = {"cd", ".", NULL};
    char *exit_args[] = {"exit", "23", NULL};
    char *failed_args[] = {"cd", "/missing-cshell-test-directory", NULL};
    int original = open("/dev/null", O_RDONLY);
    int target = 40, before, closed_source;
    struct stat expected, actual;
    size_t body_length = 1024 * 1024, offset;
    unsigned char *body = malloc(body_length);
    unsigned char received[8192];
    pid_t unrelated;
    int status;
    siginfo_t child_info;
    assert(body != NULL);
    for (offset = 0; offset < body_length; ++offset) body[offset] = (unsigned char)(offset % 251);
    assert(original >= 0 && dup2(original, target) == target);
    assert(fcntl(target, F_SETFD, FD_CLOEXEC) == 0);
    assert(fstat(target, &expected) == 0);
    close(original);
    original = -1;
    close(41);
    before = fd_count();
    redirs[0].kind = CSH_REDIRECT_WRITE;
    redirs[0].fd = target;
    redirs[0].path = "api-output";
    redirs[1].kind = CSH_REDIRECT_DUP_WRITE;
    redirs[1].fd = 41;
    redirs[1].source_fd = target;
    command.argv = cd_args;
    command.argc = 2;
    command.redirections = redirs;
    command.redirection_count = 2;
    assert(csh_execute_command(state, &command, &result, &error) == 0);
    assert(result.status == 0 && result.category == CSH_EXEC_REGULAR_BUILTIN);
    assert(!result.exit_requested);
    assert(fstat(target, &actual) == 0 && actual.st_dev == expected.st_dev &&
        actual.st_ino == expected.st_ino);
    assert(fcntl(target, F_GETFD) == FD_CLOEXEC);
    assert(fcntl(41, F_GETFD) == -1 && errno == EBADF);
    assert(fd_count() == before);
    command.argv = failed_args;
    assert(csh_execute_command(state, &command, &result, &error) == 0);
    assert(result.status != 0 && !result.exit_requested);
    assert(fcntl(target, F_GETFD) == FD_CLOEXEC && fd_count() == before);
    command.argv = exit_args;
    assert(csh_execute_command(state, &command, &result, &error) == 0);
    assert(result.status == 23 && result.exit_requested);
    assert(result.category == CSH_EXEC_SPECIAL_BUILTIN);
    assert(fcntl(target, F_GETFD) == FD_CLOEXEC && fd_count() == before);
    /* A later open failure must undo earlier successful descriptor changes. */
    redirs[1].kind = CSH_REDIRECT_READ;
    redirs[1].path = "missing/input";
    command.argv = cd_args;
    assert(csh_execute_command(state, &command, &result, &error) == -1);
    assert(result.status != 0 && !result.exit_requested && error.message != NULL);
    assert(fcntl(target, F_GETFD) == FD_CLOEXEC && fd_count() == before);
    /* Saving descriptor 41 may not accidentally make it a valid dup operand. */
    redirs[1].kind = CSH_REDIRECT_DUP_WRITE;
    redirs[1].source_fd = 41;
    redirs[1].fd = 42;
    close(42);
    assert(csh_redirect_apply(redirs, 2, &save, &error) == -1 && save == NULL);
    assert(fcntl(41, F_GETFD) == -1 && fcntl(42, F_GETFD) == -1);
    assert(fcntl(target, F_GETFD) == FD_CLOEXEC && fd_count() == before);
    /* Use the first available descriptor so the backup allocator must skip a
     * closed source operand even when a runtime owns descriptor 3. */
    for (closed_source = 3; closed_source < target; ++closed_source) {
        if (fcntl(closed_source, F_GETFD) == -1) {
            assert(errno == EBADF);
            break;
        }
    }
    assert(closed_source < target);
    redirs[1].source_fd = closed_source;
    assert(csh_redirect_apply(redirs, 2, &save, &error) == -1 && save == NULL);
    assert(fcntl(closed_source, F_GETFD) == -1 && errno == EBADF);
    assert(fcntl(target, F_GETFD) == FD_CLOEXEC && fd_count() == before);
    /* A self-dup makes the target inheritable, then restores original flags. */
    redirs[0].kind = CSH_REDIRECT_DUP_READ;
    redirs[0].path = NULL;
    redirs[0].source_fd = target;
    assert(csh_redirect_apply(redirs, 1, &save, &error) == 0);
    assert(fcntl(target, F_GETFD) == 0);
    assert(csh_redirect_restore(&save, &error) == 0 && save == NULL);
    assert(fcntl(target, F_GETFD) == FD_CLOEXEC && fd_count() == before);
    /* Dup-output must reject an originally read-only source. */
    redirs[0].kind = CSH_REDIRECT_DUP_WRITE;
    redirs[0].fd = 41;
    assert(csh_redirect_apply(redirs, 1, &save, &error) == -1 && save == NULL);
    assert(fcntl(41, F_GETFD) == -1 && errno == EBADF);
    assert(fcntl(target, F_GETFD) == FD_CLOEXEC && fd_count() == before);
    redirs[0].fd = target;
    /* Prepared here-documents are byte counted and may contain embedded NUL. */
    redirs[0].kind = CSH_REDIRECT_HEREDOC;
    redirs[0].path = NULL;
    redirs[0].data = body;
    redirs[0].length = body_length;
    assert(csh_redirect_apply(redirs, 1, &save, &error) == 0);
    offset = 0;
    while (offset < body_length) {
        ssize_t amount = read(target, received, sizeof(received));
        assert(amount > 0 && (size_t)amount <= body_length - offset);
        assert(memcmp(body + offset, received, (size_t)amount) == 0);
        offset += (size_t)amount;
    }
    assert(read(target, received, sizeof(received)) == 0);
    assert(csh_redirect_restore(&save, &error) == 0 && save == NULL);
    assert(fcntl(target, F_GETFD) == FD_CLOEXEC && fd_count() == before);
    /* Validation rejects the complete vector before the first file is made. */
    redirs[0].kind = CSH_REDIRECT_WRITE;
    redirs[0].path = "invalid-side-effect";
    redirs[0].data = NULL;
    redirs[0].length = 0;
    redirs[1].fd = -1;
    assert(csh_redirect_apply(redirs, 2, &save, &error) == -1 && save == NULL);
    assert(access("invalid-side-effect", F_OK) == -1);
    command.redirection_count = 1;
    command.assignments = &assignment;
    command.assignment_count = 1;
    assert(csh_execute_command(state, &command, &result, &error) == -1);
    assert(result.status == 2 && error.message != NULL);
    assert(access("invalid-side-effect", F_OK) == -1);
    command.assignments = NULL;
    command.assignment_count = 0;
    /* Executor must not reap this other owner's already-exited child. */
    unrelated = fork();
    assert(unrelated >= 0);
    if (unrelated == 0) _exit(37);
    assert(waitid(P_PID, (id_t)unrelated, &child_info, WEXITED | WNOWAIT) == 0);
    assert(child_info.si_pid == unrelated);
    assert(run_script(state, "/bin/sh -c 'exit 9'\n") == 9);
    assert(waitpid(unrelated, &status, 0) == unrelated);
    assert(WIFEXITED(status) && WEXITSTATUS(status) == 37);
    close(target);
    free(body);
    puts("execution API checks passed");
}

int main(int argc, char **argv)
{
    struct csh_state *state = make_state();
    int status;
    if (argc == 2 && strcmp(argv[1], "--api") == 0) {
        api_checks(state);
        status = 0;
    } else {
        assert(argc == 2 || argc == 4);
        if (argc == 4) {
            /* Lookup uses even an unexported state PATH; env is a snapshot. */
            assert(strcmp(argv[1], "--state-path") == 0);
            assert(csh_state_set_variable(state, "PATH", argv[2]) == CSH_STATE_OK);
            assert(csh_state_update_attributes(state, "PATH", 0, CSH_VAR_EXPORT) == CSH_STATE_OK);
            assert(csh_state_set_variable(state, "PRIVATE", "secret") == CSH_STATE_OK);
            assert(csh_state_set_variable(state, "VISIBLE", "from-state") == CSH_STATE_OK);
            assert(csh_state_update_attributes(state, "VISIBLE", CSH_VAR_EXPORT, 0) == CSH_STATE_OK);
        }
        status = run_script(state, argv[argc - 1]);
    }
    csh_state_destroy(state);
    return status;
}
