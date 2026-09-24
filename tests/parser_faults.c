#define CSHELL_PARSER_FAULT_IMPLEMENTATION
#include "parser_faults.h"
#include "cshell/alias.h"
#include "cshell/parser.h"

#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

static void *allocations[16384];
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

void *csh_parser_fault_malloc(size_t size)
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

void *csh_parser_fault_calloc(size_t count, size_t size)
{
    void *pointer;
    if (fail_now())
        return NULL;
    pointer = calloc(count, size);
    assert(pointer != NULL);
    allocations[slot_for(NULL)] = pointer;
    ++live_allocations;
    return pointer;
}

void *csh_parser_fault_realloc(void *pointer, size_t size)
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

void csh_parser_fault_free(void *pointer)
{
    if (pointer == NULL)
        return;
    allocations[slot_for(pointer)] = NULL;
    --live_allocations;
    free(pointer);
}

static void sticky(struct csh_parser *parser, enum csh_parse_result first_result,
    const struct csh_error *first)
{
    size_t calls = allocation_calls;
    int repeat;
    assert(first->message != NULL && first->status != 0);
    for (repeat = 0; repeat < 3; ++repeat) {
        struct csh_ast *tree = NULL;
        struct csh_error error;
        assert(csh_parser_next(parser, &tree, &error) == first_result);
        assert(tree == NULL);
        assert(error.message == first->message && error.status == first->status &&
            error.system_errno == first->system_errno &&
            error.position.offset == first->position.offset &&
            error.position.line == first->position.line &&
            error.position.column == first->position.column);
    }
    assert(allocation_calls == calls);
}

/* The final AST survives both parser and borrowed-input destruction. */
static int run(const char *source, int valid, int use_aliases)
{
    struct csh_aliases *aliases = NULL;
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *saved = NULL;
    struct csh_error error;
    enum csh_parse_result result = CSH_PARSE_ERROR;
    int succeeded = 0;
    if (use_aliases) {
        static const char *const definitions[][2] = {
            { "a", "b " }, { "b", "echo $(inside)" },
            { "inside", "printf" }, { "pipe", "a | a" },
            { "doc", "cat <<END" }, { "empty", "" },
            { "bad", "echo >" }, { "self", "self argument" },
            { "loop", "other" }, { "other", "loop" },
            { "replay", "echo $((echo $(inside)" }
        };
        size_t index;
        if (csh_aliases_create(&aliases, &error) != 0)
            goto done;
        for (index = 0; index < sizeof(definitions) / sizeof(definitions[0]); ++index) {
            if (csh_aliases_set(aliases, definitions[index][0], definitions[index][1],
                &error) != 0)
                goto done;
        }
    }
    if (csh_input_from_string(&input, source, "allocation-fault", &error) != 0)
        assert(input == NULL);
    else if (csh_parser_create(&parser, input, &error) != 0)
        assert(parser == NULL);
    else {
        csh_parser_set_aliases(parser, aliases);
        for (;;) {
            struct csh_ast *tree = NULL;
            result = csh_parser_next(parser, &tree, &error);
            if (result == CSH_PARSE_TREE) {
                assert(tree != NULL);
                csh_ast_destroy(saved);
                saved = tree;
            } else {
                assert(tree == NULL);
                if (result != CSH_PARSE_EOF)
                    sticky(parser, result, &error);
                if (error.system_errno != ENOMEM) {
                    if (valid)
                        assert(result == CSH_PARSE_EOF);
                    else
                        assert(result == CSH_PARSE_ERROR || result == CSH_PARSE_INCOMPLETE);
                    succeeded = 1;
                }
                break;
            }
        }
    }
done:
    if (!succeeded)
        assert(error.system_errno == ENOMEM && error.status == 1);
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    csh_aliases_destroy(aliases);
    csh_ast_destroy(saved);
    return succeeded;
}

static void sweep_mode(const char *source, int valid, int use_aliases)
{
    size_t point;
    for (point = 1; point < 20000; ++point) {
        int succeeded;
        assert(live_allocations == 0);
        allocation_calls = 0;
        fail_allocation = point;
        succeeded = run(source, valid, use_aliases);
        assert(live_allocations == 0);
        if (succeeded) {
            assert(point > allocation_calls);
            return;
        }
        assert(point <= allocation_calls);
    }
    assert(!"allocation sweep did not converge");
}

static void sweep(const char *source, int valid)
{
    sweep_mode(source, valid, 0);
}

