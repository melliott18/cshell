#include "prepare.h"
#include "cshell/parser.h"

#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int fail(struct csh_error *error, const char *message, int number)
{
    memset(error, 0, sizeof(*error));
    error->message = message;
    error->system_errno = number;
    error->status = number ? 1 : 2;
    return -1;
}

struct substitution {
    const struct csh_ast_word *word;
    struct csh_command *command;
    char *bytes;
};

/* Backquote source is decoded once, then sent through the same parser as $().
 * Expansion output is never reparsed. Unselected operands never reach here. */
static int backquote_tree(const struct csh_token *token, size_t fragment,
    struct csh_ast **out, struct csh_error *error)
{
    const struct csh_fragment *f = &token->fragments[fragment];
    struct csh_input *input = NULL;
    struct csh_parser *parser = NULL;
    char *text;
    size_t i, used = 0;
    int rc = -1;
    *out = NULL;
    text = malloc(f->end - f->begin);
    if (text == NULL) return fail(error, "cannot allocate backquote source", ENOMEM);
    for (i = f->begin + 1; i + 1 < f->end; ++i) {
        if (token->raw[i] == '\\' && i + 2 < f->end &&
            (strchr("$`\\", token->raw[i + 1]) != NULL ||
             (f->quote == CSH_QUOTE_DOUBLE && token->raw[i + 1] == '"'))) ++i;
        text[used++] = (char)token->raw[i];
    }
    text[used] = 0;
    if (csh_input_from_string(&input, text, "backquote", error) == -1 ||
        csh_parser_create(&parser, input, error) == -1 ||
        csh_ast_create(out, CSH_AST_LIST, error) == -1) goto done;
    for (;;) {
        struct csh_ast_list_item item = {0};
        enum csh_parse_result parsed = csh_parser_next(parser, &item.command, error);
        if (parsed == CSH_PARSE_EOF) break;
        if (parsed != CSH_PARSE_TREE) goto done;
        if (csh_ast_list_add(*out, &item, error) == -1) {
            csh_ast_destroy(item.command);
            goto done;
        }
    }
    rc = 0;
done:
    free(text);
    csh_parser_destroy(parser);
    csh_input_destroy(input);
    if (rc == -1) { csh_ast_destroy(*out); *out = NULL; }
    return rc;
}

static enum csh_expand_result substitute(void *user, struct csh_state *state,
    const struct csh_token *token, size_t fragment,
    const char **bytes, size_t *length, struct csh_expand_error *error)
{
    struct substitution *context = user;
    struct csh_ast *owned = NULL;
    const struct csh_ast *body = NULL;
    struct csh_error failure = {0};
    size_t i;
    int rc = -1;
    free(context->bytes);
    context->bytes = NULL;
    if (token->fragments[fragment].kind == CSH_FRAGMENT_BACKQUOTE) {
        if (backquote_tree(token, fragment, &owned, &failure) == -1) goto done;
        body = owned;
    } else {
        for (i = 0; i < context->word->substitution_count; ++i)
            if (context->word->substitutions[i].fragment_index == fragment) {
                body = context->word->substitutions[i].body;
                break;
            }
        if (body == NULL) {
            fail(&failure, "missing command substitution tree", 0);
            goto done;
        }
    }
    rc = csh_execute_substitution(state, body, &context->bytes, length,
        &context->command->substitution_status, &failure);
done:
    csh_ast_destroy(owned);
    if (rc == -1) {
        enum csh_expand_result result = failure.system_errno == ENOMEM ?
            CSH_EXPAND_NOMEM : failure.system_errno ? CSH_EXPAND_IO : CSH_EXPAND_INVALID;
        error->code = result;
        error->fragment = fragment;
        error->position = token->fragments[fragment].start;
        snprintf(error->message, sizeof(error->message), "%s", csh_error_message(&failure));
        return result;
    }
    *bytes = context->bytes;
    return CSH_EXPAND_OK;
}

