/* CSH-079: interrupt actual libc output to an already-full owned pipe.
 * This source-including probe installs a caught signal only for the EINTR
 * experiment; the selected production providers install no signal handlers.
 * No fork, process inventory, host limits, or external files are involved.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

#ifdef HOST_FORMATTED_ECHO
#define main profile_main
#include "../tools/host-profile/echo.c"
#undef main
#else
#define HOST_PRINTF_MAIN profile_main
#include "../tools/host-profile/printf.c"
#endif

static volatile sig_atomic_t delivered;
static void caught(int number)
{
    (void)number;
    if (delivered < 100) ++delivered;
}

int main(int argc, char **argv)
{
    const char *mode = getenv("CSH_FORMATTED_INTERRUPT");
    int descriptors[2], flags, status, stream_error;
    size_t filled = 0, drained = 0;
    ssize_t amount;
    char bytes[1024];
    FILE *record;
    struct sigaction action;
    struct itimerval timer;
    if (!mode || !strcmp(mode, "control")) return profile_main(argc, argv);
    if (strcmp(mode, "caught") && strcmp(mode, "default")) return 125;
    memset(bytes, 'p', sizeof bytes);
    if (pipe(descriptors) < 0) return 125;
    flags = fcntl(descriptors[1], F_GETFL);
    if (flags < 0 || fcntl(descriptors[1], F_SETFL, flags | O_NONBLOCK) < 0) return 125;
    while ((amount = write(descriptors[1], bytes, sizeof bytes)) > 0)
        filled += (size_t)amount;
    if (amount != -1 || (errno != EAGAIN && errno != EWOULDBLOCK) || !filled) return 125;
    /* Finish filling even on systems that leave less than PIPE_BUF writable. */
    while ((amount = write(descriptors[1], bytes, 1)) == 1) ++filled;
    if (amount != -1 || (errno != EAGAIN && errno != EWOULDBLOCK)) return 125;
    if (fcntl(descriptors[1], F_SETFL, flags) < 0 ||
        dup2(descriptors[1], STDOUT_FILENO) < 0 || close(descriptors[1]) < 0 ||
        setvbuf(stdout, NULL, _IONBF, 0)) return 125;
    record = fopen("interrupt.json", "w");
    if (!record) return 125;
    fprintf(record, "{\"ready\":true,\"filled\":%zu}\n", filled);
    if (fclose(record)) return 125;
    memset(&action, 0, sizeof action);
    action.sa_handler = !strcmp(mode, "caught") ? caught : SIG_DFL;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGALRM, &action, NULL) < 0) return 125;
    memset(&timer, 0, sizeof timer);
    timer.it_value.tv_usec = timer.it_interval.tv_usec = 10000;
    if (setitimer(ITIMER_REAL, &timer, NULL) < 0) return 125;
    status = profile_main(argc, argv);
    memset(&timer, 0, sizeof timer);
    if (setitimer(ITIMER_REAL, &timer, NULL) < 0) return 125;
    stream_error = !!ferror(stdout);
    if (close(STDOUT_FILENO) < 0) return 125;
    while ((amount = read(descriptors[0], bytes, sizeof bytes)) > 0) {
        ssize_t index;
        for (index = 0; index < amount; ++index)
            if (bytes[index] != 'p') return 125;
        drained += (size_t)amount;
    }
    if (amount < 0 || close(descriptors[0]) < 0) return 125;
    record = fopen("interrupt.json", "w");
    if (!record) return 125;
    fprintf(record, "{\"ready\":true,\"filled\":%zu,\"drained\":%zu,"
            "\"signals\":%d,\"stream_error\":%d,\"provider_status\":%d}\n",
            filled, drained, (int)delivered, stream_error, status);
    if (fclose(record)) return 125;
    return status;
}
