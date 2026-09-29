/* Linux-only opt-in clock boundary oracle. Does not alter the host clock. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static int record(const struct timespec *requested)
{
    const char *path = getenv("CSH_CLOCK_RECORD");
    FILE *file;
    if (!path || !(file = fopen(path, "a"))) { errno = EIO; return -1; }
    fprintf(file, "%lld %ld\n", (long long)requested->tv_sec, requested->tv_nsec);
    if (fclose(file)) return -1;
    return 0;
}
int nanosleep(const struct timespec *requested, struct timespec *remaining)
{
    (void)remaining;
    return record(requested);
}
int clock_nanosleep(clockid_t clock, int flags, const struct timespec *requested,
                    struct timespec *remaining)
{
    (void)remaining;
    if (clock != CLOCK_REALTIME && clock != CLOCK_MONOTONIC) return EINVAL;
    if (flags != 0) return EINVAL; /* Absolute deadlines are outside this oracle. */
    return record(requested) ? errno : 0;
}