/* Offset slicing retains fragment indices for the parser's substitution map.
 * Consumed prefix fragments become empty root TEXT fragments. */
static int expand(struct csh_state *state, const struct csh_ast_word *word,
    size_t offset, enum csh_expand_context mode, struct csh_command *command,
    struct csh_fields *out, struct csh_error *error)
{
    struct csh_token token = word->token;
    struct csh_fragment *fragments = NULL;
    struct csh_expansion value = {0};
    struct csh_expand_error expansion_error = {0};
    struct csh_state_checkpoint *checkpoint = NULL;
    struct substitution substitution = {word, command, NULL};
    struct csh_expand_options options = {mode, substitute, &substitution};
    enum csh_expand_result result;
    size_t i;
    int rc = -1;
    memset(out, 0, sizeof(*out));
    if (offset > token.length) return fail(error, "invalid assignment word", 0);
    if (offset != 0) {
        if (token.fragment_count > SIZE_MAX / sizeof(*fragments)) goto nomem;
        fragments = calloc(token.fragment_count ? token.fragment_count : 1, sizeof(*fragments));
        if (fragments == NULL) goto nomem;
        for (i = 0; i < token.fragment_count; ++i) {
            fragments[i] = token.fragments[i];
            if (fragments[i].end <= offset) {
                fragments[i].kind = CSH_FRAGMENT_TEXT;
                fragments[i].parent = CSH_FRAGMENT_ROOT;
                fragments[i].quote = CSH_QUOTE_NONE;
                fragments[i].begin = fragments[i].end = 0;
            } else {
                fragments[i].begin = fragments[i].begin < offset ? 0 : fragments[i].begin - offset;
                fragments[i].end -= offset;
            }
        }
        token.fragments = fragments;
        token.raw += offset;
        token.length -= offset;
    }
    if (csh_state_save(state, &checkpoint) != CSH_STATE_OK) goto nomem;
    result = csh_expand_word(state, &token, &options, &value, &expansion_error);
    if (result == CSH_EXPAND_OK)
        result = csh_expand_fields(state, &value, NULL, out, &expansion_error);
    if (result != CSH_EXPAND_OK) {
        csh_state_restore(state, &checkpoint);
        fail(error, "word expansion failed", result == CSH_EXPAND_NOMEM ? ENOMEM :
            result == CSH_EXPAND_IO ? EIO : result == CSH_EXPAND_INTERRUPTED ? EINTR : 0);
        snprintf(error->detail, sizeof(error->detail), "%s", expansion_error.message);
        error->position = expansion_error.position;
        goto done;
    }
    rc = 0;
    goto done;
nomem:
    fail(error, "cannot allocate command expansion", ENOMEM);
done:
    free(fragments);
    free(substitution.bytes);
    csh_expansion_destroy(&value);
    csh_state_checkpoint_destroy(checkpoint);
    return rc;
}

int csh_prepare_word(struct csh_state *state, const struct csh_ast_word *word,
    enum csh_expand_context mode, struct csh_fields *out, struct csh_error *error)
{
    struct csh_command command = {0};
    return expand(state, word, 0, mode, &command, out, error);
}

static int scalar(struct csh_state *state, const struct csh_ast_word *word,
    size_t offset, enum csh_expand_context mode, struct csh_command *command,
    char **out, struct csh_error *error)
{
    struct csh_fields fields = {0};
    *out = NULL;
    if (expand(state, word, offset, mode, command, &fields, error) == -1) return -1;
    if (fields.count == 0) {
        *out = calloc(1, 1);
        csh_fields_destroy(&fields);
        return *out == NULL ? fail(error, "cannot allocate empty value", ENOMEM) : 0;
    }
    if (fields.count != 1) {
        csh_fields_destroy(&fields);
        return fail(error, "expansion requires one field", 0);
    }
    *out = fields.values[0];
    free(fields.values);
    return 0;
}

