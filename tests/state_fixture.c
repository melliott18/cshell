/* Replacement state API checks. Assertions remain active with NDEBUG. */
#include "cshell/state.h"

#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "state fixture failed at line %d: %s\n", \
            __LINE__, #condition); \
        exit(90); \
    } \
} while (0)

#define OK(operation) CHECK((operation) == CSH_STATE_OK)

static struct csh_state *new_state(char *const environment[])
{
    char *arguments[] = {"fixture-shell", "-c", "", "state-zero", "first", ""};
    struct csh_invocation invocation;
    struct csh_error error;
    struct csh_state *state;
    int fd = open("/dev/null", O_RDONLY);

    CHECK(fd >= 0);
    CHECK(csh_invocation_parse(&invocation, 6, arguments, fd, fd, &error) == 0);
    OK(csh_state_create(&state, &invocation, environment));
    csh_invocation_destroy(&invocation);
    CHECK(close(fd) == 0);
    return state;
}

static void variable_is(const struct csh_state *state, const char *name,
    const char *value, unsigned attributes)
{
    struct csh_variable_view actual;

    OK(csh_state_get_variable(state, name, &actual));
    CHECK(actual.attributes == attributes);
    if (value == NULL) {
        CHECK(actual.value == NULL);
    } else {
        CHECK(actual.value != NULL && strcmp(actual.value, value) == 0);
    }
}

static void parameters_are(const struct csh_state *state, const char *arg0,
    size_t count, const char *const arguments[])
{
    struct csh_state_info info;
    size_t index;

    OK(csh_state_get_info(state, &info));
    CHECK(info.argument_count == count);
    CHECK(strcmp(csh_state_parameter(state, 0), arg0) == 0);
    for (index = 0; index < count; ++index) {
        CHECK(strcmp(csh_state_parameter(state, index + 1), arguments[index]) == 0);
    }
    CHECK(csh_state_parameter(state, count + 1) == NULL);
    CHECK(csh_state_parameter(state, SIZE_MAX) == NULL);
}

static size_t environment_count(char *const environment[])
{
    size_t count = 0;

    CHECK(environment != NULL);
    while (environment[count] != NULL) {
        ++count;
    }
    return count;
}

static void environment_has(char *const environment[], const char *entry)
{
    size_t index;
    size_t matches = 0;

    for (index = 0; environment[index] != NULL; ++index) {
        if (strcmp(environment[index], entry) == 0) {
            ++matches;
        }
    }
    CHECK(matches == 1);
}

static void info_is(const struct csh_state *state,
    const struct csh_state_info *expected)
{
    struct csh_state_info actual;

    OK(csh_state_get_info(state, &actual));
    CHECK(actual.argument_count == expected->argument_count);
    CHECK(actual.last_status == expected->last_status);
    CHECK(actual.shell_pid == expected->shell_pid);
    CHECK(actual.background_pid == expected->background_pid);
    CHECK(actual.mode == expected->mode);
    CHECK(actual.options == expected->options);
}

