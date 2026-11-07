#define CATALOG_ADAPTER_TEST 1
#include "../tools/host-profile/catalog_adapter.c"
#include <assert.h>

static void check(const char *name, int argc, char **input, char **expected)
{
    char **arguments = NULL, **owned = NULL;
    size_t index;
    assert(adapt(name, argc, input, &arguments, &owned) == 0);
    for (index = 0; expected[index]; ++index) {
        assert(arguments[index]);
        assert(strcmp(arguments[index], expected[index]) == 0);
    }
    assert(!arguments[index]);
    release(arguments, owned);
}

int main(void)
{
    char *decoded = c_string("\\a\\b\\f\\n\\r\\t\\v\\\\\\\"\\?\\101\\12\\1\\x42");
    char *plural[] = {"-e", "d\\141", "\\101", "\\102", "2"};
    char *plural_expected[] = {"-E", "--", "d\\141", "A", "B", "2", NULL};
    char *domain[] = {"-e", "-d", "d\\141", "\\101"};
    char *domain_expected[] = {"-d", "d\\141", "-E", "--", "A", NULL};
    char *many[] = {"-se", "\\101", "\\102"};
    char *many_expected[] = {"-s", "-E", "--", "A", "B", NULL};
    char *literal[] = {"-s", "\\101"};
    char *literal_expected[] = {"-s", "-E", "--", "\\101", NULL};
    char *options[] = {"-cfS", "-o", "-S", "-Ddir", "--", "-S"};
    char *options_expected[] = {"-c", "-f", "--strict", "-o", "-S", "-D", "dir", "--", "-S", NULL};
    assert(decoded && !strcmp(decoded, "\a\b\f\n\r\t\v\\\"?A\n\1B"));
    free(decoded);
    decoded = c_string("\\x4a\\x4B\\000ignored");
    assert(decoded && !strcmp(decoded, "JK"));
    free(decoded);
    check("ngettext", 5, plural, plural_expected);
    check("gettext", 4, domain, domain_expected);
    check("gettext", 3, many, many_expected);
    check("gettext", 2, literal, literal_expected);
    check("msgfmt", 6, options, options_expected);
    {
        char *missing[] = {"-d"};
        char **arguments = NULL, **owned = NULL;
        assert(adapt("gettext", 1, missing, &arguments, &owned) == 2);
        release(arguments, owned);
    }
    puts("PASS: native catalog adapter escapes and option/operand boundaries");
    return 0;
}
