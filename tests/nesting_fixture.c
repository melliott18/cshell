/* CSH-066: API cleanup/rollback after native stack exhaustion, plus heap-owned
 * plan traversal at a depth that cannot fit on the deliberately small stack. */
#include "cshell/arithmetic.h"
#include "cshell/execute.h"
#include "cshell/expand.h"
#include "cshell/parser.h"
#include "cshell/stack.h"

#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <unistd.h>

static struct csh_ast *parse(const char *text)
{
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    struct csh_ast *tree = NULL;
    struct csh_error error;
    assert(csh_input_from_string(&input, text, "nesting", &error) == 0);
    assert(csh_parser_create(&parser, input, &error) == 0);
    assert(csh_parser_next(parser, &tree, &error) == CSH_PARSE_TREE);
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    return tree;
}

static int interrupt_read(void *user, int fd)
{
    (void)user; (void)fd;
    errno = EINTR;
    return -1;
}

static void after_line(void *user, const unsigned char *bytes, size_t length)
{
    (void)bytes; (void)length;
    csh_input_set_wait_hook(user, interrupt_read, NULL);
}

static void *thread_capacity(void *argument)
{
    size_t *remaining = argument;
    assert(csh_stack_available(remaining) == 0);
    return NULL;
}

static void thread_stacks(void)
{
    size_t previous = 0, i;
    for (i = 0; i < 8; ++i) {
        pthread_attr_t attributes;
        pthread_t thread;
        void *stack;
        size_t size = (i % 2 ? 1024 : 256) * 1024, remaining = 0;
        /* Supply exact storage: pthread implementations may otherwise reuse
         * a larger cached stack than the requested stack-size attribute. */
        assert(posix_memalign(&stack, (size_t)sysconf(_SC_PAGESIZE), size) == 0);
        assert(pthread_attr_init(&attributes) == 0);
        assert(pthread_attr_setstack(&attributes, stack, size) == 0);
        assert(pthread_create(&thread, &attributes, thread_capacity, &remaining) == 0);
        assert(pthread_join(thread, NULL) == 0);
        assert(pthread_attr_destroy(&attributes) == 0);
        free(stack);
        assert(remaining > 0 && remaining < size);
        if (i % 2) assert(remaining > previous);
        previous = remaining;
    }
}

int main(void)
{
    struct rlimit original, small;
    struct csh_invocation invocation = {0};
    struct csh_state *state = NULL;
    struct csh_execution_context context = {0};
    struct csh_ast *tree, *node;
    struct csh_execution execution;
    struct csh_error error;
    struct csh_expansion expansion = {0};
    struct csh_expand_error expansion_error;
    struct csh_variable_view variable;
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    char *text = malloc(200000), *at;
    size_t i, before, after;
    long number = 77;
    int ends[2], status;
    assert(text != NULL);
    invocation.mode = CSH_MODE_STRING;
    invocation.arg0 = "nesting";
    assert(csh_state_create(&state, &invocation, NULL) == CSH_STATE_OK);
    context.state = state;
    assert(getrlimit(RLIMIT_STACK, &original) == 0);
    assert(csh_stack_available(&before) == 0);
    small = original;
    small.rlim_cur = 256 * 1024;
    assert(setrlimit(RLIMIT_STACK, &small) == 0);
    assert(csh_stack_available(&after) == 0 && after < before);

    tree = parse(":\n");
    for (i = 0; i < 12000; ++i) {
        assert(csh_ast_create(&node, CSH_AST_BRACE, &error) == 0);
        node->data.group.body = tree;
        tree = node;
    }
    assert(csh_state_update_options(state, CSH_OPT_NOEXEC, 0) == CSH_STATE_OK);
    assert(csh_execute_context_ast(&context, tree, &execution, &error) == 0);
    assert(csh_state_update_options(state, 0, CSH_OPT_NOEXEC) == CSH_STATE_OK);
    /* Guard runtime recursion even for trees supplied directly by API clients. */
    assert(csh_execute_context_ast(&context, tree, &execution, &error) == -1);
    assert(execution.status == 1 && strstr(csh_error_message(&error), "stack exhausted"));
    csh_ast_destroy(tree);

    strcpy(text, "fresh=1, "); at = text + strlen(text);
    memset(at, '(', 12000); at += 12000;
    *at++ = '1'; memset(at, ')', 12000); at += 12000; *at = 0;
    assert(csh_arith_probe(text) == CSH_ARITH_RESOURCE);
    assert(csh_arith_probe_prefix(text) == -1);
    assert(csh_arith_eval(state, text, &number) == CSH_ARITH_RESOURCE && number == 77);
    assert(csh_state_get_variable(state, "fresh", &variable) == CSH_STATE_OK && variable.value == NULL);

    strcpy(text, "echo ${fresh:=changed}"); at = text + strlen(text);
    for (i = 0; i < 2048; ++i) { memcpy(at, "${absent:-", 10); at += 10; }
    *at++ = 'x'; memset(at, '}', 2048); at += 2048; *at++ = '\n'; *at = 0;
    tree = parse(text);
    node = tree->data.list.items[0].command;
    assert(node->kind == CSH_AST_SIMPLE);
    assert(csh_expand_word(state, &node->data.simple.words[1].word.token, NULL,
        &expansion, &expansion_error) == CSH_EXPAND_RESOURCE);
    assert(expansion.fields == NULL && expansion.field_count == 0);
    assert(strstr(expansion_error.message, "stack exhausted"));
    assert(csh_state_get_variable(state, "fresh", &variable) == CSH_STATE_OK && variable.value == NULL);
    csh_ast_destroy(tree);

    /* Restore capacity for a partially owned command > the old 128 boundary.
     * Inject interruption exactly after its first physical line was consumed. */
    assert(setrlimit(RLIMIT_STACK, &original) == 0);
    assert(csh_stack_available(&after) == 0 && after > small.rlim_cur);
    at = text;
    for (i = 0; i < 192; ++i) { memcpy(at, "{ ", 2); at += 2; }
    *at++ = '\n';
    assert(pipe(ends) == 0);
    assert(write(ends[1], text, (size_t)(at - text)) == at - text);
    close(ends[1]);
    assert(csh_input_from_fd(&input, ends[0], "interrupted", &error) == 0);
    close(ends[0]);
    csh_input_set_line_hook(input, after_line, input);
    assert(csh_parser_create(&parser, input, &error) == 0);
    tree = NULL;
    assert(csh_parser_next(parser, &tree, &error) == CSH_PARSE_INTERRUPTED);
    assert(tree == NULL && error.system_errno == EINTR);
    csh_parser_destroy(parser); csh_input_destroy(input);
    csh_execution_context_destroy(&context);
    assert(waitpid(-1, &status, WNOHANG) == -1 && errno == ECHILD);
    csh_state_destroy(state);
    thread_stacks();
    free(text);
    puts("PASS: deep plan destruction, native stack failure, rollback and interrupted parser cleanup");
    return 0;
}
