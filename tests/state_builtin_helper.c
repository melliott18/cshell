/* Host process observations for CSH-048. No shell/reference oracle. */
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <time.h>
int main(int argc, char **argv)
{
    struct rlimit limit;
    if (argc != 2) return 2;
    if (!strcmp(argv[1], "cpu")) {
        clock_t start = clock();
        if (start == (clock_t)-1) return 2;
        while ((double)(clock() - start) / CLOCKS_PER_SEC < 0.15) {}
        return 0;
    }
    if (!strcmp(argv[1], "file-limit") && !getrlimit(RLIMIT_FSIZE, &limit)) {
        printf("%lu:%lu\n", (unsigned long)limit.rlim_cur, (unsigned long)limit.rlim_max);
        return 0;
    }
    return 2;
}
