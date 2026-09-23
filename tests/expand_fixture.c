/* Value/provenance API fixtures, independent of shell execution and parsing. */
#include "cshell/expand.h"

#include <limits.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "expand fixture failed at line %d: %s\n", \
            __LINE__, #condition); \
        exit(90); \
    } \
} while (0)
#define STATE(operation) CHECK((operation) == CSH_STATE_OK)

static struct csh_state *new_state(void)
{
    struct csh_invocation invocation = {0};
    struct csh_state *state;
    invocation.mode = CSH_MODE_STRING;
    invocation.arg0 = "fixture-zero";
    STATE(csh_state_create(&state, &invocation, NULL));
    return state;
}

/* Only simple command words occur inside $(...) in these fixtures. Selecting
 * their first RPAREN is a fixture handshake, not an implementation of grammar. */
static struct csh_token word(const char *source)
{
    struct csh_lexer *frames[32] = {0};
    struct csh_token token = {0};
    struct csh_error error;
    size_t depth = 0;
    CHECK(csh_lexer_create(&frames[0], "expansion-fixture", &error) == 0);
    CHECK(csh_lexer_feed(frames[0], source, strlen(source), 1, &error) == 0);
    for (;;) {
        enum csh_lex_result result = csh_lexer_next(frames[depth], &token, &error);
        if (result == CSH_LEX_COMMAND) {
            CHECK(depth + 1 < sizeof(frames) / sizeof(frames[0]));
            CHECK(csh_lexer_command_begin(frames[depth], &frames[depth + 1],
                &error) == 0);
            ++depth;
        } else if (result == CSH_LEX_TOKEN && depth != 0) {
            if (token.kind == CSH_TOKEN_RPAREN) {
                CHECK(csh_lexer_command_end(frames[depth - 1], frames[depth],
                    &token, &error) == 0);
                --depth;
            }
            csh_token_destroy(&token);
        } else {
            CHECK(result == CSH_LEX_TOKEN && token.kind == CSH_TOKEN_WORD);
            break;
        }
    }
    csh_lexer_destroy(frames[0]);
    return token;
}

static void variable_is(struct csh_state *state, const char *name,
    const char *expected)
{
    struct csh_variable_view actual;
    STATE(csh_state_get_variable(state, name, &actual));
    CHECK(expected == NULL ? actual.value == NULL :
        actual.value != NULL && strcmp(expected, actual.value) == 0);
}

static void field_is(const struct csh_expansion *out, size_t field,
    const char *expected)
{
    size_t index, offset = 0, length = strlen(expected);
    CHECK(field < out->field_count);
    for (index = 0; index < out->fields[field].span_count; ++index) {
        const struct csh_expand_span *span = &out->fields[field].spans[index];
        CHECK(span->text != NULL && strlen(span->text) == span->length);
        CHECK(span->length <= length - offset);
        CHECK(memcmp(span->text, expected + offset, span->length) == 0);
        CHECK(!span->keep_empty || span->quote != CSH_QUOTE_NONE);
        CHECK(!span->split || span->quote == CSH_QUOTE_NONE);
        offset += span->length;
    }
    CHECK(offset == length);
}

static struct csh_expansion expand(struct csh_state *state, const char *source,
    const struct csh_expand_options *options)
{
    struct csh_expansion out = {0};
    struct csh_expand_error error;
    struct csh_token token = word(source);
    enum csh_expand_result result = csh_expand_word(state, &token, options,
        &out, &error);
    if (result != CSH_EXPAND_OK)
        fprintf(stderr, "expanding %s failed: %d %s\n", source, result, error.message);
    CHECK(result == CSH_EXPAND_OK);
    CHECK(out.context == (options == NULL ? CSH_EXPAND_ARGUMENT : options->context));
    /* Published spans must survive token destruction. */
    csh_token_destroy(&token);
    return out;
}

static void one(struct csh_state *state, const char *source, const char *expected)
{
    struct csh_expansion out = expand(state, source, NULL);
    CHECK(out.field_count == 1);
    field_is(&out, 0, expected);
    csh_expansion_destroy(&out);
    CHECK(out.fields == NULL && out.field_count == 0);
    csh_expansion_destroy(&out);
}