static void variables_and_import(void)
{
    char imported[] = "IMPORTED=initial";
    char duplicate[] = "DUP=last=part";
    char *environment[] = {imported, "EMPTY=", "DUP=first", "DUP",
        duplicate, "=bad", "9BAD=no", "BAD-NAME=no", "NO_EQUALS",
        "_valid9=yes", "\303\251=bad", NULL};
    const char *invalid_names[] = {"", "9BAD", "BAD-NAME", "A=B", "a.b",
        "a b", "\303\251", NULL};
    struct csh_state *state = new_state(environment);
    struct csh_variable_view view;
    char **snapshot;
    char name[] = "OWNED";
    char value[] = "copied";
    size_t index;

    memset(imported, '#', sizeof(imported) - 1);
    memset(duplicate, '#', sizeof(duplicate) - 1);
    variable_is(state, "IMPORTED", "initial", CSH_VAR_EXPORT);
    variable_is(state, "EMPTY", "", CSH_VAR_EXPORT);
    variable_is(state, "DUP", "last=part", CSH_VAR_EXPORT);
    variable_is(state, "_valid9", "yes", CSH_VAR_EXPORT);
    variable_is(state, "NO_EQUALS", NULL, 0);
    OK(csh_state_environment(state, &snapshot));
    CHECK(environment_count(snapshot) == 4);
    environment_has(snapshot, "IMPORTED=initial");
    environment_has(snapshot, "EMPTY=");
    environment_has(snapshot, "DUP=last=part");
    environment_has(snapshot, "_valid9=yes");
    csh_state_environment_destroy(snapshot);

    variable_is(state, "UNSET", NULL, 0);
    OK(csh_state_unset_variable(state, "UNSET"));
    OK(csh_state_set_variable(state, "UNSET", ""));
    variable_is(state, "UNSET", "", 0);
    OK(csh_state_set_variable(state, "UNSET", "replacement"));
    variable_is(state, "UNSET", "replacement", 0);
    OK(csh_state_unset_variable(state, "UNSET"));
    variable_is(state, "UNSET", NULL, 0);
    OK(csh_state_set_variable(state, name, value));
    memset(name, '#', sizeof(name) - 1);
    memset(value, '#', sizeof(value) - 1);
    variable_is(state, "OWNED", "copied", 0);

    /* Both a new name and a replacement value can borrow existing storage. */
    OK(csh_state_set_variable(state, "ALIAS", "BORROWED"));
    OK(csh_state_get_variable(state, "ALIAS", &view));
    OK(csh_state_set_variable(state, view.value, "created"));
    variable_is(state, "BORROWED", "created", 0);
    OK(csh_state_get_variable(state, "ALIAS", &view));
    OK(csh_state_set_variable(state, "ALIAS", view.value + 1));
    variable_is(state, "ALIAS", "ORROWED", 0);

    for (index = 0; invalid_names[index] != NULL; ++index) {
        CHECK(csh_state_get_variable(state, invalid_names[index], &view) ==
            CSH_STATE_INVALID);
        CHECK(csh_state_set_variable(state, invalid_names[index], "bad") ==
            CSH_STATE_INVALID);
        CHECK(csh_state_update_attributes(state, invalid_names[index],
            CSH_VAR_EXPORT, 0) == CSH_STATE_INVALID);
        CHECK(csh_state_unset_variable(state, invalid_names[index]) ==
            CSH_STATE_INVALID);
    }
    variable_is(state, "IMPORTED", "initial", CSH_VAR_EXPORT);
    csh_state_destroy(state);

    state = new_state(NULL);
    OK(csh_state_environment(state, &snapshot));
    CHECK(environment_count(snapshot) == 0);
    csh_state_environment_destroy(snapshot);
    csh_state_destroy(state);
}

