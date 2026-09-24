#include <errno.h>
#include <stdint.h>
#include <stdlib.h>

#include "cshell/ast.h"

static void clear_error(struct csh_error *error)
{
    *error = (struct csh_error){0};
}

static int fail(struct csh_error *error, const char *message, int number)
{
    error->message = message;
    error->system_errno = number;
    error->status = number == ENOMEM || number == EOVERFLOW ? 1 : 2;
    return -1;
}

static int implemented_kind(enum csh_ast_kind kind)
{
    return kind >= CSH_AST_SIMPLE && kind <= CSH_AST_FUNCTION;
}

/* A failed reserve never changes the vector or capacity. */
static int reserve(void **vector, size_t *capacity, size_t count,
    size_t item_size, struct csh_error *error)
{
    size_t maximum = SIZE_MAX / item_size;
    size_t grown;
    void *replacement;
    if (count >= maximum)
        return fail(error, "AST collection overflow", EOVERFLOW);
    if (count < *capacity)
        return 0;
    grown = *capacity == 0 ? 4 : *capacity;
    if (grown > maximum)
        grown = maximum;
    while (grown <= count) {
        if (grown > maximum / 2) {
            grown = maximum;
            break;
        }
        grown *= 2;
    }
    replacement = realloc(*vector, grown * item_size);
    if (replacement == NULL)
        return fail(error, "cannot allocate AST collection", ENOMEM);
    *vector = replacement;
    *capacity = grown;
    return 0;
}

int csh_ast_create(struct csh_ast **out, enum csh_ast_kind kind,
    struct csh_error *error)
{
    struct csh_ast *node;
    clear_error(error);
    if (out != NULL)
        *out = NULL;
    if (out == NULL || !implemented_kind(kind))
        return fail(error, "invalid AST node kind", EINVAL);
    node = malloc(sizeof(*node));
    if (node == NULL)
        return fail(error, "cannot allocate AST node", ENOMEM);
    *node = (struct csh_ast){0};
    node->kind = kind;
    *out = node;
    return 0;
}

/* Intrusive pending links permit destruction at any tree depth without stack
 * growth or allocation. They are written only after ownership is relinquished. */
static void enqueue(struct csh_ast **pending, struct csh_ast *node)
{
    if (node != NULL) {
        node->destroy_next = *pending;
        *pending = node;
    }
}

static void destroy_word(struct csh_ast_word *word, struct csh_ast **pending)
{
    size_t index;
    csh_token_destroy(&word->token);
    for (index = 0; index < word->substitution_count; ++index)
        enqueue(pending, word->substitutions[index].body);
    free(word->substitutions);
    *word = (struct csh_ast_word){0};
}

static void destroy_redirection(struct csh_ast_redirection *redirection,
    struct csh_ast **pending)
{
    if (redirection == NULL)
        return;
    csh_token_destroy(&redirection->io_number);
    destroy_word(&redirection->operand, pending);
    free(redirection->delimiter);
    free(redirection->body);
    free(redirection);
}

static void destroy_word_vector(struct csh_ast_word_vector *vector,
    struct csh_ast **pending)
{
    size_t index;
    for (index = 0; index < vector->count; ++index)
        destroy_word(&vector->items[index], pending);
    free(vector->items);
    *vector = (struct csh_ast_word_vector){0};
}

static void destroy_case_item(struct csh_ast_case_item *item,
    struct csh_ast **pending)
{
    destroy_word_vector(&item->patterns, pending);
    enqueue(pending, item->body);
    *item = (struct csh_ast_case_item){0};
}

static void destroy_pending(struct csh_ast *pending)
{
    while (pending != NULL) {
        struct csh_ast *node = pending;
        size_t index;
        pending = node->destroy_next;
        for (index = 0; index < node->redirection_count; ++index)
            destroy_redirection(node->redirections[index], &pending);
        free(node->redirections);
        switch (node->kind) {
        case CSH_AST_SIMPLE:
            for (index = 0; index < node->data.simple.word_count; ++index)
                destroy_word(&node->data.simple.words[index].word, &pending);
            free(node->data.simple.words);
            break;
        case CSH_AST_PIPELINE:
            for (index = 0; index < node->data.pipeline.command_count; ++index)
                enqueue(&pending, node->data.pipeline.commands[index]);
            free(node->data.pipeline.commands);
            break;
        case CSH_AST_AND:
        case CSH_AST_OR:
            enqueue(&pending, node->data.binary.left);
            enqueue(&pending, node->data.binary.right);
            break;
        case CSH_AST_LIST:
            for (index = 0; index < node->data.list.item_count; ++index)
                enqueue(&pending, node->data.list.items[index].command);
            free(node->data.list.items);
            break;
        case CSH_AST_SUBSHELL:
        case CSH_AST_BRACE:
            enqueue(&pending, node->data.group.body);
            break;
        case CSH_AST_IF:
            for (index = 0; index < node->data.if_clause.branch_count; ++index) {
                enqueue(&pending, node->data.if_clause.branches[index].condition);
                enqueue(&pending, node->data.if_clause.branches[index].body);
            }
            free(node->data.if_clause.branches);
            enqueue(&pending, node->data.if_clause.else_body);
            break;
        case CSH_AST_FOR:
            destroy_word(&node->data.for_clause.name, &pending);
            destroy_word_vector(&node->data.for_clause.words, &pending);
            enqueue(&pending, node->data.for_clause.body);
            break;
        case CSH_AST_WHILE:
        case CSH_AST_UNTIL:
            enqueue(&pending, node->data.loop.condition);
            enqueue(&pending, node->data.loop.body);
            break;
        case CSH_AST_CASE:
            destroy_word(&node->data.case_clause.word, &pending);
            for (index = 0; index < node->data.case_clause.item_count; ++index)
                destroy_case_item(&node->data.case_clause.items[index], &pending);
            free(node->data.case_clause.items);
            break;
        case CSH_AST_FUNCTION:
            destroy_word(&node->data.function.name, &pending);
            enqueue(&pending, node->data.function.body);
            break;
        default:
            break;
        }
        free(node);
    }
}

