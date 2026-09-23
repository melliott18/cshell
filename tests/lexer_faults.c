#define CSHELL_LEXER_FAULT_IMPLEMENTATION
#include "lexer_faults.h"
#include "cshell/lexer.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

static void *allocations[8192];
static size_t live_allocations;
static size_t allocation_calls;
static size_t fail_allocation;

static size_t slot_for(void *pointer)
{
    size_t index;
    for (index = 0; index < sizeof(allocations) / sizeof(allocations[0]); ++index) {
        if (allocations[index] == pointer)
            return index;
    }
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

void *csh_lexer_fault_malloc(size_t size)
{
    void *pointer;
    if (fail_now())
        return NULL;
    pointer = malloc(size);
    assert(pointer != NULL);
    allocations[slot_for(NULL)] = pointer;
    ++live_allocations;
    return pointer;
}

void *csh_lexer_fault_realloc(void *pointer, size_t size)
{
    size_t slot = slot_for(pointer);
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

void csh_lexer_fault_free(void *pointer)
{
    if (pointer == NULL)
        return;
    allocations[slot_for(pointer)] = NULL;
    --live_allocations;
    free(pointer);
}

static void sticky(struct csh_lexer *lexer, const struct csh_error *first)
{
    size_t calls = allocation_calls;
    int repeat;
    assert(first->message != NULL && first->status != 0);
    for (repeat = 0; repeat < 3; ++repeat) {
        struct csh_token token = {0};
        struct csh_error error;
        assert(csh_lexer_next(lexer, &token, &error) == CSH_LEX_ERROR);
        assert(token.raw == NULL && token.fragments == NULL && token.source_name == NULL);
        assert(error.message == first->message && error.status == first->status &&
            error.system_errno == first->system_errno &&
            error.position.offset == first->position.offset);
    }
    assert(allocation_calls == calls);
}

/* Each run uses only simple command grammar, so every child RPAREN is the
 * parser-selected delimiter. The root owns all outstanding child frames. */
static int run(const char *source, size_t chunk)
{
    struct csh_lexer *frames[256] = {0};
    struct csh_error error;
    size_t length = strlen(source), fed = 0, depth = 0;
    int final = 0;
    int succeeded = 0;
    if (csh_lexer_create(&frames[0], "allocation-fault", &error) != 0) {
        assert(frames[0] == NULL && error.system_errno == ENOMEM && error.status == 1);
        return 0;
    }
    for (;;) {
        struct csh_token token = {0};
        enum csh_lex_result result = csh_lexer_next(frames[depth], &token, &error);
        if (result == CSH_LEX_TOKEN) {
            if (depth != 0 && token.kind == CSH_TOKEN_RPAREN) {
                if (csh_lexer_command_end(frames[depth - 1], frames[depth], &token,
                    &error) != 0) {
                    csh_token_destroy(&token);
                    break;
                }
                --depth;
            }
            csh_token_destroy(&token);
        } else if (result == CSH_LEX_COMMAND) {
            assert(depth + 1 < sizeof(frames) / sizeof(frames[0]));
            if (csh_lexer_command_begin(frames[depth], &frames[depth + 1], &error) != 0)
                break;
            ++depth;
        } else if (result == CSH_LEX_MORE) {
            size_t count = length - fed;
            assert(!final);
            if (count > chunk)
                count = chunk;
            final = fed + count == length;
            if (csh_lexer_feed(frames[0], source + fed, count, final, &error) != 0)
                break;
            fed += count;
        } else if (result == CSH_LEX_ERROR) {
            assert(token.raw == NULL && token.fragments == NULL && token.source_name == NULL);
            sticky(frames[depth], &error);
            break;
        } else {
            assert(result == CSH_LEX_EOF && depth == 0);
            succeeded = 1;
            break;
        }
    }
    if (!succeeded)
        assert(error.system_errno == ENOMEM && error.status == 1);
    csh_lexer_destroy(frames[0]);
    return succeeded;
}

static void sweep(const char *source, size_t chunk)
{
    size_t point;
    for (point = 1; point < 5000; ++point) {
        int succeeded;
        assert(live_allocations == 0);
        allocation_calls = 0;
        fail_allocation = point;
        succeeded = run(source, chunk);
        assert(live_allocations == 0);
        if (succeeded) {
            assert(point > allocation_calls);
            return;
        }
        assert(point <= allocation_calls);
    }
    assert(!"allocation sweep did not converge");
}

int main(void)
{
    char *large = malloc(32769);
    char nested[2048];
    size_t i, used = 0;
    assert(large != NULL);
    large[0] = '\'';
    memset(large + 1, 'x', 32766);
    large[32767] = '\'';
    large[32768] = '\0';
    sweep("", 4096);
    sweep("one a''\"two\" ${x:-${y}} $((1+2)) `echo x` &\\\n& end\n", 4096);
    sweep("first $(echo \"x\" $(echo y)) last", 1);
    sweep(large, 4096);
    for (i = 0; i < 40; ++i) {
        memcpy(nested + used, "${x:-", 5);
        used += 5;
    }
    nested[used++] = 'x';
    for (i = 0; i < 40; ++i)
        nested[used++] = '}';
    nested[used] = '\0';
    sweep(nested, 1);
    used = 0;
    for (i = 0; i < 30; ++i) {
        memcpy(nested + used, "$(echo ", 7);
        used += 7;
    }
    nested[used++] = 'x';
    for (i = 0; i < 30; ++i)
        nested[used++] = ')';
    nested[used] = '\0';
    sweep(nested, 8);
    free(large);
    puts("PASS: every allocation failure, growing buffers, nested children, sticky errors, cleanup");
    return 0;
}
