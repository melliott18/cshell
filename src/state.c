#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "cshell/state.h"

#define VARIABLE_ATTRIBUTES (CSH_VAR_EXPORT | CSH_VAR_READONLY)
#define SHELL_OPTIONS (CSH_OPT_INTERACTIVE | CSH_OPT_ALLEXPORT | CSH_OPT_ERREXIT | \
    CSH_OPT_NOGLOB | CSH_OPT_NOEXEC | CSH_OPT_NOUNSET | CSH_OPT_VERBOSE | \
    CSH_OPT_XTRACE | CSH_OPT_NOCLOBBER | CSH_OPT_PIPEFAIL | CSH_OPT_MONITOR | \
    CSH_OPT_NOTIFY)

struct variable {
    char *name;
    char *value;
    unsigned attributes;
    struct variable *next;
};

struct csh_state {
    struct variable *variables;
    char *arg0;
    char **arguments;
    struct csh_state_info info;
};

struct csh_state_checkpoint {
    struct csh_state *saved;
};

static int name_start(unsigned char byte)
{
    return (byte >= 'a' && byte <= 'z') || (byte >= 'A' && byte <= 'Z') ||
        byte == '_';
}

static int valid_name(const char *name, size_t length)
{
    size_t index;
    if (length == 0 || !name_start((unsigned char)name[0]))
        return 0;
    for (index = 1; index < length; ++index) {
        unsigned char byte = (unsigned char)name[index];
        if (!name_start(byte) && !(byte >= '0' && byte <= '9'))
            return 0;
    }
    return 1;
}

static char *copy_bytes(const char *text, size_t length)
{
    char *copy;
    if (length == SIZE_MAX)
        return NULL;
    copy = malloc(length + 1);
    if (copy != NULL) {
        memcpy(copy, text, length);
        copy[length] = '\0';
    }
    return copy;
}

static struct variable *find_variable(const struct csh_state *state,
    const char *name)
{
    struct variable *variable;
    for (variable = state->variables; variable != NULL; variable = variable->next) {
        if (strcmp(variable->name, name) == 0)
            return variable;
    }
    return NULL;
}

static void destroy_variable(struct variable *variable)
{
    free(variable->name);
    free(variable->value);
    free(variable);
}

/* Build the complete node before linking it into a live state. */
static struct variable *new_variable(const char *name, const char *value,
    unsigned attributes)
{
    struct variable *variable = malloc(sizeof(*variable));
    if (variable == NULL)
        return NULL;
    *variable = (struct variable){0};
    variable->name = copy_bytes(name, strlen(name));
    if (variable->name == NULL)
        goto failure;
    if (value != NULL) {
        variable->value = copy_bytes(value, strlen(value));
        if (variable->value == NULL)
            goto failure;
    }
    variable->attributes = attributes;
    return variable;
failure:
    destroy_variable(variable);
    return NULL;
}

void csh_state_environment_destroy(char **environment)
{
    size_t index;
    if (environment == NULL)
        return;
    for (index = 0; environment[index] != NULL; ++index)
        free(environment[index]);
    free(environment);
}

void csh_state_destroy(struct csh_state *state)
{
    struct variable *variable;
    if (state == NULL)
        return;
    variable = state->variables;
    while (variable != NULL) {
        struct variable *next = variable->next;
        destroy_variable(variable);
        variable = next;
    }
    free(state->arg0);
    csh_state_environment_destroy(state->arguments);
    free(state);
}

enum csh_state_result csh_state_get_variable(const struct csh_state *state,
    const char *name, struct csh_variable_view *out)
{
    struct variable *variable;
    if (out != NULL)
        *out = (struct csh_variable_view){0};
    if (state == NULL || name == NULL || out == NULL ||
        !valid_name(name, strlen(name)))
        return CSH_STATE_INVALID;
    variable = find_variable(state, name);
    if (variable != NULL) {
        out->value = variable->value;
        out->attributes = variable->attributes;
    }
    return CSH_STATE_OK;
}

