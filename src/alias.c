#include "cshell/alias.h"

#include <errno.h>
#include <stdlib.h>
#include <string.h>

struct alias {
    char *name;
    char *value;
    struct alias *next;
};

struct csh_aliases {
    struct alias *first;
};

static int fail(struct csh_error *error, const char *message, int number,
    int status)
{
    if (error != NULL) {
        memset(error, 0, sizeof(*error));
        error->message = message;
        error->system_errno = number;
        error->status = status;
    }
    return -1;
}

static int valid_name(const char *name, size_t length)
{
    size_t index;
    if (length == 0)
        return 0;
    for (index = 0; index < length; ++index) {
        unsigned char byte = (unsigned char)name[index];
        if (!((byte >= 'a' && byte <= 'z') ||
              (byte >= 'A' && byte <= 'Z') ||
              (byte >= '0' && byte <= '9') ||
              byte == '!' || byte == '%' || byte == ',' || byte == '-' ||
              byte == '@' || byte == '_'))
            return 0;
    }
    return 1;
}

int csh_alias_name_valid(const char *name)
{
    return name != NULL && valid_name(name, strlen(name));
}

static char *copy_bytes(const char *text, size_t length)
{
    char *copy = malloc(length + 1);
    if (copy != NULL) {
        memcpy(copy, text, length);
        copy[length] = '\0';
    }
    return copy;
}

static void destroy_alias(struct alias *entry)
{
    free(entry->name);
    free(entry->value);
    free(entry);
}

int csh_aliases_create(struct csh_aliases **out, struct csh_error *error)
{
    struct csh_aliases *aliases;
    if (out != NULL)
        *out = NULL;
    if (out == NULL || error == NULL)
        return fail(error, "invalid alias table arguments", EINVAL, 2);
    aliases = malloc(sizeof(*aliases));
    if (aliases == NULL)
        return fail(error, "cannot allocate alias table", ENOMEM, 1);
    aliases->first = NULL;
    *out = aliases;
    memset(error, 0, sizeof(*error));
    return 0;
}

void csh_aliases_clear(struct csh_aliases *aliases)
{
    struct alias *entry;
    if (aliases == NULL)
        return;
    entry = aliases->first;
    while (entry != NULL) {
        struct alias *next = entry->next;
        destroy_alias(entry);
        entry = next;
    }
    aliases->first = NULL;
}

void csh_aliases_destroy(struct csh_aliases *aliases)
{
    csh_aliases_clear(aliases);
    free(aliases);
}

static struct alias *find_alias(const struct csh_aliases *aliases,
    const char *name, size_t length)
{
    struct alias *entry;
    for (entry = aliases->first; entry != NULL; entry = entry->next) {
        if (strlen(entry->name) == length &&
            memcmp(entry->name, name, length) == 0)
            return entry;
    }
    return NULL;
}

const char *csh_aliases_get(const struct csh_aliases *aliases, const char *name)
{
    struct alias *entry;
    if (aliases == NULL || !csh_alias_name_valid(name))
        return NULL;
    entry = find_alias(aliases, name, strlen(name));
    return entry == NULL ? NULL : entry->value;
}

static int set_alias(struct csh_aliases *aliases, const char *name,
    size_t length, const char *value, struct csh_error *error)
{
    struct alias *entry;
    struct alias **link;
    char *copy;
    if (aliases == NULL || error == NULL || name == NULL || value == NULL ||
        !valid_name(name, length))
        return fail(error, "invalid alias definition", EINVAL, 2);
    entry = find_alias(aliases, name, length);
    copy = copy_bytes(value, strlen(value));
    if (copy == NULL)
        return fail(error, "cannot allocate alias value", ENOMEM, 1);
    if (entry != NULL) {
        free(entry->value);
        entry->value = copy;
    } else {
        entry = malloc(sizeof(*entry));
        if (entry == NULL) {
            free(copy);
            return fail(error, "cannot allocate alias definition", ENOMEM, 1);
        }
        entry->value = copy;
        entry->name = copy_bytes(name, length);
        if (entry->name == NULL) {
            destroy_alias(entry);
            return fail(error, "cannot allocate alias name", ENOMEM, 1);
        }
        link = &aliases->first;
        while (*link != NULL && strcmp((*link)->name, entry->name) < 0)
            link = &(*link)->next;
        entry->next = *link;
        *link = entry;
    }
    memset(error, 0, sizeof(*error));
    return 0;
}

int csh_aliases_set(struct csh_aliases *aliases, const char *name,
    const char *value, struct csh_error *error)
{
    return set_alias(aliases, name, name == NULL ? 0 : strlen(name), value,
        error);
}