static void attributes_and_snapshots(void)
{
    struct csh_state *state = new_state(NULL);
    char **snapshot;
    char **later;

    OK(csh_state_set_variable(state, "LOCAL", "hidden"));
    OK(csh_state_set_variable(state, "EXPORTED", "one=two"));
    OK(csh_state_update_attributes(state, "EXPORTED", CSH_VAR_EXPORT, 0));
    OK(csh_state_set_variable(state, "EMPTY", ""));
    OK(csh_state_update_attributes(state, "EMPTY", CSH_VAR_EXPORT, 0));
    OK(csh_state_update_attributes(state, "DECLARED", CSH_VAR_EXPORT, 0));
    variable_is(state, "DECLARED", NULL, CSH_VAR_EXPORT);
    OK(csh_state_set_variable(state, "REMOVED", "old"));
    OK(csh_state_update_attributes(state, "REMOVED", CSH_VAR_EXPORT, 0));
    OK(csh_state_unset_variable(state, "REMOVED"));
    variable_is(state, "REMOVED", NULL, 0);

    OK(csh_state_set_variable(state, "LOCKED", "fixed"));
    OK(csh_state_update_attributes(state, "LOCKED", CSH_VAR_READONLY, 0));
    CHECK(csh_state_set_variable(state, "LOCKED", "changed") == CSH_STATE_READONLY);
    CHECK(csh_state_set_variable(state, "LOCKED", "fixed") == CSH_STATE_READONLY);
    CHECK(csh_state_unset_variable(state, "LOCKED") == CSH_STATE_READONLY);
    CHECK(csh_state_update_attributes(state, "LOCKED", CSH_VAR_EXPORT,
        CSH_VAR_READONLY) == CSH_STATE_READONLY);
    variable_is(state, "LOCKED", "fixed", CSH_VAR_READONLY);
    OK(csh_state_update_attributes(state, "LOCKED", CSH_VAR_EXPORT, 0));
    variable_is(state, "LOCKED", "fixed", CSH_VAR_READONLY | CSH_VAR_EXPORT);
    OK(csh_state_update_attributes(state, "LOCKED", 0, CSH_VAR_EXPORT));
    OK(csh_state_update_attributes(state, "LOCKED", CSH_VAR_READONLY, 0));
    variable_is(state, "LOCKED", "fixed", CSH_VAR_READONLY);
    OK(csh_state_update_attributes(state, "LOCKED_UNSET", CSH_VAR_READONLY, 0));
    CHECK(csh_state_set_variable(state, "LOCKED_UNSET", "new") == CSH_STATE_READONLY);
    CHECK(csh_state_unset_variable(state, "LOCKED_UNSET") == CSH_STATE_READONLY);
    variable_is(state, "LOCKED_UNSET", NULL, CSH_VAR_READONLY);
    CHECK(csh_state_update_attributes(state, "EXPORTED", CSH_VAR_EXPORT,
        CSH_VAR_EXPORT) == CSH_STATE_INVALID);
    CHECK(csh_state_update_attributes(state, "EXPORTED", 1u << 30, 0) ==
        CSH_STATE_INVALID);
    CHECK(csh_state_update_attributes(state, "EXPORTED", 0, 1u << 30) ==
        CSH_STATE_INVALID);
    variable_is(state, "EXPORTED", "one=two", CSH_VAR_EXPORT);

    OK(csh_state_environment(state, &snapshot));
    CHECK(environment_count(snapshot) == 2);
    environment_has(snapshot, "EXPORTED=one=two");
    environment_has(snapshot, "EMPTY=");
    OK(csh_state_set_variable(state, "EXPORTED", "changed"));
    OK(csh_state_unset_variable(state, "EMPTY"));
    OK(csh_state_set_variable(state, "DECLARED", "now-set"));
    OK(csh_state_environment(state, &later));
    CHECK(environment_count(later) == 2);
    environment_has(later, "EXPORTED=changed");
    environment_has(later, "DECLARED=now-set");
    csh_state_destroy(state);
    environment_has(snapshot, "EXPORTED=one=two");
    environment_has(snapshot, "EMPTY=");
    environment_has(later, "EXPORTED=changed");
    csh_state_environment_destroy(snapshot);
    csh_state_environment_destroy(later);
}

static void invocation_case(int argc, char **argv, enum csh_input_mode mode,
    unsigned options, const char *arg0, size_t count,
    const char *const arguments[], const char *source)
{
    struct csh_invocation invocation;
    struct csh_error error;
    struct csh_input_line line;
    struct csh_state_info info;
    struct csh_state *state;
    int fd = open("/dev/null", O_RDONLY);

    CHECK(fd >= 0);
    CHECK(csh_invocation_parse(&invocation, argc, argv, fd, fd, &error) == 0);
    OK(csh_state_create(&state, &invocation, NULL));
    if (source == NULL) {
        CHECK(csh_input_read_line(invocation.input, &line, &error) == CSH_INPUT_EOF);
    } else {
        CHECK(csh_input_read_line(invocation.input, &line, &error) == CSH_INPUT_LINE);
        CHECK(line.length == strlen(source));
        CHECK(memcmp(line.data, source, line.length) == 0);
    }
    csh_invocation_destroy(&invocation);
    CHECK(close(fd) == 0);
    parameters_are(state, arg0, count, arguments);
    OK(csh_state_get_info(state, &info));
    CHECK(info.mode == mode && info.options == options);
    CHECK(info.last_status == 0 && info.background_pid == 0);
    CHECK(info.shell_pid == getpid());
    csh_state_destroy(state);
}