enum csh_state_result csh_state_set_variable(struct csh_state *state,
    const char *name, const char *value)
{
    struct variable *variable;
    char *copy;
    if (state == NULL || name == NULL || value == NULL ||
        !valid_name(name, strlen(name)))
        return CSH_STATE_INVALID;
    variable = find_variable(state, name);
    if (variable != NULL) {
        if (variable->attributes & CSH_VAR_READONLY)
            return CSH_STATE_READONLY;
        copy = copy_bytes(value, strlen(value));
        if (copy == NULL)
            return CSH_STATE_NOMEM;
        free(variable->value);
        variable->value = copy;
    } else {
        variable = new_variable(name, value, 0);
        if (variable == NULL)
            return CSH_STATE_NOMEM;
        variable->next = state->variables;
        state->variables = variable;
    }
    return CSH_STATE_OK;
}

enum csh_state_result csh_state_update_attributes(struct csh_state *state,
    const char *name, unsigned set, unsigned clear)
{
    struct variable *variable;
    unsigned attributes;
    if (state == NULL || name == NULL || !valid_name(name, strlen(name)) ||
        ((set | clear) & ~VARIABLE_ATTRIBUTES) != 0 || (set & clear) != 0)
        return CSH_STATE_INVALID;
    variable = find_variable(state, name);
    if (variable != NULL) {
        if ((variable->attributes & CSH_VAR_READONLY) && (clear & CSH_VAR_READONLY))
            return CSH_STATE_READONLY;
        variable->attributes = (variable->attributes | set) & ~clear;
    } else {
        attributes = set & ~clear;
        if (attributes == 0)
            return CSH_STATE_OK;
        variable = new_variable(name, NULL, attributes);
        if (variable == NULL)
            return CSH_STATE_NOMEM;
        variable->next = state->variables;
        state->variables = variable;
    }
    return CSH_STATE_OK;
}

enum csh_state_result csh_state_unset_variable(struct csh_state *state,
    const char *name)
{
    struct variable **link;
    if (state == NULL || name == NULL || !valid_name(name, strlen(name)))
        return CSH_STATE_INVALID;
    for (link = &state->variables; *link != NULL; link = &(*link)->next) {
        struct variable *variable = *link;
        if (strcmp(variable->name, name) != 0)
            continue;
        if (variable->attributes & CSH_VAR_READONLY)
            return CSH_STATE_READONLY;
        *link = variable->next;
        destroy_variable(variable);
        break;
    }
    return CSH_STATE_OK;
}

enum csh_state_result csh_state_set_parameters(struct csh_state *state,
    size_t count, const char *const arguments[])
{
    size_t index;
    char **copy;
    if (state == NULL || (count != 0 && arguments == NULL))
        return CSH_STATE_INVALID;
    if (count > SIZE_MAX / sizeof(*copy) - 1)
        return CSH_STATE_NOMEM;
    for (index = 0; index < count; ++index) {
        if (arguments[index] == NULL)
            return CSH_STATE_INVALID;
    }
    copy = malloc((count + 1) * sizeof(*copy));
    if (copy == NULL)
        return CSH_STATE_NOMEM;
    copy[0] = NULL;
    for (index = 0; index < count; ++index) {
        copy[index] = copy_bytes(arguments[index], strlen(arguments[index]));
        if (copy[index] == NULL) {
            csh_state_environment_destroy(copy);
            return CSH_STATE_NOMEM;
        }
        copy[index + 1] = NULL;
    }
    csh_state_environment_destroy(state->arguments);
    state->arguments = copy;
    state->info.argument_count = count;
    return CSH_STATE_OK;
}

static enum csh_state_result import_environment(struct csh_state *state,
    char *const envp[])
{
    size_t index;
    if (envp == NULL)
        return CSH_STATE_OK;
    for (index = 0; envp[index] != NULL; ++index) {
        const char *equals = strchr(envp[index], '=');
        char *name;
        enum csh_state_result result;
        if (equals == NULL || !valid_name(envp[index], (size_t)(equals - envp[index])))
            continue;
        name = copy_bytes(envp[index], (size_t)(equals - envp[index]));
        if (name == NULL)
            return CSH_STATE_NOMEM;
        result = csh_state_set_variable(state, name, equals + 1);
        if (result == CSH_STATE_OK)
            result = csh_state_update_attributes(state, name, CSH_VAR_EXPORT, 0);
        free(name);
        if (result != CSH_STATE_OK)
            return result;
    }
    return CSH_STATE_OK;
}

