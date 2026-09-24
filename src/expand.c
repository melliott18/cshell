#include "cshell/expand.h"
#include "cshell/arithmetic.h"
#include "cshell/quote.h"

#include <fnmatch.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pwd.h>
#include <wchar.h>

#define EXPAND_DEPTH 128

struct expansion_work {
    struct csh_state *state;
    const struct csh_token *word;
    struct csh_expand_options options;
    struct csh_expand_error *error;
    size_t *next;
    char **decoded;
    unsigned depth;
};

static enum csh_expand_result fail(struct expansion_work *work,
    enum csh_expand_result code, size_t fragment, const char *message)
{
    if (work->error != NULL) {
        work->error->code = code;
        work->error->fragment = fragment;
        work->error->position = fragment < work->word->fragment_count ?
            work->word->fragments[fragment].start : work->word->start;
        snprintf(work->error->message, sizeof(work->error->message), "%s", message);
    }
    return code;
}

void csh_expansion_destroy(struct csh_expansion *expansion)
{
    size_t i, j;
    if (expansion == NULL)
        return;
    for (i = 0; i < expansion->field_count; ++i) {
        for (j = 0; j < expansion->fields[i].span_count; ++j)
            free(expansion->fields[i].spans[j].text);
        free(expansion->fields[i].spans);
    }
    free(expansion->fields);
    memset(expansion, 0, sizeof(*expansion));
}

static enum csh_expand_result new_field(struct csh_expansion *out)
{
    struct csh_expand_field *fields;
    if (out->field_count >= SIZE_MAX / sizeof(*fields) - 1)
        return CSH_EXPAND_NOMEM;
    fields = realloc(out->fields, (out->field_count + 1) * sizeof(*fields));
    if (fields == NULL)
        return CSH_EXPAND_NOMEM;
    out->fields = fields;
    memset(&fields[out->field_count++], 0, sizeof(*fields));
    return CSH_EXPAND_OK;
}

static enum csh_expand_result append(struct csh_expansion *out,
    const char *bytes, size_t length, enum csh_quote quote,
    enum csh_expand_origin origin, int keep)
{
    struct csh_expand_field *field;
    struct csh_expand_span *spans;
    char *text;
    if (length == SIZE_MAX || (length != 0 && bytes == NULL))
        return CSH_EXPAND_NOMEM;
    if (out->field_count == 0 && new_field(out) != CSH_EXPAND_OK)
        return CSH_EXPAND_NOMEM;
    field = &out->fields[out->field_count - 1];
    if (field->span_count >= SIZE_MAX / sizeof(*spans) - 1)
        return CSH_EXPAND_NOMEM;
    text = malloc(length + 1);
    if (text == NULL)
        return CSH_EXPAND_NOMEM;
    if (length != 0)
        memcpy(text, bytes, length);
    text[length] = 0;
    spans = realloc(field->spans, (field->span_count + 1) * sizeof(*spans));
    if (spans == NULL) {
        free(text);
        return CSH_EXPAND_NOMEM;
    }
    field->spans = spans;
    spans += field->span_count++;
    spans->text = text;
    spans->length = length;
    spans->quote = quote;
    spans->origin = origin;
    spans->keep_empty = keep;
    spans->split = out->context == CSH_EXPAND_ARGUMENT &&
        quote == CSH_QUOTE_NONE && origin != CSH_EXPAND_LITERAL &&
        origin != CSH_EXPAND_TILDE;
    return CSH_EXPAND_OK;
}

static enum csh_expand_result scalar(struct csh_expansion *out,
    const char *text, enum csh_quote quote, enum csh_expand_origin origin)
{
    return append(out, text, strlen(text), quote, origin, quote != CSH_QUOTE_NONE);
}

/* Join fields for contexts where POSIX specifies one scalar. IFS is read from
 * shell state, never the host process environment. Invalid multibyte input is
 * treated as individual bytes; fixtures use the C locale. */
static size_t character_bytes(const char *text, size_t length)
{
    mbstate_t state = {0};
    size_t n = mbrlen(text, length, &state);
    return n == (size_t)-1 || n == (size_t)-2 || n == 0 ? 1 : n;
}

static const char *separator(struct csh_state *state, size_t *length)
{
    struct csh_variable_view view;
    csh_state_get_variable(state, "IFS", &view);
    if (view.value == NULL) {
        *length = 1;
        return " ";
    }
    *length = view.value[0] == 0 ? 0 : character_bytes(view.value, strlen(view.value));
    return view.value;
}

