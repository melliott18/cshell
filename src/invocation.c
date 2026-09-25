#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "cshell/invocation.h"

static int invocation_error(struct csh_error *error, const char *message,
    int system_errno, int status, size_t argument_index)
{
    if (error != NULL) {
        memset(error, 0, sizeof(*error));
        error->message = message;
        error->system_errno = system_errno;
        error->status = status;
        error->argument_index = argument_index;
    }
    return -1;
}

static char *copy_string(const char *text)
{
    size_t length = strlen(text);
    char *copy;

    if (length == SIZE_MAX) {
        return NULL;
    }
    copy = malloc(length + 1);
    if (copy != NULL) {
        memcpy(copy, text, length + 1);
    }
    return copy;
}

void csh_invocation_destroy(struct csh_invocation *invocation)
{
    size_t index;

    if (invocation == NULL) {
        return;
    }
    csh_input_destroy(invocation->input);
    free(invocation->arg0);
    for (index = 0; index < invocation->argument_count; ++index) {
        free(invocation->arguments[index]);
    }
    free(invocation->arguments);
    memset(invocation, 0, sizeof(*invocation));
}

int csh_invocation_parse(struct csh_invocation *out, int argc,
    char *const argv[], int stdin_fd, int stderr_fd, struct csh_error *error)
{
    struct csh_invocation invocation = {0};
    bool command_string = false;
    bool standard_input = false;
    bool force_interactive = false;
    const char *arg0;
    size_t source_index = 0;
    size_t argument_index;
    size_t argument_count;
    int operand = 1;
    int index;
    int result;

    if (out != NULL) {
        memset(out, 0, sizeof(*out));
    }
    if (error != NULL) {
        memset(error, 0, sizeof(*error));
    }
    if (out == NULL || error == NULL || argc < 1 || argv == NULL) {
        return invocation_error(error, "invalid invocation arguments", EINVAL,
            2, 0);
    }
    for (index = 0; index < argc; ++index) {
        if (argv[index] == NULL) {
            return invocation_error(error, "missing invocation argument", EINVAL,
                2, (size_t)index);
        }
    }

    while (operand < argc) {
        const char *option = argv[operand];
        size_t letter;

        if (strcmp(option, "--") == 0 || strcmp(option, "-") == 0) {
            ++operand;
            break;
        }
        if ((option[0] != '-' && option[0] != '+') || !option[1]) {
            break;
        }
        for (letter = 1; option[letter] != '\0'; ++letter) {
            unsigned bit = csh_option_letter(option[letter]);
            int enable = option[0] == '-';
            if (option[letter] == 'o') {
                const char *name = option + letter + 1;
                if (!*name) {
                    if (++operand == argc)
                        return invocation_error(error, "-o requires an option name", 0, 2, (size_t)operand - 1);
                    name = argv[operand];
                }
                bit = csh_option_name(name);
                if (!bit) return invocation_error(error, "unsupported shell option", 0, 2, (size_t)operand);
                letter = strlen(option) - 1;
            }
            if (bit) {
                invocation.option_mask |= bit;
                if (enable) invocation.options |= bit;
                else invocation.options &= ~bit;
                continue;
            }
            if (!enable) return invocation_error(error, "unsupported shell option", 0, 2, (size_t)operand);
            switch (option[letter]) {
            case 'c':
                command_string = true;
                break;
            case 's':
                standard_input = true;
                break;
            case 'i':
                force_interactive = true;
                break;
            default:
                return invocation_error(error, "unsupported shell option", 0,
                    2, (size_t)operand);
            }
        }
        if (command_string && standard_input) {
            return invocation_error(error, "-c and -s cannot be combined", 0,
                2, (size_t)operand);
        }
        ++operand;
    }

    arg0 = argv[0];
    if (command_string) {
        if (operand == argc) {
            return invocation_error(error, "-c requires a command string", 0,
                2, 0);
        }
        invocation.mode = CSH_MODE_STRING;
        source_index = (size_t)operand++;
        if (operand < argc) {
            arg0 = argv[operand++];
        }
    } else if (standard_input || operand == argc) {
        invocation.mode = CSH_MODE_STDIN;
    } else {
        invocation.mode = CSH_MODE_FILE;
        source_index = (size_t)operand;
        arg0 = argv[operand++];
    }

    invocation.arg0 = copy_string(arg0);
    if (invocation.arg0 == NULL) {
        goto allocation_failure;
    }
    argument_count = (size_t)(argc - operand);
    if (argument_count > SIZE_MAX / sizeof(*invocation.arguments) - 1) {
        goto allocation_failure;
    }
    invocation.arguments = malloc((argument_count + 1) *
        sizeof(*invocation.arguments));
    if (invocation.arguments == NULL) {
        goto allocation_failure;
    }
    for (argument_index = 0; argument_index < argument_count; ++argument_index) {
        invocation.arguments[argument_index] =
            copy_string(argv[(size_t)operand + argument_index]);
        if (invocation.arguments[argument_index] == NULL) {
            goto allocation_failure;
        }
        ++invocation.argument_count;
    }
    invocation.arguments[argument_count] = NULL;

    switch (invocation.mode) {
    case CSH_MODE_STRING:
        result = csh_input_from_string(&invocation.input, argv[source_index],
            "-c", error);
        break;
    case CSH_MODE_FILE:
        result = csh_input_from_file(&invocation.input, argv[source_index], error);
        break;
    case CSH_MODE_STDIN:
    default:
        result = csh_input_from_fd(&invocation.input, stdin_fd, "stdin", error);
        break;
    }
    if (result < 0) {
        error->argument_index = source_index;
        csh_invocation_destroy(&invocation);
        return -1;
    }
    invocation.interactive = force_interactive ||
        (invocation.mode == CSH_MODE_STDIN && isatty(stdin_fd) &&
            isatty(stderr_fd));
    *out = invocation;
    return 0;

allocation_failure:
    csh_invocation_destroy(&invocation);
    return invocation_error(error, "cannot allocate invocation", ENOMEM, 1, 0);
}

const char *csh_invocation_prompt(const struct csh_invocation *invocation,
    bool continuation, const char *ps1, const char *ps2)
{
    if (invocation == NULL || !invocation->interactive ||
        invocation->mode != CSH_MODE_STDIN) {
        return NULL;
    }
    return continuation ? ps2 : ps1;
}