enum csh_state_result csh_state_create(struct csh_state **out,
    const struct csh_invocation *invocation, char *const envp[])
{
    struct csh_state *state;
    enum csh_state_result result;
    if (out != NULL)
        *out = NULL;
    if (out == NULL || invocation == NULL || invocation->arg0 == NULL ||
        (invocation->mode != CSH_MODE_STDIN && invocation->mode != CSH_MODE_STRING &&
            invocation->mode != CSH_MODE_FILE))
        return CSH_STATE_INVALID;
    state = malloc(sizeof(*state));
    if (state == NULL)
        return CSH_STATE_NOMEM;
    *state = (struct csh_state){0};
    state->arg0 = copy_bytes(invocation->arg0, strlen(invocation->arg0));
    if (state->arg0 == NULL) {
        csh_state_destroy(state);
        return CSH_STATE_NOMEM;
    }
    result = csh_state_set_parameters(state, invocation->argument_count,
        (const char *const *)invocation->arguments);
    if (result == CSH_STATE_OK)
        result = import_environment(state, envp);
    if (result != CSH_STATE_OK) {
        csh_state_destroy(state);
        return result;
    }
    state->info.shell_pid = getpid();
    state->info.mode = invocation->mode;
    state->info.options = invocation->interactive ? CSH_OPT_INTERACTIVE : 0;
    *out = state;
    return CSH_STATE_OK;
}

enum csh_state_result csh_state_environment(const struct csh_state *state,
    char ***out)
{
    struct variable *variable;
    size_t count = 0;
    size_t index = 0;
    char **environment;
    if (out != NULL)
        *out = NULL;
    if (state == NULL || out == NULL)
        return CSH_STATE_INVALID;
    for (variable = state->variables; variable != NULL; variable = variable->next) {
        if (variable->value != NULL && (variable->attributes & CSH_VAR_EXPORT)) {
            if (count == SIZE_MAX / sizeof(*environment) - 1)
                return CSH_STATE_NOMEM;
            ++count;
        }
    }
    environment = malloc((count + 1) * sizeof(*environment));
    if (environment == NULL)
        return CSH_STATE_NOMEM;
    environment[0] = NULL;
    for (variable = state->variables; variable != NULL; variable = variable->next) {
        size_t name_length;
        size_t value_length;
        char *entry;
        if (variable->value == NULL || !(variable->attributes & CSH_VAR_EXPORT))
            continue;
        name_length = strlen(variable->name);
        value_length = strlen(variable->value);
        if (name_length > SIZE_MAX - 2 || value_length > SIZE_MAX - name_length - 2)
            goto failure;
        entry = malloc(name_length + value_length + 2);
        if (entry == NULL)
            goto failure;
        memcpy(entry, variable->name, name_length);
        entry[name_length] = '=';
        memcpy(entry + name_length + 1, variable->value, value_length + 1);
        environment[index++] = entry;
        environment[index] = NULL;
    }
    *out = environment;
    return CSH_STATE_OK;
failure:
    csh_state_environment_destroy(environment);
    return CSH_STATE_NOMEM;
}

const char *csh_state_parameter(const struct csh_state *state, size_t index)
{
    if (state == NULL || index > state->info.argument_count)
        return NULL;
    return index == 0 ? state->arg0 : state->arguments[index - 1];
}

enum csh_state_result csh_state_get_info(const struct csh_state *state,
    struct csh_state_info *out)
{
    if (out != NULL)
        *out = (struct csh_state_info){0};
    if (state == NULL || out == NULL)
        return CSH_STATE_INVALID;
    *out = state->info;
    return CSH_STATE_OK;
}

enum csh_state_result csh_state_set_status(struct csh_state *state, int status)
{
    if (state == NULL || status < 0)
        return CSH_STATE_INVALID;
    state->info.last_status = status;
    return CSH_STATE_OK;
}

