/* CSH-079: interrupt actual libc output to an already-full owned pipe.
 * This source-including probe installs a caught signal only for the EINTR
 * experiment; the selected production providers install no signal handlers.
 * The restart handler drains only the known prefill using async-signal-safe
 * read(). No child, process inventory, or host limit changes are involved.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>
#ifdef __APPLE__
#include <sys/ucontext.h>
#else
#include <ucontext.h>
#endif

#ifdef HOST_FORMATTED_ECHO
#define main profile_main
#include "../tools/host-profile/echo.c"
#undef main
#else
#define HOST_PRINTF_MAIN profile_main
#include "../tools/host-profile/printf.c"
#endif

static volatile sig_atomic_t delivered;
static volatile sig_atomic_t drain_error;
static volatile sig_atomic_t restart_fd = -1;
static volatile sig_atomic_t restart_remaining;
static volatile sig_atomic_t pc_low, pc_high;
static void caught(int number, siginfo_t *info, void *context)
{
    int saved_errno = errno;
    uintptr_t pc = 0;
    (void)number;
    (void)info;
#if defined(__APPLE__) && defined(__aarch64__)
    pc = ((ucontext_t *)context)->uc_mcontext->__ss.__pc;
#elif defined(__APPLE__) && defined(__x86_64__)
    pc = ((ucontext_t *)context)->uc_mcontext->__ss.__rip;
#elif defined(__linux__) && defined(__aarch64__)
    pc = ((ucontext_t *)context)->uc_mcontext.pc;
#elif defined(__linux__) && defined(__x86_64__)
    pc = ((ucontext_t *)context)->uc_mcontext.gregs[REG_RIP];
#else
    (void)context; /* An unresolved PC is an explicit failed attestation. */
#endif
    pc_low = (sig_atomic_t)(uint32_t)pc;
    pc_high = (sig_atomic_t)(uint32_t)(pc >> 32);
    if (delivered < 100) ++delivered;
    while (restart_fd >= 0 && restart_remaining) {
        char buffer[1024];
        size_t wanted = (size_t)restart_remaining < sizeof buffer ? (size_t)restart_remaining : sizeof buffer;
        ssize_t n = read(restart_fd, buffer, wanted);
        if (n <= 0) { drain_error = 1; break; }
        for (ssize_t i = 0; i < n; ++i)
            if (buffer[i] != 'p') drain_error = 1;
        restart_remaining -= (sig_atomic_t)n;
    }
    errno = saved_errno;
}

int main(int argc, char **argv)
{
    const char *mode = getenv("CSH_FORMATTED_INTERRUPT");
    int descriptors[2], flags, status, stream_error;
    size_t filled = 0, drained = 0;
    ssize_t amount;
    char bytes[1024];
    FILE *record, *capture;
    int restart, partial;
    char *payload = NULL;
    size_t payload_size = 0;
    struct sigaction action;
    struct itimerval timer;
    if (!mode || !strcmp(mode, "control")) return profile_main(argc, argv);
    restart = !strcmp(mode, "restart");
    partial = !strcmp(mode, "partial");
    if (strcmp(mode, "caught") && strcmp(mode, "default") && !restart && !partial) return 125;
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
    if (filled > 2 * 1024 * 1024) return 125;
    if (partial) {
        size_t remaining = filled;
        while (remaining) {
            amount = read(descriptors[0], bytes, remaining < sizeof bytes ? remaining : sizeof bytes);
            if (amount <= 0) return 125;
            remaining -= (size_t)amount;
        }
        /* Generate after exec: this is a write boundary, not an ARG_MAX test. */
        payload_size = 4 * filled + 1;
        payload = malloc(payload_size + 1);
        if (!payload || argc < 2) return 125;
        for (size_t i = 0; i < payload_size; ++i) payload[i] = "ab"[i % 2];
        payload[payload_size] = '\0';
        argv[argc - 1] = payload;
    }
    if (fcntl(descriptors[1], F_SETFL, flags) < 0 ||
        dup2(descriptors[1], STDOUT_FILENO) < 0 || close(descriptors[1]) < 0 ||
        setvbuf(stdout, NULL, _IONBF, 0)) return 125;
    record = fopen("interrupt.json", "w");
    if (!record) return 125;
    fprintf(record, "{\"ready\":true,\"filled\":%zu}\n", filled);
    if (fclose(record)) return 125;
    memset(&action, 0, sizeof action);
    action.sa_flags = SA_SIGINFO;
    action.sa_sigaction = caught;
    if (!strcmp(mode, "default")) {
        action.sa_flags = 0;
        action.sa_handler = SIG_DFL;
    }
    if (restart) {
        action.sa_flags |= SA_RESTART;
        restart_fd = descriptors[0];
        restart_remaining = (sig_atomic_t)filled;
    }
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGALRM, &action, NULL) < 0) return 125;
    memset(&timer, 0, sizeof timer);
    timer.it_value.tv_usec = 10000;
    /* echo can attempt its trailing newline after the first output failure. */
    timer.it_interval.tv_usec = restart ? 0 : 10000;
    if (setitimer(ITIMER_REAL, &timer, NULL) < 0) return 125;
    status = profile_main(argc, argv);
    memset(&timer, 0, sizeof timer);
    if (setitimer(ITIMER_REAL, &timer, NULL) < 0) return 125;
    stream_error = !!ferror(stdout);
    if (close(STDOUT_FILENO) < 0) return 125;
    capture = fopen("interrupt-output", "wb");
    if (!capture) return 125;
    while ((amount = read(descriptors[0], bytes, sizeof bytes)) > 0) {
        if (fwrite(bytes, 1, (size_t)amount, capture) != (size_t)amount) return 125;
        drained += (size_t)amount;
    }
    if (amount < 0 || close(descriptors[0]) < 0 || fclose(capture)) return 125;
    record = fopen("interrupt.json", "w");
    if (!record) return 125;
    Dl_info interrupted = {0};
    uintptr_t pc = ((uintptr_t)(uint32_t)pc_high << 32) | (uint32_t)pc_low;
    dladdr((const void *)pc, &interrupted);
    fprintf(record, "{\"ready\":true,\"filled\":%zu,\"drained\":%zu,"
            "\"signals\":%d,\"stream_error\":%d,\"provider_status\":%d,"
            "\"prefill_remaining\":%zu,\"drain_error\":%d,\"payload_size\":%zu,"
            "\"interrupted_symbol\":\"%s\"}\n",
            filled, drained, (int)delivered, stream_error, status,
            (size_t)restart_remaining, (int)drain_error, payload_size,
            interrupted.dli_sname ? interrupted.dli_sname : "unresolved");
    if (fclose(record)) return 125;
    free(payload);
    return status;
}
