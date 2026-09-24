#include "cshell/input.h"

#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

struct csh_input {
    char *name;
    unsigned char *text;
    size_t text_length;
    size_t text_offset;
    int fd;
    unsigned char *buffer;
    size_t capacity;
    struct csh_position position;
    int ended;
    struct csh_error failure;
    int (*wait_hook)(void *, int);
    void *wait_context;
};

static void clear_error(struct csh_error *error)
{
    memset(error, 0, sizeof(*error));
}

static int fail(struct csh_error *error, const char *message, int number,
                int status)
{
    clear_error(error);
    error->message = message;
    error->system_errno = number;
    error->status = status;
    error->position.line = 1;
    error->position.column = 1;
    return -1;
}

static struct csh_input *allocate_input(const char *name,
                                         struct csh_error *error)
{
    struct csh_input *input = malloc(sizeof(*input));
    size_t length;

    if (input == NULL) {
        fail(error, "cannot allocate input source", ENOMEM, 1);
        return NULL;
    }
    memset(input, 0, sizeof(*input));
    input->fd = -1;
    input->position.line = 1;
    input->position.column = 1;
    length = strlen(name);
    input->name = malloc(length + 1);
    if (input->name == NULL) {
        free(input);
        fail(error, "cannot allocate source name", ENOMEM, 1);
        return NULL;
    }
    memcpy(input->name, name, length + 1);
    return input;
}

int csh_input_from_string(struct csh_input **out, const char *text,
                          const char *name, struct csh_error *error)
{
    struct csh_input *input;

    *out = NULL;
    clear_error(error);
    if (text == NULL || name == NULL)
        return fail(error, "invalid string input", EINVAL, 2);
    input = allocate_input(name, error);
    if (input == NULL)
        return -1;
    input->text_length = strlen(text);
    input->text = malloc(input->text_length + 1);
    if (input->text == NULL) {
        csh_input_destroy(input);
        return fail(error, "cannot allocate command string", ENOMEM, 1);
    }
    memcpy(input->text, text, input->text_length + 1);
    *out = input;
    return 0;
}

/* Keep internal descriptors out of the standard descriptor slots and close
 * them across exec. Duplication never consumes or closes a borrowed fd. */
static int duplicate_fd(int fd)
{
    int result;
    do {
        result = fcntl(fd, F_DUPFD_CLOEXEC, 10);
    } while (result == -1 && errno == EINTR);
    return result;
}

int csh_input_from_file(struct csh_input **out, const char *path,
                        struct csh_error *error)
{
    struct csh_input *input;
    struct stat info;
    int fd;
    int number;

    *out = NULL;
    clear_error(error);
    if (path == NULL)
        return fail(error, "invalid script path", EINVAL, 2);
    input = allocate_input(path, error);
    if (input == NULL)
        return -1;
    do {
        fd = open(path, O_RDONLY | O_CLOEXEC);
    } while (fd == -1 && errno == EINTR);
    if (fd == -1) {
        number = errno;
        csh_input_destroy(input);
        return fail(error, "cannot open script", number,
                    number == ENOENT || number == ENOTDIR ? 127 : 1);
    }
    if (fstat(fd, &info) == -1) {
        number = errno;
        close(fd);
        csh_input_destroy(input);
        return fail(error, "cannot inspect script", number, 1);
    }
    if (S_ISDIR(info.st_mode)) {
        close(fd);
        csh_input_destroy(input);
        return fail(error, "script is a directory", EISDIR, 1);
    }
    input->fd = duplicate_fd(fd);
    number = errno;
    close(fd);
    if (input->fd == -1) {
        csh_input_destroy(input);
        return fail(error, "cannot retain script descriptor", number, 1);
    }
    *out = input;
    return 0;
}

int csh_input_from_fd(struct csh_input **out, int fd, const char *name,
                      struct csh_error *error)
{
    struct csh_input *input;
    struct stat info;
    int flags;
    int number;

