#define CSHELL_FAULT_IMPLEMENTATION
#include "input_faults.h"
#include "cshell/invocation.h"

/* Fault checks and their setup must run even with release CFLAGS. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>

static void *allocations[64];
static size_t live_allocations;
static size_t allocation_calls;
static size_t fail_allocation;
static size_t read_calls;
static size_t fail_read;
static size_t interrupt_read;

static size_t allocation_slot(void *pointer)
{
    size_t index;
    for (index = 0; index < sizeof(allocations) / sizeof(allocations[0]); ++index) {
        if (allocations[index] == pointer)
            return index;
    }
    assert(!"untracked allocation or exhausted allocation table");
    return 0;
}

static int should_fail_allocation(void)
{
    ++allocation_calls;
    if (allocation_calls == fail_allocation) {
        errno = ENOMEM;
        return 1;
    }
    return 0;
}

void *csh_fault_malloc(size_t size)
{
    void *pointer;
    if (should_fail_allocation())
        return NULL;
    pointer = malloc(size);
    assert(pointer != NULL);
    allocations[allocation_slot(NULL)] = pointer;
    ++live_allocations;
    return pointer;
}

void *csh_fault_realloc(void *pointer, size_t size)
{
    size_t slot = allocation_slot(pointer);
    void *result;
    if (should_fail_allocation())
        return NULL;
    if (pointer == NULL)
        ++live_allocations;
    result = realloc(pointer, size);
    assert(result != NULL);
    allocations[slot] = result;
    return result;
}

void csh_fault_free(void *pointer)
{
    if (pointer == NULL)
        return;
    allocations[allocation_slot(pointer)] = NULL;
    --live_allocations;
    free(pointer);
}

ssize_t csh_fault_read(int fd, void *buffer, size_t size)
{
    ++read_calls;
    if (read_calls == interrupt_read || read_calls == fail_read) {
        errno = read_calls == interrupt_read ? EINTR : EIO;
        return -1;
    }
    return read(fd, buffer, size);
}

static void reset_faults(void)
{
    assert(live_allocations == 0);
    allocation_calls = 0;
    fail_allocation = 0;
    read_calls = 0;
    fail_read = 0;
    interrupt_read = 0;
}

static void check_sticky_failure(struct csh_input *input,
    struct csh_error first, struct csh_input_line *line)
{
    struct csh_error repeated;
    size_t reads = read_calls;
    size_t calls = allocation_calls;
    int repeat;
    assert(line->data == NULL && line->length == 0);
    assert(first.message != NULL && first.status != 0);
    for (repeat = 0; repeat < 3; ++repeat) {
        assert(csh_input_read_line(input, line, &repeated) == CSH_INPUT_ERROR);
        assert(line->data == NULL && line->length == 0);
        assert(repeated.message == first.message);
        assert(repeated.system_errno == first.system_errno);
        assert(repeated.status == first.status);
        assert(repeated.position.offset == first.position.offset);
    }
    assert(read_calls == reads && allocation_calls == calls);
}

static int next_descriptor(int fd, int minimum)
{
    int result = fcntl(fd, F_DUPFD_CLOEXEC, minimum);
    assert(result != -1);
    assert(close(result) == 0);
    return result;
}

static void check_allocation_failures(const char *path, int fd, char *payload)
{
    size_t mode;
    size_t point;
    int low = next_descriptor(fd, 0);
    int high = next_descriptor(fd, 10);
    for (mode = 0; mode < 6; ++mode) {
        /* Fail each allocation in construction and line growth in turn, until
         * a complete run succeeds without reaching the injected fault. */
        for (point = 1; point < 100; ++point) {
            struct csh_input *input = NULL;
            struct csh_invocation invocation = {0};
            struct csh_error error;
            struct csh_input_line line;
            enum csh_input_result result = CSH_INPUT_ERROR;
            size_t total = 0;
            int created;
            int succeeded = 0;
            char *string_argv[] = {"cshell", "-c", payload, "arg0", "one", "", "three"};
            char *file_argv[] = {"cshell", (char *)path, "one", "", "three"};
            char *stdin_argv[] = {"cshell", "-s", "one", "", "three"};
            reset_faults();
            fail_allocation = point;
            assert(lseek(fd, 0, SEEK_SET) == 0);
            switch (mode) {
            case 0:
                created = csh_input_from_string(&input, payload, "fault-string", &error);
                break;
            case 1:
                created = csh_input_from_file(&input, path, &error);
                break;
            case 2:
                created = csh_input_from_fd(&input, fd, "fault-fd", &error);
                break;
            case 3:
                created = csh_invocation_parse(&invocation, 7, string_argv, fd, -1, &error);
                input = invocation.input;
                break;
            case 4:
                created = csh_invocation_parse(&invocation, 5, file_argv, fd, -1, &error);
                input = invocation.input;
                break;
            default:
                created = csh_invocation_parse(&invocation, 5, stdin_argv, fd, -1, &error);
                input = invocation.input;
                break;
            }
            if (created == -1) {
                assert(input == NULL);
                assert(invocation.input == NULL && invocation.arg0 == NULL);
                assert(invocation.arguments == NULL && invocation.argument_count == 0);
                assert(error.system_errno == ENOMEM && error.status == 1);
            } else {
                while ((result = csh_input_read_line(input, &line, &error)) == CSH_INPUT_LINE)
                    total += line.length;
                if (result == CSH_INPUT_ERROR) {
                    assert(error.system_errno == ENOMEM && error.status == 1);
                    check_sticky_failure(input, error, &line);
                } else {
                    assert(total == strlen(payload));
                    succeeded = 1;
                }
            }
            if (mode < 3)
                csh_input_destroy(input);
            else {
                csh_invocation_destroy(&invocation);
                csh_invocation_destroy(&invocation);
            }
            assert(live_allocations == 0);
            assert(next_descriptor(fd, 0) == low);
            assert(next_descriptor(fd, 10) == high);
            if (succeeded) {
                assert(point > allocation_calls);
                break;
            }
        }
        assert(point < 100);
    }
}

