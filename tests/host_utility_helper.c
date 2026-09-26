#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    if (argc == 3 && !strcmp(argv[1], "env")) {
        const char *value = getenv(argv[2]);
        return value && printf("%s\n", value) >= 0 ? 0 : 1;
    }
    if (argc == 2 && !strcmp(argv[1], "file-limit")) {
        struct rlimit limit;
        if (getrlimit(RLIMIT_FSIZE, &limit)) return 1;
        return printf("%llu\n", (unsigned long long)limit.rlim_cur) < 0;
    }
    if (argc == 2 && !strcmp(argv[1], "signal-child")) {
        for (;;) pause();
    }
    return 2;
}
