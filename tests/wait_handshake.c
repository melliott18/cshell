/* CSH-054: interpose only jobs.c's sigsuspend in the test runtime. Inject at
 * the blocked-wait boundary, never using elapsed sleeps as a scheduling oracle. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int csh_wait_sigsuspend(const sigset_t *mask)
{
    static int delivered;
    const char *selected = getenv("CSH_WAIT_SIGNALS");
    if (!delivered && selected) {
        sigset_t blocked, pending;
        int first = !strcmp(selected, "TERM") ? SIGTERM : SIGUSR1;
        delivered = 1;
        assert(sigprocmask(SIG_SETMASK, NULL, &blocked) == 0);
        assert(sigismember(&blocked, first) == 1);
        assert(sigismember(mask, first) == 0);
        assert(write(STDERR_FILENO, "wait-armed\n", 11) == 11);
        assert(raise(first) == 0);
        if (!strcmp(selected, "both")) {
            assert(sigismember(&blocked, SIGUSR2) == 1);
            assert(sigismember(mask, SIGUSR2) == 0);
            assert(raise(SIGUSR2) == 0);
        }
        assert(sigpending(&pending) == 0 && sigismember(&pending, first) == 1);
    }
    return sigsuspend(mask);
}