/* Scalar consumers concatenate spans. Patterns use csh_expand_fields instead. */
static char *flatten(const struct csh_expansion *value)
{
    size_t i, j, length = 0, position = 0;
    char *text;
    for (i = 0; i < value->field_count; ++i)
        for (j = 0; j < value->fields[i].span_count; ++j) {
            size_t bytes = value->fields[i].spans[j].length;
            if (bytes >= SIZE_MAX - length) return NULL;
            length += bytes;
        }
    text = malloc(length + 1);
    if (text == NULL) return NULL;
    for (i = 0; i < value->field_count; ++i)
        for (j = 0; j < value->fields[i].span_count; ++j) {
            const struct csh_expand_span *span = &value->fields[i].spans[j];
            memcpy(text + position, span->text, span->length);
            position += span->length;
        }
    text[position] = 0;
    return text;
}

static char *copy_bytes(const unsigned char *bytes, size_t length)
{
    char *text;
    if (length == SIZE_MAX || (text = malloc(length + 1)) == NULL)
        return NULL;
    memcpy(text, bytes, length);
    text[length] = 0;
    return text;
}

static int name_start(int byte)
{
    return (byte >= 'a' && byte <= 'z') || (byte >= 'A' && byte <= 'Z') || byte == '_';
}
static int digit(int byte) { return byte >= '0' && byte <= '9'; }
static int name_char(int byte) { return name_start(byte) || digit(byte); }

/* The lexer's physical spelling can have continuations even in delimiters. */
static int logical(const struct csh_token *word, size_t *position, size_t end)
{
    while (*position + 1 < end && word->raw[*position] == '\\' &&
            word->raw[*position + 1] == '\n')
        *position += 2;
    return *position < end ? word->raw[(*position)++] : -1;
}

static enum csh_expand_result range(struct expansion_work *work, size_t parent,
    size_t begin, size_t end, struct csh_expansion *out,
    enum csh_expand_origin literal_origin, int tilde);

static enum csh_expand_result positional(struct expansion_work *work,
    struct csh_expansion *out, int star, enum csh_quote quote)
{
    struct csh_state_info info;
    size_t i, sep_length;
    const char *sep;
    int join = out->context != CSH_EXPAND_ARGUMENT || (star && quote != CSH_QUOTE_NONE);
    csh_state_get_info(work->state, &info);
    sep = separator(work->state, &sep_length);
    if (join) {
        if (scalar(out, "", quote, CSH_EXPAND_PARAMETER) != CSH_EXPAND_OK)
            return CSH_EXPAND_NOMEM;
        for (i = 1; i <= info.argument_count; ++i) {
            if (i > 1 && append(out, sep, sep_length, quote, CSH_EXPAND_PARAMETER,
                    quote != CSH_QUOTE_NONE) != CSH_EXPAND_OK)
                return CSH_EXPAND_NOMEM;
            if (scalar(out, csh_state_parameter(work->state, i), quote,
                    CSH_EXPAND_PARAMETER) != CSH_EXPAND_OK)
                return CSH_EXPAND_NOMEM;
        }
    } else {
        for (i = 1; i <= info.argument_count; ++i) {
            if (i > 1 && new_field(out) != CSH_EXPAND_OK)
                return CSH_EXPAND_NOMEM;
            if (scalar(out, csh_state_parameter(work->state, i), quote,
                    CSH_EXPAND_PARAMETER) != CSH_EXPAND_OK)
                return CSH_EXPAND_NOMEM;
        }
    }
    return CSH_EXPAND_OK;
}

