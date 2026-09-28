/* Host process observations for CSH-048. No shell/reference oracle. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
extern char **environ;
int main(int argc, char **argv)
{
    struct rlimit limit;
    if (argc >= 3 && !strcmp(argv[1], "deep-directory")) {
        char component[81], *path;
        long maximum = pathconf(".", _PC_PATH_MAX);
        size_t used;
        if (maximum <= 0 || maximum > 65536) return 2;
        path = malloc((size_t)maximum + 256);
        if (!path || !getcwd(path, (size_t)maximum + 256)) { free(path); return 2; }
        memset(component, 'd', sizeof(component)-1); component[sizeof(component)-1] = 0;
        used = strlen(path);
        while (used <= (size_t)maximum) {
            if (mkdir(component, 0700) || chdir(component)) { free(path); return 2; }
            path[used++] = '/';
            strcpy(path + used, component); used += strlen(component);
        }
        if (setenv("PWD", path, 1) || setenv("EXPECTED_CWD", path, 1)) { free(path); return 2; }
        free(path);
        execv(argv[2], argv + 2);
        return 2;
    }
    if (argc >= 3 && !strcmp(argv[1], "malformed-environment")) {
        size_t n = 0;
        char **environment;
        while (environ[n]) ++n;
        environment = calloc(n + 7, sizeof(*environment));
        if (!environment) return 2;
        memcpy(environment, environ, n * sizeof(*environment));
        environment[n++] = "1bad=invalid";
        environment[n++] = "NOEQUAL";
        environment[n++] = "=invalid";
        environment[n++] = "DUPLICATE=first";
        environment[n++] = "DUPLICATE=last";
        environment[n++] = "VALID=okay";
        execve(argv[2], argv + 2, environment);
        free(environment); return 2;
    }
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