static struct csh_expand_error failure(struct csh_state *state, const char *source,
    const struct csh_expand_options *options, enum csh_expand_result expected)
{
    struct csh_token token = word(source);
    struct csh_expansion out = {0};
    struct csh_expand_error error;
    enum csh_expand_result result = csh_expand_word(state, &token, options,
        &out, &error);
    if (result != expected)
        fprintf(stderr, "failure case %s: expected %d, got %d (%s)\n",
            source, expected, result, error.message);
    CHECK(result == expected && error.code == expected);
    CHECK(error.message[0] != '\0');
    CHECK(out.fields == NULL && out.field_count == 0);
    if (error.fragment != CSH_FRAGMENT_ROOT) {
        CHECK(error.fragment < token.fragment_count);
        CHECK(error.position.offset == token.fragments[error.fragment].start.offset);
    }
    csh_token_destroy(&token);
    csh_expansion_destroy(&out);
    return error;
}

static void parameters(void)
{
    struct csh_state *state = new_state();
    struct csh_expand_error error;
    STATE(csh_state_set_variable(state, "empty", ""));
    STATE(csh_state_set_variable(state, "v", "value"));
    one(state, "${missing-word}", "word");
    one(state, "${missing:-word}", "word");
    one(state, "${empty-word}", "");
    one(state, "${empty:-word}", "word");
    one(state, "${v-word}", "value");
    one(state, "${v:-word}", "value");
    one(state, "${missing+word}", "");
    one(state, "${missing:+word}", "");
    one(state, "${empty+word}", "word");
    one(state, "${empty:+word}", "");
    one(state, "${v+word}", "word");
    one(state, "${v:+word}", "word");
    one(state, "${missing=${v}}", "value");
    variable_is(state, "missing", "value");
    one(state, "${empty=unchanged}", "");
    variable_is(state, "empty", "");
    one(state, "${empty:=filled}", "filled");
    variable_is(state, "empty", "filled");
    one(state, "${v?bad}", "value");
    one(state, "${v:?bad}", "value");
    error = failure(state, "${absent?missing value}", NULL, CSH_EXPAND_UNSET);
    CHECK(strstr(error.message, "missing value") != NULL);
    STATE(csh_state_set_variable(state, "empty", ""));
    one(state, "${empty?bad}", "");
    failure(state, "${empty:?empty value}", NULL, CSH_EXPAND_UNSET);
    one(state, "${#empty}", "0");
    one(state, "${#v}", "5");
    one(state, "${#absent}", "0");
    one(state, "\"${absent:-\\\n}\"", "");
    one(state, "$\\\n{v}", "value");
    one(state, "${v\\\n}", "value");
    one(state, "${absent:\\\n-fall\\\nback}", "fallback");
    one(state, "${absent:-${other:-${v}}}", "value");
    one(state, "${absent:-${other:=nested}}", "nested");
    variable_is(state, "other", "nested");
    one(state, "${v:-${never:=wrong}}", "value");
    variable_is(state, "never", NULL);
    one(state, "${absent:+${never:=wrong}}", "");
    variable_is(state, "never", NULL);
    one(state, "${v:-${never:?wrong}}", "value");
    one(state, "${v:+${empty:-chosen}}", "chosen");
    STATE(csh_state_set_variable(state, "path", "abcabc"));
    one(state, "${path#a*c}", "abc");
    one(state, "${path##a*c}", "");
    one(state, "${path%a*c}", "abc");
    one(state, "${path%%a*c}", "");
    one(state, "${path#[ab]?}", "cabc");
    one(state, "${path%z*}", "abcabc");
    one(state, "${path#\"a*c\"}", "abcabc");
    one(state, "${path#'a*c'}", "abcabc");
    one(state, "${path#\\a\\*c}", "abcabc");
    STATE(csh_state_set_variable(state, "pattern", "a*c"));
    one(state, "${path#$pattern}", "abc");
    one(state, "${path#\"$pattern\"}", "abcabc");
    one(state, "\"${path#a*c}\"", "abc");
    one(state, "${path#${absent:-a*c}}", "abc");
    STATE(csh_state_update_options(state, CSH_OPT_ALLEXPORT, 0));
    one(state, "${exported:=value}", "value");
    {
        struct csh_variable_view view;
        STATE(csh_state_get_variable(state, "exported", &view));
        CHECK(view.attributes == CSH_VAR_EXPORT);
    }
    csh_state_destroy(state);
}