static enum csh_expand_result parameter_value(struct expansion_work *work,
    const char *name, char **out, int *is_set)
{
    const char *value = NULL;
    struct csh_state_info info;
    struct csh_variable_view view;
    char number[64];
    size_t i, index = 0;
    csh_state_get_info(work->state, &info);
    *out = NULL;
    if (name_start((unsigned char)name[0])) {
        if (csh_state_get_variable(work->state, name, &view) != CSH_STATE_OK)
            return CSH_EXPAND_INVALID;
        value = view.value;
    } else if (digit((unsigned char)name[0])) {
        for (i = 0; name[i] != 0; ++i) {
            if (index > (SIZE_MAX - (size_t)(name[i] - '0')) / 10)
                return CSH_EXPAND_INVALID;
            index = index * 10 + (size_t)(name[i] - '0');
        }
        value = csh_state_parameter(work->state, index);
    } else {
        value = number;
        switch (name[0]) {
        case '#': snprintf(number, sizeof(number), "%zu", info.argument_count); break;
        case '?': snprintf(number, sizeof(number), "%d", info.last_status); break;
        case '$': snprintf(number, sizeof(number), "%jd", (intmax_t)info.shell_pid); break;
        case '!':
            if (info.background_pid == 0) value = NULL;
            else snprintf(number, sizeof(number), "%jd", (intmax_t)info.background_pid);
            break;
        case '-': {
            static const unsigned bits[] = { CSH_OPT_ALLEXPORT, CSH_OPT_NOTIFY,
                CSH_OPT_NOCLOBBER, CSH_OPT_ERREXIT, CSH_OPT_NOGLOB,
                CSH_OPT_INTERACTIVE, CSH_OPT_MONITOR, CSH_OPT_NOEXEC,
                CSH_OPT_NOUNSET, CSH_OPT_VERBOSE, CSH_OPT_XTRACE };
            static const char letters[] = "abCefimnuvx";
            index = 0;
            for (i = 0; i < sizeof(bits) / sizeof(bits[0]); ++i)
                if ((info.options & bits[i]) != 0) number[index++] = letters[i];
            number[index] = 0;
            break;
        }
        default: return CSH_EXPAND_INVALID;
        }
    }
    *is_set = value != NULL;
    *out = copy_bytes((const unsigned char *)(value != NULL ? value : ""),
        value != NULL ? strlen(value) : 0);
    return *out == NULL ? CSH_EXPAND_NOMEM : CSH_EXPAND_OK;
}

static enum csh_expand_result assign(struct expansion_work *work,
    const char *name, const char *value)
{
    enum csh_state_result result = csh_state_set_variable(work->state, name, value);
    struct csh_state_info info;
    if (result == CSH_STATE_READONLY) return CSH_EXPAND_READONLY;
    if (result == CSH_STATE_NOMEM) return CSH_EXPAND_NOMEM;
    if (result != CSH_STATE_OK) return CSH_EXPAND_INVALID;
    csh_state_get_info(work->state, &info);
    if ((info.options & CSH_OPT_ALLEXPORT) != 0 &&
        csh_state_update_attributes(work->state, name, CSH_VAR_EXPORT, 0) != CSH_STATE_OK)
        return CSH_EXPAND_NOMEM;
    return CSH_EXPAND_OK;
}

static char *remove_pattern(char *value, const char *pattern, int suffix, int longest)
{
    size_t length = strlen(value), offset = 0, selected = 0;
    int found = 0;
    for (;;) {
        int matches;
        if (suffix) matches = fnmatch(pattern, value + offset, 0) == 0;
        else {
            char saved = value[offset];
            value[offset] = 0;
            matches = fnmatch(pattern, value, 0) == 0;
            value[offset] = saved;
        }
        if (matches) {
            selected = offset;
            found = 1;
            if (suffix == longest) break;
        }
        if (offset == length) break;
        offset += character_bytes(value + offset, length - offset);
    }
    if (found) {
        if (suffix) value[selected] = 0;
        else memmove(value, value + selected, length - selected + 1);
    }
    return value;
}

static int length_parameter(const struct csh_token *word, size_t begin, size_t end)
{
    int byte = logical(word, &begin, end);
    if (name_start(byte)) {
        do { byte = logical(word, &begin, end); } while (name_char(byte));
    } else if (digit(byte)) {
        do { byte = logical(word, &begin, end); } while (digit(byte));
    } else if (byte > 0 && strchr("@*#?$!-", byte) != NULL) {
        byte = logical(word, &begin, end);
    } else return 0;
    return byte == -1;
}

static int empty_operand(const struct csh_token *word, size_t begin, size_t end)
{
    return logical(word, &begin, end) == -1;
}