/* Return the byte just after an unquoted NAME= prefix, or zero. */
static size_t assignment_name(const struct csh_ast_word *word, char **name)
{
    const struct csh_token *token = &word->token;
    size_t i, j, used = 0;
    char *text = NULL;
    if (name != NULL) {
        *name = NULL;
        text = malloc(token->length + 1);
        if (text == NULL) return SIZE_MAX;
    }
    for (i = 0; i < token->fragment_count; ++i) {
        const struct csh_fragment *f = &token->fragments[i];
        if (f->kind == CSH_FRAGMENT_CONTINUATION) continue;
        if (f->kind != CSH_FRAGMENT_TEXT || f->quote != CSH_QUOTE_NONE ||
            f->parent != CSH_FRAGMENT_ROOT) break;
        for (j = f->begin; j < f->end; ++j) {
            unsigned char byte = token->raw[j];
            if (byte == '=' && used != 0) {
                if (text != NULL) { text[used] = 0; *name = text; }
                return j + 1;
            }
            if (!(byte == '_' || (byte >= 'a' && byte <= 'z') ||
                  (byte >= 'A' && byte <= 'Z') || (used && byte >= '0' && byte <= '9')))
                goto invalid;
            if (text != NULL) text[used] = (char)byte;
            ++used;
        }
    }
invalid:
    free(text);
    return 0;
}

static int append_fields(struct csh_command *command, struct csh_fields *fields,
    struct csh_error *error)
{
    char **replacement;
    if (fields->count >= SIZE_MAX / sizeof(char *) - command->argc)
        return fail(error, "command has too many arguments", ENOMEM);
    replacement = realloc(command->argv,
        (command->argc + fields->count + 1) * sizeof(char *));
    if (replacement == NULL) return fail(error, "cannot allocate command arguments", ENOMEM);
    command->argv = replacement;
    if (fields->count) memcpy(command->argv + command->argc, fields->values,
        fields->count * sizeof(char *));
    command->argc += fields->count;
    command->argv[command->argc] = NULL;
    free(fields->values);
    memset(fields, 0, sizeof(*fields));
    return 0;
}

int csh_command_arguments(struct csh_state *state, const struct csh_ast *tree,
    struct csh_command *out, struct csh_error *error)
{
    size_t i;
    for (i = 0; i < tree->data.simple.word_count; ++i) {
        const struct csh_ast_command_word *source = &tree->data.simple.words[i];
        struct csh_fields fields = {0};
        int declaration = out->argc &&
            (!strcmp(out->argv[0], "export") || !strcmp(out->argv[0], "readonly"));
        if (source->assignment) {
            struct csh_variable_view view;
            char *name = NULL;
            size_t offset = assignment_name(&source->word, &name);
            if (offset == SIZE_MAX) return fail(error, "cannot allocate assignment name", ENOMEM);
            if (offset == 0) return fail(error, "invalid assignment word", 0);
            csh_state_get_variable(state, name, &view);
            free(name);
            if (view.attributes & CSH_VAR_READONLY) {
                fail(error, "cannot assign to readonly variable", 0);
                error->status = 1;
                return -1;
            }
            continue;
        }
        if (declaration && assignment_name(&source->word, NULL) != 0) {
            char *name = NULL, *value = NULL, *joined;
            size_t offset = assignment_name(&source->word, &name), length;
            if (offset == SIZE_MAX) return fail(error, "cannot allocate assignment name", ENOMEM);
            if (scalar(state, &source->word, offset, CSH_EXPAND_ASSIGNMENT,
                out, &value, error) == -1) { free(name); return -1; }
            length = strlen(name) + strlen(value) + 2;
            joined = malloc(length);
            fields.values = calloc(2, sizeof(char *));
            if (joined != NULL) snprintf(joined, length, "%s=%s", name, value);
            free(name);
            free(value);
            if (joined == NULL || fields.values == NULL) {
                free(joined); free(fields.values);
                return fail(error, "cannot allocate declaration argument", ENOMEM);
            }
            fields.values[0] = joined;
            fields.count = 1;
        } else if (expand(state, &source->word, 0, CSH_EXPAND_ARGUMENT,
            out, &fields, error) == -1) return -1;
        if (append_fields(out, &fields, error) == -1) {
            csh_fields_destroy(&fields);
            return -1;
        }
    }
    return 0;
}

