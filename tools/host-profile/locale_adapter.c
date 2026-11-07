/* Issue 8 locale environment report. Keyword/database queries stay with the
 * selected vendor. Native execution retains inherited signal dispositions. */
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#ifndef LOCALE_ADAPTER_TEST
#include "catalog_providers.h"
#endif

static int safe_value(const char *value)
{
    const char *safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_./-";
    return strspn(value, safe) == strlen(value);
}

static void value(const char *text, int implied)
{
    if (implied) {
        putchar('"');
        for (; *text; ++text) {
            if (strchr("\\\"$`", *text)) putchar('\\');
            putchar((unsigned char)*text);
        }
        putchar('"');
    } else if (safe_value(text)) fputs(text, stdout);
    else {
        putchar('\'');
        for (; *text; ++text) {
            if (*text == '\'') fputs("'\\''", stdout);
            else putchar((unsigned char)*text);
        }
        putchar('\'');
    }
}

int main(int argc, char **argv)
{
    static const struct { const char *name; int category; } categories[] = {
        {"LC_CTYPE", LC_CTYPE}, {"LC_NUMERIC", LC_NUMERIC},
        {"LC_TIME", LC_TIME}, {"LC_COLLATE", LC_COLLATE},
        {"LC_MONETARY", LC_MONETARY}, {"LC_MESSAGES", LC_MESSAGES}
    };
    const char *lang, *all;
    size_t index;
    if (argc != 1 && !(argc == 2 && !strcmp(argv[1], "--"))) {
        argv[0] = (char *)CATALOG_LOCALE;
        execv(CATALOG_LOCALE, argv);
        perror("locale");
        return 126;
    }
    if (!setlocale(LC_ALL, "")) {
        fputs("locale: cannot select the requested locale\n", stderr);
        return 1;
    }
    lang = getenv("LANG");
    all = getenv("LC_ALL");
    fputs("LANG=", stdout); value(lang ? lang : "", 0); putchar('\n');
    for (index = 0; index < sizeof(categories) / sizeof(categories[0]); ++index) {
        const char *explicit_value = getenv(categories[index].name);
        int implied = !explicit_value || (all && *all);
        printf("%s=", categories[index].name);
        value(implied ? setlocale(categories[index].category, NULL) : explicit_value, implied);
        putchar('\n');
    }
    fputs("LC_ALL=", stdout); value(all ? all : "", 0); putchar('\n');
    if (fflush(stdout) == EOF || ferror(stdout)) {
        perror("locale: stdout");
        return 1;
    }
    return 0;
}
