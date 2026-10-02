/* Opt-in, bounded file observation for the CSH-057 fixture, not the shell. */
#ifndef _DARWIN_C_SOURCE
#define _DARWIN_C_SOURCE
#endif
#include "retention_trace.h"

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

/* Leave generous room below smoke's unchanged 1 MiB RLIMIT_FSIZE. A parent
 * and a just-forked child may both see the limit at once; each can append one
 * short truncation record before disabling its own inherited descriptor. */
#define TRACE_LIMIT (768 * 1024)
static int trace_fd = -1;
static int trace_capacity, trace_round, trace_item;

void csh_retention_trace_init(void)
{
    const char *path;
    int saved = errno;
    path = getenv("CSH_RETENTION_TRACE");
    if (path != NULL && *path != '\0')
        trace_fd = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_APPEND |
            O_CLOEXEC | O_NOFOLLOW, 0600);
    errno = saved;
}

int csh_retention_trace_enabled(void) { return trace_fd >= 0; }

void csh_retention_trace_context(int capacity, int round, int item)
{
    trace_capacity = capacity;
    trace_round = round;
    trace_item = item;
}

void csh_retention_trace_close(void)
{
    int saved = errno;
    if (trace_fd >= 0) close(trace_fd);
    trace_fd = -1;
    errno = saved;
}

void csh_retention_trace_event(const char *event, pid_t child)
{
    struct timespec now;
    struct itimerval timer;
    struct sigaction action;
    struct stat info;
    sigset_t mask, pending;
    char record[384];
    long long stamp = -1, remaining = -1;
    int saved = errno, blocked = -1, queued = -1, disposition = -1;
    int length, truncated = 0;
    ssize_t written;
    if (trace_fd < 0) return;
    if (clock_gettime(CLOCK_MONOTONIC, &now) == 0)
        stamp = (long long)now.tv_sec * 1000000 + now.tv_nsec / 1000;
    /* NULL set/action arguments only query the calling process. */
    if (sigprocmask(SIG_SETMASK, NULL, &mask) == 0)
        blocked = sigismember(&mask, SIGALRM);
    if (sigpending(&pending) == 0) queued = sigismember(&pending, SIGALRM);
    if (sigaction(SIGALRM, NULL, &action) == 0)
        disposition = action.sa_handler == SIG_DFL ? 0 :
            action.sa_handler == SIG_IGN ? 1 : 2;
    if (getitimer(ITIMER_REAL, &timer) == 0)
        remaining = (long long)timer.it_value.tv_sec * 1000000 + timer.it_value.tv_usec;
    if (fstat(trace_fd, &info) == -1) {
        csh_retention_trace_close();
        errno = saved;
        return;
    }
    if (info.st_size >= TRACE_LIMIT - (off_t)sizeof(record)) {
        event = "truncated";
        truncated = 1;
    }
    /* a = [blocked, pending, disposition (0 default/1 ignore/2 handler),
     * remaining ITIMER_REAL microseconds]. -1 means the query failed.
     * t is absolute CLOCK_MONOTONIC microseconds, not elapsed case time.
     * Only constant internal event names are passed; none needs escaping. */
    length = snprintf(record, sizeof(record),
        "{\"t\":%lld,\"p\":%ld,\"e\":\"%s\",\"n\":%d,\"r\":%d,\"i\":%d,"
        "\"c\":%ld,\"a\":[%d,%d,%d,%lld]}\n", stamp, (long)getpid(), event,
        trace_capacity, trace_round, trace_item, (long)child,
        blocked, queued, disposition, remaining);
    if (length <= 0 || (size_t)length >= sizeof(record)) {
        csh_retention_trace_close();
        errno = saved;
        return;
    }
    /* One O_APPEND write keeps a complete small record together across fork.
     * A short/error write disables observation without changing the fixture. */
    do { written = write(trace_fd, record, (size_t)length); }
    while (written < 0 && errno == EINTR);
    if (written != length || truncated) csh_retention_trace_close();
    errno = saved;
}

pid_t csh_retention_fork(void)
{
    pid_t child;
    int number;
    csh_retention_trace_event("fork+", 0);
    child = fork();
    number = errno;
    csh_retention_trace_event(child == 0 ? "fork-child" : "fork-parent", child);
    /* One child-entry record is sufficient here. Descendants must not retain
     * an observer descriptor while executing builtins or waiting on gates. */
    if (child == 0) csh_retention_trace_close();
    errno = number;
    return child;
}
