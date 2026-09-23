/* Replacement-only API driver. JSON is a test protocol, not shell output. */
#include "cshell/input.h"
#include "cshell/invocation.h"

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static void json_bytes(const unsigned char *value, size_t length)
{
    size_t i;

    putchar('"');
    for (i = 0; i < length; i++) {
        unsigned char byte = value[i];
        if (byte == '"' || byte == '\\') {
            putchar('\\');
            putchar(byte);
        } else if (byte < 32 || byte > 126) {
            printf("\\u%04x", (unsigned int)byte);
        } else {
            putchar(byte);
        }
    }
    putchar('"');
}

static void json_string(const char *value)
{
    if (value == NULL) {
        fputs("null", stdout);
    } else {
        json_bytes((const unsigned char *)value, strlen(value));
    }
}

static void json_position(struct csh_position position)
{
    printf("[%zu,%zu,%zu]", position.offset, position.line, position.column);
}

static void json_error(const struct csh_error *error)
{
    fputs("{\"error\":", stdout);
    json_string(error->message);
    printf(",\"errno\":%d,\"status\":%d,\"argument_index\":%zu,\"position\":",
        error->system_errno, error->status, error->argument_index);
    json_position(error->position);
    puts("}");
}

static void require(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "fixture assertion failed: %s\n", message);
        exit(90);
    }
}

static void dump_input(struct csh_input *input)
{
    struct csh_input_line line;
    struct csh_error error;
    enum csh_input_result result;
    size_t lines = 0;
    int repeats;

    fputs("\"source\":", stdout);
    json_string(csh_input_name(input));
    fputs(",\"lines\":[", stdout);
    while ((result = csh_input_read_line(input, &line, &error)) == CSH_INPUT_LINE) {
        require(error.message == NULL && error.status == 0 && error.system_errno == 0,
            "successful read clears diagnostic");
        require(line.data[line.length] == '\0', "convenience NUL after line");
        if (lines++ != 0) {
            putchar(',');
        }
        fputs("{\"data\":", stdout);
        json_bytes(line.data, line.length);
        fputs(",\"start\":", stdout);
        json_position(line.start);
        fputs(",\"end\":", stdout);
        json_position(line.end);
        putchar('}');
    }
    require(result == CSH_INPUT_EOF, "source reaches EOF, not an error");
    require(line.data == NULL && line.length == 0, "EOF clears line");
    for (repeats = 0; repeats < 3; repeats++) {
        /* Sentinel fields ensure EOF does not leave stale caller data. */
        line.data = (const unsigned char *)"stale";
        line.length = 5;
        require(csh_input_read_line(input, &line, &error) == CSH_INPUT_EOF,
            "EOF remains sticky");
        require(line.data == NULL && line.length == 0, "repeated EOF clears line");
    }
    fputs("],\"position\":", stdout);
    json_position(csh_input_position(input));
    fputs(",\"eof_repeats\":3", stdout);
}

static void dump_invocation(const struct csh_invocation *invocation, int with_input)
{
    const char *mode = invocation->mode == CSH_MODE_STRING ? "string" :
        invocation->mode == CSH_MODE_FILE ? "file" : "stdin";
    size_t i;

    printf("{\"mode\":\"%s\",\"interactive\":%s,\"arg0\":", mode,
        invocation->interactive ? "true" : "false");
    json_string(invocation->arg0);
    fputs(",\"arguments\":[", stdout);
    for (i = 0; i < invocation->argument_count; i++) {
        if (i != 0) {
            putchar(',');
        }
        json_string(invocation->arguments[i]);
    }
    require(invocation->arguments[invocation->argument_count] == NULL,
        "argument vector is NULL-terminated");
    fputs("],\"primary\":", stdout);
    json_string(csh_invocation_prompt(invocation, 0, "primary> ", "more> "));
    fputs(",\"secondary\":", stdout);
    json_string(csh_invocation_prompt(invocation, 1, "primary> ", "more> "));
    if (with_input) {
        putchar(',');
        dump_input(invocation->input);
    }
    puts("}");
}

static int invocation_command(int argc, char **argv, int with_input, int quiet,
    int mutate_arguments)
{
    struct csh_invocation invocation;
    struct csh_error error;
    char **shell_argv = calloc((size_t)argc + 1, sizeof(*shell_argv));
    int i;
    int result;

    require(shell_argv != NULL, "allocate fixture argument vector");
    shell_argv[0] = strdup("fixture-shell");
    require(shell_argv[0] != NULL, "allocate fixture argv[0]");
    for (i = 1; i < argc; i++) {
        shell_argv[i] = strdup(argv[i]);
        require(shell_argv[i] != NULL, "allocate fixture argument");
    }
    result = csh_invocation_parse(&invocation, argc, shell_argv,
        STDIN_FILENO, STDERR_FILENO, &error);
    if (mutate_arguments) {
        for (i = 0; i < argc; i++) {
            memset(shell_argv[i], '#', strlen(shell_argv[i]));
        }
    }
    for (i = 0; i < argc; i++) {
        free(shell_argv[i]);
    }
    free(shell_argv);
    if (result != 0) {
        require(invocation.input == NULL && invocation.arg0 == NULL &&
            invocation.arguments == NULL && invocation.argument_count == 0,
            "failed parse zeroes owned fields");
        json_error(&error);
    } else if (!quiet) {
        dump_invocation(&invocation, with_input);
    }
    csh_invocation_destroy(&invocation);
    return 0;
}

static void snapshot_fds(int *snapshot, size_t count)
{
    size_t i;
    for (i = 0; i < count; i++) {
        snapshot[i] = fcntl((int)i, F_GETFD);
    }
}

