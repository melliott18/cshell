#ifndef CSHELL_INVOCATION_H
#define CSHELL_INVOCATION_H

#include <stdbool.h>
#include "cshell/input.h"
#include "cshell/options.h"

enum csh_input_mode {
    CSH_MODE_STDIN,
    CSH_MODE_STRING,
    CSH_MODE_FILE
};

/* Owns input, arg0, and the NULL-terminated positional argument vector.
 * Fields are read-only to consumers; CSH-022 must copy strings it retains.
 * Destroy accepts a zero-initialized or successfully parsed invocation. */
struct csh_invocation {
    struct csh_input *input;
    enum csh_input_mode mode;
    bool interactive;
    unsigned options;
    unsigned option_mask; /* Explicit selections, including disabled options. */
    char *arg0;
    size_t argument_count;
    char **arguments;
};

/* Supports -c, -s, -i, shared letter/named options, --, and lone -.
 * argv and descriptors are borrowed
 * during parsing; all retained strings are copied. stdin_fd supplies input
 * and terminal detection; stderr_fd is used only for terminal detection.
 * out must not own an earlier invocation. It is zeroed on any failure.
 * error is required. Returns 0 or -1 and supplies a non-allocating
 * diagnostic/status in error. */
int csh_invocation_parse(struct csh_invocation *out, int argc,
    char *const argv[], int stdin_fd, int stderr_fd, struct csh_error *error);
void csh_invocation_destroy(struct csh_invocation *invocation);

/* Selects an already-expanded caller-owned PS1/PS2 string, or NULL when no
 * prompt is due. Call once before each physical read; continuation is decided
 * by the lexer/parser. Caller writes any selected prompt to stderr. */
const char *csh_invocation_prompt(const struct csh_invocation *invocation,
    bool continuation, const char *ps1, const char *ps2);

#endif