static void span_values(const struct csh_expansion *out,
    enum csh_expand_origin origin, enum csh_quote quote, int split, int empty)
{
    size_t field, index, found = 0;
    for (field = 0; field < out->field_count; ++field) {
        for (index = 0; index < out->fields[field].span_count; ++index) {
            const struct csh_expand_span *span = &out->fields[field].spans[index];
            if (span->origin == origin) {
                CHECK(span->quote == quote && span->split == split);
                if (empty)
                    CHECK(span->length == 0 && span->keep_empty);
                ++found;
            }
        }
    }
    CHECK(found != 0);
}

static void provenance(void)
{
    struct csh_state *state = new_state();
    struct csh_expansion out;
    struct csh_expand_options options = {CSH_EXPAND_ASSIGNMENT, NULL, NULL};
    STATE(csh_state_set_variable(state, "v", "a * b"));
    out = expand(state, "pre$v/post", NULL);
    field_is(&out, 0, "prea * b/post");
    span_values(&out, CSH_EXPAND_PARAMETER, CSH_QUOTE_NONE, 1, 0);
    span_values(&out, CSH_EXPAND_LITERAL, CSH_QUOTE_NONE, 0, 0);
    csh_expansion_destroy(&out);
    out = expand(state, "\"$v\"", NULL);
    field_is(&out, 0, "a * b");
    span_values(&out, CSH_EXPAND_PARAMETER, CSH_QUOTE_DOUBLE, 0, 0);
    csh_expansion_destroy(&out);
    out = expand(state, "\"$absent\"", NULL);
    field_is(&out, 0, "");
    span_values(&out, CSH_EXPAND_PARAMETER, CSH_QUOTE_DOUBLE, 0, 1);
    csh_expansion_destroy(&out);
    out = expand(state, "''", NULL);
    field_is(&out, 0, "");
    span_values(&out, CSH_EXPAND_LITERAL, CSH_QUOTE_SINGLE, 0, 1);
    csh_expansion_destroy(&out);
    out = expand(state, "\"\"", NULL);
    field_is(&out, 0, "");
    span_values(&out, CSH_EXPAND_LITERAL, CSH_QUOTE_DOUBLE, 0, 1);
    csh_expansion_destroy(&out);
    out = expand(state, "\\*", NULL);
    field_is(&out, 0, "*");
    span_values(&out, CSH_EXPAND_LITERAL, CSH_QUOTE_SINGLE, 0, 0);
    csh_expansion_destroy(&out);
    out = expand(state, "${absent:-a*b}", NULL);
    field_is(&out, 0, "a*b");
    span_values(&out, CSH_EXPAND_PARAMETER, CSH_QUOTE_NONE, 1, 0);
    csh_expansion_destroy(&out);
    out = expand(state, "${assigned:=a\\ b}", NULL);
    field_is(&out, 0, "a b");
    span_values(&out, CSH_EXPAND_PARAMETER, CSH_QUOTE_NONE, 1, 0);
    variable_is(state, "assigned", "a b");
    csh_expansion_destroy(&out);
    out = expand(state, "${absent:-a\\ b}", NULL);
    field_is(&out, 0, "a b");
    {
        size_t index;
        int escaped_space = 0;
        for (index = 0; index < out.fields[0].span_count; ++index) {
            const struct csh_expand_span *span = &out.fields[0].spans[index];
            if (span->length == 1 && span->text[0] == ' ') {
                CHECK(span->quote == CSH_QUOTE_SINGLE && !span->split);
                escaped_space = 1;
            }
        }
        CHECK(escaped_space);
    }
    csh_expansion_destroy(&out);
    out = expand(state, "$v", &options);
    field_is(&out, 0, "a * b");
    span_values(&out, CSH_EXPAND_PARAMETER, CSH_QUOTE_NONE, 0, 0);
    csh_expansion_destroy(&out);
    options.context = CSH_EXPAND_PATTERN;
    out = expand(state, "$v", &options);
    field_is(&out, 0, "a * b");
    span_values(&out, CSH_EXPAND_PARAMETER, CSH_QUOTE_NONE, 0, 0);
    csh_expansion_destroy(&out);
    out = expand(state, "$v", NULL);
    STATE(csh_state_set_variable(state, "v", "changed"));
    csh_state_destroy(state);
    field_is(&out, 0, "a * b");
    csh_expansion_destroy(&out);
}