static void check_read_failures(int fd)
{
    size_t point;
    /* Failure before any byte, within a line, after a complete line, and at
     * EOF. No failed line may escape as valid data. EINTR is retried. */
    const char text[] = "first\nsecond";
    assert(ftruncate(fd, 0) == 0);
    assert(lseek(fd, 0, SEEK_SET) == 0);
    assert(write(fd, text, sizeof(text) - 1) == (ssize_t)(sizeof(text) - 1));
    for (point = 1; point <= sizeof(text); ++point) {
        struct csh_input *input;
        struct csh_error error;
        struct csh_input_line line;
        enum csh_input_result result;
        reset_faults();
        fail_read = point;
        assert(lseek(fd, 0, SEEK_SET) == 0);
        assert(csh_input_from_fd(&input, fd, "read-error", &error) == 0);
        while ((result = csh_input_read_line(input, &line, &error)) == CSH_INPUT_LINE) {
            assert(line.length == 6 && memcmp(line.data, "first\n", 6) == 0);
        }
        assert(result == CSH_INPUT_ERROR);
        assert(error.system_errno == EIO && error.status == 128);
        assert(error.position.offset == point - 1);
        assert(error.position.line == (point <= 6 ? 1 : 2));
        assert(error.position.column == (point <= 6 ? point : point - 6));
        check_sticky_failure(input, error, &line);
        csh_input_destroy(input);
        assert(live_allocations == 0);
    }
    for (point = 1; point <= sizeof(text); ++point) {
        struct csh_input *input;
        struct csh_error error;
        struct csh_input_line line;
        size_t total = 0;
        enum csh_input_result result;
        reset_faults();
        interrupt_read = point;
        assert(lseek(fd, 0, SEEK_SET) == 0);
        assert(csh_input_from_fd(&input, fd, "interrupted", &error) == 0);
        while ((result = csh_input_read_line(input, &line, &error)) == CSH_INPUT_LINE)
            total += line.length;
        assert(result == CSH_INPUT_EOF && total == sizeof(text) - 1);
        csh_input_destroy(input);
        assert(live_allocations == 0);
    }
}

int main(void)
{
    char path[] = "/tmp/cshell-input-faults-XXXXXX";
    char *payload = malloc(32771);
    int fd = mkstemp(path);
    assert(fd >= 0 && payload != NULL);
    memset(payload, 'x', 32770);
    payload[2] = '\n';
    payload[32768] = '\n';
    payload[32770] = '\0';
    assert(write(fd, payload, 32770) == 32770);
    check_allocation_failures(path, fd, payload);
    check_read_failures(fd);
    assert(close(fd) == 0);
    assert(unlink(path) == 0);
    free(payload);
    puts("PASS: allocation failure sweep, read failures, EINTR, sticky errors, resource cleanup");
    return 0;
}
