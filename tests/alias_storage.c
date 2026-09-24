/* Alias storage and dispatch-ready handler checks, independent of the runtime. */
#include "cshell/alias.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "alias storage fixture failed at line %d: %s\n", \
            __LINE__, #condition); \
        exit(90); \
    } \
} while (0)

static struct csh_aliases *new_aliases(void)
{
    struct csh_aliases *aliases = NULL;
    struct csh_error error;
    CHECK(csh_aliases_create(&aliases, &error) == 0);
    CHECK(error.message == NULL && error.status == 0);
    return aliases;
}

static void value_is(const struct csh_aliases *aliases, const char *name,
    const char *expected)
{
    const char *actual = csh_aliases_get(aliases, name);
    if (expected == NULL)
        CHECK(actual == NULL);
    else
        CHECK(actual != NULL && strcmp(actual, expected) == 0);
}

static void stream_is(FILE *stream, const char *expected)
{
    char buffer[4096];
    size_t length;
    CHECK(fflush(stream) == 0);
    CHECK(fseek(stream, 0, SEEK_SET) == 0);
    length = fread(buffer, 1, sizeof(buffer) - 1, stream);
    CHECK(!ferror(stream) && feof(stream));
    buffer[length] = '\0';
    CHECK(strcmp(buffer, expected) == 0);
}

typedef int (*handler)(struct csh_aliases *, int, const char *const[], FILE *, FILE *);

static void invoke(handler function, struct csh_aliases *aliases, int argc,
    const char *const argv[], int status, const char *output, const char *errors)
{
    FILE *out = tmpfile();
    FILE *err = tmpfile();
    CHECK(out != NULL && err != NULL);
    CHECK(function(aliases, argc, argv, out, err) == status);
    stream_is(out, output);
    stream_is(err, errors);
    CHECK(fclose(out) == 0 && fclose(err) == 0);
}

static void storage(void)
{
    struct csh_aliases *aliases = new_aliases();
    struct csh_aliases *other = new_aliases();
    struct csh_error error;
    char name[] = "owned";
    char value[] = "a 'quoted' replacement\t ";
    const char *invalid[] = {"", "a b", "a=b", "a/b", "a.b", "a+b", "a:b",
        "a\tb", "a\nb", "a?", "a$", "a\\b", "\303\251", NULL};
    const char *valid[] = {"a", "Z", "_", "9", "-", "--", "!", "%", ",", "@",
        "1aZ!%,-@_", NULL};
    size_t index;

    CHECK(csh_aliases_set(aliases, name, value, &error) == 0);
    memset(name, '#', sizeof(name) - 1);
    memset(value, '#', sizeof(value) - 1);
    value_is(aliases, "owned", "a 'quoted' replacement\t ");
    value_is(other, "owned", NULL);
    CHECK(csh_aliases_set(aliases, "empty", "", &error) == 0);
    value_is(aliases, "empty", "");
    CHECK(csh_aliases_set(aliases, "owned", "new", &error) == 0);
    CHECK(csh_aliases_set(aliases, "owned", csh_aliases_get(aliases, "owned"),
        &error) == 0);
    value_is(aliases, "owned", "new");
    CHECK(csh_aliases_set(aliases, csh_aliases_get(aliases, "owned"),
        csh_aliases_get(aliases, "owned"), &error) == 0);
    value_is(aliases, "new", "new");
    CHECK(csh_aliases_set(aliases, "owned", "owned", &error) == 0);
    CHECK(csh_aliases_set(aliases, csh_aliases_get(aliases, "owned"),
        "replacement", &error) == 0);
    value_is(aliases, "owned", "replacement");
    for (index = 0; valid[index] != NULL; ++index) {
        CHECK(csh_alias_name_valid(valid[index]));
        CHECK(csh_aliases_set(aliases, valid[index], "portable", &error) == 0);
        value_is(aliases, valid[index], "portable");
    }
    for (index = 0; invalid[index] != NULL; ++index) {
        CHECK(!csh_alias_name_valid(invalid[index]));
        CHECK(csh_aliases_set(aliases, invalid[index], "bad", &error) == -1);
        CHECK(error.system_errno == EINVAL && error.status == 2);
        CHECK(csh_aliases_unset(aliases, invalid[index], &error) == -1);
        value_is(aliases, invalid[index], NULL);
    }
    CHECK(!csh_alias_name_valid(NULL));
    CHECK(csh_aliases_set(aliases, NULL, "bad", &error) == -1);
    CHECK(csh_aliases_set(aliases, "owned", NULL, &error) == -1);
    CHECK(csh_aliases_set(NULL, "name", "value", &error) == -1);
    CHECK(csh_aliases_set(aliases, "name", "value", NULL) == -1);
    value_is(aliases, "owned", "replacement");
    value_is(NULL, "owned", NULL);
    value_is(aliases, NULL, NULL);
    CHECK(csh_aliases_unset(aliases, "absent", &error) == 0);
    CHECK(error.message == NULL && error.system_errno == 0 && error.status == 0);
    CHECK(csh_aliases_unset(aliases, "owned", &error) == 0);
    value_is(aliases, "owned", NULL);
    CHECK(csh_aliases_set(aliases, "self", "self", &error) == 0);
    CHECK(csh_aliases_unset(aliases, csh_aliases_get(aliases, "self"), &error) == 0);
    value_is(aliases, "self", NULL);
    csh_aliases_clear(aliases);
    value_is(aliases, "empty", NULL);
    value_is(aliases, "9", NULL);
    CHECK(csh_aliases_set(aliases, "reused", "ok", &error) == 0);
    csh_aliases_destroy(aliases);
    csh_aliases_destroy(other);
    aliases = (struct csh_aliases *)&error;
    CHECK(csh_aliases_create(&aliases, NULL) == -1 && aliases == NULL);
    CHECK(csh_aliases_create(NULL, &error) == -1 && error.status == 2);
    csh_aliases_clear(NULL);
    csh_aliases_destroy(NULL);
}

