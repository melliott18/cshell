#ifndef CSHELL_INPUT_H
#define CSHELL_INPUT_H

#include <stddef.h>

/* Byte offsets are zero-based; physical lines and byte columns are one-based. */
struct csh_position {
    size_t offset;
    size_t line;
    size_t column;
};

/* No allocated members. message is static; detail is an optional owned message.
 * csh_error_message selects the diagnostic; reported prevents duplicate output.
 * argument_index is zero if unknown.
 * status is a suggested shell failure status, not a request to exit. */
struct csh_error {
    const char *message;
    char detail[256]; /* Optional owned expansion diagnostic; survives struct copies. */
    int reported; /* Diagnostic already emitted under active redirections. */
    int system_errno;
    int status;
    size_t argument_index;
    struct csh_position position;
};

static inline const char *csh_error_message(const struct csh_error *error)
{
    return error->detail[0] ? error->detail : error->message;
}

struct csh_input;

/* Constructors copy strings and set *out to NULL on failure. Return 0 on
 * success, -1 on failure. error is required and cleared on success. */
int csh_input_from_string(struct csh_input **out, const char *text,
                          const char *name, struct csh_error *error);
int csh_input_from_file(struct csh_input **out, const char *path,
                        struct csh_error *error);
/* Duplicates fd with close-on-exec; never closes the borrowed descriptor.
 * The duplicate shares the underlying offset and file status flags; callers
 * must serialize reads. FIFO/terminal O_NONBLOCK is cleared on the shared open
 * file description, as required for shell stdin. Other flags are preserved. */
int csh_input_from_fd(struct csh_input **out, int fd, const char *name,
                      struct csh_error *error);
/* Stack token borrows descriptor operands until end. Nested calls exclude all
 * enclosing operands when relocating parser descriptors. Initialize with {0}. */
struct csh_input_reservation {
    const int *fds;
    size_t count;
    struct csh_input_reservation *previous;
    int active;
};
int csh_input_reserve_begin(struct csh_input_reservation *reservation,
    const int *fds, size_t count, struct csh_error *error);
/* Shared with other private descriptor owners during nested execution. */
int csh_input_descriptor_reserved(int fd);
void csh_input_reserve_end(struct csh_input_reservation *reservation);
void csh_input_destroy(struct csh_input *input);
/* Optional borrowed event-loop hook, called before each descriptor read.
 * Return 0 when ready or -1 with errno. String sources do not call it. */
void csh_input_set_wait_hook(struct csh_input *input,
    int (*hook)(void *context, int fd), void *context);

/* Borrowed observers: line runs once per physical line before parsing; eof
 * returns nonzero to retry a terminal EOF (e.g. interactive ignoreeof). */
void csh_input_set_line_hook(struct csh_input *input,
    void (*hook)(void *, const unsigned char *, size_t), void *context);
void csh_input_set_eof_hook(struct csh_input *input, int (*hook)(void *), void *context);

/* Borrowed name remains valid until destroy. Position is the next unread byte. */
const char *csh_input_name(const struct csh_input *input);
struct csh_position csh_input_position(const struct csh_input *input);

struct csh_input_line {
    const unsigned char *data;
    size_t length;
    struct csh_position start;
    struct csh_position end;
};

enum csh_input_result {
    CSH_INPUT_ERROR = -1,
    CSH_INPUT_EOF = 0,
    CSH_INPUT_LINE = 1,
    CSH_INPUT_INTERRUPTED = 2
};

/* Acquires exactly one physical line, including its newline when present.
 * No descriptor read-ahead past that newline. A final unterminated line is
 * returned before EOF. data is borrowed until the next read or destroy;
 * length, not the trailing convenience NUL, defines the bytes (NULs survive).
 * A line is NOT a complete shell command: syntax/continuations belong to the
 * lexer/parser. EOF and failures are sticky; *line is cleared on either, and
 * partial lines are never published on failure. error is required. */
enum csh_input_result csh_input_read_line(struct csh_input *input,
    struct csh_input_line *line, struct csh_error *error);

#endif