static void invocation_mapping(void)
{
    char *string_argv[] = {"shell-exe", "-c", "command-source\n", "command-zero",
        "first", "", "-last"};
    char *default_zero_argv[] = {"shell-exe", "-c", ""};
    char *stdin_argv[] = {"shell-exe", "-is", "--", "one", ""};
    char *implicit_stdin_argv[] = {"shell-exe"};
    const char *string_args[] = {"first", "", "-last"};
    const char *stdin_args[] = {"one", ""};
    const char *file_args[] = {"file-arg", ""};
    char path[] = "/tmp/cshell-state-fixture-XXXXXX";
    char *file_argv[] = {"shell-exe", path, "file-arg", ""};
    int fd;

    invocation_case(7, string_argv, CSH_MODE_STRING, 0, "command-zero", 3,
        string_args, "command-source\n");
    invocation_case(3, default_zero_argv, CSH_MODE_STRING, 0, "shell-exe", 0,
        NULL, NULL);
    invocation_case(5, stdin_argv, CSH_MODE_STDIN, CSH_OPT_INTERACTIVE,
        "shell-exe", 2, stdin_args, NULL);
    invocation_case(1, implicit_stdin_argv, CSH_MODE_STDIN, 0, "shell-exe", 0,
        NULL, NULL);
    fd = mkstemp(path);
    CHECK(fd >= 0);
    CHECK(write(fd, "file-source\n", 12) == 12);
    CHECK(close(fd) == 0);
    invocation_case(4, file_argv, CSH_MODE_FILE, 0, path, 2, file_args,
        "file-source\n");
    CHECK(unlink(path) == 0);
}

static void parameters_and_scalars(void)
{
    struct csh_state *state = new_state(NULL);
    struct csh_state_info info;
    struct csh_variable_view view;
    char first[] = "new-first";
    char second[] = "new-second";
    const char *replacements[] = {first, second};
    const char *expected[] = {"new-first", "new-second"};
    const char *aliased[4];
    const char *alias_expected[] = {"new-second", "state-zero", "variable", "new-second"};
    const char *invalid[] = {"valid", NULL};
    unsigned all_options = CSH_OPT_INTERACTIVE | CSH_OPT_ALLEXPORT |
        CSH_OPT_ERREXIT | CSH_OPT_NOGLOB | CSH_OPT_NOEXEC | CSH_OPT_NOUNSET |
        CSH_OPT_VERBOSE | CSH_OPT_XTRACE | CSH_OPT_NOCLOBBER | CSH_OPT_PIPEFAIL |
        CSH_OPT_MONITOR | CSH_OPT_NOTIFY;

    OK(csh_state_set_parameters(state, 2, replacements));
    memset(first, '#', sizeof(first) - 1);
    memset(second, '#', sizeof(second) - 1);
    parameters_are(state, "state-zero", 2, expected);
    OK(csh_state_set_variable(state, "ARG", "variable"));
    OK(csh_state_get_variable(state, "ARG", &view));
    aliased[0] = csh_state_parameter(state, 2);
    aliased[1] = csh_state_parameter(state, 0);
    aliased[2] = view.value;
    aliased[3] = aliased[0];
    OK(csh_state_set_parameters(state, 4, aliased));
    OK(csh_state_set_variable(state, "ARG", "changed"));
    parameters_are(state, "state-zero", 4, alias_expected);
    CHECK(csh_state_set_parameters(state, 1, NULL) == CSH_STATE_INVALID);
    CHECK(csh_state_set_parameters(state, 2, invalid) == CSH_STATE_INVALID);
    parameters_are(state, "state-zero", 4, alias_expected);
    OK(csh_state_set_parameters(state, 0, NULL));
    parameters_are(state, "state-zero", 0, NULL);

    OK(csh_state_set_status(state, 7));
    OK(csh_state_set_background(state, (pid_t)12345));
    OK(csh_state_update_options(state, all_options, 0));
    OK(csh_state_get_info(state, &info));
    CHECK(info.last_status == 7 && info.background_pid == (pid_t)12345);
    CHECK(info.options == all_options && info.shell_pid == getpid());
    /* Flags store configuration; ALLEXPORT does not implement assignments yet. */
    OK(csh_state_set_variable(state, "OPTION_LOCAL", "value"));
    variable_is(state, "OPTION_LOCAL", "value", 0);
    CHECK(csh_state_update_options(state, CSH_OPT_XTRACE, CSH_OPT_XTRACE) ==
        CSH_STATE_INVALID);
    CHECK(csh_state_update_options(state, 1u << 30, 0) == CSH_STATE_INVALID);
    CHECK(csh_state_update_options(state, 0, 1u << 30) == CSH_STATE_INVALID);
    CHECK(csh_state_set_status(state, -1) == CSH_STATE_INVALID);
    CHECK(csh_state_set_background(state, (pid_t)-1) == CSH_STATE_INVALID);
    info_is(state, &info);
    OK(csh_state_update_options(state, 0, all_options));
    OK(csh_state_set_status(state, 255));
    OK(csh_state_set_background(state, 0));
    OK(csh_state_get_info(state, &info));
    CHECK(info.options == 0 && info.last_status == 255 && info.background_pid == 0);
    OK(csh_state_set_status(state, 300));
    OK(csh_state_get_info(state, &info));
    CHECK(info.last_status == 300);
    csh_state_destroy(state);
}