int csh_aliases_unset(struct csh_aliases *aliases, const char *name,
    struct csh_error *error)
{
    struct alias **link;
    if (aliases == NULL || error == NULL || !csh_alias_name_valid(name))
        return fail(error, "invalid alias name", EINVAL, 2);
    for (link = &aliases->first; *link != NULL; link = &(*link)->next) {
        if (strcmp((*link)->name, name) == 0) {
            struct alias *entry = *link;
            *link = entry->next;
            destroy_alias(entry);
            break;
        }
    }
    memset(error, 0, sizeof(*error));
    return 0;
}

static int valid_arguments(struct csh_aliases *aliases, int argc,
    const char *const argv[], FILE *out, FILE *err)
{
    int index;
    if (aliases == NULL || argc < 1 || argv == NULL || out == NULL || err == NULL)
        return 0;
    for (index = 0; index < argc; ++index) {
        if (argv[index] == NULL)
            return 0;
    }
    return 1;
}

static int diagnostic(FILE *err, const char *utility, const char *operand,
    const char *message, int status)
{
    if (err != NULL) {
        if (operand == NULL)
            fprintf(err, "%s: %s\n", utility, message);
        else
            fprintf(err, "%s: %s: %s\n", utility, operand, message);
    }
    return status;
}

static int print_alias(FILE *out, const char *name, const char *value)
{
    const unsigned char *cursor = (const unsigned char *)value;
    if (fprintf(out, "%s='", name) < 0)
        return -1;
    for (; *cursor != '\0'; ++cursor) {
        if (*cursor == '\'') {
            if (fputs("'\\''", out) == EOF)
                return -1;
        } else if (fputc(*cursor, out) == EOF) {
            return -1;
        }
    }
    return fputs("'\n", out) == EOF ? -1 : 0;
}

int csh_builtin_alias(struct csh_aliases *aliases, int argc,
    const char *const argv[], FILE *out, FILE *err)
{
    int index = 1;
    int status = 0;
    int printed = 0;
    struct csh_error error;
    if (!valid_arguments(aliases, argc, argv, out, err))
        return diagnostic(err, "alias", NULL, "invalid handler arguments", 2);
    if (index < argc && strcmp(argv[index], "--") == 0)
        ++index;
    else if (index < argc && argv[index][0] == '-' && argv[index][1] != '\0')
        return diagnostic(err, "alias", argv[index], "invalid option", 2);
    if (index == argc) {
        struct alias *entry;
        for (entry = aliases->first; entry != NULL; entry = entry->next) {
            if (print_alias(out, entry->name, entry->value) < 0)
                return diagnostic(err, "alias", NULL, "cannot write output", 1);
            printed = 1;
        }
    }
    for (; index < argc; ++index) {
        const char *equals = strchr(argv[index], '=');
        if (equals != NULL) {
            if (set_alias(aliases, argv[index], (size_t)(equals - argv[index]),
                equals + 1, &error) < 0)
                status = diagnostic(err, "alias", argv[index], error.message, 1);
        } else if (!csh_alias_name_valid(argv[index])) {
            status = diagnostic(err, "alias", argv[index], "invalid alias name", 1);
        } else {
            const char *value = csh_aliases_get(aliases, argv[index]);
            if (value == NULL)
                status = diagnostic(err, "alias", argv[index], "not found", 1);
            else if (print_alias(out, argv[index], value) < 0)
                return diagnostic(err, "alias", NULL, "cannot write output", 1);
            else
                printed = 1;
        }
    }
    if (printed && fflush(out) == EOF)
        return diagnostic(err, "alias", NULL, "cannot write output", 1);
    return status;
}

int csh_builtin_unalias(struct csh_aliases *aliases, int argc,
    const char *const argv[], FILE *out, FILE *err)
{
    int index = 1;
    int all = 0;
    int status = 0;
    struct csh_error error;
    if (!valid_arguments(aliases, argc, argv, out, err))
        return diagnostic(err, "unalias", NULL, "invalid handler arguments", 2);
    while (index < argc && argv[index][0] == '-' && argv[index][1] != '\0') {
        const char *option;
        if (strcmp(argv[index], "--") == 0) {
            ++index;
            break;
        }
        for (option = argv[index] + 1; *option != '\0'; ++option) {
            if (*option != 'a')
                return diagnostic(err, "unalias", argv[index], "invalid option", 2);
        }
        all = 1;
        ++index;
    }
    if (all) {
        if (index != argc)
            return diagnostic(err, "unalias", NULL, "-a does not accept operands", 2);
        csh_aliases_clear(aliases);
        return 0;
    }
    if (index == argc)
        return diagnostic(err, "unalias", NULL, "expected an alias name", 2);
    for (; index < argc; ++index) {
        if (!csh_alias_name_valid(argv[index]))
            status = diagnostic(err, "unalias", argv[index], "invalid alias name", 1);
        else if (csh_aliases_get(aliases, argv[index]) == NULL)
            status = diagnostic(err, "unalias", argv[index], "not found", 1);
        else
            csh_aliases_unset(aliases, argv[index], &error);
    }
    return status;
}
