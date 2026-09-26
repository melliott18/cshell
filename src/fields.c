#include "cshell/character.h"
#include "cshell/expand.h"
#include "field_internal.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

struct field_cursor {
    const struct csh_expand_field *field;
    size_t span, offset;
};

enum field_protection { FIELD_QUOTED = 1, FIELD_LITERAL = 2 };

void csh_fields_destroy(struct csh_fields *fields)
{
    size_t i;
    if (fields == NULL) return;
    for (i = 0; i < fields->count; ++i) free(fields->values[i]);
    free(fields->values);
    memset(fields, 0, sizeof(*fields));
}

enum csh_expand_result csh_fields_append(struct csh_fields *out,
    const char *text, size_t length)
{
    char *copy, **values;
    if (length == SIZE_MAX || out->count > SIZE_MAX / sizeof(*values) - 2)
        return CSH_EXPAND_NOMEM;
    copy = malloc(length + 1);
    if (copy == NULL) return CSH_EXPAND_NOMEM;
    memcpy(copy, text, length);
    copy[length] = 0;
    values = realloc(out->values, (out->count + 2) * sizeof(*values));
    if (values == NULL) {
        free(copy);
        return CSH_EXPAND_NOMEM;
    }
    out->values = values;
    values[out->count++] = copy;
    values[out->count] = NULL;
    return CSH_EXPAND_OK;
}

static int interrupted(const struct csh_field_options *options)
{
    return options != NULL && options->interrupted != NULL &&
        options->interrupted(options->user);
}

/* Empty protected spans are real positions in the input: a quote after a
 * delimiter retains a different field from a quote before that delimiter.
 * Skip only implicit empty expansion results, never protected empty spans. */
static const struct csh_expand_span *current(struct field_cursor *cursor)
{
    while (cursor->span < cursor->field->span_count) {
        const struct csh_expand_span *span = &cursor->field->spans[cursor->span];
        if (cursor->offset < span->length ||
            (span->length == 0 && span->keep_empty)) return span;
        ++cursor->span;
        cursor->offset = 0;
    }
    return NULL;
}

/* Match IFS character byte sequences against arbitrary input bytes. A
 * delimiter may not straddle expansion results. Each span is one contiguous
 * result/protected region; matching stops at its boundary. Invalid IFS
 * multibyte sequences are treated as individual bytes. Only space, tab and
 * newline count as IFS whitespace, independently of the active locale. */
static size_t delimiter(const struct csh_expand_span *span, size_t offset,
    const char *ifs, size_t ifs_length, int *white)
{
    size_t i = 0;
    *white = 0;
    if (span == NULL || !span->split || span->quote != CSH_QUOTE_NONE ||
        offset == span->length) return 0;
    while (i < ifs_length) {
        mbstate_t state = {0};
        size_t length = mbrlen(ifs + i, ifs_length - i, &state);
        if (length == (size_t)-1 || length == (size_t)-2 || length == 0)
            length = 1;
        if (length <= span->length - offset &&
            memcmp(span->text + offset, ifs + i, length) == 0) {
            *white = length == 1 && strchr(" \t\n", ifs[i]) != NULL;
            return length;
        }
        i += length;
    }
    return 0;
}

/* A shell-quoted byte inside [:name:], [.element.], or [=element=] must not
 * regain its syntactic role after quote removal. Find the complete raw form
 * so the encoder can make its inner '[' literal when any part was quoted.
 * An incomplete form remains subject to the host matcher's bracket rules. */
static enum csh_expand_result bracket_subexpression(const char *raw,
    const unsigned char *protection, size_t length, size_t begin,
    enum csh_expand_context context, const struct csh_field_options *options,
    size_t *end, int *quoted)
{
    size_t i;
    *end = begin;
    *quoted = 0;
    if (begin + 1 >= length || strchr(":.=", raw[begin + 1]) == NULL)
        return CSH_EXPAND_OK;
    for (i = begin + 1; i < length; i += csh_character_length(raw + i, length - i, 0, 1)) {
        if (interrupted(options)) return CSH_EXPAND_INTERRUPTED;
        if (context == CSH_EXPAND_ARGUMENT && raw[i] == '/') break;
        if (protection[i] & FIELD_QUOTED) *quoted = 1;
        if (i > begin + 1 && raw[i] == raw[begin + 1] &&
            i + 1 < length && raw[i + 1] == ']') {
            if (protection[i + 1] & FIELD_QUOTED) *quoted = 1;
            *end = i + 1;
            break;
        }
    }
    return CSH_EXPAND_OK;
}

/* At most one protective backslash is inserted per raw byte. bracket is zero
 * outside a list, one before its first member, two after initial '!', and
 * three once ']' can close it. Pattern escapes may cross span boundaries. */