int main(void)
{
    char *large = malloc(32800);
    char nested[2048];
    size_t i, used = 0;
    assert(large != NULL);
    memcpy(large, "x '", 3);
    memset(large + 3, 'x', 32766);
    memcpy(large + 32769, "'\n", 3);
    sweep("", 1);
    sweep("A=1 >one B='two' echo x 2>&1 | !literal && (left; right &) || { other; } >>last\n", 1);
    sweep("cat <<OUT $(cat <<'IN'\ninside ) $x\nIN\n)\noutside\nOUT\nnext\n", 1);
    sweep("cat <<A <<-'B'\none\nA\n\t$two\n\tB\n", 1);
    sweep("cat <<$'E\\x4eD' <<$'END\\0discarded'X\nfirst\nEND\nsecond\nENDX\n", 1);
    sweep("cat <<${x:-\"EOF\"} <<$(echo \"EOF\") <<$(ec\\\nho)\none\n${x:-EOF}\ntwo\n$(echo EOF)\nthree\n$(echo)\n", 1);
    sweep("if first; then a; elif second; then b; elif third; then c; else d; fi <in >out\n", 1);
    sweep("for in in a 'b c' $(case x in x) echo yes ;; esac); do while ready; do until finished; do next; done; done; done\n", 1);
    sweep("for implicit; do x; done; for empty in; do y; done\n", 1);
    sweep("case $(echo subject) in (a|b|$(echo pattern)) one ;& (esac) ;; *) last; esac 2>out\n", 1);
    sweep("case x in a) ;; b) ;& c) esac; case x in esac\n", 1);
    sweep("outer() { if ready; then inner() (echo x); else fallback; fi; } <in >>out\n", 1);
    sweep("f() if x; then y; fi; g() for x in a; do y; done; h() case x in a) y ;; esac\n", 1);
    sweep("f() { if cat <<IF\ncondition\nIF\nthen for x in a; do cat <<BODY\nloop\nBODY\ndone; fi; } <<FUNCTION\nfunction\nFUNCTION\n", 1);
    sweep("case x in a) cat <<A ;; b) cat <<B ;& c) cat <<C ;; esac\none\nA\ntwo\nB\nthree\nC\n", 1);
    /* Force each new growable vector past its initial allocation. */
    sweep("if a; then b; elif a; then b; elif a; then b; elif a; then b; elif a; then b; elif a; then b; elif a; then b; elif a; then b; elif a; then b; fi", 1);
    sweep("for x in a b c d e f g h i; do x; done; case x in a|b|c|d|e|f|g|h|i) ;; a) ;; b) ;; c) ;; d) ;; e) ;; f) ;; g) ;; h) ;; esac", 1);
    sweep("echo $((echo $(cat <<END\nbody\nEND\n)); )\n", 1);
    sweep("cat <<OUT $((cat <<END\n$(|)\nEND\n))\nouter\nOUT\n", 1);
    sweep("echo \"$(echo first)$((echo $((1+2)) $(echo inner)); )$(echo last)\"\n", 1);
    sweep("echo $((1 + ${n:-$(echo 2)}))\n", 1);
    sweep("echo $((echo 'unfinished", 0);
    sweep("echo $((1+2", 0);
    sweep("echo $((1 + ${unfinished", 0);
    sweep("echo $((1 + $(unfinished", 0);
    sweep("echo $((cat <<END\n${unfinished\nEND\n))", 1);
    sweep_mode("replay); )\n", 1, 1);
    sweep_mode("echo $((cat <<END\n$(bad)\nEND\n))\n", 1, 1);
    sweep(large, 1);
    memcpy(large, "cat <<E\n", 8);
    memset(large + 8, 'x', 32766);
    memcpy(large + 32774, "\nE\n", 4);
    sweep(large, 1);
    for (i = 0; i < 16; ++i) {
        memcpy(nested + used, "echo $(", 7);
        used += 7;
    }
    memcpy(nested + used, "inner", 5);
    used += 5;
    for (i = 0; i < 16; ++i)
        nested[used++] = ')';
    nested[used] = '\0';
    sweep(nested, 1);
    sweep("echo 'unterminated", 0);
    sweep("first; (second && )\n", 0);
    sweep("cat <<A\nbody\n", 0);
    sweep("cat <<$'E\\nD'\nbody\n", 0);
    sweep("{ echo >; }\n", 0);
    sweep_mode("a arg\npipe\ndoc\nbody\nEND\nempty\nself; loop\n", 1, 1);
    sweep_mode("echo $(doc\ninside\nEND\n)\n", 1, 1);
    sweep_mode("a; (bad)\n", 0, 1);
    sweep_mode("doc\nmissing delimiter\n", 0, 1);
    sweep("if a; then b; elif c; then d; else", 0);
    sweep("if a; then b; elif c; then d; else ; fi", 0);
    sweep("for x in $(echo a) b; do if c; then d;", 0);
    sweep("for x in a b; do while c; do ; done; done", 0);
    sweep("case $(echo x) in a|$(echo b)) c ;; d|", 0);
    sweep("case x in a) b ;; c) d ;& e|) f ;; esac", 0);
    sweep("outer() { inner() { if a; then b; fi; };", 0);
    sweep("outer() { inner() { cat <<E\nbody\nE\n}; if a; then ; fi; }", 0);
    sweep("f() { if cat <<IF\ncondition\nIF\nthen cat <<BODY\nunclosed body\n", 0);
    sweep("case x in a) cat <<A ;; b) cat <<B ;; esac\none\nA\nmissing second delimiter\n", 0);
    sweep("f() { x; } <<FUNCTION\nmissing delimiter\n", 0);
    free(large);
    puts("PASS: every allocation failure, compound/function trees, heredoc queues, partial errors, sticky results, cleanup");
    return 0;
}