    *out = NULL;
    clear_error(error);
    if (name == NULL)
        return fail(error, "invalid input name", EINVAL, 2);
    input = allocate_input(name, error);
    if (input == NULL)
        return -1;
    input->fd = duplicate_fd(fd);
    if (input->fd == -1) {
        number = errno;
        csh_input_destroy(input);
        return fail(error, "cannot duplicate input descriptor", number, 1);
    }
    if (fstat(input->fd, &info) == -1 ||
        (flags = fcntl(input->fd, F_GETFL)) == -1) {
        number = errno;
        csh_input_destroy(input);
        return fail(error, "cannot inspect input descriptor", number, 1);
    }
    /* sh's STDIN contract requires blocking reads on FIFO/terminal input.
     * File status flags belong to the shared open file description. */
    if ((flags & O_NONBLOCK) != 0 &&
        (S_ISFIFO(info.st_mode) || isatty(input->fd))) {
        if (fcntl(input->fd, F_SETFL, flags & ~O_NONBLOCK) == -1) {
            number = errno;
            csh_input_destroy(input);
            return fail(error, "cannot enable blocking input", number, 1);
        }
    }
    *out = input;
    return 0;
}

void csh_input_destroy(struct csh_input *input)
{
    if (input == NULL)
        return;
    if (input->fd != -1)
        close(input->fd);
    free(input->buffer);
    free(input->text);
    free(input->name);
    free(input);
}

const char *csh_input_name(const struct csh_input *input)
{
    return input->name;
}

struct csh_position csh_input_position(const struct csh_input *input)
{
    return input->position;
}

static int reserve(struct csh_input *input, size_t needed)
{
    size_t capacity = input->capacity == 0 ? 128 : input->capacity;
    unsigned char *buffer;

    if (needed <= input->capacity)
        return 0;
    while (capacity < needed) {
        if (capacity > SIZE_MAX / 2) {
            capacity = needed;
            break;
        }
        capacity *= 2;
    }
    buffer = realloc(input->buffer, capacity);
    if (buffer == NULL)
        return -1;
    input->buffer = buffer;
    input->capacity = capacity;
    return 0;
}

void csh_input_set_wait_hook(struct csh_input *input,
    int (*hook)(void *context, int fd), void *context)
{
    input->wait_hook = hook;
    input->wait_context = context;
}

static int next_byte(struct csh_input *input, unsigned char *byte)
{
    ssize_t count;

    if (input->text != NULL) {
        if (input->text_offset == input->text_length)
            return 0;
        *byte = input->text[input->text_offset++];
        return 1;
    }
    do {
        if (input->wait_hook != NULL &&
            input->wait_hook(input->wait_context, input->fd) == -1) return -1;
        count = read(input->fd, byte, 1);
    } while (count == -1 && errno == EINTR);
    return (int)count;
}

static enum csh_input_result read_failure(struct csh_input *input,
    struct csh_error *error, const char *message, int number, int status)
{
    fail(error, message, number, status);
    error->position = input->position;
    input->failure = *error;
    /* Discard the partial line; later calls return this same error. */
    free(input->buffer);
    input->buffer = NULL;
    input->capacity = 0;
    return CSH_INPUT_ERROR;
}

enum csh_input_result csh_input_read_line(struct csh_input *input,
    struct csh_input_line *line, struct csh_error *error)
{
    struct csh_position start = input->position;
    size_t length = 0;
    unsigned char byte;
    int result;

    memset(line, 0, sizeof(*line));
    clear_error(error);
    if (input->failure.status != 0) {
        *error = input->failure;
        return CSH_INPUT_ERROR;
    }
    if (input->ended)
        return CSH_INPUT_EOF;
    for (;;) {
        /* Reserve before consuming a byte, including room for trailing NUL. */
        if (length > SIZE_MAX - 2 || reserve(input, length + 2) == -1)
            return read_failure(input, error, "cannot grow input line", ENOMEM, 1);
        if (input->position.offset == SIZE_MAX ||
            input->position.line == SIZE_MAX ||
            input->position.column == SIZE_MAX)
            return read_failure(input, error, "input position overflow", EOVERFLOW, 1);
        result = next_byte(input, &byte);
        if (result == -1)
            return read_failure(input, error, "cannot read input", errno, 128);
        if (result == 0) {
            input->ended = 1;
            if (length == 0)
                return CSH_INPUT_EOF;
            break;
        }
        input->buffer[length++] = byte;
        input->position.offset++;
        if (byte == '\n') {
            input->position.line++;
            input->position.column = 1;
            break;
        }
        input->position.column++;
    }
    input->buffer[length] = '\0';
    line->data = input->buffer;
    line->length = length;
    line->start = start;
    line->end = input->position;
    return CSH_INPUT_LINE;
}