static void alias_handler(void)
{
    struct csh_aliases *aliases = new_aliases();
    const char *list[] = {"alias"};
    const char *define[] = {"alias", "z=last", "a=first", "empty=", "z=updated"};
    const char *queries[] = {"alias", "missing", "z", "empty", "a", "z"};
    const char *mixed[] = {"alias", "a=changed", "missing", "a", "bad.name=no",
        "after=retained", "a=b=c", "a"};
    const char *special[] = {"alias", "quote=$x `date` \\ \"\n'\t ", "quote"};
    const char *invalid_option[] = {"alias", "-p", "untouched=no"};
    const char *dash_names[] = {"alias", "--", "-x=option name", "--=terminator", "-=dash"};
    const char *dash_queries[] = {"alias", "--", "-x", "--", "-"};
    const char *after_operand[] = {"alias", "a=one", "-q=two", "-q"};
    const char *invalid[] = {"alias", "=empty name", "bad/name=x", "", "bad name"};
    const char *bad_argv[] = {"alias", NULL};
    const char *list_after_delimiter[] = {"alias", "--"};

    invoke(csh_builtin_alias, aliases, 1, list, 0, "", "");
    invoke(csh_builtin_alias, aliases, 5, define, 0, "", "");
    invoke(csh_builtin_alias, aliases, 1, list, 0,
        "a='first'\nempty=''\nz='updated'\n", "");
    invoke(csh_builtin_alias, aliases, 2, list_after_delimiter, 0,
        "a='first'\nempty=''\nz='updated'\n", "");
    invoke(csh_builtin_alias, aliases, 6, queries, 1,
        "z='updated'\nempty=''\na='first'\nz='updated'\n",
        "alias: missing: not found\n");
    invoke(csh_builtin_alias, aliases, 8, mixed, 1, "a='changed'\na='b=c'\n",
        "alias: missing: not found\nalias: bad.name=no: invalid alias definition\n");
    value_is(aliases, "after", "retained");
    invoke(csh_builtin_alias, aliases, 3, special, 0,
        "quote='$x `date` \\ \"\n'\\''\t '\n", "");
    value_is(aliases, "quote", "$x `date` \\ \"\n'\t ");
    invoke(csh_builtin_alias, aliases, 3, invalid_option, 2, "",
        "alias: -p: invalid option\n");
    value_is(aliases, "untouched", NULL);
    invoke(csh_builtin_alias, aliases, 5, dash_names, 0, "", "");
    invoke(csh_builtin_alias, aliases, 5, dash_queries, 0,
        "-x='option name'\n--='terminator'\n-='dash'\n", "");
    invoke(csh_builtin_alias, aliases, 4, after_operand, 0, "-q='two'\n", "");
    invoke(csh_builtin_alias, aliases, 5, invalid, 1, "",
        "alias: =empty name: invalid alias definition\n"
        "alias: bad/name=x: invalid alias definition\n"
        "alias: : invalid alias name\nalias: bad name: invalid alias name\n");
    invoke(csh_builtin_alias, aliases, 2, bad_argv, 2, "",
        "alias: invalid handler arguments\n");
    invoke(csh_builtin_alias, aliases, 0, NULL, 2, "",
        "alias: invalid handler arguments\n");
    csh_aliases_destroy(aliases);
}