static enum csh_expand_result parameter(struct expansion_work *work,
    size_t index, struct csh_expansion *out)
{
    const struct csh_fragment *f = &work->word->fragments[index];
    size_t pos = f->begin, end = f->end, name_length = 0, save, operand;
    char *name = NULL, *value = NULL, *text = NULL;
    int byte, braced = 0, length_op = 0, colon = 0, op = 0, longest = 0;
    int is_set = 0, use_word;
    struct csh_expansion expanded = {0};
    struct csh_state_info info;
    enum csh_expand_result result = CSH_EXPAND_INVALID;
    logical(work->word, &pos, end); /* $ */
    save = pos;
    byte = logical(work->word, &pos, end);
    if (byte == '{') {
        braced = 1;
        --end;
        save = pos;
        byte = logical(work->word, &pos, end);
        if (byte == '#') {
            if (length_parameter(work->word, pos, end)) {
                length_op = 1;
                save = pos;
                byte = logical(work->word, &pos, end);
            }
        }
    }
    if (end < save || (name = malloc(end - save + 1)) == NULL) {
        result = CSH_EXPAND_NOMEM;
        goto done;
    }
    if (name_start(byte) || digit(byte)) {
        int numeric = digit(byte);
        name[name_length++] = (char)byte;
        for (;;) {
            save = pos;
            byte = logical(work->word, &pos, end);
            if ((numeric ? digit(byte) : name_char(byte)) && (!numeric || braced))
                name[name_length++] = (char)byte;
            else { pos = save; break; }
        }
    } else if (byte > 0 && strchr("@*#?$!-", byte) != NULL) {
        name[name_length++] = (char)byte;
    } else goto done;
    name[name_length] = 0;
    byte = logical(work->word, &pos, end);
    if (byte != -1) {
        if (!braced || length_op) goto done;
        if (byte == ':') { colon = 1; byte = logical(work->word, &pos, end); }
        if (byte < 0 || strchr("-+=?#%", byte) == NULL ||
            (colon && (byte == '#' || byte == '%'))) goto done;
        op = byte;
        if (op == '#' || op == '%') {
            save = pos;
            if (logical(work->word, &pos, end) == op) longest = 1;
            else pos = save;
        }
    }
    operand = pos;
    if (name[0] == '@' || name[0] == '*') {
        if (length_op || op) goto done; /* POSIX leaves modified positional lists unspecified. */
        result = positional(work, out, name[0] == '*', f->quote);
        goto done;
    }
    result = parameter_value(work, name, &value, &is_set);
    if (result != CSH_EXPAND_OK) goto done;
    csh_state_get_info(work->state, &info);
    if (!is_set && (info.options & CSH_OPT_NOUNSET) != 0 &&
        (length_op || !op || op == '#' || op == '%')) {
        result = fail(work, CSH_EXPAND_UNSET, index, name);
        goto done;
    }
    if (length_op) {
        char number[64];
        size_t count = 0, offset = 0, bytes = strlen(value);
        while (offset < bytes) { offset += character_bytes(value + offset, bytes - offset); ++count; }
        snprintf(number, sizeof(number), "%zu", count);
        result = scalar(out, number, f->quote, CSH_EXPAND_PARAMETER);
        goto done;
    }
    if (!op) {
        result = scalar(out, value, f->quote, CSH_EXPAND_PARAMETER);
        goto done;
    }
    if (op == '#' || op == '%') {
        expanded.context = CSH_EXPAND_PATTERN;
        result = range(work, index, operand, end, &expanded, CSH_EXPAND_PARAMETER, 1);
        if (result != CSH_EXPAND_OK) goto done;
        {
            struct csh_fields patterns = {0};
            result = csh_expand_fields(work->state, &expanded, NULL, &patterns, work->error);
            if (result != CSH_EXPAND_OK) goto done;
            if (patterns.count > 1) {
                csh_fields_destroy(&patterns);
                result = CSH_EXPAND_INVALID;
                goto done;
            }
            text = patterns.count ? patterns.values[0] : copy_bytes((const unsigned char *)"", 0);
            free(patterns.values);
            if (text == NULL) { result = CSH_EXPAND_NOMEM; goto done; }
        }
        result = scalar(out, remove_pattern(value, text, op == '%', longest),
            f->quote, CSH_EXPAND_PARAMETER);
        goto done;
    }
    use_word = !is_set || (colon && value[0] == 0);
    if (op == '+') use_word = !use_word;
    if (!use_word) {
        result = scalar(out, op == '+' ? "" : value, f->quote, CSH_EXPAND_PARAMETER);
        goto done;
    }
    if (op == '-' || op == '+') {
        if (empty_operand(work->word, operand, end))
            result = scalar(out, "", f->quote, CSH_EXPAND_PARAMETER);
        else result = range(work, index, operand, end, out, CSH_EXPAND_PARAMETER, 1);
        goto done;
    }
    expanded.context = CSH_EXPAND_ASSIGNMENT;
    result = range(work, index, operand, end, &expanded, CSH_EXPAND_PARAMETER, 1);
    if (result != CSH_EXPAND_OK) goto done;
    text = flatten(&expanded);
    if (text == NULL) { result = CSH_EXPAND_NOMEM; goto done; }
    if (op == '?') {
        result = fail(work, CSH_EXPAND_UNSET, index,
            operand == end ? "parameter is unset or empty" : text);
        goto done;
    }
    result = assign(work, name, text);
    if (result == CSH_EXPAND_OK)
        result = scalar(out, text, f->quote, CSH_EXPAND_PARAMETER);
 done:
    free(name);
    free(value);
    free(text);
    csh_expansion_destroy(&expanded);
    if (result != CSH_EXPAND_OK && (work->error == NULL || work->error->code == CSH_EXPAND_OK))
        fail(work, result, index, "parameter expansion failed");
    return result;
}

