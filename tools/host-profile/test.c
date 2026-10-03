#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <fcntl.h>
#include <locale.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "host-test-provider.h"

/* Query the filesystem with effective credentials, including ACLs. A mode-bit
 * approximation (or access() using real IDs) loses grants and denials when
 * identities differ. The kernel owns lookup, ACL and privilege semantics. */
static int permission(const char *operator)
{
    if (!strcmp(operator, "-r")) return R_OK;
    if (!strcmp(operator, "-w")) return W_OK;
    if (!strcmp(operator, "-x")) return X_OK;
    return 0;
}

/* Issue 8 collation and effective-credential predicates; other expressions
 * delegate to the selected, inventoried vendor test. Never install globally. */
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
    if (argc == 3 && permission(argv[1]))
        return faccessat(AT_FDCWD, argv[2], permission(argv[1]), AT_EACCESS) == 0 ? 0 : 1;
    if (argc == 4 && !strcmp(argv[1], "!") && permission(argv[2]))
        return faccessat(AT_FDCWD, argv[3], permission(argv[2]), AT_EACCESS) == 0 ? 1 : 0;
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
