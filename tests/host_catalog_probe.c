/* Independent libc consumer of generated catalogs/locales; no utility oracle. */
#include <langinfo.h>
#include <locale.h>
#include <nl_types.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

int main(int argc, char **argv)
{
    if (argc == 5 && strcmp(argv[1], "catalog") == 0) {
        nl_catd catalog;
        const char *message;
        if (!setlocale(LC_ALL, "")) return 77;
        catalog = catopen(argv[2], NL_CAT_LOCALE);
        if (catalog == (nl_catd)-1) { perror("catopen"); return 1; }
        message = catgets(catalog, atoi(argv[3]), atoi(argv[4]), "<missing>");
        if (fwrite(message, 1, strlen(message), stdout) != strlen(message)) return 2;
        return catclose(catalog) || fflush(stdout) ? 2 : 0;
    }
    if (argc == 3 && strcmp(argv[1], "numeric") == 0) {
        struct lconv *numeric;
        if (!setlocale(LC_NUMERIC, argv[2])) return 77;
        numeric = localeconv();
        printf("%s\n%s\n", numeric->decimal_point, numeric->thousands_sep);
        return fflush(stdout) ? 2 : 0;
    }
    if (argc == 3 && strcmp(argv[1], "locale") == 0) {
        if (!setlocale(LC_ALL, argv[2])) return 77;
        printf("%s\n%s\n", nl_langinfo(CODESET), localeconv()->decimal_point);
        return fflush(stdout) ? 2 : 0;
    }
    if (argc == 2 && strcmp(argv[1], "limits") == 0) {
        printf("%d\n", NL_SETD);
        return 0;
    }
    return 2;
}
