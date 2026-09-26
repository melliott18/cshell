#include "cshell/character.h"
#include "cshell/lexer.h"

#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void require(int ok, const char *message)
{
    if (!ok) { fprintf(stderr, "%s\n", message); exit(1); }
}

int main(int argc, char **argv)
{
    const unsigned char tails[] = "\\`|[]{}";
    size_t i, split, variant;
    const char *prefixes[] = {"", "\\", "\"", "'", "$'", "$"};
    const char *suffixes[] = {"", "", "\"", "'", "'", ""};
    unsigned char text[8];
    if (argc != 3 || !setlocale(LC_ALL, argv[1])) return 77;
    text[0] = (unsigned char)strtoul(argv[2], NULL, 16);
    for (i = 0; i < sizeof(tails) - 1; ++i) {
        text[1] = tails[i];
        if (csh_character_length(text, 2, 0, 1) != 2) return 77;
    }
    require(csh_character_startup() == 0, "startup snapshot");
    require(setlocale(LC_ALL, "C") != NULL, "set C locale");
    for (i = 0; i < sizeof(tails) - 1; ++i) {
        text[1] = tails[i]; text[2] = '\n';
        require(csh_character_length(text, 2, 1, 1) == 2, "fixed startup decoder");
        require(csh_character_length(text, 2, 0, 1) == 1, "current runtime decoder");
        require(csh_character_length(text, 1, 1, 0) == 0, "incomplete character");
        require(csh_character_length(text, 1, 1, 1) == 1, "final incomplete byte fallback");
        for (variant = 0; variant < sizeof(prefixes) / sizeof(prefixes[0]); ++variant) {
            unsigned char source[16];
            size_t length = strlen(prefixes[variant]);
            memcpy(source, prefixes[variant], length);
            memcpy(source + length, text, 2);
            length += 2;
            memcpy(source + length, suffixes[variant], strlen(suffixes[variant]));
            length += strlen(suffixes[variant]);
            source[length++] = '\n';
            for (split = 0; split <= length; ++split) {
                struct csh_lexer *lexer = NULL;
                struct csh_token token = {0};
                struct csh_error error;
                enum csh_lex_result result;
                require(csh_lexer_create(&lexer, "split", &error) == 0, "create lexer");
                require(csh_lexer_feed(lexer, source, split, 0, &error) == 0, "first feed");
                result = csh_lexer_next(lexer, &token, &error);
                if (result == CSH_LEX_MORE) {
                    require(csh_lexer_feed(lexer, source + split, length - split, 1, &error) == 0, "second feed");
                    result = csh_lexer_next(lexer, &token, &error);
                }
                require(result == CSH_LEX_TOKEN && token.kind == CSH_TOKEN_WORD &&
                    token.length == length - 1 && !memcmp(token.raw, source, length - 1), "whole character token");
                if (variant == 0 || variant == 5)
                    require(token.fragment_count == 1 && token.fragments[0].kind == CSH_FRAGMENT_TEXT,
                        "constituent byte is not syntax");
                if (variant == 1)
                    require(token.fragment_count == 1 && token.fragments[0].kind == CSH_FRAGMENT_ESCAPE &&
                        token.fragments[0].end == 3, "escape protects complete character");
                csh_token_destroy(&token);
                require(csh_lexer_next(lexer, &token, &error) == CSH_LEX_TOKEN &&
                    token.kind == CSH_TOKEN_NEWLINE, "newline stays separate");
                csh_token_destroy(&token);
                csh_lexer_destroy(lexer);
            }
        }
    }
    csh_character_shutdown();
    return 0;
}
