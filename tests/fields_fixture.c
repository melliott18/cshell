/* Final argument inspection, independent of the replacement executor. */
#include "cshell/expand.h"

#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "fields fixture failed at line %d: %s\n", \
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
    invocation.arg0 = "fields-fixture";
    STATE(csh_state_create(&state, &invocation, NULL));
    return state;
}

static struct csh_token word(const char *source)
{
    struct csh_lexer *lexer = NULL;
    struct csh_token token = {0}, end = {0};
    struct csh_error error;
    CHECK(csh_lexer_create(&lexer, "fields-fixture", &error) == 0);
    CHECK(csh_lexer_feed(lexer, source, strlen(source), 1, &error) == 0);
    CHECK(csh_lexer_next(lexer, &token, &error) == CSH_LEX_TOKEN);
    CHECK(token.kind == CSH_TOKEN_WORD);
    CHECK(csh_lexer_next(lexer, &end, &error) == CSH_LEX_EOF);
    csh_lexer_destroy(lexer);
    return token;
}

/* Include every provenance member as well as bytes in the mutation check. */
static unsigned long fingerprint(const struct csh_expansion *expansion)
{
    unsigned long value = (unsigned long)expansion->field_count;
    size_t field, span, byte;
    value = value * 33 + (unsigned long)expansion->context;
    for (field = 0; field < expansion->field_count; ++field) {
        const struct csh_expand_field *item = &expansion->fields[field];
        value = value * 33 + (unsigned long)item->span_count;
        for (span = 0; span < item->span_count; ++span) {
            const struct csh_expand_span *part = &item->spans[span];
            value = value * 33 + (unsigned long)part->length;
            value = value * 33 + (unsigned long)part->quote;
            value = value * 33 + (unsigned long)part->origin;
            value = value * 33 + (unsigned long)part->split;
            value = value * 33 + (unsigned long)part->keep_empty;
            for (byte = 0; byte <= part->length; ++byte)
                value = value * 33 + (unsigned char)part->text[byte];
        }
    }
    return value;
}

static void emit(size_t count, char *const values[])
{
    size_t index;
    printf("%lu\n", (unsigned long)count);
    for (index = 0; index < count; ++index) {
        CHECK(values[index] != NULL);
        CHECK(fwrite(values[index], 1, strlen(values[index]) + 1, stdout) ==
            strlen(values[index]) + 1);
    }
}

static void arguments(int argc, char *argv[])
{
    struct csh_state *state = new_state();
    struct csh_expand_options options = {CSH_EXPAND_ARGUMENT, NULL, NULL};
    struct csh_expansion expansion = {0};
    struct csh_fields first = {0}, second = {0};
    struct csh_expand_error error;
    struct csh_token token;
    unsigned long before;
    size_t index;
    enum csh_expand_result result;
    CHECK(argc >= 9);
    if (strcmp(argv[2], "assignment") == 0)
        options.context = CSH_EXPAND_ASSIGNMENT;
    else if (strcmp(argv[2], "pattern") == 0)
        options.context = CSH_EXPAND_PATTERN;
    else
        CHECK(strcmp(argv[2], "argument") == 0);
    if (strcmp(argv[3], "1") == 0)
        STATE(csh_state_update_options(state, CSH_OPT_NOGLOB, 0));
    else
        CHECK(strcmp(argv[3], "0") == 0);
    if (strcmp(argv[4], "set") == 0)
        STATE(csh_state_set_variable(state, "IFS", argv[5]));
    else
        CHECK(strcmp(argv[4], "unset") == 0);
    STATE(csh_state_set_variable(state, "x", argv[6]));
    STATE(csh_state_set_variable(state, "y", argv[7]));
    STATE(csh_state_set_variable(state, "HOME", "home space/*"));
    STATE(csh_state_set_parameters(state, (size_t)(argc - 9),
        (const char *const *)(argv + 9)));
    token = word(argv[8]);
    CHECK(csh_expand_word(state, &token, &options, &expansion, &error) ==
        CSH_EXPAND_OK);
    csh_token_destroy(&token);
    CHECK(expansion.context == options.context);
    before = fingerprint(&expansion);
    result = csh_expand_fields(state, &expansion, NULL, &first, &error);
    if (result != CSH_EXPAND_OK)
        fprintf(stderr, "field expansion failed: %d: %s\n", result, error.message);
    CHECK(result == CSH_EXPAND_OK);
    CHECK(fingerprint(&expansion) == before);
    CHECK(first.values == NULL || first.values[first.count] == NULL);
    CHECK(csh_expand_fields(state, &expansion, NULL, &second, &error) ==
        CSH_EXPAND_OK);
    CHECK(fingerprint(&expansion) == before);
    CHECK(first.count == second.count);
    CHECK(second.values == NULL || second.values[second.count] == NULL);
    for (index = 0; index < first.count; ++index) {
        CHECK(first.values[index] != second.values[index]);
        CHECK(strcmp(first.values[index], second.values[index]) == 0);
    }
    csh_fields_destroy(&first);
    CHECK(first.values == NULL && first.count == 0);
    csh_fields_destroy(&first);
    CHECK(fingerprint(&expansion) == before);
    csh_expansion_destroy(&expansion);
    csh_state_destroy(state);
    emit(second.count, second.values);
    csh_fields_destroy(&second);
}