static int new_owned_fd(const int *before, size_t count)
{
    size_t i;
    int owned = -1;
    for (i = 0; i < count; i++) {
        if (before[i] < 0 && fcntl((int)i, F_GETFD) >= 0) {
            require(owned == -1, "exactly one new descriptor");
            owned = (int)i;
        }
    }
    require(owned >= 0, "find owned descriptor");
    require((fcntl(owned, F_GETFD) & FD_CLOEXEC) != 0,
        "owned descriptor is close-on-exec");
    return owned;
}

static int fd_contract(void)
{
    int pipe_fds[2];
    int before[256];
    int owned;
    int flags;
    char remaining[8];
    struct csh_input *input;
    struct csh_input_line line;
    struct csh_error error;

    require(pipe(pipe_fds) == 0, "create pipe");
    require(write(pipe_fds[1], "first\nsecond", 12) == 12, "seed pipe");
    require(close(pipe_fds[1]) == 0, "close pipe writer");
    flags = fcntl(pipe_fds[0], F_GETFL);
    require(flags >= 0 && fcntl(pipe_fds[0], F_SETFL, flags | O_NONBLOCK) == 0,
        "set pipe nonblocking before construction");
    snapshot_fds(before, sizeof(before) / sizeof(before[0]));
    require(csh_input_from_fd(&input, pipe_fds[0], "borrowed", &error) == 0,
        "construct descriptor input");
    owned = new_owned_fd(before, sizeof(before) / sizeof(before[0]));
    require(fcntl(pipe_fds[0], F_GETFD) == before[pipe_fds[0]],
        "borrowed descriptor flags preserved");
    require((fcntl(pipe_fds[0], F_GETFL) & O_NONBLOCK) == 0,
        "shared pipe is made blocking");
    require(csh_input_read_line(input, &line, &error) == CSH_INPUT_LINE &&
        line.length == 6 && memcmp(line.data, "first\n", 6) == 0,
        "read one physical line");
    require(read(pipe_fds[0], remaining, sizeof(remaining)) == 6 &&
        memcmp(remaining, "second", 6) == 0,
        "descriptor source does not read ahead beyond newline");
    csh_input_destroy(input);
    errno = 0;
    require(fcntl(owned, F_GETFD) == -1 && errno == EBADF,
        "destroy closes owned duplicate");
    require(fcntl(pipe_fds[0], F_GETFD) >= 0,
        "destroy preserves borrowed descriptor");
    require(close(pipe_fds[0]) == 0, "close original descriptor");
    puts("ok");
    return 0;
}

static int ownership(void)
{
    char text[] = "owned\nlast";
    char name[] = "owned-name";
    char path[] = "/tmp/cshell-input-fixture-XXXXXX";
    int file_fd;
    int owned;
    int before[256];
    struct csh_input *input;
    struct csh_input_line line;
    struct csh_error error;

    require(csh_input_from_string(&input, text, name, &error) == 0,
        "construct owned string");
    memset(text, '#', sizeof(text) - 1);
    memset(name, '#', sizeof(name) - 1);
    require(strcmp(csh_input_name(input), "owned-name") == 0, "copy source name");
    require(csh_input_read_line(input, &line, &error) == CSH_INPUT_LINE &&
        line.length == 6 && memcmp(line.data, "owned\n", 6) == 0,
        "copy string source bytes");
    csh_input_destroy(input);
    file_fd = mkstemp(path);
    require(file_fd >= 0 && close(file_fd) == 0, "create file source");
    snapshot_fds(before, sizeof(before) / sizeof(before[0]));
    require(csh_input_from_file(&input, path, &error) == 0, "open file source");
    owned = new_owned_fd(before, sizeof(before) / sizeof(before[0]));
    require(unlink(path) == 0, "unlink temporary file");
    csh_input_destroy(input);
    errno = 0;
    require(fcntl(owned, F_GETFD) == -1 && errno == EBADF,
        "destroy closes owned file");
    csh_input_destroy(NULL);
    puts("ok");
    return 0;
}

int main(int argc, char **argv)
{
    struct csh_input *input = NULL;
    struct csh_error error;
    int result;

    require(argc >= 2, "fixture subcommand required");
    if (strcmp(argv[1], "invoke") == 0 || strcmp(argv[1], "meta") == 0 ||
        strcmp(argv[1], "quiet") == 0 || strcmp(argv[1], "invoke-owned") == 0) {
        return invocation_command(argc - 1, argv + 1,
            strcmp(argv[1], "meta") != 0, strcmp(argv[1], "quiet") == 0,
            strcmp(argv[1], "invoke-owned") == 0);
    }
    if (strcmp(argv[1], "ownership") == 0) {
        return ownership();
    }
    if (strcmp(argv[1], "fd-contract") == 0) {
        return fd_contract();
    }
    if (strcmp(argv[1], "string") == 0) {
        require(argc == 3, "string operand required");
        result = csh_input_from_string(&input, argv[2], "fixture-string", &error);
    } else if (strcmp(argv[1], "file") == 0) {
        require(argc == 3, "file operand required");
        result = csh_input_from_file(&input, argv[2], &error);
    } else {
        require(strcmp(argv[1], "fd") == 0, "known fixture subcommand");
        result = csh_input_from_fd(&input, STDIN_FILENO, "fixture-stdin", &error);
    }
    if (result != 0) {
        require(input == NULL, "failed constructor clears result");
        json_error(&error);
    } else {
        putchar('{');
        dump_input(input);
        puts("}");
    }
    csh_input_destroy(input);
    return 0;
}