static enum csh_expand_result make_pattern(const char *raw,
    const unsigned char *protection, size_t length, char *pattern,
    enum csh_expand_context context, const struct csh_field_options *options)
{
    size_t i, position = 0;
    int pending_escape = 0, bracket = 0;
    for (i = 0; i < length; ++i) {
        size_t width = csh_character_length(raw + i, length - i, 0, 1);
        char byte = raw[i];
        int quoted = (protection[i] & FIELD_QUOTED) != 0, force_literal = 0;
        if (interrupted(options)) return CSH_EXPAND_INTERRUPTED;
        if (width > 1) {
            memcpy(pattern + position, raw + i, width);
            position += width;
            i += width - 1;
            pending_escape = 0;
            if (bracket) bracket = 3;
            continue;
        }
        if (context == CSH_EXPAND_ARGUMENT && byte == '/') bracket = 0;
        if (pending_escape) {
            /* A second protective slash could reactivate a quoted wildcard. */
            pattern[position++] = byte;
            pending_escape = 0;
            if (bracket != 0) bracket = 3;
            continue;
        }
        if (bracket != 0 && byte == '[' && !quoted) {
            size_t end;
            enum csh_expand_result result = bracket_subexpression(raw,
                protection, length, i, context, options, &end, &force_literal);
            if (result != CSH_EXPAND_OK) return result;
            if (end != i && !force_literal) {
                /* Unquoted POSIX syntax goes intact to fnmatch. Its inner
                 * closing bracket is not the end of the enclosing list. */
                memcpy(pattern + position, raw + i, end - i + 1);
                position += end - i + 1;
                i = end;
                bracket = 3;
                continue;
            }
            if (end == i) force_literal = 0;
        }
        if (force_literal || (byte == '\\' &&
                (quoted || (protection[i] & FIELD_LITERAL))) ||
            (quoted && strchr("*?[]-!^", byte) != NULL))
            pattern[position++] = '\\';
        else if (byte == '\\') pending_escape = 1;
        pattern[position++] = byte;
        if (pending_escape) continue;
        if (bracket == 0) {
            if (byte == '[' && !quoted && !force_literal) bracket = 1;
        } else if (bracket == 1 && byte == '!' && !quoted) bracket = 2;
        else if (bracket == 3 && byte == ']' && !quoted) bracket = 0;
        else bracket = 3;
    }
    pattern[position] = 0;
    return CSH_EXPAND_OK;
}

static enum csh_expand_result emit(const char *raw,
    const unsigned char *protection, size_t length, char *pattern,
    enum csh_expand_context context, unsigned shell_options,
    const struct csh_field_options *options, struct csh_fields *out)
{
    enum csh_expand_result result;
    if (context == CSH_EXPAND_ASSIGNMENT || context == CSH_EXPAND_REDIRECTION ||
        context == CSH_EXPAND_HEREDOC ||
        (context == CSH_EXPAND_ARGUMENT && (shell_options & CSH_OPT_NOGLOB)))
        return csh_fields_append(out, raw, length);
    result = make_pattern(raw, protection, length, pattern, context, options);
    if (result != CSH_EXPAND_OK) return result;
    if (context == CSH_EXPAND_PATTERN)
        return csh_fields_append(out, pattern, strlen(pattern));
    if (context == CSH_EXPAND_ARGUMENT && !(shell_options & CSH_OPT_NOGLOB))
        return csh_pathname_expand(raw, pattern, options, out);
    return csh_fields_append(out, raw, strlen(raw));
}