static void clone_isolation(void)
{
    struct csh_state *state = new_state(NULL);
    struct csh_state *clone;
    struct csh_state_info info;
    const char *arguments[] = {"clone-first", "", "clone-last"};
    const char *changed[] = {"changed"};
    char **snapshot;
    pid_t child;
    int child_status;

    OK(csh_state_set_variable(state, "MUTABLE", "original"));
    OK(csh_state_set_variable(state, "LOCKED", "fixed"));
    OK(csh_state_update_attributes(state, "LOCKED", CSH_VAR_EXPORT | CSH_VAR_READONLY, 0));
    OK(csh_state_update_attributes(state, "UNSET", CSH_VAR_EXPORT | CSH_VAR_READONLY, 0));
    OK(csh_state_set_parameters(state, 3, arguments));
    OK(csh_state_set_status(state, 42));
    OK(csh_state_set_background(state, (pid_t)123));
    OK(csh_state_update_options(state, CSH_OPT_INTERACTIVE | CSH_OPT_PIPEFAIL |
        CSH_OPT_NOUNSET, 0));
    OK(csh_state_get_info(state, &info));
    OK(csh_state_clone(state, &clone));
    info_is(clone, &info);
    parameters_are(clone, "state-zero", 3, arguments);
    variable_is(clone, "MUTABLE", "original", 0);
    variable_is(clone, "LOCKED", "fixed", CSH_VAR_EXPORT | CSH_VAR_READONLY);
    variable_is(clone, "UNSET", NULL, CSH_VAR_EXPORT | CSH_VAR_READONLY);
    CHECK(csh_state_set_variable(clone, "LOCKED", "bad") == CSH_STATE_READONLY);

    /* A copied shell's $$ remains its original pid after a process fork. */
    child = fork();
    CHECK(child >= 0);
    if (child == 0) {
        struct csh_state *child_clone;

        CHECK(getpid() != info.shell_pid);
        OK(csh_state_clone(state, &child_clone));
        info_is(child_clone, &info);
        csh_state_destroy(child_clone);
        csh_state_destroy(clone);
        csh_state_destroy(state);
        _exit(0);
    }
    CHECK(waitpid(child, &child_status, 0) == child);
    CHECK(WIFEXITED(child_status) && WEXITSTATUS(child_status) == 0);

    OK(csh_state_set_variable(clone, "MUTABLE", "clone"));
    OK(csh_state_update_attributes(clone, "LOCKED", 0, CSH_VAR_EXPORT));
    variable_is(state, "MUTABLE", "original", 0);
    variable_is(state, "LOCKED", "fixed", CSH_VAR_EXPORT | CSH_VAR_READONLY);
    OK(csh_state_set_parameters(state, 1, changed));
    OK(csh_state_set_status(state, 1));
    OK(csh_state_set_background(state, 0));
    OK(csh_state_update_options(state, CSH_OPT_XTRACE, CSH_OPT_PIPEFAIL));
    OK(csh_state_unset_variable(state, "MUTABLE"));
    csh_state_destroy(state);
    info_is(clone, &info);
    parameters_are(clone, "state-zero", 3, arguments);
    variable_is(clone, "MUTABLE", "clone", 0);
    variable_is(clone, "LOCKED", "fixed", CSH_VAR_READONLY);
    OK(csh_state_environment(clone, &snapshot));
    CHECK(environment_count(snapshot) == 0);
    csh_state_environment_destroy(snapshot);
    csh_state_destroy(clone);
}

