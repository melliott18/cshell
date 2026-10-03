/* Disposable resource controls applied AFTER process startup, so stack tests
 * measure formatting, not the kernel's argv/loader reservation. No host limits
 * or accounts are changed. This includes the actual selected provider source. */
#define HOST_PRINTF_MAIN profile_main
#include "../tools/host-profile/printf.c"
#include <sys/resource.h>

int main(int argc, char **argv)
{
    struct rlimit limit;
    char *format;
    char *operands[4] = {"printf", NULL, "x", NULL};
    FILE *record;
    int resource;
    if (argc != 2) return 2;
    if (!strcmp(argv[1], "stack")) {
        resource = RLIMIT_STACK;
        limit.rlim_cur = 64 * 1024;
        format = malloc(262147);
        if (!format) return 2;
        memcpy(format, "%s", 2);
        memset(format + 2, 'x', 262144);
        format[262146] = 0;
    } else if (!strcmp(argv[1], "memory")) {
#ifdef __linux__
        resource = RLIMIT_AS;
        limit.rlim_cur = 16 * 1024 * 1024;
        format = strdup("%.20000000f");
        if (!format) return 2;
        operands[2] = "1.5";
#else
        return 77; /* Caller records unavailable; never a passing assertion. */
#endif
    } else return 2;
    if (getrlimit(resource, &limit) < 0) return 2;
    limit.rlim_cur = resource == RLIMIT_STACK ? 64 * 1024 : 16 * 1024 * 1024;
    if (setrlimit(resource, &limit) < 0 || getrlimit(resource, &limit) < 0) return 2;
    record = fopen("resource.json", "w");
    if (!record) return 2;
    fprintf(record, "{\"resource\":\"%s\",\"soft\":%llu,\"hard\":%llu}\n",
            argv[1], (unsigned long long)limit.rlim_cur, (unsigned long long)limit.rlim_max);
    if (fclose(record)) return 2;
    operands[1] = format;
    argc = profile_main(3, operands);
    free(format);
    return argc;
}