static void positionals(void)
{
    const char *args[] = {"one", "", "three words", "4", "5", "6", "7", "8", "9", "ten"};
    struct csh_state *state = new_state();
    struct csh_expansion out;
    struct csh_state_info info;
    struct csh_expand_options options = {CSH_EXPAND_ASSIGNMENT, NULL, NULL};
    char number[64];
    STATE(csh_state_set_parameters(state, 3, args));
    out = expand(state, "\"$@\"", NULL);
    CHECK(out.field_count == 3);
    field_is(&out, 0, "one");
    field_is(&out, 1, "");
    field_is(&out, 2, "three words");
    CHECK(out.fields[1].span_count != 0);
    CHECK(out.fields[1].spans[0].keep_empty);
    span_values(&out, CSH_EXPAND_PARAMETER, CSH_QUOTE_DOUBLE, 0, 0);
    csh_expansion_destroy(&out);
    out = expand(state, "$@", NULL);
    CHECK(out.field_count == 3);
    field_is(&out, 0, "one");
    field_is(&out, 1, "");
    field_is(&out, 2, "three words");
    span_values(&out, CSH_EXPAND_PARAMETER, CSH_QUOTE_NONE, 1, 0);
    CHECK(!out.fields[1].spans[0].keep_empty);
    csh_expansion_destroy(&out);
    out = expand(state, "\"$@$@\"", NULL);
    CHECK(out.field_count == 5);
    field_is(&out, 0, "one");
    field_is(&out, 1, "");
    field_is(&out, 2, "three wordsone");
    field_is(&out, 3, "");
    field_is(&out, 4, "three words");
    csh_expansion_destroy(&out);
    out = expand(state, "pre\"$@\"post", NULL);
    CHECK(out.field_count == 3);
    field_is(&out, 0, "preone");
    field_is(&out, 1, "");
    field_is(&out, 2, "three wordspost");
    csh_expansion_destroy(&out);
    one(state, "\"$*\"", "one  three words");
    STATE(csh_state_set_variable(state, "IFS", ":;"));
    one(state, "\"$*\"", "one::three words");
    out = expand(state, "$@", &options);
    CHECK(out.field_count == 1);
    field_is(&out, 0, "one::three words");
    span_values(&out, CSH_EXPAND_PARAMETER, CSH_QUOTE_NONE, 0, 0);
    csh_expansion_destroy(&out);
    options.context = CSH_EXPAND_PATTERN;
    out = expand(state, "$@", &options);
    CHECK(out.field_count == 1);
    field_is(&out, 0, "one::three words");
    csh_expansion_destroy(&out);
    STATE(csh_state_set_variable(state, "IFS", ""));
    one(state, "\"$*\"", "onethree words");
    STATE(csh_state_unset_variable(state, "IFS"));
    one(state, "$#", "3");
    one(state, "${##}", "1");
    one(state, "$0", "fixture-zero");
    one(state, "${1}", "one");
    one(state, "${9:-absent}", "absent");
    STATE(csh_state_set_parameters(state, 10, args));
    one(state, "${##}", "2");
    one(state, "${#-word}", "10");
    one(state, "${#?word}", "10");
    one(state, "${#+word}", "word");
    one(state, "${10}", "ten");
    one(state, "$10", "one0");
    one(state, "${#10}", "3");
    STATE(csh_state_set_status(state, 137));
    STATE(csh_state_set_background(state, 12345));
    one(state, "$?", "137");
    one(state, "${#?}", "3");
    one(state, "$!", "12345");
    STATE(csh_state_get_info(state, &info));
    snprintf(number, sizeof(number), "%ld", (long)info.shell_pid);
    one(state, "$$", number);
    STATE(csh_state_update_options(state, CSH_OPT_NOGLOB | CSH_OPT_NOUNSET, 0));
    out = expand(state, "$-", NULL);
    CHECK(out.field_count == 1);
    CHECK(out.fields[0].span_count == 1);
    CHECK(strchr(out.fields[0].spans[0].text, 'f') != NULL);
    CHECK(strchr(out.fields[0].spans[0].text, 'u') != NULL);
    csh_expansion_destroy(&out);
    STATE(csh_state_update_options(state, 0, CSH_OPT_NOUNSET));
    STATE(csh_state_set_parameters(state, 0, NULL));
    out = expand(state, "\"$@\"", NULL);
    CHECK(out.field_count == 0);
    csh_expansion_destroy(&out);
    one(state, "pre\"$@\"post", "prepost");
    one(state, "\"$*\"", "");
    one(state, "$#", "0");
    STATE(csh_state_set_background(state, 0));
    one(state, "$!", "");
    csh_state_destroy(state);
}