static void save_and_restore(void)
{
    struct csh_state *state = new_state(NULL);
    struct csh_state_checkpoint *outer;
    struct csh_state_checkpoint *inner;
    struct csh_state_checkpoint *discarded;
    struct csh_state_info initial;
    struct csh_state_info middle;
    const char *initial_args[] = {"first", ""};
    const char *middle_args[] = {"middle", "more", ""};
    char **snapshot;

    OK(csh_state_set_variable(state, "VALUE", "initial"));
    OK(csh_state_update_attributes(state, "VALUE", CSH_VAR_EXPORT, 0));
    OK(csh_state_update_attributes(state, "UNSET", CSH_VAR_READONLY, 0));
    OK(csh_state_get_info(state, &initial));
    OK(csh_state_save(state, &outer));
    OK(csh_state_set_variable(state, "VALUE", "middle"));
    OK(csh_state_set_parameters(state, 3, middle_args));
    OK(csh_state_set_status(state, 17));
    OK(csh_state_set_background(state, (pid_t)456));
    OK(csh_state_update_options(state, CSH_OPT_NOGLOB | CSH_OPT_XTRACE, 0));
    OK(csh_state_get_info(state, &middle));
    OK(csh_state_save(state, &inner));
    OK(csh_state_environment(state, &snapshot));
    OK(csh_state_set_variable(state, "VALUE", "leaf"));
    OK(csh_state_update_attributes(state, "VALUE", CSH_VAR_READONLY, 0));
    OK(csh_state_set_variable(state, "ADDED", "leaf-only"));
    OK(csh_state_set_parameters(state, 0, NULL));
    OK(csh_state_set_status(state, 99));
    OK(csh_state_set_background(state, 0));
    OK(csh_state_update_options(state, 0, CSH_OPT_XTRACE));

    OK(csh_state_restore(state, &inner));
    CHECK(inner == NULL);
    info_is(state, &middle);
    parameters_are(state, "state-zero", 3, middle_args);
    variable_is(state, "VALUE", "middle", CSH_VAR_EXPORT);
    variable_is(state, "ADDED", NULL, 0);
    variable_is(state, "UNSET", NULL, CSH_VAR_READONLY);
    CHECK(csh_state_restore(state, &inner) == CSH_STATE_INVALID);
    info_is(state, &middle);
    OK(csh_state_update_attributes(state, "VALUE", CSH_VAR_READONLY, 0));
    OK(csh_state_restore(state, &outer));
    CHECK(outer == NULL);
    info_is(state, &initial);
    parameters_are(state, "state-zero", 2, initial_args);
    variable_is(state, "VALUE", "initial", CSH_VAR_EXPORT);
    OK(csh_state_set_variable(state, "VALUE", "mutable-again"));
    OK(csh_state_save(state, &discarded));
    csh_state_destroy(state);
    environment_has(snapshot, "VALUE=middle");
    csh_state_environment_destroy(snapshot);
    csh_state_checkpoint_destroy(discarded);
    csh_state_checkpoint_destroy(NULL);
}