int csh_command_assignments(struct csh_state *state, const struct csh_ast *tree,
    struct csh_command *out, struct csh_error *error)
{
    struct csh_variable_save *save = NULL;
    const char **names = NULL;
    size_t i, count = 0, index = 0;
    int rc = -1;
    for (i = 0; i < tree->data.simple.word_count; ++i)
        if (tree->data.simple.words[i].assignment) ++count;
    if (!count) return 0;
    out->assignments = calloc(count, sizeof(*out->assignments));
    names = calloc(count, sizeof(*names));
    if (out->assignments == NULL || names == NULL) goto nomem;
    for (i = 0; i < tree->data.simple.word_count; ++i) {
        const struct csh_ast_command_word *source = &tree->data.simple.words[i];
        size_t offset;
        if (!source->assignment) continue;
        offset = assignment_name(&source->word, &out->assignments[index].name);
        if (offset == SIZE_MAX) goto nomem;
        if (offset == 0) { fail(error, "invalid assignment word", 0); goto done; }
        names[index] = out->assignments[index].name;
        out->assignment_count = ++index;
    }
    if (csh_state_save_variables(state, count, names, &save) != CSH_STATE_OK) goto nomem;
    index = 0;
    for (i = 0; i < tree->data.simple.word_count; ++i) {
        const struct csh_ast_command_word *source = &tree->data.simple.words[i];
        struct csh_assignment *assignment;
        enum csh_state_result assigned;
        if (!source->assignment) continue;
        assignment = &out->assignments[index++];
        if (scalar(state, &source->word, assignment_name(&source->word, NULL),
            CSH_EXPAND_ASSIGNMENT, out, &assignment->value, error) == -1) goto done;
        assigned = csh_state_set_variable(state, assignment->name, assignment->value);
        if (assigned == CSH_STATE_NOMEM) goto nomem;
        if (assigned != CSH_STATE_OK) {
            fail(error, "cannot apply assignment value", 0);
            goto done;
        }
    }
    rc = 0;
    goto done;
nomem:
    fail(error, "cannot allocate command assignments", ENOMEM);
done:
    /* Later values see earlier assignments. Dispatch still owns their final
     * category-specific lifetime; unrelated expansion mutations survive. */
    csh_state_restore_variables(state, &save);
    free(names);
    return rc;
}

int csh_descriptor(const unsigned char *text, size_t length, int *out)
{
    size_t i;
    int value = 0, digits = 0;
    for (i = 0; i < length; ++i) {
        int digit;
        if (text[i] == '\\' && i + 1 < length && text[i + 1] == '\n') { ++i; continue; }
        digit = text[i] - '0';
        if (digit < 0 || digit > 9 || value > (INT_MAX - digit) / 10) return -1;
        value = value * 10 + digit;
        digits = 1;
    }
    if (!digits) return -1;
    *out = value;
    return 0;
}