void csh_ast_destroy(struct csh_ast *node)
{
    struct csh_ast *pending = NULL;
    enqueue(&pending, node);
    destroy_pending(pending);
}

void csh_ast_word_destroy(struct csh_ast_word *word)
{
    struct csh_ast *pending = NULL;
    if (word == NULL)
        return;
    destroy_word(word, &pending);
    destroy_pending(pending);
}

void csh_ast_redirection_destroy(struct csh_ast_redirection *redirection)
{
    struct csh_ast *pending = NULL;
    destroy_redirection(redirection, &pending);
    destroy_pending(pending);
}

void csh_ast_case_item_destroy(struct csh_ast_case_item *item)
{
    struct csh_ast *pending = NULL;
    if (item == NULL)
        return;
    destroy_case_item(item, &pending);
    destroy_pending(pending);
}

int csh_ast_word_add_substitution(struct csh_ast_word *word,
    struct csh_ast_substitution *substitution, struct csh_error *error)
{
    void *vector;
    clear_error(error);
    if (word == NULL || substitution == NULL)
        return fail(error, "invalid AST substitution", EINVAL);
    vector = word->substitutions;
    if (reserve(&vector, &word->substitution_capacity, word->substitution_count,
                sizeof(*word->substitutions), error) == -1)
        return -1;
    word->substitutions = vector;
    word->substitutions[word->substitution_count++] = *substitution;
    *substitution = (struct csh_ast_substitution){0};
    return 0;
}

int csh_ast_add_word(struct csh_ast *node, struct csh_ast_word *word,
    int assignment, struct csh_error *error)
{
    struct csh_ast_command_word *entry;
    void *vector;
    clear_error(error);
    if (node == NULL || node->kind != CSH_AST_SIMPLE || word == NULL)
        return fail(error, "invalid AST command word", EINVAL);
    vector = node->data.simple.words;
    if (reserve(&vector, &node->data.simple.word_capacity,
                node->data.simple.word_count, sizeof(*node->data.simple.words),
                error) == -1)
        return -1;
    node->data.simple.words = vector;
    entry = &node->data.simple.words[node->data.simple.word_count++];
    entry->word = *word;
    entry->assignment = assignment != 0;
    *word = (struct csh_ast_word){0};
    return 0;
}

int csh_ast_redirection_create(struct csh_ast_redirection **out,
    enum csh_token_kind operator_kind, struct csh_error *error)
{
    struct csh_ast_redirection *redirection;
    clear_error(error);
    if (out != NULL)
        *out = NULL;
    if (out == NULL)
        return fail(error, "invalid AST redirection destination", EINVAL);
    switch (operator_kind) {
    case CSH_TOKEN_LESS:
    case CSH_TOKEN_GREAT:
    case CSH_TOKEN_DLESS:
    case CSH_TOKEN_DGREAT:
    case CSH_TOKEN_LESS_AND:
    case CSH_TOKEN_GREAT_AND:
    case CSH_TOKEN_LESS_GREAT:
    case CSH_TOKEN_DLESS_DASH:
    case CSH_TOKEN_CLOBBER:
        break;
    default:
        return fail(error, "invalid AST redirection operator", EINVAL);
    }
    redirection = malloc(sizeof(*redirection));
    if (redirection == NULL)
        return fail(error, "cannot allocate AST redirection", ENOMEM);
    *redirection = (struct csh_ast_redirection){0};
    redirection->operator_kind = operator_kind;
    *out = redirection;
    return 0;
}