/* Test syntax provenance, not expanded bytes, when identifying a tilde-prefix. */
static int plain_at(const struct expansion_work *work, size_t parent, size_t pos)
{
    size_t i = parent == CSH_FRAGMENT_ROOT ? 0 : parent + 1;
    size_t limit = parent == CSH_FRAGMENT_ROOT ? work->word->fragment_count : work->next[parent];
    while (i < limit) {
        const struct csh_fragment *f = &work->word->fragments[i];
        if (f->begin <= pos && pos < f->end)
            return f->parent == parent && f->quote == CSH_QUOTE_NONE &&
                (f->kind == CSH_FRAGMENT_TEXT || f->kind == CSH_FRAGMENT_CONTINUATION);
        i = work->next[i];
    }
    return 0;
}

static enum csh_expand_result tilde_prefix(struct expansion_work *work,
    size_t parent, size_t begin, size_t end, struct csh_expansion *out, size_t *after,
    int assignment_tilde)
{
    size_t pos = begin + 1, length = 0;
    char *name;
    const char *home;
    struct csh_variable_view view;
    struct passwd *entry;
    enum csh_expand_result result;
    *after = begin;
    name = malloc(end - begin + 1);
    if (name == NULL) return CSH_EXPAND_NOMEM;
    while (pos < end) {
        if (!plain_at(work, parent, pos)) { free(name); return CSH_EXPAND_OK; }
        if (work->word->raw[pos] == '/' || (assignment_tilde && work->word->raw[pos] == ':')) break;
        if (pos + 1 < end && work->word->raw[pos] == '\\' && work->word->raw[pos + 1] == '\n') {
            pos += 2;
            continue;
        }
        name[length++] = (char)work->word->raw[pos++];
    }
    name[length] = 0;
    if (length == 0) {
        csh_state_get_variable(work->state, "HOME", &view);
        home = view.value;
    } else {
        entry = getpwnam(name);
        home = entry != NULL ? entry->pw_dir : NULL;
    }
    free(name);
    if (home == NULL) return CSH_EXPAND_OK; /* documented unspecified choice */
    length = strlen(home);
    if (length != 0 && home[length - 1] == '/' && pos < end && work->word->raw[pos] == '/')
        --length;
    result = append(out, home, length, CSH_QUOTE_SINGLE, CSH_EXPAND_TILDE, 1);
    if (result == CSH_EXPAND_OK) *after = pos;
    return result;
}

static size_t trim_delimiters(const struct csh_token *word, size_t begin, size_t end, unsigned count)
{
    while (count-- != 0) {
        if (end <= begin || word->raw[end - 1] != ')') return SIZE_MAX;
        --end;
        while (end - begin >= 2 && word->raw[end - 2] == '\\' &&
            word->raw[end - 1] == '\n') end -= 2;
    }
    return end;
}

static enum csh_expand_result arithmetic(struct expansion_work *work,
    size_t index, struct csh_expansion *out)
{
    const struct csh_fragment *f = &work->word->fragments[index];
    struct csh_expansion expression = {0};
    size_t begin = f->begin, end = trim_delimiters(work->word, f->begin, f->end, 2);
    enum csh_expand_result result;
    enum csh_arith_result arith;
    char *text = NULL, number[64];
    long value;
    unsigned n;
    if (end == SIZE_MAX) return CSH_EXPAND_INVALID;
    for (n = 0; n < 3; ++n) logical(work->word, &begin, end);
    expression.context = CSH_EXPAND_ASSIGNMENT;
    result = range(work, index, begin, end, &expression, CSH_EXPAND_LITERAL, 0);
    if (result != CSH_EXPAND_OK) goto done;
    text = flatten(&expression);
    if (text == NULL) { result = CSH_EXPAND_NOMEM; goto done; }
    arith = csh_arith_eval(work->state, text, &value);
    if (arith != CSH_ARITH_OK) {
        result = arith == CSH_ARITH_NOMEM ? CSH_EXPAND_NOMEM :
            arith == CSH_ARITH_READONLY ? CSH_EXPAND_READONLY : CSH_EXPAND_ARITHMETIC_ERROR;
        goto done;
    }
    snprintf(number, sizeof(number), "%ld", value);
    result = scalar(out, number, f->quote, CSH_EXPAND_ARITHMETIC);
 done:
    free(text);
    csh_expansion_destroy(&expression);
    if (result != CSH_EXPAND_OK && (work->error == NULL || work->error->code == CSH_EXPAND_OK))
        fail(work, result, index, "arithmetic expansion failed");
    return result;
}

