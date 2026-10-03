/* CSH-077: create ONLY an explicitly named private utmpx fixture. */
#define _GNU_SOURCE
#define _DARWIN_C_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <utmpx.h>

int main(int argc, char **argv)
{
    struct utmpx row;
    int i;
    if ((argc < 3 || argc > 5) || argv[1][0] != '/' || strstr(argv[1], "/csh077-") == NULL) {
        fputs("expected absolute private csh077 fixture path\n", stderr);
        return 2;
    }
    if (utmpxname(argv[1])
#ifdef __APPLE__
        == 0
#else
        != 0
#endif
    ) {
        perror("utmpxname");
        return 1;
    }
    setutxent();
    for (i = 0; i < 2; ++i) {
        memset(&row, 0, sizeof(row));
        row.ut_type = USER_PROCESS;
        row.ut_pid = getppid();
        if (argc == 5)
            snprintf(row.ut_user, sizeof(row.ut_user), "%s", argv[4]);
        else
            snprintf(row.ut_user, sizeof(row.ut_user), "csh077%c", 'a' + i);
        snprintf(row.ut_line, sizeof(row.ut_line), "%s", argv[i && argc >= 4 ? 3 : 2]);
        memcpy(row.ut_id, i ? "077b" : "077a", 4);
        row.ut_tv.tv_sec = 946684800; /* 2000-01-01 00:00 UTC, authored oracle */
        if (!pututxline(&row)) {
            perror("pututxline");
            endutxent();
            return 1;
        }
    }
    endutxent();
    return 0;
}
