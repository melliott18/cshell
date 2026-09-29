#define _POSIX_C_SOURCE 200809L
#include <locale.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "host-test-provider.h"

/* Issue 8 adds locale-aware < and > binary primaries. Delegate every other
 * expression to the selected, inventoried vendor test. Never install globally. */
int main(int argc, char **argv)
{
    const char *name = strrchr(argv[0], '/');
    int offset = 1, negate = 0;
    name = name ? name + 1 : argv[0];
    if (!strcmp(name, "[")) {
        if (argc < 2 || strcmp(argv[argc - 1], "]")) {
            fputs("[: missing closing bracket\n", stderr);
            return 2;
        }
        argv[--argc] = NULL;
    }
    if (argc == 5 && !strcmp(argv[1], "!")) {
        offset = 2;
        negate = 1;
    }
    if (argc - offset == 3 &&
        (!strcmp(argv[offset + 1], "<") || !strcmp(argv[offset + 1], ">"))) {
        int order, truth;
        if (!setlocale(LC_ALL, "")) {
            fputs("test: unavailable locale\n", stderr);
            return 2;
        }
        order = strcoll(argv[offset], argv[offset + 2]);
        truth = !strcmp(argv[offset + 1], "<") ? order < 0 : order > 0;
        return (truth != negate) ? 0 : 1;
    }
    argv[0] = (char *)"test";
    execv(CSH_TEST_PROVIDER, argv);
    perror("test: selected provider");
    return 2;
}