static enum csh_expand_result substitution(struct expansion_work *work,
    size_t index, struct csh_expansion *out)
{
    const char *bytes = NULL;
    size_t length = 0;
    enum csh_expand_result result;
    if (work->options.substitute == NULL)
        return fail(work, CSH_EXPAND_DEFERRED, index, "command substitution requires an executor");
    result = work->options.substitute(work->options.user, work->state,
        work->word, index, &bytes, &length, work->error);
    if (result != CSH_EXPAND_OK) return result;
    if ((bytes == NULL && length != 0) || length == SIZE_MAX ||
        (length != 0 && memchr(bytes, 0, length) != NULL))
        return fail(work, CSH_EXPAND_INVALID, index, "invalid command substitution bytes");
    return append(out, bytes, length, work->word->fragments[index].quote,
        CSH_EXPAND_SUBSTITUTION, work->word->fragments[index].quote != CSH_QUOTE_NONE);
}

static enum csh_expand_result range(struct expansion_work *work, size_t parent,
    size_t begin, size_t end, struct csh_expansion *out,
    enum csh_expand_origin literal_origin, int tilde)
{
    size_t i = parent == CSH_FRAGMENT_ROOT ? 0 : parent + 1;
    size_t limit = parent == CSH_FRAGMENT_ROOT ? work->word->fragment_count : work->next[parent];
    size_t cursor = begin;
    int tilde_ok = tilde;
    enum csh_expand_result result = CSH_EXPAND_OK;
    if (++work->depth > EXPAND_DEPTH) {
        --work->depth;
        return fail(work, CSH_EXPAND_LIMIT, parent, "expansion nesting limit exceeded");
    }
    for (; i < limit && result == CSH_EXPAND_OK; i = work->next[i]) {
        const struct csh_fragment *f = &work->word->fragments[i];
        size_t start, stop;
        if (f->end <= cursor || f->begin >= end) continue;
        start = f->begin < cursor ? cursor : f->begin;
        stop = f->end > end ? end : f->end;
        if (f->kind == CSH_FRAGMENT_TEXT) {
            size_t p = start, run = start;
            while (p < stop) {
                if (tilde_ok && f->quote == CSH_QUOTE_NONE && work->word->raw[p] == '~') {
                    size_t after;
                    if (p > run) {
                        result = append(out, (const char *)work->word->raw + run, p - run,
                            f->quote, literal_origin, f->quote != CSH_QUOTE_NONE);
                        if (result != CSH_EXPAND_OK) break;
                    }
                    result = tilde_prefix(work, parent, p, end, out, &after, tilde & 2);
                    if (result != CSH_EXPAND_OK) break;
                    if (after != p) { p = after; run = p; tilde_ok = 0; continue; }
                    run = p;
                }
                tilde_ok = (tilde & 2) &&
                    f->quote == CSH_QUOTE_NONE && work->word->raw[p] == ':';
                ++p;
            }
            if (result == CSH_EXPAND_OK && run < stop)
                result = append(out, (const char *)work->word->raw + run, stop - run,
                    f->quote, literal_origin, f->quote != CSH_QUOTE_NONE);
            cursor = p > stop ? p : stop;
            continue;
        }
        if (f->kind == CSH_FRAGMENT_CONTINUATION) { cursor = stop; continue; }
        tilde_ok = 0;
        if (start != f->begin || stop != f->end) {
            result = fail(work, CSH_EXPAND_INVALID, i, "partial expansion fragment");
            break;
        }
        switch (f->kind) {
        case CSH_FRAGMENT_QUOTED:
            if (f->quote == CSH_QUOTE_DOLLAR_SINGLE) {
                result = scalar(out, work->decoded[i], f->quote, literal_origin);
            } else {
                size_t child;
                int content = 0;
                for (child = i + 1; child < work->next[i]; child = work->next[child])
                    if (work->word->fragments[child].kind != CSH_FRAGMENT_CONTINUATION) content = 1;
                if (!content) result = scalar(out, "", f->quote, literal_origin);
                else result = range(work, i, f->begin + 1, f->end - 1, out, literal_origin, 0);
            }
            break;
        case CSH_FRAGMENT_ESCAPE:
            result = append(out, (const char *)work->word->raw + f->begin + 1,
                f->end - f->begin - 1, CSH_QUOTE_SINGLE, literal_origin, 1);
            break;
        case CSH_FRAGMENT_PARAMETER: result = parameter(work, i, out); break;
        case CSH_FRAGMENT_ARITHMETIC: result = arithmetic(work, i, out); break;
        case CSH_FRAGMENT_COMMAND:
        case CSH_FRAGMENT_BACKQUOTE: result = substitution(work, i, out); break;
        default: result = CSH_EXPAND_INVALID; break;
        }
        cursor = stop;
    }
    --work->depth;
    return result;
}