static void invalid_arguments(void)
{
    struct csh_state *state = new_state(NULL);
    struct csh_state *out = NULL;
    struct csh_invocation invocation = {0};
    struct csh_state_info info;
    struct csh_variable_view view;
    struct csh_state_checkpoint *checkpoint = NULL;
    char **environment = NULL;
    char *invalid_parameters[] = {NULL};

    CHECK(csh_state_create(&out, NULL, NULL) == CSH_STATE_INVALID);
    CHECK(out == NULL);
    CHECK(csh_state_create(NULL, &invocation, NULL) == CSH_STATE_INVALID);
    CHECK(csh_state_create(&out, &invocation, NULL) == CSH_STATE_INVALID);
    CHECK(out == NULL);
    invocation.arg0 = "invalid-source";
    invocation.mode = (enum csh_input_mode)999;
    CHECK(csh_state_create(&out, &invocation, NULL) == CSH_STATE_INVALID);
    CHECK(out == NULL);
    invocation.mode = CSH_MODE_STDIN;
    invocation.argument_count = 1;
    CHECK(csh_state_create(&out, &invocation, NULL) == CSH_STATE_INVALID);
    CHECK(out == NULL);
    invocation.arguments = invalid_parameters;
    CHECK(csh_state_create(&out, &invocation, NULL) == CSH_STATE_INVALID);
    CHECK(out == NULL);
    CHECK(csh_state_get_variable(NULL, "A", &view) == CSH_STATE_INVALID);
    CHECK(csh_state_get_variable(state, NULL, &view) == CSH_STATE_INVALID);
    CHECK(csh_state_get_variable(state, "A", NULL) == CSH_STATE_INVALID);
    CHECK(csh_state_set_variable(NULL, "A", "value") == CSH_STATE_INVALID);
    CHECK(csh_state_set_variable(state, NULL, "value") == CSH_STATE_INVALID);
    CHECK(csh_state_set_variable(state, "A", NULL) == CSH_STATE_INVALID);
    CHECK(csh_state_unset_variable(NULL, "A") == CSH_STATE_INVALID);
    CHECK(csh_state_unset_variable(state, NULL) == CSH_STATE_INVALID);
    CHECK(csh_state_update_attributes(NULL, "A", CSH_VAR_EXPORT, 0) == CSH_STATE_INVALID);
    CHECK(csh_state_update_attributes(state, NULL, CSH_VAR_EXPORT, 0) == CSH_STATE_INVALID);
    CHECK(csh_state_environment(NULL, &environment) == CSH_STATE_INVALID);
    CHECK(csh_state_environment(state, NULL) == CSH_STATE_INVALID);
    CHECK(csh_state_parameter(NULL, 0) == NULL);
    CHECK(csh_state_set_parameters(NULL, 0, NULL) == CSH_STATE_INVALID);
    CHECK(csh_state_get_info(NULL, &info) == CSH_STATE_INVALID);
    CHECK(csh_state_get_info(state, NULL) == CSH_STATE_INVALID);
    CHECK(csh_state_set_status(NULL, 0) == CSH_STATE_INVALID);
    CHECK(csh_state_set_background(NULL, 0) == CSH_STATE_INVALID);
    CHECK(csh_state_update_options(NULL, 0, 0) == CSH_STATE_INVALID);
    CHECK(csh_state_clone(NULL, &out) == CSH_STATE_INVALID);
    CHECK(out == NULL);
    CHECK(csh_state_clone(state, NULL) == CSH_STATE_INVALID);
    CHECK(csh_state_save(NULL, &checkpoint) == CSH_STATE_INVALID);
    CHECK(checkpoint == NULL);
    CHECK(csh_state_save(state, NULL) == CSH_STATE_INVALID);
    CHECK(csh_state_restore(NULL, &checkpoint) == CSH_STATE_INVALID);
    CHECK(csh_state_restore(state, NULL) == CSH_STATE_INVALID);
    variable_is(state, "A", NULL, 0);
    csh_state_destroy(state);
    csh_state_destroy(NULL);
    csh_state_environment_destroy(NULL);
}

int main(void)
{
    variables_and_import();
    attributes_and_snapshots();
    invocation_mapping();
    parameters_and_scalars();
    clone_isolation();
    save_and_restore();
    invalid_arguments();
    puts("state fixtures passed");
    return 0;
}