static void tilde_and_quotes(void)
{
    struct csh_state *state = new_state();
    struct csh_expansion out;
    struct csh_expand_options options = {CSH_EXPAND_ASSIGNMENT, NULL, NULL};
    struct csh_expand_error error;
    STATE(csh_state_set_variable(state, "HOME", "/tmp/home space"));
    one(state, "~/file", "/tmp/home space/file");
    one(state, "~\\\n/file", "/tmp/home space/file");
    one(state, "'~'/file", "~/file");
    one(state, "\\~/file", "~/file");
    one(state, "a:~/file", "a:~/file");
    one(state, "~$HOME", "~/tmp/home space");
    one(state, "${u:=a:~}", "a:~");
    variable_is(state, "u", "a:~");
    STATE(csh_state_unset_variable(state, "u"));
    one(state, "${u:-a:~}", "a:~");
    error = failure(state, "${u:?a:~}", NULL, CSH_EXPAND_UNSET);
    CHECK(strcmp(error.message, "a:~") == 0);
    out = expand(state, "${u:-a:~}", &options);
    field_is(&out, 0, "a:~");
    csh_expansion_destroy(&out);
    out = expand(state, "${u:=a:~}", &options);
    field_is(&out, 0, "a:~");
    variable_is(state, "u", "a:~");
    csh_expansion_destroy(&out);
    STATE(csh_state_unset_variable(state, "u"));
    error = failure(state, "${u:?a:~}", &options, CSH_EXPAND_UNSET);
    CHECK(strcmp(error.message, "a:~") == 0);
    out = expand(state, "~/a:~/b", &options);
    field_is(&out, 0, "/tmp/home space/a:/tmp/home space/b");
    span_values(&out, CSH_EXPAND_TILDE, CSH_QUOTE_SINGLE, 0, 0);
    csh_expansion_destroy(&out);
    out = expand(state, "~\\\n/a:~\\\n/b", &options);
    field_is(&out, 0, "/tmp/home space/a:/tmp/home space/b");
    csh_expansion_destroy(&out);
    out = expand(state, "name=~/a", &options);
    field_is(&out, 0, "name=~/a");
    csh_expansion_destroy(&out);
    STATE(csh_state_unset_variable(state, "HOME"));
    one(state, "~/file", "~/file");
    STATE(csh_state_set_variable(state, "HOME", ""));
    one(state, "~/file", "/file");
    one(state, "$'\\a\\b\\e\\f\\n\\r\\t\\v'", "\a\b\033\f\n\r\t\v");
    one(state, "$'\\\\\\\"\\\''", "\\\"'");
    one(state, "$'\\101\\x42\\1034'", "ABC4");
    one(state, "$'\\x4142'", "A42");
    one(state, "$'\\cA\\c?'", "\001\177");
    one(state, "$'\\z'", "\\z");
    one(state, "$'left\\0discarded'right", "leftright");
    one(state, "$'\\0discarded'$'kept'", "kept");
    out = expand(state, "$''", NULL);
    field_is(&out, 0, "");
    CHECK(out.fields[0].span_count != 0);
    CHECK(out.fields[0].spans[0].quote != CSH_QUOTE_NONE);
    CHECK(out.fields[0].spans[0].keep_empty && !out.fields[0].spans[0].split);
    csh_expansion_destroy(&out);
    one(state, "'literal $v'\" and \\$v\"", "literal $v and $v");
    csh_state_destroy(state);
}

static void multibyte(void)
{
    static const char *locales[] = {"en_US.UTF-8", "C.UTF-8", "UTF-8"};
    const char *args[] = {"left", "right"};
    struct csh_state *state;
    size_t index;
    for (index = 0; index < sizeof(locales) / sizeof(locales[0]); ++index)
        if (setlocale(LC_CTYPE, locales[index]) != NULL)
            break;
    if (index == sizeof(locales) / sizeof(locales[0])) {
        puts("SKIP: UTF-8 locale unavailable for multibyte expansion checks");
        return;
    }
    state = new_state();
    STATE(csh_state_set_variable(state, "v", "\303\251\347\214\253a"));
    one(state, "${#v}", "3");
    one(state, "${v#?}", "\347\214\253a");
    one(state, "${v%?}", "\303\251\347\214\253");
    one(state, "${v#[\303\251]}", "\347\214\253a");
    STATE(csh_state_set_parameters(state, 2, args));
    STATE(csh_state_set_variable(state, "IFS", "\303\251,"));
    one(state, "\"$*\"", "left\303\251right");
    csh_state_destroy(state);
    CHECK(setlocale(LC_CTYPE, "C") != NULL);
}

