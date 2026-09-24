#define _POSIX_C_SOURCE 200809L
#ifdef __APPLE__
#define _DARWIN_C_SOURCE
#endif
#define CSHELL_FIELDS_FAULT_IMPLEMENTATION
#include "fields_faults.h"
#include "cshell/expand.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <locale.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void *allocations[16384];
static DIR *directories[256];
static size_t live_allocations, allocation_calls, fail_allocation;
static size_t live_directories, open_calls, fail_open, read_calls, fail_read;
static size_t close_calls, fail_close;
static size_t stat_calls, fail_stat, lstat_calls, fail_lstat;
static size_t interrupt_calls, fail_interrupt;
static int interrupted_with_directory, interrupted_with_allocation;
static int io_error = EIO;
static struct stat partial_directory_status;
static DIR *partial_directory;
static size_t partial_read_calls, fail_partial_read;
static int partial_read_enabled;

static size_t allocation_slot(void *pointer)
{
    size_t index;
    for (index = 0; index < sizeof(allocations) / sizeof(allocations[0]); ++index)
        if (allocations[index] == pointer)
            return index;
    assert(!"untracked pointer or exhausted allocation table");
    return 0;
}

static int fail_now(void)
{
    ++allocation_calls;
    if (allocation_calls == fail_allocation) {
        errno = ENOMEM;
        return 1;
    }
    return 0;
}

void *csh_fields_fault_malloc(size_t size)
{
    void *pointer;
    if (fail_now())
        return NULL;
    pointer = malloc(size);
    assert(pointer != NULL);
    allocations[allocation_slot(NULL)] = pointer;
    ++live_allocations;
    return pointer;
}

void *csh_fields_fault_realloc(void *pointer, size_t size)
{
    size_t slot = allocation_slot(pointer);
    void *result;
    if (fail_now())
        return NULL;
    if (pointer == NULL)
        ++live_allocations;
    result = realloc(pointer, size);
    assert(result != NULL);
    allocations[slot] = result;
    return result;
}

void csh_fields_fault_free(void *pointer)
{
    if (pointer == NULL)
        return;
    allocations[allocation_slot(pointer)] = NULL;
    assert(live_allocations != 0);
    --live_allocations;
    free(pointer);
}

static size_t directory_slot(DIR *directory)
{
    size_t index;
    for (index = 0; index < sizeof(directories) / sizeof(directories[0]); ++index)
        if (directories[index] == directory)
            return index;
    assert(!"untracked directory or exhausted directory table");
    return 0;
}

DIR *csh_fields_fault_opendir(const char *path)
{
    DIR *directory;
    ++open_calls;
    if (open_calls == fail_open) {
        errno = io_error;
        return NULL;
    }
    directory = opendir(path);
    if (directory != NULL) {
        directories[directory_slot(NULL)] = directory;
        ++live_directories;
        if (partial_read_enabled) {
            struct stat status;
            assert(fstat(dirfd(directory), &status) == 0);
            if (status.st_dev == partial_directory_status.st_dev &&
                status.st_ino == partial_directory_status.st_ino)
                partial_directory = directory;
        }
    }
    return directory;
}

struct dirent *csh_fields_fault_readdir(DIR *directory)
{
    (void)directory_slot(directory);
    ++read_calls;
    if (directory == partial_directory &&
        ++partial_read_calls == fail_partial_read) {
        errno = io_error;
        return NULL;
    }
    if (read_calls == fail_read) {
        errno = io_error;
        return NULL;
    }
    return readdir(directory);
}

int csh_fields_fault_closedir(DIR *directory)
{
    int result;
    if (directory == partial_directory)
        partial_directory = NULL;
    directories[directory_slot(directory)] = NULL;
    assert(live_directories != 0);
    --live_directories;
    result = closedir(directory);
    assert(result == 0);
    ++close_calls;
    if (close_calls == fail_close) {
        errno = io_error;
        return -1;
    }
    return result;
}

int csh_fields_fault_stat(const char *path, struct stat *status)
{
    ++stat_calls;
    if (stat_calls == fail_stat) {
        errno = io_error;
        return -1;
    }
    return stat(path, status);
}

int csh_fields_fault_lstat(const char *path, struct stat *status)
{
    ++lstat_calls;
    if (lstat_calls == fail_lstat) {
        errno = io_error;
        return -1;
    }
    return lstat(path, status);
}

static int interrupted(void *user)
{
    assert(user == &interrupt_calls);
    ++interrupt_calls;
    if (interrupt_calls != fail_interrupt)
        return 0;
    if (live_directories != 0)
        interrupted_with_directory = 1;
    if (live_allocations != 0)
        interrupted_with_allocation = 1;
    return 1;
}

