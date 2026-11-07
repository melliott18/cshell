/* Quote output must survive reentry and distinguish explicit/implied values. */
#define LOCALE_ADAPTER_TEST
#define CATALOG_LOCALE "/usr/bin/locale"
#define main locale_adapter_main
#include "../tools/host-profile/locale_adapter.c"
#undef main
#include <assert.h>

int main(void)
{
    char data[128] = {0};
    FILE *file = tmpfile();
    int saved = dup(STDOUT_FILENO);
    size_t count;
    assert(file && saved >= 0);
    assert(dup2(fileno(file), STDOUT_FILENO) >= 0);
    value("C", 0); putchar('\n');
    value("", 0); putchar('\n');
    value("a'b $`\\\"", 0); putchar('\n');
    value("a'b $`\\\"", 1); putchar('\n');
    assert(fflush(stdout) == 0);
    assert(dup2(saved, STDOUT_FILENO) >= 0);
    close(saved);
    rewind(file);
    count = fread(data, 1, sizeof(data) - 1, file);
    assert(!ferror(file) && count < sizeof(data) - 1);
    assert(!strcmp(data, "C\n\n'a'\\''b $`\\\"'\n\"a'b \\$\\`\\\\\\\"\"\n"));
    fclose(file);
    puts("PASS: locale explicit and implied shell quoting");
    return 0;
}