struct callback_info { size_t calls; int fail; int mutate; };

static enum csh_expand_result substitute(void *user, struct csh_state *state,
    const struct csh_token *token, size_t fragment, const char **bytes,
    size_t *length, struct csh_expand_error *error)
{
    struct callback_info *info = user;
    CHECK(fragment < token->fragment_count);
    CHECK(token->fragments[fragment].kind == CSH_FRAGMENT_COMMAND ||
        token->fragments[fragment].kind == CSH_FRAGMENT_BACKQUOTE);
    ++info->calls;
    if (info->mutate) {
        STATE(csh_state_set_variable(state, "callback", "changed"));
        STATE(csh_state_set_status(state, 99));
        STATE(csh_state_set_background(state, 5678));
        STATE(csh_state_update_options(state, CSH_OPT_XTRACE, 0));
    }
    if (info->fail) {
        error->code = CSH_EXPAND_INVALID;
        snprintf(error->message, sizeof(error->message), "fixture callback failure");
        return CSH_EXPAND_INVALID;
    }
    *bytes = "callback * bytes";
    *length = strlen(*bytes);
    return CSH_EXPAND_OK;
}

static void substitution_and_failures(void)
{
    struct csh_state *state = new_state();
    struct callback_info info = {0};
    struct csh_expand_options options = {CSH_EXPAND_ARGUMENT, substitute, &info};
    struct csh_expansion out;
    struct csh_expand_error error;
    struct csh_state_info before, after;
    STATE(csh_state_set_variable(state, "v", "set"));
    out = expand(state, "${v:-$(ignored)}", &options);
    field_is(&out, 0, "set");
    CHECK(info.calls == 0);
    csh_expansion_destroy(&out);
    out = expand(state, "${absent:+`ignored`}", &options);
    field_is(&out, 0, "");
    CHECK(info.calls == 0);
    csh_expansion_destroy(&out);
    one(state, "${v:-$(ignored)}", "set");
    out = expand(state, "${absent:-$(selected)}", &options);
    field_is(&out, 0, "callback * bytes");
    CHECK(info.calls == 1);
    csh_expansion_destroy(&out);
    out = expand(state, "\"`selected`\"", &options);
    field_is(&out, 0, "callback * bytes");
    span_values(&out, CSH_EXPAND_SUBSTITUTION, CSH_QUOTE_DOUBLE, 0, 0);
    CHECK(info.calls == 2);
    csh_expansion_destroy(&out);
    error = failure(state, "prefix$(selected)", NULL, CSH_EXPAND_DEFERRED);
    CHECK(error.fragment != CSH_FRAGMENT_ROOT);
    failure(state, "`selected`", NULL, CSH_EXPAND_DEFERRED);
    failure(state, "${new:=changed}$(selected)", NULL, CSH_EXPAND_DEFERRED);
    variable_is(state, "new", NULL);
    STATE(csh_state_update_attributes(state, "locked", CSH_VAR_READONLY, 0));
    failure(state, "${locked:=no}", NULL, CSH_EXPAND_READONLY);
    variable_is(state, "locked", NULL);
    failure(state, "${new:=yes}${locked:=no}", NULL, CSH_EXPAND_READONLY);
    variable_is(state, "new", NULL);
    failure(state, "${new:=yes}${absent:?stop}", NULL, CSH_EXPAND_UNSET);
    variable_is(state, "new", NULL);
    STATE(csh_state_get_info(state, &before));
    info.mutate = 1;
    info.fail = 1;
    failure(state, "${new:=yes}$(selected)", &options, CSH_EXPAND_INVALID);
    variable_is(state, "new", NULL);
    variable_is(state, "callback", NULL);
    STATE(csh_state_get_info(state, &after));
    CHECK(before.last_status == after.last_status && before.options == after.options &&
        before.background_pid == after.background_pid);
    info.fail = 0;
    failure(state, "$(selected)${absent:?stop}", &options, CSH_EXPAND_UNSET);
    variable_is(state, "callback", NULL);
    failure(state, "${}", NULL, CSH_EXPAND_INVALID);
    failure(state, "${v:invalid}", NULL, CSH_EXPAND_INVALID);
    failure(state, "${1:=bad}", NULL, CSH_EXPAND_INVALID);
    failure(state, "${@:-bad}", NULL, CSH_EXPAND_INVALID);
    STATE(csh_state_update_options(state, CSH_OPT_NOUNSET, 0));
    failure(state, "$absent", NULL, CSH_EXPAND_UNSET);
    one(state, "${absent:-fallback}", "fallback");
    csh_state_destroy(state);
}