struct span_spec {
    const char *text;
    enum csh_quote quote;
    enum csh_expand_origin origin;
    int split, keep_empty;
};

struct input {
    struct csh_expansion expansion;
    struct csh_expand_field field;
    struct csh_expand_span spans[8];
    struct csh_expansion saved_expansion;
    struct csh_expand_field saved_field;
    struct csh_expand_span saved_spans[8];
    const struct span_spec *specs;
    size_t count;
};

static void input_create(struct input *input, const struct span_spec *specs,
    size_t count, enum csh_expand_context context)
{
    size_t index;
    assert(count <= sizeof(input->spans) / sizeof(input->spans[0]));
    memset(input, 0, sizeof(*input));
    input->specs = specs;
    input->count = count;
    input->expansion.fields = &input->field;
    input->expansion.field_count = 1;
    input->expansion.context = context;
    input->field.spans = input->spans;
    input->field.span_count = count;
    for (index = 0; index < count; ++index) {
        struct csh_expand_span *span = &input->spans[index];
        span->length = strlen(specs[index].text);
        span->text = malloc(span->length + 1);
        assert(span->text != NULL);
        memcpy(span->text, specs[index].text, span->length + 1);
        span->quote = specs[index].quote;
        span->origin = specs[index].origin;
        span->split = specs[index].split;
        span->keep_empty = specs[index].keep_empty;
    }
    memcpy(&input->saved_expansion, &input->expansion, sizeof(input->expansion));
    memcpy(&input->saved_field, &input->field, sizeof(input->field));
    memcpy(input->saved_spans, input->spans, sizeof(input->spans));
}

static void input_unchanged(const struct input *input)
{
    size_t index;
    assert(memcmp(&input->expansion, &input->saved_expansion,
        sizeof(input->expansion)) == 0);
    assert(memcmp(&input->field, &input->saved_field, sizeof(input->field)) == 0);
    assert(memcmp(input->spans, input->saved_spans, sizeof(input->spans)) == 0);
    for (index = 0; index < input->count; ++index)
        assert(strcmp(input->spans[index].text, input->specs[index].text) == 0);
}

static void input_destroy(struct input *input)
{
    size_t index;
    input_unchanged(input);
    for (index = 0; index < input->count; ++index)
        free(input->spans[index].text);
}

enum fault_kind { ALLOCATION, OPEN_DIRECTORY, READ_DIRECTORY, CLOSE_DIRECTORY,
    STAT_DIRECTORY, LSTAT_COMPONENT, INTERRUPTION };

static void sweep(struct csh_state *state, const struct span_spec *specs,
    size_t count, enum csh_expand_context context, enum fault_kind fault)
{
    struct input input;
    struct csh_state_info before, after;
    struct csh_variable_view ifs;
    const char *borrowed_ifs;
    size_t point;
    assert(csh_state_get_info(state, &before) == CSH_STATE_OK);
    assert(csh_state_get_variable(state, "IFS", &ifs) == CSH_STATE_OK);
    borrowed_ifs = ifs.value;
    input_create(&input, specs, count, context);
    for (point = 1; point < 10000; ++point) {
        struct csh_fields out = {0};
        struct csh_expand_error error;
        struct csh_field_options options = {interrupted, &interrupt_calls};
        enum csh_expand_result result, expected;
        size_t calls;
        assert(live_allocations == 0 && live_directories == 0);
        allocation_calls = open_calls = read_calls = interrupt_calls = 0;
        stat_calls = lstat_calls = close_calls = 0;
        fail_allocation = fault == ALLOCATION ? point : 0;
        fail_open = fault == OPEN_DIRECTORY ? point : 0;
        fail_read = fault == READ_DIRECTORY ? point : 0;
        fail_close = fault == CLOSE_DIRECTORY ? point : 0;
        fail_stat = fault == STAT_DIRECTORY ? point : 0;
        fail_lstat = fault == LSTAT_COMPONENT ? point : 0;
        fail_interrupt = fault == INTERRUPTION ? point : 0;
        memset(&error, 0, sizeof(error));
        result = csh_expand_fields(state, &input.expansion, &options, &out, &error);
        calls = fault == ALLOCATION ? allocation_calls :
            fault == OPEN_DIRECTORY ? open_calls :
            fault == READ_DIRECTORY ? read_calls :
            fault == CLOSE_DIRECTORY ? close_calls :
            fault == STAT_DIRECTORY ? stat_calls :
            fault == LSTAT_COMPONENT ? lstat_calls : interrupt_calls;
        expected = fault == ALLOCATION ? CSH_EXPAND_NOMEM :
            fault == INTERRUPTION || io_error == EINTR ? CSH_EXPAND_INTERRUPTED :
            io_error == ENOMEM ? CSH_EXPAND_NOMEM : CSH_EXPAND_IO;
        if (result == CSH_EXPAND_OK) {
            assert(point > 1); /* Each sweep must reach its targeted operation. */
            assert(point > calls);
            assert(out.count != 0);
            assert(out.values != NULL);
            assert(out.values[out.count] == NULL);
        } else {
            if (result != expected)
                fprintf(stderr, "field fault %d at %zu: expected %d, got %d %s\n",
                    fault, point, expected, result, error.message);
            assert(result == expected && error.code == expected);
            assert(point <= calls);
            assert(out.values == NULL && out.count == 0);
            assert(error.fragment == CSH_FRAGMENT_ROOT);
            assert(error.message[0] != '\0');
        }
        input_unchanged(&input);
        assert(csh_state_get_info(state, &after) == CSH_STATE_OK);
        assert(before.argument_count == after.argument_count);
        assert(before.last_status == after.last_status);
        assert(before.shell_pid == after.shell_pid);
        assert(before.background_pid == after.background_pid);
        assert(before.mode == after.mode && before.options == after.options);
        assert(csh_state_get_variable(state, "IFS", &ifs) == CSH_STATE_OK);
        assert(ifs.value == borrowed_ifs);
        fail_allocation = fail_open = fail_read = fail_interrupt = 0;
        fail_stat = fail_lstat = fail_close = 0;
        csh_fields_destroy(&out);
        assert(out.values == NULL && out.count == 0);
        csh_fields_destroy(&out);
        assert(live_allocations == 0 && live_directories == 0);
        if (result == CSH_EXPAND_OK) {
            input_destroy(&input);
            return;
        }
    }
    assert(!"field failure sweep did not converge");
}