static void unalias_handler(void)
{
    struct csh_aliases *aliases = new_aliases();
    struct csh_error error;
    const char *define[] = {"alias", "a=one", "b=two", "c=three", "-x=dash"};
    const char *mixed[] = {"unalias", "a", "missing", "bad/name", "b", "a"};
    const char *empty[] = {"unalias"};
    const char *empty_delimiter[] = {"unalias", "--"};
    const char *invalid[] = {"unalias", "-az"};
    const char *all_operands[] = {"unalias", "-a", "c"};
    const char *dash[] = {"unalias", "--", "-x"};
    const char *all[] = {"unalias", "-aa", "-a", "--"};
    const char *bad_argv[] = {"unalias", NULL};
    const char *after_operand[] = {"unalias", "a", "-x"};

    invoke(csh_builtin_alias, aliases, 5, define, 0, "", "");
    invoke(csh_builtin_unalias, aliases, 6, mixed, 1, "",
        "unalias: missing: not found\nunalias: bad/name: invalid alias name\n"
        "unalias: a: not found\n");
    value_is(aliases, "a", NULL);
    value_is(aliases, "b", NULL);
    value_is(aliases, "c", "three");
    invoke(csh_builtin_unalias, aliases, 1, empty, 2, "",
        "unalias: expected an alias name\n");
    invoke(csh_builtin_unalias, aliases, 2, empty_delimiter, 2, "",
        "unalias: expected an alias name\n");
    invoke(csh_builtin_unalias, aliases, 2, invalid, 2, "",
        "unalias: -az: invalid option\n");
    invoke(csh_builtin_unalias, aliases, 3, all_operands, 2, "",
        "unalias: -a does not accept operands\n");
    value_is(aliases, "c", "three");
    invoke(csh_builtin_unalias, aliases, 3, dash, 0, "", "");
    value_is(aliases, "-x", NULL);
    CHECK(csh_aliases_set(aliases, "a", "one", &error) == 0);
    CHECK(csh_aliases_set(aliases, "-x", "dash", &error) == 0);
    invoke(csh_builtin_unalias, aliases, 3, after_operand, 0, "", "");
    value_is(aliases, "a", NULL);
    value_is(aliases, "-x", NULL);
    invoke(csh_builtin_unalias, aliases, 4, all, 0, "", "");
    value_is(aliases, "c", NULL);
    invoke(csh_builtin_unalias, aliases, 4, all, 0, "", "");
    invoke(csh_builtin_unalias, aliases, 2, bad_argv, 2, "",
        "unalias: invalid handler arguments\n");
    csh_aliases_destroy(aliases);
}

static void output_failure(void)
{
    struct csh_aliases *aliases = new_aliases();
    struct csh_error error;
    const char *list[] = {"alias"};
    const char *query[] = {"alias", "a"};
    FILE *out = fopen("/dev/null", "r");
    FILE *err = tmpfile();
    CHECK(out != NULL && err != NULL);
    CHECK(csh_aliases_set(aliases, "a", "value", &error) == 0);
    CHECK(csh_builtin_alias(aliases, 1, list, out, err) == 1);
    stream_is(err, "alias: cannot write output\n");
    CHECK(fclose(err) == 0);
    err = tmpfile();
    CHECK(err != NULL);
    clearerr(out);
    CHECK(csh_builtin_alias(aliases, 2, query, out, err) == 1);
    stream_is(err, "alias: cannot write output\n");
    CHECK(fclose(out) == 0 && fclose(err) == 0);
    csh_aliases_destroy(aliases);
}

int main(void)
{
    storage();
    alias_handler();
    unalias_handler();
    output_failure();
    puts("ok");
    return 0;
}
