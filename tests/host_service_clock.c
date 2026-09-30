/* CSH-078 test clock: intercept reads only, never set any system clock.
 * 2024-02-29 12:34:56 UTC. Other clocks retain libc behavior. Linux fixture only.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <time.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>

static time_t fixture_time(void)
{
    const char *value = getenv("CSH078_CLOCK_EPOCH");
    char *end;
    long long parsed;
    if (value == NULL || *value == '\0') return 1709210096;
    errno = 0;
    parsed = strtoll(value, &end, 10);
    if (errno != 0 || *end != '\0' || (long long)(time_t)parsed != parsed)
        abort();
    return (time_t)parsed;
}

time_t time(time_t *result)
{
    if (result != NULL) *result = fixture_time();
    return fixture_time();
}

int clock_gettime(clockid_t clock_id, struct timespec *result)
{
    int (*original)(clockid_t, struct timespec *);
    void *symbol;
    if (clock_id == CLOCK_REALTIME) {
        result->tv_sec = fixture_time();
        result->tv_nsec = 0;
        return 0;
    }
    symbol = dlsym(RTLD_NEXT, "clock_gettime");
    if (symbol == NULL) return -1;
    memcpy(&original, &symbol, sizeof(original));
    return original(clock_id, result);
}