enum csh_state_result csh_state_set_background(struct csh_state *state, pid_t pid)
{
    if (state == NULL || pid < 0)
        return CSH_STATE_INVALID;
    state->info.background_pid = pid;
    return CSH_STATE_OK;
}

enum csh_state_result csh_state_update_options(struct csh_state *state,
    unsigned set, unsigned clear)
{
    if (state == NULL || ((set | clear) & ~SHELL_OPTIONS) != 0 || (set & clear) != 0)
        return CSH_STATE_INVALID;
    state->info.options = (state->info.options | set) & ~clear;
    return CSH_STATE_OK;
}

enum csh_state_result csh_state_clone(const struct csh_state *state,
    struct csh_state **out)
{
    struct csh_state *copy;
    struct variable *variable;
    struct variable **tail;
    enum csh_state_result result;
    if (out != NULL)
        *out = NULL;
    if (state == NULL || out == NULL)
        return CSH_STATE_INVALID;
    copy = malloc(sizeof(*copy));
    if (copy == NULL)
        return CSH_STATE_NOMEM;
    *copy = (struct csh_state){0};
    copy->arg0 = copy_bytes(state->arg0, strlen(state->arg0));
    if (copy->arg0 == NULL)
        goto failure;
    result = csh_state_set_parameters(copy, state->info.argument_count,
        (const char *const *)state->arguments);
    if (result != CSH_STATE_OK)
        goto failure;
    tail = &copy->variables;
    for (variable = state->variables; variable != NULL; variable = variable->next) {
        *tail = new_variable(variable->name, variable->value, variable->attributes);
        if (*tail == NULL)
            goto failure;
        tail = &(*tail)->next;
    }
    copy->info = state->info;
    *out = copy;
    return CSH_STATE_OK;
failure:
    csh_state_destroy(copy);
    return CSH_STATE_NOMEM;
}

enum csh_state_result csh_state_save(const struct csh_state *state,
    struct csh_state_checkpoint **out)
{
    struct csh_state_checkpoint *checkpoint;
    enum csh_state_result result;
    if (out != NULL)
        *out = NULL;
    if (state == NULL || out == NULL)
        return CSH_STATE_INVALID;
    checkpoint = malloc(sizeof(*checkpoint));
    if (checkpoint == NULL)
        return CSH_STATE_NOMEM;
    result = csh_state_clone(state, &checkpoint->saved);
    if (result != CSH_STATE_OK) {
        free(checkpoint);
        return result;
    }
    *out = checkpoint;
    return CSH_STATE_OK;
}

void csh_state_checkpoint_destroy(struct csh_state_checkpoint *checkpoint)
{
    if (checkpoint == NULL)
        return;
    csh_state_destroy(checkpoint->saved);
    free(checkpoint);
}

enum csh_state_result csh_state_restore(struct csh_state *state,
    struct csh_state_checkpoint **checkpoint)
{
    struct csh_state discarded;
    if (state == NULL || checkpoint == NULL || *checkpoint == NULL)
        return CSH_STATE_INVALID;
    discarded = *state;
    *state = *(*checkpoint)->saved;
    *(*checkpoint)->saved = discarded;
    csh_state_checkpoint_destroy(*checkpoint);
    *checkpoint = NULL;
    return CSH_STATE_OK;
}


enum csh_state_result csh_state_names(const struct csh_state *state, char ***out)
{
    struct variable *v;
    size_t count = 0, i = 0;
    char **names;
    if (out == NULL) return CSH_STATE_INVALID;
    *out = NULL;
    if (state == NULL) return CSH_STATE_INVALID;
    for (v = state->variables; v; v = v->next) ++count;
    if (count >= SIZE_MAX / sizeof(*names)) return CSH_STATE_NOMEM;
    names = malloc((count + 1) * sizeof(*names));
    if (!names) return CSH_STATE_NOMEM;
    memset(names, 0, (count + 1) * sizeof(*names));
    for (v = state->variables; v; v = v->next) {
        names[i] = copy_bytes(v->name, strlen(v->name));
        if (!names[i++]) { csh_state_environment_destroy(names); return CSH_STATE_NOMEM; }
    }
    *out = names;
    return CSH_STATE_OK;
}