static void make_file(const char *path)
{
    FILE *file = fopen(path, "wb");
    assert(file != NULL);
    assert(fclose(file) == 0);
}

/* Content-related read errors must act as an empty directory even after some
 * matches were read; matches from other directories still remain usable. */
static void swallowed_read_failures(struct csh_state *state)
{
    const int errors[] = {EACCES, ENOENT};
    size_t mode, error_index, point;
    assert(stat("a-dir", &partial_directory_status) == 0);
    partial_read_enabled = 1;
    for (mode = 0; mode < 2; ++mode) {
        const struct span_spec spec = {mode == 0 ? "a-dir/*.txt" : "*/*.txt",
            CSH_QUOTE_NONE, CSH_EXPAND_LITERAL, 0, 0};
        struct input input;
        input_create(&input, &spec, 1, CSH_EXPAND_ARGUMENT);
        for (error_index = 0; error_index < sizeof(errors) / sizeof(errors[0]);
            ++error_index) {
            io_error = errors[error_index];
            for (point = 1; point < 100; ++point) {
                struct csh_fields out = {0};
                struct csh_expand_error error;
                int reached;
                assert(live_allocations == 0 && live_directories == 0);
                fail_partial_read = point;
                partial_read_calls = 0;
                assert(csh_expand_fields(state, &input.expansion, NULL, &out,
                    &error) == CSH_EXPAND_OK);
                reached = point <= partial_read_calls;
                if (reached) {
                    assert(out.count == 1);
                    assert(strcmp(out.values[0], mode == 0 ? "a-dir/*.txt" :
                        "b-dir/m.txt") == 0);
                } else {
                    assert(point > 1);
                    assert(out.count == (mode == 0 ? 2 : 3));
                    assert(strcmp(out.values[0], "a-dir/a.txt") == 0);
                    assert(strcmp(out.values[1], "a-dir/z.txt") == 0);
                    if (mode != 0)
                        assert(strcmp(out.values[2], "b-dir/m.txt") == 0);
                }
                input_unchanged(&input);
                csh_fields_destroy(&out);
                assert(live_allocations == 0 && live_directories == 0);
                if (!reached)
                    break;
            }
            assert(point < 100);
        }
        input_destroy(&input);
    }
    partial_read_enabled = 0;
    fail_partial_read = 0;
    io_error = EIO;
}