int csh_command_redirect(struct csh_state *state,
    const struct csh_ast_redirection *source, struct csh_command *command,
    struct csh_redirect *out, struct csh_error *error)
{
    char *operand = NULL;
    int input = 0;
    memset(out, 0, sizeof(*out));
    switch (source->operator_kind) {
    case CSH_TOKEN_LESS: out->kind = CSH_REDIRECT_READ; input = 1; break;
    case CSH_TOKEN_GREAT: out->kind = CSH_REDIRECT_WRITE; break;
    case CSH_TOKEN_DGREAT: out->kind = CSH_REDIRECT_APPEND; break;
    case CSH_TOKEN_LESS_GREAT: out->kind = CSH_REDIRECT_READ_WRITE; input = 1; break;
    case CSH_TOKEN_CLOBBER: out->kind = CSH_REDIRECT_CLOBBER; break;
    case CSH_TOKEN_LESS_AND: out->kind = CSH_REDIRECT_DUP_READ; input = 1; break;
    case CSH_TOKEN_GREAT_AND: out->kind = CSH_REDIRECT_DUP_WRITE; break;
    case CSH_TOKEN_DLESS:
    case CSH_TOKEN_DLESS_DASH: out->kind = CSH_REDIRECT_HEREDOC; input = 1; break;
    default: return fail(error, "unsupported redirection operator", 0);
    }
    out->fd = input ? STDIN_FILENO : STDOUT_FILENO;
    if (source->has_io_number && csh_descriptor(source->io_number.raw,
        source->io_number.length, &out->fd) == -1)
        return fail(error, "invalid redirection descriptor", 0);
    if (out->kind == CSH_REDIRECT_HEREDOC) {
        struct csh_ast_word word = {0};
        int rc;
        if (source->body == NULL) return fail(error, "here-document body has not been collected", 0);
        if (source->delimiter_quoted) {
            out->data = malloc(source->body_length ? source->body_length : 1);
            if (out->data == NULL) return fail(error, "cannot allocate here-document body", ENOMEM);
            memcpy(out->data, source->body, source->body_length);
            out->length = source->body_length;
            return 0;
        }
        if (csh_parser_document(source->body, source->body_length, &word, error) == -1) return -1;
        rc = scalar(state, &word, 0, CSH_EXPAND_HEREDOC, command, &operand, error);
        csh_ast_word_destroy(&word);
        if (rc == -1) return -1;
        out->data = (unsigned char *)operand;
        out->length = strlen(operand);
        return 0;
    }
    if (scalar(state, &source->operand, 0, CSH_EXPAND_REDIRECTION,
        command, &operand, error) == -1) return -1;
    if (out->kind == CSH_REDIRECT_DUP_READ || out->kind == CSH_REDIRECT_DUP_WRITE) {
        if (strcmp(operand, "-") == 0) out->kind = CSH_REDIRECT_CLOSE;
        else if (csh_descriptor((const unsigned char *)operand, strlen(operand), &out->source_fd) == -1) {
            free(operand);
            fail(error, "descriptor operand must be digits or '-'", 0);
            error->status = 1;
            return -2;
        }
        free(operand);
    } else out->path = operand;
    return 0;
}

int csh_command_from_ast(struct csh_state *state, const struct csh_ast *tree,
    struct csh_command *out, struct csh_error *error)
{
    size_t i;
    memset(out, 0, sizeof(*out));
    memset(error, 0, sizeof(*error));
    if (tree != NULL && tree->kind == CSH_AST_LIST && tree->redirection_count == 0 &&
        tree->data.list.item_count == 1 &&
        tree->data.list.items[0].separator != CSH_AST_AMPERSAND)
        tree = tree->data.list.items[0].command;
    if (state == NULL || tree == NULL || tree->kind != CSH_AST_SIMPLE)
        return fail(error, "only a single foreground simple command is supported", 0);
    if (csh_command_arguments(state, tree, out, error) == -1) goto failure;
    if (tree->redirection_count) {
        out->redirections = calloc(tree->redirection_count, sizeof(*out->redirections));
        if (out->redirections == NULL) {
            fail(error, "cannot allocate command redirections", ENOMEM);
            goto failure;
        }
    }
    for (i = 0; i < tree->redirection_count; ++i) {
        ++out->redirection_count;
        if (csh_command_redirect(state, tree->redirections[i], out,
            &out->redirections[i], error) < 0) goto failure;
    }
    if (csh_command_assignments(state, tree, out, error) == -1) goto failure;
    return 0;
failure:
    csh_command_destroy(out);
    return -1;
}
