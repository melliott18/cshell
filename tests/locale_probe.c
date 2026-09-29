/* Host capability only: no cshell decoder or fnmatch oracle here. */
#include <langinfo.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

int main(int argc, char **argv)
{
    char bytes[16];
    size_t i, length;
    mbstate_t state = {0};
    if (argc < 2 || argc > 3) return 2;
    if (!setlocale(LC_ALL, argv[1])) return 77;
    printf("%s\n", nl_langinfo(CODESET));
    if (argc == 2) return 0;
    length = strlen(argv[2]) / 2;
    if (length == 0 || length > sizeof(bytes) || strlen(argv[2]) % 2) return 2;
    for (i = 0; i < length; ++i) {
        char pair[3] = {argv[2][2*i], argv[2][2*i+1], 0};
        bytes[i] = (char)strtoul(pair, NULL, 16);
    }
    if (mbrlen(bytes, length, &state) != length || !mbsinit(&state)) {
        fprintf(stderr, "sample is not one complete initial-state character\n");
        return 1;
    }
    return 0;
}