int main(void)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state;
    char temporary[] = "/tmp/cshell-fields-faults-XXXXXX";
    int original_directory;
    size_t index;
    const int io_errors[] = {EIO, EINTR, ENOMEM};
    const char *files[] = {"alpha.txt", "beta.txt", ".hidden.txt", "a-dir/z.txt",
        "a-dir/a.txt", "b-dir/m.txt", "b-dir/deep/inner.txt"};
    const struct span_spec split[] = {
        {"prefix", CSH_QUOTE_NONE, CSH_EXPAND_LITERAL, 0, 0},
        {"  one : two:: three\t four ", CSH_QUOTE_NONE, CSH_EXPAND_PARAMETER, 1, 0},
        {" suffix", CSH_QUOTE_DOUBLE, CSH_EXPAND_LITERAL, 0, 0}
    };
    const struct span_spec glob[] = {
        {"*/*.txt */*/*.txt [ab]*.txt no-match-*.none .*.txt",
            CSH_QUOTE_NONE, CSH_EXPAND_PARAMETER, 1, 0}
    };
    const struct span_spec no_match[] = {
        {"missing*/[ab]*.txt", CSH_QUOTE_NONE, CSH_EXPAND_LITERAL, 0, 0}
    };
    const struct span_spec directory[] = {
        {"*/", CSH_QUOTE_NONE, CSH_EXPAND_LITERAL, 0, 0}
    };
    const struct span_spec literal_component[] = {
        {"*/a.txt", CSH_QUOTE_NONE, CSH_EXPAND_LITERAL, 0, 0}
    };
    const struct span_spec restricted[] = {
        {"*.txt split words", CSH_QUOTE_NONE, CSH_EXPAND_PARAMETER, 1, 0},
        {"", CSH_QUOTE_DOUBLE, CSH_EXPAND_PARAMETER, 0, 1}
    };
    const struct span_spec quoted[] = {
        {"*.txt", CSH_QUOTE_SINGLE, CSH_EXPAND_LITERAL, 0, 0},
        {"", CSH_QUOTE_DOUBLE, CSH_EXPAND_PARAMETER, 0, 1}
    };
    assert(setlocale(LC_ALL, "C") != NULL);
    original_directory = open(".", O_RDONLY);
    assert(original_directory >= 0);
    assert(mkdtemp(temporary) != NULL);
    assert(chdir(temporary) == 0);
    assert(mkdir("a-dir", 0700) == 0);
    assert(mkdir("b-dir", 0700) == 0);
    assert(mkdir("b-dir/deep", 0700) == 0);
    for (index = 0; index < sizeof(files) / sizeof(files[0]); ++index)
        make_file(files[index]);
    invocation.arg0 = "fields-fault-zero";
    invocation.mode = CSH_MODE_STRING;
    assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
    assert(csh_state_set_status(state, 42) == CSH_STATE_OK);
    assert(csh_state_set_variable(state, "IFS", " \t:") == CSH_STATE_OK);
    sweep(state, split, 3, CSH_EXPAND_ARGUMENT, ALLOCATION);
    sweep(state, split, 3, CSH_EXPAND_ARGUMENT, INTERRUPTION);
    assert(csh_state_unset_variable(state, "IFS") == CSH_STATE_OK);
    sweep(state, glob, 1, CSH_EXPAND_ARGUMENT, ALLOCATION);
    sweep(state, no_match, 1, CSH_EXPAND_ARGUMENT, ALLOCATION);
    sweep(state, restricted, 2, CSH_EXPAND_ASSIGNMENT, ALLOCATION);
    sweep(state, restricted, 2, CSH_EXPAND_PATTERN, ALLOCATION);
    sweep(state, quoted, 2, CSH_EXPAND_ARGUMENT, ALLOCATION);
    for (index = 0; index < sizeof(io_errors) / sizeof(io_errors[0]); ++index) {
        io_error = io_errors[index];
        sweep(state, glob, 1, CSH_EXPAND_ARGUMENT, OPEN_DIRECTORY);
        sweep(state, glob, 1, CSH_EXPAND_ARGUMENT, READ_DIRECTORY);
        sweep(state, glob, 1, CSH_EXPAND_ARGUMENT, CLOSE_DIRECTORY);
        sweep(state, directory, 1, CSH_EXPAND_ARGUMENT, STAT_DIRECTORY);
        sweep(state, literal_component, 1, CSH_EXPAND_ARGUMENT, LSTAT_COMPONENT);
    }
    sweep(state, glob, 1, CSH_EXPAND_ARGUMENT, INTERRUPTION);
    swallowed_read_failures(state);
    assert(interrupted_with_directory);
    assert(interrupted_with_allocation);
    csh_fields_destroy(NULL);
    csh_state_destroy(state);
    for (index = 0; index < sizeof(files) / sizeof(files[0]); ++index)
        assert(unlink(files[index]) == 0);
    assert(rmdir("b-dir/deep") == 0);
    assert(rmdir("a-dir") == 0);
    assert(rmdir("b-dir") == 0);
    assert(fchdir(original_directory) == 0);
    assert(close(original_directory) == 0);
    assert(rmdir(temporary) == 0);
    puts("PASS: field/pathname allocation, I/O, interruption, and ownership cleanup");
    return 0;
}