struct borrowed_callback {
    char buffer[32];
    size_t calls;
    int mode;
};

static enum csh_expand_result borrowed_substitute(void *user,
    struct csh_state *state, const struct csh_token *token, size_t fragment,
    const char **bytes, size_t *length, struct csh_expand_error *error)
{
    struct borrowed_callback *info = user;
    (void)state;
    (void)token;
    (void)fragment;
    (void)error;
    ++info->calls;
    if (info->mode == 1) {
        *bytes = NULL;
        *length = 1;
    } else if (info->mode == 2) {
        *bytes = "a\0b";
        *length = 3;
    } else if (info->mode == 3) {
        *bytes = NULL;
        *length = 0;
    } else {
        snprintf(info->buffer, sizeof(info->buffer), "value-%zu", info->calls);
        *bytes = info->buffer;
        *length = strlen(*bytes);
    }
    return CSH_EXPAND_OK;
}

static void callback_ownership(void)
{
    struct csh_state *state = new_state();
    struct borrowed_callback info = {{0}, 0, 0};
    struct csh_expand_options options = {CSH_EXPAND_ARGUMENT, borrowed_substitute, &info};
    struct csh_expansion out = expand(state, "$(first)$(second)", &options);
    CHECK(info.calls == 2);
    memset(info.buffer, 'x', sizeof(info.buffer));
    field_is(&out, 0, "value-1value-2");
    csh_expansion_destroy(&out);
    info.mode = 1;
    failure(state, "${new:=set}$(invalid)", &options, CSH_EXPAND_INVALID);
    variable_is(state, "new", NULL);
    info.mode = 2;
    failure(state, "${new:=set}$(invalid)", &options, CSH_EXPAND_INVALID);
    variable_is(state, "new", NULL);
    info.mode = 3;
    out = expand(state, "\"$(empty)\"", &options);
    CHECK(out.field_count == 1);
    field_is(&out, 0, "");
    span_values(&out, CSH_EXPAND_SUBSTITUTION, CSH_QUOTE_DOUBLE, 0, 1);
    csh_expansion_destroy(&out);
    csh_state_destroy(state);
}

static void arithmetic(void)
{
    struct csh_state *state = new_state();
    struct csh_expansion out;
    one(state, "$((2 + 3 * 4))", "14");
    one(state, "$\\\n(\\\n(2 + 3)\\\n)", "5");
    one(state, "$(((2 + 3) * 4))", "20");
    one(state, "$((010 + 0x10))", "24");
    one(state, "$((~0 & 15))", "15");
    one(state, "$((1 << 4 | 3))", "19");
    one(state, "$((9 > 2 && 4 != 3))", "1");
    one(state, "$((0 && 1 / 0))", "0");
    one(state, "$((1 || 1 / 0))", "1");
    one(state, "$((1 ? 7 : 1 / 0))", "7");
    STATE(csh_state_set_variable(state, "x", "5"));
    one(state, "$((x += 3))", "8");
    variable_is(state, "x", "8");
    one(state, "$((x = 2 + 9))", "11");
    variable_is(state, "x", "11");
    STATE(csh_state_set_variable(state, "locked", "1"));
    STATE(csh_state_update_attributes(state, "locked", CSH_VAR_READONLY, 0));
    failure(state, "$((locked = 2))", NULL, CSH_EXPAND_READONLY);
    variable_is(state, "locked", "1");
    one(state, "$((0 && (x = 99)))", "0");
    variable_is(state, "x", "11");
    one(state, "$((1 ? x : (x = 99)))", "11");
    variable_is(state, "x", "11");
    one(state, "$(( ${absent:-3} + $x ))", "14");
    out = expand(state, "$((2 + 3))", NULL);
    span_values(&out, CSH_EXPAND_ARITHMETIC, CSH_QUOTE_NONE, 1, 0);
    csh_expansion_destroy(&out);
    out = expand(state, "\"$((2 + 3))\"", NULL);
    span_values(&out, CSH_EXPAND_ARITHMETIC, CSH_QUOTE_DOUBLE, 0, 0);
    csh_expansion_destroy(&out);
    failure(state, "$((1 / 0))", NULL, CSH_EXPAND_ARITHMETIC_ERROR);
    failure(state, "$((1 % 0))", NULL, CSH_EXPAND_ARITHMETIC_ERROR);
    failure(state, "$((1 << -1))", NULL, CSH_EXPAND_ARITHMETIC_ERROR);
    failure(state, "$((1 + ))", NULL, CSH_EXPAND_ARITHMETIC_ERROR);
    failure(state, "$((9223372036854775807 + 1))", NULL, CSH_EXPAND_ARITHMETIC_ERROR);
    failure(state, "${new:=yes}$((1 / 0))", NULL, CSH_EXPAND_ARITHMETIC_ERROR);
    variable_is(state, "new", NULL);
    failure(state, "$((x = 7))${absent:?stop}", NULL, CSH_EXPAND_UNSET);
    variable_is(state, "x", "11");
    csh_state_destroy(state);
}

