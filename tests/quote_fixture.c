#include "cshell/quote.h"

/* These checks remain active for release builds with caller-supplied flags. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void check_bytes(const unsigned char *input, size_t input_length,
    const unsigned char *expected, size_t expected_length)
{
    char *output = NULL;
    size_t output_length = SIZE_MAX;

    assert(csh_quote_decode(input, input_length, &output, &output_length) ==
        CSH_QUOTE_OK);
    assert(output != NULL);
    assert(output_length == expected_length);
    assert(memcmp(output, expected, expected_length) == 0);
    assert(output[output_length] == '\0');
    assert(strlen(output) == output_length);
    free(output);
}

static void check(const char *input, const char *expected)
{
    check_bytes((const unsigned char *)input, strlen(input),
        (const unsigned char *)expected, strlen(expected));
}

static void controls(void)
{
    unsigned int letter;
    char input[] = {'\\', 'c', 'A', '\0'};
    unsigned char expected;

    for (letter = 0; letter < 26; ++letter) {
        input[2] = (char)('A' + letter);
        expected = (unsigned char)(letter + 1);
        check_bytes((const unsigned char *)input, 3, &expected, 1);
        input[2] = (char)('a' + letter);
        check_bytes((const unsigned char *)input, 3, &expected, 1);
    }
    check("\\c[\\c\\\\\\c]\\c^\\c_\\c?", "\033\034\035\036\037\177");
    check("\\c@\\c1\\c!", "\\c@\\c1\\c!");
    check("\\c", "\\c");
    check("\\c\\", "\\c\\");
    check("\\c\\x", "\\c\\x");
}

static void invalid_arguments(void)
{
    char sentinel[] = "unchanged";
    char *output = sentinel;
    size_t output_length = 12;
    const unsigned char nul[] = {'a', '\0', 'b'};

    assert(csh_quote_decode(NULL, 1, &output, &output_length) ==
        CSH_QUOTE_INVALID);
    assert(output == NULL && output_length == 0);
    output = sentinel;
    assert(csh_quote_decode((const unsigned char *)"", 0, &output, NULL) ==
        CSH_QUOTE_INVALID);
    assert(output == NULL);
    output_length = 12;
    assert(csh_quote_decode((const unsigned char *)"", 0, NULL, &output_length) ==
        CSH_QUOTE_INVALID);
    assert(output_length == 0);
    output = sentinel;
    output_length = 12;
    assert(csh_quote_decode(nul, sizeof(nul), &output, &output_length) ==
        CSH_QUOTE_INVALID);
    assert(output == NULL && output_length == 0);
    output = sentinel;
    output_length = 12;
    assert(csh_quote_decode((const unsigned char *)"", SIZE_MAX, &output,
        &output_length) == CSH_QUOTE_NOMEM);
    assert(output == NULL && output_length == 0);
}

static void ownership(void)
{
    unsigned char input[] = {'a', '\\', 'n', 'b'};
    char *output;
    size_t output_length;

    assert(csh_quote_decode(input, sizeof(input), &output, &output_length) ==
        CSH_QUOTE_OK);
    memset(input, '?', sizeof(input));
    assert(output_length == 3 && memcmp(output, "a\nb", 4) == 0);
    free(output);
}

int main(void)
{
    check("", "");
    check_bytes(NULL, 0, (const unsigned char *)"", 0);
    check("plain ' \" text", "plain ' \" text");
    check("\\\"\\'\\\\\\a\\b\\e\\f\\n\\r\\t\\v",
        "\"'\\\a\b\033\f\n\r\t\v");
    check("\\1|\\12|\\123|\\1234|\\7|\\77|\\777|\\401",
        "\1|\12|\123|\1234|\7|\77|\377|\1");
    check("\\x1|\\xA|\\xaf|\\xAF|\\x414|\\xg|\\x",
        "\1|\12|\257|\257|A4|\\xg|\\x");
    check("\\8\\9\\q\\E\\u0041\\$\\\nend\\",
        "\\8\\9\\q\\E\\u0041\\$\\\nend\\");
    check("$HOME ${x:=bad} $(exit 1) `exit 1` $((1 / 0))",
        "$HOME ${x:=bad} $(exit 1) `exit 1` $((1 / 0))");
    check("a\\0discard\\n", "a");
    check("a\\00discard", "a");
    check("a\\000discard", "a");
    check("a\\x0discard", "a\015iscard");
    check("a\\x00discard", "a");
    check("a\\400discard", "a");
    check("\\000discard", "");
    /* Regions remain independent after an earlier region's decoded NUL. */
    check("a\\0discard", "a");
    check("adjacent\\n", "adjacent\n");
    check("\303\251\\t\342\202\254", "\303\251\t\342\202\254");
    controls();
    invalid_arguments();
    ownership();
    puts("quote fixtures passed");
    return 0;
}