static void invalid_api(void)
{
    struct csh_state *state = new_state();
    struct csh_expansion expansion = {0};
    struct csh_fields out = {0};
    struct csh_expand_error error;
    CHECK(csh_expand_fields(NULL, &expansion, NULL, &out, &error) ==
        CSH_EXPAND_INVALID);
    CHECK(out.values == NULL && out.count == 0);
    CHECK(error.code == CSH_EXPAND_INVALID && error.message[0] != '\0');
    CHECK(csh_expand_fields(state, NULL, NULL, &out, &error) ==
        CSH_EXPAND_INVALID);
    CHECK(out.values == NULL && out.count == 0);
    CHECK(csh_expand_fields(state, &expansion, NULL, NULL, &error) ==
        CSH_EXPAND_INVALID);
    expansion.context = (enum csh_expand_context)999;
    CHECK(csh_expand_fields(state, &expansion, NULL, &out, &error) ==
        CSH_EXPAND_INVALID);
    CHECK(out.values == NULL && out.count == 0);
    expansion.context = CSH_EXPAND_ARGUMENT;
    expansion.field_count = 1;
    CHECK(csh_expand_fields(state, &expansion, NULL, &out, &error) ==
        CSH_EXPAND_INVALID);
    CHECK(out.values == NULL && out.count == 0);
    expansion.field_count = 0;
    CHECK(csh_expand_fields(state, &expansion, NULL, &out, NULL) == CSH_EXPAND_OK);
    CHECK(out.count == 0);
    csh_fields_destroy(&out);
    csh_fields_destroy(NULL);
    csh_state_destroy(state);
    puts("PASS: final-field invalid API and cleanup");
}

static void multibyte(void)
{
    const char *const locales[] = {"C.UTF-8", "en_US.UTF-8", "UTF-8"};
    struct csh_state *state;
    char first[] = "a\xc3", second[] = "\xa9" "b", complete[] = "a\xc3\xa9" "b";
    struct csh_expand_span spans[] = {
        {first, 2, CSH_QUOTE_NONE, CSH_EXPAND_PARAMETER, 1, 0},
        {second, 2, CSH_QUOTE_NONE, CSH_EXPAND_PARAMETER, 1, 0}
    };
    struct csh_expand_field field = {spans, 2};
    struct csh_expansion expansion = {&field, 1, CSH_EXPAND_ARGUMENT};
    struct csh_fields out = {0};
    struct csh_expand_error error;
    size_t index;
    for (index = 0; index < sizeof(locales) / sizeof(locales[0]); ++index)
        if (setlocale(LC_CTYPE, locales[index]) != NULL)
            break;
    if (index == sizeof(locales) / sizeof(locales[0])) {
        puts("SKIP: multibyte IFS needs an installed UTF-8 locale");
        return;
    }
    state = new_state();
    STATE(csh_state_set_variable(state, "IFS", "\xc3\xa9"));
    /* Issue 8 prevents constructing one IFS character from multiple expansions. */
    CHECK(csh_expand_fields(state, &expansion, NULL, &out, &error) == CSH_EXPAND_OK);
    CHECK(out.count == 1 && strcmp(out.values[0], complete) == 0);
    csh_fields_destroy(&out);
    spans[0].text = complete;
    spans[0].length = 4;
    field.span_count = 1;
    CHECK(csh_expand_fields(state, &expansion, NULL, &out, &error) == CSH_EXPAND_OK);
    CHECK(out.count == 2 && strcmp(out.values[0], "a") == 0 &&
        strcmp(out.values[1], "b") == 0);
    csh_fields_destroy(&out);
    csh_state_destroy(state);
    puts("PASS: multibyte IFS respects expansion boundaries");
}

int main(int argc, char *argv[])
{
    CHECK(setlocale(LC_ALL, "") != NULL);
    CHECK(argc >= 2);
    if (strcmp(argv[1], "expand") == 0)
        arguments(argc, argv);
    else if (strcmp(argv[1], "inspect") == 0)
        emit((size_t)(argc - 2), argv + 2);
    else if (strcmp(argv[1], "invalid") == 0)
        invalid_api();
    else if (strcmp(argv[1], "multibyte") == 0)
        multibyte();
    else
        CHECK(0);
    return 0;
}