/* Delimiters must also be sound for parser-constructed public records. */
static int fragment_syntax(const struct csh_token *word, const struct csh_fragment *f)
{
    size_t pos = f->begin, end;
    int byte;
    switch (f->kind) {
    case CSH_FRAGMENT_TEXT: return 1;
    case CSH_FRAGMENT_CONTINUATION:
        return f->end - f->begin == 2 && word->raw[pos] == '\\' && word->raw[pos + 1] == '\n';
    case CSH_FRAGMENT_ESCAPE:
        return f->end - f->begin == 2 && word->raw[pos] == '\\';
    case CSH_FRAGMENT_QUOTED:
        if (f->quote == CSH_QUOTE_DOLLAR_SINGLE) {
            if (logical(word, &pos, f->end) != '$') return 0;
            return logical(word, &pos, f->end) == '\'' &&
                pos < f->end && word->raw[f->end - 1] == '\'';
        }
        byte = f->quote == CSH_QUOTE_SINGLE ? '\'' : f->quote == CSH_QUOTE_DOUBLE ? '"' : -1;
        return word->raw[pos] == byte && word->raw[f->end - 1] == byte;
    case CSH_FRAGMENT_BACKQUOTE:
        return word->raw[pos] == '`' && word->raw[f->end - 1] == '`';
    case CSH_FRAGMENT_PARAMETER:
        if (logical(word, &pos, f->end) != '$') return 0;
        byte = logical(word, &pos, f->end);
        if (byte == '{') return pos < f->end && word->raw[f->end - 1] == '}';
        return name_char(byte) || (byte > 0 && strchr("@*#?$!-", byte) != NULL);
    case CSH_FRAGMENT_COMMAND:
        return logical(word, &pos, f->end) == '$' && logical(word, &pos, f->end) == '(' &&
            pos < f->end && word->raw[f->end - 1] == ')';
    case CSH_FRAGMENT_ARITHMETIC:
        end = trim_delimiters(word, f->begin, f->end, 2);
        return end != SIZE_MAX && logical(word, &pos, end) == '$' &&
            logical(word, &pos, end) == '(' && logical(word, &pos, end) == '(';
    }
    return 0;
}

/* Validate structure once and cache subtree ends. Inputs originate at the lexer
 * (or parser-preserving copies); rejecting malformed public records avoids
 * accidental out-of-bounds access when integration code supplies bad ranges. */