static void invalid_api(void)
{
    struct csh_state *state = new_state();
    struct csh_token token = word("value");
    struct csh_expansion out = {0};
    struct csh_expand_error error;
    struct csh_expand_options options = {(enum csh_expand_context)999, NULL, NULL};
    CHECK(csh_expand_word(NULL, &token, NULL, &out, &error) == CSH_EXPAND_INVALID);
    CHECK(out.fields == NULL && out.field_count == 0);
    CHECK(csh_expand_word(state, NULL, NULL, &out, &error) == CSH_EXPAND_INVALID);
    CHECK(csh_expand_word(state, &token, NULL, NULL, &error) == CSH_EXPAND_INVALID);
    CHECK(csh_expand_word(state, &token, &options, &out, &error) == CSH_EXPAND_INVALID);
    token.kind = CSH_TOKEN_PIPE;
    CHECK(csh_expand_word(state, &token, NULL, &out, &error) == CSH_EXPAND_INVALID);
    token.kind = CSH_TOKEN_WORD;
    token.fragments[0].end = token.length + 1;
    CHECK(csh_expand_word(state, &token, NULL, &out, &error) == CSH_EXPAND_INVALID);
    csh_token_destroy(&token);
    {
        unsigned char raw[] = {'\\', '\n', '\\', '\n', ')'};
        struct csh_fragment fragment = {0};
        struct csh_token malformed = {0};
        fragment.kind = CSH_FRAGMENT_ARITHMETIC;
        fragment.parent = CSH_FRAGMENT_ROOT;
        fragment.end = sizeof(raw);
        malformed.kind = CSH_TOKEN_WORD;
        malformed.raw = raw;
        malformed.length = sizeof(raw);
        malformed.fragments = &fragment;
        malformed.fragment_count = 1;
        CHECK(csh_expand_word(state, &malformed, NULL, &out, &error) ==
            CSH_EXPAND_INVALID);
        CHECK(out.fields == NULL && out.field_count == 0);
    }
    csh_expansion_destroy(NULL);
    csh_state_destroy(state);
}

static void nesting_limit(void)
{
    struct csh_state *state = new_state();
    char source[4096];
    size_t index, length = 0;
    for (index = 0; index < 129; ++index) {
        memcpy(source + length, "${absent:-", sizeof("${absent:-") - 1);
        length += sizeof("${absent:-") - 1;
    }
    source[length++] = 'x';
    for (index = 0; index < 129; ++index)
        source[length++] = '}';
    source[length] = '\0';
    failure(state, source, NULL, CSH_EXPAND_LIMIT);
    csh_state_destroy(state);
}

int main(void)
{
    parameters();
    provenance();
    positionals();
    tilde_and_quotes();
    multibyte();
    substitution_and_failures();
    callback_ownership();
    arithmetic();
    invalid_api();
    nesting_limit();
    puts("PASS: value expansions, provenance, lazy operands, callbacks, arithmetic, ownership, rollback");
    return 0;
}
