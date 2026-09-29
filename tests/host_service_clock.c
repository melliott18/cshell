/* CSH-078 test clock: intercept reads only, never set any system clock.
 * 2024-02-29 12:34:56 UTC. Other clocks retain libc behavior. Linux fixture only.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <time.h>
#include <string.h>

static const time_t fixture_time = 1709210096;

time_t time(time_t *result)
{
    if (result != NULL) *result = fixture_time;
    return fixture_time;
}

int clock_gettime(clockid_t clock_id, struct timespec *result)
{
    int (*original)(clockid_t, struct timespec *);
    void *symbol;
    if (clock_id == CLOCK_REALTIME) {
        result->tv_sec = fixture_time;
        result->tv_nsec = 0;
        return 0;
    }
    symbol = dlsym(RTLD_NEXT, "clock_gettime");
    if (symbol == NULL) return -1;
    memcpy(&original, &symbol, sizeof(original));
    return original(clock_id, result);
}