static enum csh_expand_result prepare(struct expansion_work *work)
{
    size_t i, depth = 0, previous = 0, *stack;
    const struct csh_token *word = work->word;
    if (word->kind != CSH_TOKEN_WORD || word->raw == NULL ||
        (word->fragment_count != 0 && word->fragments == NULL) ||
        memchr(word->raw, 0, word->length) != NULL)
        return CSH_EXPAND_INVALID;
    if (word->fragment_count > SIZE_MAX / sizeof(size_t) - 1 ||
        word->fragment_count > SIZE_MAX / sizeof(char *) - 1)
        return CSH_EXPAND_NOMEM;
    work->next = malloc((word->fragment_count + 1) * sizeof(*work->next));
    work->decoded = malloc((word->fragment_count + 1) * sizeof(*work->decoded));
    stack = malloc((word->fragment_count + 1) * sizeof(*stack));
    if (work->decoded != NULL)
        memset(work->decoded, 0, (word->fragment_count + 1) * sizeof(*work->decoded));
    if (work->next == NULL || work->decoded == NULL || stack == NULL) {
        free(stack);
        return CSH_EXPAND_NOMEM;
    }
    for (i = 0; i < word->fragment_count; ++i) {
        const struct csh_fragment *f = &word->fragments[i];
        while (depth != 0 && f->parent != stack[depth - 1]) {
            previous = word->fragments[stack[depth - 1]].end;
            work->next[stack[--depth]] = i;
        }
        if ((depth == 0 && f->parent != CSH_FRAGMENT_ROOT) ||
            (depth != 0 && (f->begin < word->fragments[f->parent].begin ||
                f->end > word->fragments[f->parent].end)) ||
            f->begin < previous || f->end < f->begin || f->end > word->length ||
            f->quote < CSH_QUOTE_NONE || f->quote > CSH_QUOTE_DOLLAR_SINGLE ||
            f->kind < CSH_FRAGMENT_TEXT || f->kind > CSH_FRAGMENT_BACKQUOTE ||
            (f->kind != CSH_FRAGMENT_TEXT && f->end - f->begin < 2) ||
            (f->kind == CSH_FRAGMENT_ARITHMETIC && f->end - f->begin < 5)) {
            free(stack);
            return fail(work, CSH_EXPAND_INVALID, i, "invalid structured word");
        }
        if (!fragment_syntax(word, f) || (depth != 0 &&
            (word->fragments[f->parent].kind == CSH_FRAGMENT_TEXT ||
             word->fragments[f->parent].kind == CSH_FRAGMENT_ESCAPE ||
             word->fragments[f->parent].kind == CSH_FRAGMENT_CONTINUATION ||
             word->fragments[f->parent].kind == CSH_FRAGMENT_COMMAND))) {
            free(stack);
            return fail(work, CSH_EXPAND_INVALID, i, "invalid fragment syntax");
        }
        if (depth >= EXPAND_DEPTH) {
            free(stack);
            return fail(work, CSH_EXPAND_LIMIT, i, "expansion nesting limit exceeded");
        }
        previous = f->begin;
        stack[depth++] = i;
    }
    while (depth != 0) work->next[stack[--depth]] = word->fragment_count;
    free(stack);
    for (i = 0; i < word->fragment_count; ++i) {
        const struct csh_fragment *f = &word->fragments[i];
        if (f->kind == CSH_FRAGMENT_QUOTED && f->quote == CSH_QUOTE_DOLLAR_SINGLE) {
            size_t begin = f->begin, length;
            enum csh_quote_result decoded;
            if (logical(word, &begin, f->end) != '$' || logical(word, &begin, f->end) != '\'' ||
                begin >= f->end || word->raw[f->end - 1] != '\'')
                return fail(work, CSH_EXPAND_INVALID, i, "invalid dollar-single-quote region");
            decoded = csh_quote_decode(word->raw + begin, f->end - begin - 1,
                &work->decoded[i], &length);
            if (decoded != CSH_QUOTE_OK)
                return fail(work, decoded == CSH_QUOTE_NOMEM ? CSH_EXPAND_NOMEM : CSH_EXPAND_INVALID,
                    i, "dollar-single-quote decoding failed");
        }
    }
    return CSH_EXPAND_OK;
}

enum csh_expand_result csh_expand_word(struct csh_state *state,
    const struct csh_token *word, const struct csh_expand_options *options,
    struct csh_expansion *out, struct csh_expand_error *error)
{
    struct expansion_work work = {0};
    struct csh_state_checkpoint *checkpoint = NULL;
    enum csh_expand_result result;
    size_t i;
    if (error != NULL) {
        memset(error, 0, sizeof(*error));
        error->fragment = CSH_FRAGMENT_ROOT;
    }
    if (out != NULL) memset(out, 0, sizeof(*out));
    if (state == NULL || word == NULL || out == NULL ||
        (options != NULL && (options->context < CSH_EXPAND_ARGUMENT ||
            options->context > CSH_EXPAND_HEREDOC))) {
        if (error != NULL) {
            error->code = CSH_EXPAND_INVALID;
            snprintf(error->message, sizeof(error->message), "invalid expansion input");
        }
        return CSH_EXPAND_INVALID;
    }
    work.state = state;
    work.word = word;
    work.error = error;
    if (options != NULL) work.options = *options;
    out->context = work.options.context;
    result = prepare(&work);
    if (result != CSH_EXPAND_OK) goto done;
    if (csh_state_save(state, &checkpoint) != CSH_STATE_OK) {
        result = CSH_EXPAND_NOMEM;
        goto done;
    }
    result = range(&work, CSH_FRAGMENT_ROOT, 0, word->length, out, CSH_EXPAND_LITERAL,
        out->context == CSH_EXPAND_HEREDOC ? 0 :
        out->context == CSH_EXPAND_ASSIGNMENT ? 3 : 1);
 done:
    if (result != CSH_EXPAND_OK) {
        csh_expansion_destroy(out);
        if (checkpoint != NULL) csh_state_restore(state, &checkpoint);
        if (error == NULL || error->code == CSH_EXPAND_OK)
            fail(&work, result, CSH_FRAGMENT_ROOT, "word expansion failed");
    }
    csh_state_checkpoint_destroy(checkpoint);
    if (work.decoded != NULL)
        for (i = 0; i < word->fragment_count; ++i) free(work.decoded[i]);
    free(work.decoded);
    free(work.next);
    return result;
}