static enum csh_expand_result finish_field(const struct csh_expand_field *field,
    enum csh_expand_context context, const char *ifs, size_t ifs_length,
    unsigned shell_options, const struct csh_field_options *options,
    struct csh_fields *out)
{
    struct field_cursor cursor = {field, 0, 0};
    const struct csh_expand_span *span;
    size_t i, total = 0, raw_length = 0;
    int keep = context != CSH_EXPAND_ARGUMENT;
    char *raw = NULL, *pattern = NULL;
    unsigned char *protection = NULL;
    enum csh_expand_result result = CSH_EXPAND_OK;
    if (field->span_count != 0 && field->spans == NULL) return CSH_EXPAND_INVALID;
    for (i = 0; i < field->span_count; ++i) {
        span = &field->spans[i];
        if (interrupted(options)) return CSH_EXPAND_INTERRUPTED;
        if (span->length > (SIZE_MAX - 1) / 2 - total) return CSH_EXPAND_NOMEM;
        if (span->text == NULL || span->quote < CSH_QUOTE_NONE ||
            span->quote > CSH_QUOTE_DOLLAR_SINGLE ||
            span->origin < CSH_EXPAND_LITERAL || span->origin > CSH_EXPAND_SUBSTITUTION ||
            (span->split && span->quote != CSH_QUOTE_NONE) ||
            (span->keep_empty && span->quote == CSH_QUOTE_NONE) ||
            memchr(span->text, 0, span->length) != NULL || span->text[span->length] != 0)
            return CSH_EXPAND_INVALID;
        total += span->length;
    }
    raw = malloc(total + 1);
    pattern = malloc(total * 2 + 1);
    protection = malloc(total + 1);
    if (raw == NULL || pattern == NULL || protection == NULL) {
        result = CSH_EXPAND_NOMEM;
        goto done;
    }
    while ((span = current(&cursor)) != NULL) {
        size_t n;
        int white;
        if (interrupted(options)) {
            result = CSH_EXPAND_INTERRUPTED;
            goto done;
        }
        if (span->length == 0) {
            keep = 1;
            ++cursor.span;
            continue;
        }
        n = context == CSH_EXPAND_ARGUMENT ?
            delimiter(span, cursor.offset, ifs, ifs_length, &white) : 0;
        if (n == 0) {
            size_t width = csh_character_length(span->text + cursor.offset,
                span->length - cursor.offset, 0, 1);
            unsigned char flags =
                (span->quote != CSH_QUOTE_NONE ? FIELD_QUOTED : 0) |
                (span->origin == CSH_EXPAND_LITERAL ? FIELD_LITERAL : 0);
            memcpy(raw + raw_length, span->text + cursor.offset, width);
            memset(protection + raw_length, flags, width);
            cursor.offset += width;
            raw_length += width;
            continue;
        }
        /* Issue 8: discard IFS whitespace, consume at most one following
         * non-whitespace delimiter, then delimit the candidate. */
        while (n != 0 && white) {
            cursor.offset += n;
            if (interrupted(options)) {
                result = CSH_EXPAND_INTERRUPTED;
                goto done;
            }
            span = current(&cursor);
            n = delimiter(span, cursor.offset, ifs, ifs_length, &white);
        }
        if (n != 0) cursor.offset += n;
        if (raw_length != 0 || keep || n != 0) {
            raw[raw_length] = 0;
            result = emit(raw, protection, raw_length, pattern,
                context, shell_options, options, out);
            if (result != CSH_EXPAND_OK) goto done;
        }
        raw_length = 0;
        keep = 0;
    }
    if (raw_length != 0 || keep) {
        raw[raw_length] = 0;
        result = emit(raw, protection, raw_length, pattern,
            context, shell_options, options, out);
    }
 done:
    free(raw);
    free(pattern);
    free(protection);
    return result;
}

enum csh_expand_result csh_expand_fields(const struct csh_state *state,
    const struct csh_expansion *expansion, const struct csh_field_options *options,
    struct csh_fields *out, struct csh_expand_error *error)
{
    struct csh_variable_view view;
    struct csh_state_info info;
    const char *ifs;
    size_t i, ifs_length;
    enum csh_expand_result result = CSH_EXPAND_INVALID;
    if (out != NULL) memset(out, 0, sizeof(*out));
    if (error != NULL) {
        memset(error, 0, sizeof(*error));
        error->fragment = CSH_FRAGMENT_ROOT;
    }
    if (state == NULL || expansion == NULL || out == NULL ||
        expansion->context < CSH_EXPAND_ARGUMENT || expansion->context > CSH_EXPAND_HEREDOC ||
        (expansion->field_count != 0 && expansion->fields == NULL)) goto done;
    if (csh_state_get_variable(state, "IFS", &view) != CSH_STATE_OK ||
        csh_state_get_info(state, &info) != CSH_STATE_OK) goto done;
    ifs = view.value == NULL ? " \t\n" : view.value;
    ifs_length = strlen(ifs);
    result = CSH_EXPAND_OK;
    for (i = 0; i < expansion->field_count; ++i) {
        if (interrupted(options)) {
            result = CSH_EXPAND_INTERRUPTED;
            break;
        }
        result = finish_field(&expansion->fields[i], expansion->context,
            ifs, ifs_length, info.options, options, out);
        if (result != CSH_EXPAND_OK) break;
    }
    if (result == CSH_EXPAND_OK && interrupted(options)) result = CSH_EXPAND_INTERRUPTED;
 done:
    if (result != CSH_EXPAND_OK) {
        csh_fields_destroy(out);
        if (error != NULL) {
            const char *message = "invalid intermediate expansion";
            if (result == CSH_EXPAND_NOMEM) message = "field expansion allocation failed";
            else if (result == CSH_EXPAND_IO) message = "pathname expansion I/O failed";
            else if (result == CSH_EXPAND_INTERRUPTED) message = "field expansion interrupted";
            else if (result == CSH_EXPAND_LIMIT) message = "pathname expansion limit exceeded";
            error->code = result;
            snprintf(error->message, sizeof(error->message), "%s", message);
        }
    }
    return result;
}