int csh_ast_add_redirection(struct csh_ast *node,
    struct csh_ast_redirection **redirection, struct csh_error *error)
{
    void *vector;
    clear_error(error);
    if (node == NULL || !implemented_kind(node->kind) ||
        redirection == NULL || *redirection == NULL)
        return fail(error, "invalid AST redirection", EINVAL);
    vector = node->redirections;
    if (reserve(&vector, &node->redirection_capacity, node->redirection_count,
                sizeof(*node->redirections), error) == -1)
        return -1;
    node->redirections = vector;
    node->redirections[node->redirection_count++] = *redirection;
    *redirection = NULL;
    return 0;
}

int csh_ast_pipeline_add(struct csh_ast *node, struct csh_ast **child,
    struct csh_error *error)
{
    void *vector;
    clear_error(error);
    if (node == NULL || node->kind != CSH_AST_PIPELINE || child == NULL ||
        *child == NULL || node == *child)
        return fail(error, "invalid AST pipeline command", EINVAL);
    vector = node->data.pipeline.commands;
    if (reserve(&vector, &node->data.pipeline.command_capacity,
                node->data.pipeline.command_count,
                sizeof(*node->data.pipeline.commands), error) == -1)
        return -1;
    node->data.pipeline.commands = vector;
    node->data.pipeline.commands[node->data.pipeline.command_count++] = *child;
    *child = NULL;
    return 0;
}

int csh_ast_list_add(struct csh_ast *node, struct csh_ast_list_item *item,
    struct csh_error *error)
{
    void *vector;
    clear_error(error);
    if (node == NULL || node->kind != CSH_AST_LIST || item == NULL ||
        item->command == NULL || item->command == node ||
        item->separator < CSH_AST_END || item->separator > CSH_AST_NEWLINE)
        return fail(error, "invalid AST list item", EINVAL);
    vector = node->data.list.items;
    if (reserve(&vector, &node->data.list.item_capacity,
                node->data.list.item_count, sizeof(*node->data.list.items),
                error) == -1)
        return -1;
    node->data.list.items = vector;
    node->data.list.items[node->data.list.item_count++] = *item;
    *item = (struct csh_ast_list_item){0};
    return 0;
}

int csh_ast_if_add(struct csh_ast *node, struct csh_ast_if_branch *branch,
    struct csh_error *error)
{
    void *vector;
    clear_error(error);
    if (node == NULL || node->kind != CSH_AST_IF || branch == NULL ||
        branch->condition == NULL || branch->body == NULL ||
        branch->condition == node || branch->body == node ||
        branch->condition == branch->body)
        return fail(error, "invalid AST if branch", EINVAL);
    vector = node->data.if_clause.branches;
    if (reserve(&vector, &node->data.if_clause.branch_capacity,
                node->data.if_clause.branch_count,
                sizeof(*node->data.if_clause.branches), error) == -1)
        return -1;
    node->data.if_clause.branches = vector;
    node->data.if_clause.branches[node->data.if_clause.branch_count++] = *branch;
    *branch = (struct csh_ast_if_branch){0};
    return 0;
}

int csh_ast_word_vector_add(struct csh_ast_word_vector *words,
    struct csh_ast_word *word, struct csh_error *error)
{
    void *vector;
    clear_error(error);
    if (words == NULL || word == NULL)
        return fail(error, "invalid AST word vector entry", EINVAL);
    vector = words->items;
    if (reserve(&vector, &words->capacity, words->count,
                sizeof(*words->items), error) == -1)
        return -1;
    words->items = vector;
    words->items[words->count++] = *word;
    *word = (struct csh_ast_word){0};
    return 0;
}

int csh_ast_case_add(struct csh_ast *node, struct csh_ast_case_item *item,
    struct csh_error *error)
{
    void *vector;
    clear_error(error);
    if (node == NULL || node->kind != CSH_AST_CASE || item == NULL ||
        item->patterns.count == 0 || item->body == NULL ||
        item->body == node || item->body->kind != CSH_AST_LIST ||
        item->terminator < CSH_AST_CASE_END ||
        item->terminator > CSH_AST_CASE_FALLTHROUGH)
        return fail(error, "invalid AST case item", EINVAL);
    vector = node->data.case_clause.items;
    if (reserve(&vector, &node->data.case_clause.item_capacity,
                node->data.case_clause.item_count,
                sizeof(*node->data.case_clause.items), error) == -1)
        return -1;
    node->data.case_clause.items = vector;
    node->data.case_clause.items[node->data.case_clause.item_count++] = *item;
    *item = (struct csh_ast_case_item){0};
    return 0;
}

const char *csh_ast_kind_name(enum csh_ast_kind kind)
{
    static const char *const names[] = {"SIMPLE", "PIPELINE", "AND", "OR",
        "LIST", "SUBSHELL", "BRACE", "IF", "FOR", "WHILE", "UNTIL",
        "CASE", "FUNCTION"};
    return (unsigned)kind < sizeof(names) / sizeof(names[0]) ? names[kind] : "UNKNOWN";
}
