#include "cshell/jobs.h"

#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/wait.h>
#include <unistd.h>

static const int signals[] = {SIGCHLD, SIGINT, SIGQUIT, SIGTSTP, SIGTTIN, SIGTTOU};
#define SIGNAL_COUNT (sizeof(signals) / sizeof(signals[0]))
struct csh_jobs {
    struct csh_state *state;
    struct csh_job *head;
    unsigned next_id;
    size_t retained;
    size_t retention_limit;
    int tty;
    pid_t shell_group;
    int interactive;
    size_t installed;
    struct sigaction saved[SIGNAL_COUNT];
    struct termios shell_modes;
    int modes_valid;
};
static volatile sig_atomic_t interrupted;

/* Own formatting buffers explicitly, including write-error paths. This also
 * avoids libc stream-attachment allocations on closed descriptor failures. */
static int outputf(int fd, const char *format, ...)
{
    char local[256], *text = local;
    va_list arguments, copy;
    int length, rc;
    size_t sent = 0;
    va_start(arguments, format);
    va_copy(copy, arguments);
    length = vsnprintf(local, sizeof(local), format, arguments);
    va_end(arguments);
    if (length < 0) { va_end(copy); return -1; }
    if ((size_t)length >= sizeof(local)) {
        text = malloc((size_t)length + 1);
        if (text == NULL) { va_end(copy); return -1; }
        if (vsnprintf(text, (size_t)length + 1, format, copy) != length) {
            free(text); va_end(copy); errno = EIO; return -1;
        }
    }
    va_end(copy);
    rc = length;
    while (sent < (size_t)length) {
        ssize_t written = write(fd, text + sent, (size_t)length - sent);
        if (written < 0 && errno == EINTR) continue;
        if (written <= 0) {
            if (written == 0) errno = EIO;
            rc = -1;
            break;
        }
        sent += (size_t)written;
    }
    if (text != local) free(text);
    return rc;
}

static void pending_signal(int number)
{
    if (number == SIGINT) interrupted = number;
}

static int terminal_group(int fd, pid_t pgid)
{
    int rc;
    do { rc = tcsetpgrp(fd, pgid); } while (rc == -1 && errno == EINTR);
    return rc;
}

static int terminal_modes(int fd, const struct termios *modes)
{
    int rc;
    do { rc = tcsetattr(fd, TCSADRAIN, modes); } while (rc == -1 && errno == EINTR);
    return rc;
}

int csh_jobs_monitor(const struct csh_jobs *jobs)
{
    struct csh_state_info info;
    csh_state_get_info(jobs->state, &info);
    return jobs->tty >= 0 && (info.options & CSH_OPT_MONITOR) != 0;
}

int csh_jobs_create(struct csh_jobs **out, struct csh_state *state, int fd)
{
    struct csh_jobs *jobs = calloc(1, sizeof(*jobs));
    struct csh_state_info info;
    size_t i;
    *out = NULL;
    if (jobs == NULL) return -1;
    jobs->state = state;
    jobs->tty = -1;
    jobs->next_id = 1;
    {
        long limit = sysconf(_SC_CHILD_MAX);
        jobs->retention_limit = limit > 0 ? (size_t)limit : 256;
    }
    jobs->shell_group = getpgrp();
    csh_state_get_info(state, &info);
    jobs->interactive = (info.options & CSH_OPT_INTERACTIVE) != 0;
    csh_state_update_options(state, 0, CSH_OPT_MONITOR | CSH_OPT_NOTIFY);
    interrupted = 0;
    for (i = 0; i < SIGNAL_COUNT; ++i) {
        struct sigaction action;
        if (i > 0 && !jobs->interactive) break;
        memset(&action, 0, sizeof(action));
        sigemptyset(&action.sa_mask);
        /* Catch keyboard signals with a no-op/flag handler: ignored signals
         * may be discarded even while blocked in a just-forked child. TTOU
         * remains ignored so a background shell can reclaim its terminal. */
        action.sa_handler = i < 4 ? pending_signal : SIG_IGN;
        if (sigaction(signals[i], &action, &jobs->saved[i]) == -1) {
            csh_jobs_destroy(jobs);
            return -1;
        }
        ++jobs->installed;
    }
    /* Do not take a terminal away from another foreground shell. A nested
     * interactive shell stops its own group until its parent foregrounds it. */
    if (jobs->interactive && fd >= 0 && isatty(fd)) {
        pid_t foreground;
        while ((foreground = tcgetpgrp(fd)) >= 0 && foreground != getpgrp()) {
            struct sigaction action;
            memset(&action, 0, sizeof(action));
            sigemptyset(&action.sa_mask);
            action.sa_handler = SIG_DFL;
            sigaction(SIGTTIN, &action, NULL);
            if (kill(-getpgrp(), SIGTTIN) == -1) break;
            action.sa_handler = SIG_IGN;
            sigaction(SIGTTIN, &action, NULL);
        }
        if (foreground >= 0 && foreground == getpgrp()) {
            int copy = fcntl(fd, F_DUPFD_CLOEXEC, 10);
            if (copy >= 0) {
                pid_t self = getpid(), previous = getpgrp();
                if ((getpgrp() == self || setpgid(0, self) == 0) &&
                    terminal_group(copy, getpgrp()) == 0 &&
                    tcgetattr(copy, &jobs->shell_modes) == 0) {
                    jobs->tty = copy;
                    jobs->shell_group = getpgrp();
                    csh_state_update_options(state, CSH_OPT_MONITOR, 0);
                } else {
                    if (getpgrp() != previous) setpgid(0, previous);
                    terminal_group(copy, previous);
                    close(copy);
                }
            }
        }
    }
    *out = jobs;
    return 0;
}

static int complete(const struct csh_job *job)
{
    size_t i;
    for (i = 0; i < job->count; ++i)
        if (job->processes[i].pid > 0 && !job->processes[i].done) return 0;
    return 1;
}

static int stopped(const struct csh_job *job)
{
    size_t i;
    int any = 0;
    for (i = 0; i < job->count; ++i) {
        const struct csh_job_process *process = &job->processes[i];
        if (process->pid <= 0 || process->done) continue;
        if (!process->stopped) return 0;
        any = 1;
    }
    return any;
}

static int job_status(const struct csh_job *job)
{
    size_t i;
    int status = job->processes[job->count - 1].status;
    if (stopped(job)) {
        for (i = 0; i < job->count; ++i)
            if (job->processes[i].stopped)
                return 128 + WSTOPSIG(job->processes[i].status);
    }
    status = WIFEXITED(status) ? WEXITSTATUS(status) :
        WIFSIGNALED(status) ? 128 + WTERMSIG(status) : 1;
    return job->negated ? !status : status;
}

void csh_jobs_remove(struct csh_jobs *jobs, struct csh_job *job)
{
    struct csh_job **link = &jobs->head;
    while (*link != NULL && *link != job) link = &(*link)->next;
    if (*link == NULL) return;
    *link = job->next;
    --jobs->retained;
    free(job->processes);
    free(job->text);
    free(job);
}

struct csh_job *csh_jobs_add(struct csh_jobs *jobs, size_t count,
    const char *text, int asynchronous, int negated)
{
    struct csh_job *job;
    if (count == 0 || jobs->next_id == UINT_MAX) { errno = EOVERFLOW; return NULL; }
    while (jobs->retained >= jobs->retention_limit) {
        struct csh_job *oldest = NULL, *candidate;
        for (candidate = jobs->head; candidate != NULL; candidate = candidate->next)
            if (complete(candidate)) oldest = candidate;
        if (oldest == NULL) break;
        csh_jobs_remove(jobs, oldest);
    }
    job = calloc(1, sizeof(*job));
    if (job == NULL) return NULL;
    job->processes = calloc(count, sizeof(*job->processes));
    job->text = strdup(text);
    if (job->processes == NULL || job->text == NULL) {
        free(job->processes); free(job->text); free(job); return NULL;
    }
    job->count = count;
    job->id = jobs->next_id++;
    job->grouped = csh_jobs_monitor(jobs);
    job->background = asynchronous;
    job->negated = negated;
    job->next = jobs->head;
    jobs->head = job;
    ++jobs->retained;
    return job;
}

int csh_jobs_poll(struct csh_jobs *jobs)
{
    struct csh_job *job;
    for (job = jobs->head; job != NULL; job = job->next) {
        size_t i;
        int was_done = complete(job), was_stopped = stopped(job);
        for (i = 0; i < job->count; ++i) {
            struct csh_job_process *process = &job->processes[i];
            pid_t pid;
            int status;
            if (process->pid <= 0 || process->done) continue;
            do {
                pid = waitpid(process->pid, &status, WNOHANG | WUNTRACED | WCONTINUED);
                if (pid > 0) {
                    if (WIFCONTINUED(status)) process->stopped = 0;
                    else {
                        process->status = status;
                        process->stopped = WIFSTOPPED(status);
                        process->done = WIFEXITED(status) || WIFSIGNALED(status);
                    }
                    if (process->done) break;
                }
            } while (pid > 0 || (pid < 0 && errno == EINTR));
            if (pid < 0 && !process->done) return -1;
        }
        if (was_done != complete(job) || was_stopped != stopped(job)) job->changed = 1;
    }
    return 0;
}

/* All status scans and sleeps use a blocked SIGCHLD, so a fast child cannot
 * exit between the final scan and an unprotected blocking read/wait. */
static void block_events(sigset_t *old)
{
    sigset_t blocked;
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGCHLD);
    sigaddset(&blocked, SIGINT);
    sigprocmask(SIG_BLOCK, &blocked, old);
}

static int wait_job(struct csh_jobs *jobs, struct csh_job *job, int interruptible)
{
    sigset_t old, waiting;
    int rc = 0;
    block_events(&old);
    waiting = old;
    sigdelset(&waiting, SIGCHLD);
    if (jobs->interactive) sigdelset(&waiting, SIGINT);
    interrupted = 0;
    for (;;) {
        if (csh_jobs_poll(jobs) == -1) { rc = -1; break; }
        if (interruptible && interrupted) { rc = 128 + interrupted; break; }
        if (complete(job) || (job->grouped && stopped(job))) break;
        sigsuspend(&waiting);
    }
    sigprocmask(SIG_SETMASK, &old, NULL);
    return rc;
}

static int restore_terminal(struct csh_jobs *jobs, struct csh_job *job)
{
    int rc = 0, number = 0;
    if (!job->grouped || jobs->tty < 0) return 0;
    if (stopped(job)) job->modes_valid = tcgetattr(jobs->tty, &job->modes) == 0;
    if (terminal_group(jobs->tty, jobs->shell_group) == -1) { rc = -1; number = errno; }
    if (jobs->modes_valid) {
        if (terminal_modes(jobs->tty, &jobs->shell_modes) == -1) {
            rc = -1; number = errno;
        } else jobs->modes_valid = 0;
    }
    if (rc == -1) errno = number;
    return rc;
}

int csh_jobs_give_terminal(struct csh_jobs *jobs, struct csh_job *job, int resume)
{
    if (!job->grouped) return 0;
    if (tcgetattr(jobs->tty, &jobs->shell_modes) == -1) return -1;
    jobs->modes_valid = 1;
    if (terminal_group(jobs->tty, job->pgid) == -1) return -1;
    if (resume && job->modes_valid && terminal_modes(jobs->tty, &job->modes) == -1)
        return -1;
    return 0;
}

static int continue_job(struct csh_job *job)
{
    size_t i;
    /* A terminal interrupt can finish the group after handoff/display and
     * before SIGCONT. Collect that exit normally instead of losing its status. */
    if (kill(-job->pgid, SIGCONT) == -1 && errno != ESRCH) return -1;
    for (i = 0; i < job->count; ++i) job->processes[i].stopped = 0;
    job->changed = 0;
    return 0;
}

static void promote_job(struct csh_jobs *jobs, struct csh_job *job)
{
    struct csh_job **link = &jobs->head;
    while (*link != NULL && *link != job) link = &(*link)->next;
    if (*link == NULL) return;
    *link = job->next;
    job->next = jobs->head;
    jobs->head = job;
}

int csh_jobs_foreground(struct csh_jobs *jobs, struct csh_job *job, int resume,
    int *status)
{
    int rc = 0, number = 0;
    job->background = 0;
    if (resume) {
        if (csh_jobs_give_terminal(jobs, job, 1) == -1) rc = -1;
        else {
            if (outputf(STDOUT_FILENO, "%s\n", job->text) < 0 ||
                continue_job(job) == -1) rc = -1;
        }
    }
    if (rc == 0) rc = wait_job(jobs, job, 0);
    if (rc == -1) number = errno;
    if (restore_terminal(jobs, job) == -1) { rc = -1; number = errno; }
    if (rc == -1) { job->background = 1; errno = number; return -1; }
    *status = job_status(job);
    if (complete(job)) csh_jobs_remove(jobs, job);
    else { job->background = 1; job->changed = 1; promote_job(jobs, job); }
    return 0;
}

void csh_jobs_cancel(struct csh_jobs *jobs, struct csh_job *job)
{
    size_t i;
    if (job->grouped && job->pgid > 0 && !complete(job)) kill(-job->pgid, SIGKILL);
    for (i = 0; i < job->count; ++i) {
        struct csh_job_process *process = &job->processes[i];
        if (process->pid > 0 && !process->done) kill(process->pid, SIGKILL);
    }
    for (i = 0; i < job->count; ++i) {
        struct csh_job_process *process = &job->processes[i];
        if (process->pid > 0 && !process->done) {
            while (waitpid(process->pid, &process->status, 0) == -1 && errno == EINTR) {}
            process->done = 1;
        }
    }
    restore_terminal(jobs, job);
    csh_jobs_remove(jobs, job);
}

int csh_jobs_reap(struct csh_jobs *jobs, int wait)
{
    struct csh_job *job;
    if (csh_jobs_poll(jobs) == -1) return -1;
    if (wait) for (job = jobs->head; job != NULL; job = job->next)
        if (wait_job(jobs, job, 0) == -1) return -1;
    return 0;
}

void csh_jobs_after_fork(struct csh_jobs *jobs, int asynchronous)
{
    size_t i;
    int monitor = csh_jobs_monitor(jobs);
    for (i = 0; i < jobs->installed; ++i) {
        struct sigaction action = jobs->saved[i];
        if (i != 0 && jobs->interactive) action.sa_handler = SIG_DFL;
        sigaction(signals[i], &action, NULL);
    }
    if (asynchronous && !monitor) {
        signal(SIGINT, SIG_IGN);
        signal(SIGQUIT, SIG_IGN);
    }
    if (jobs->tty >= 0) close(jobs->tty);
    csh_state_update_options(jobs->state, 0,
        CSH_OPT_INTERACTIVE | CSH_OPT_MONITOR | CSH_OPT_NOTIFY);
    /* These are copied parent records, never children of this process. */
    while (jobs->head != NULL) csh_jobs_remove(jobs, jobs->head);
    free(jobs);
}

void csh_jobs_destroy(struct csh_jobs *jobs)
{
    size_t i;
    if (jobs == NULL) return;
    csh_jobs_poll(jobs);
    while (jobs->head != NULL) csh_jobs_remove(jobs, jobs->head);
    if (jobs->tty >= 0) close(jobs->tty);
    for (i = jobs->installed; i > 0; --i) sigaction(signals[i - 1], &jobs->saved[i - 1], NULL);
    free(jobs);
}

/* Move the private terminal descriptor away from every descriptor operand
 * before parent redirections. The replacement is close-on-exec too. */
int csh_jobs_reserve(struct csh_jobs *jobs, const int *fds, size_t count)
{
    size_t i;
    int copy, minimum = 10;
    if (jobs->tty < 0) return 0;
    for (i = 0; i < count && fds[i] != jobs->tty; ++i) {}
    if (i == count) return 0;
    for (;;) {
        copy = fcntl(jobs->tty, F_DUPFD_CLOEXEC, minimum);
        if (copy == -1) return -1;
        for (i = 0; i < count && fds[i] != copy; ++i) {}
        if (i == count) break;
        close(copy);
        if (copy == INT_MAX) { errno = EMFILE; return -1; }
        minimum = copy + 1;
    }
    close(jobs->tty);
    jobs->tty = copy;
    return 0;
}

static struct csh_job *current_job(struct csh_jobs *jobs, int previous)
{
    struct csh_job *job;
    /* Stopped jobs take precedence; within each class, most recently
     * launched/resumed/stopped jobs are at the front of the list. */
    for (int want_stopped = 1; want_stopped >= 0; --want_stopped)
        for (job = jobs->head; job != NULL; job = job->next) {
            if (!job->background || complete(job) || stopped(job) != want_stopped) continue;
            if (previous-- == 0) return job;
        }
    return NULL;
}

static char marker(struct csh_jobs *jobs, struct csh_job *job)
{
    return current_job(jobs, 0) == job ? '+' : current_job(jobs, 1) == job ? '-' : ' ';
}

static int print_job(struct csh_jobs *jobs, struct csh_job *job, int fd, int format)
{
    char completed_status[40];
    const char *state = stopped(job) ? "Stopped" : "Running";
    if (complete(job)) {
        int status = job_status(job);
        if (status == 0) state = "Done";
        else {
            snprintf(completed_status, sizeof(completed_status), "Done(%d)", status);
            state = completed_status;
        }
    }
    if (format == 'p') return outputf(fd, "%ld\n", (long)job->pgid) < 0 ? -1 : 0;
    else if (format == 'l') {
        size_t i;
        for (i = 0; i < job->count; ++i)
            if (outputf(fd, "[%u]%c %ld %s %s\n", job->id, marker(jobs, job),
                (long)job->processes[i].pid, state, job->text) < 0) return -1;
    } else if (outputf(fd, "[%u]%c %s %s\n", job->id, marker(jobs, job), state, job->text) < 0)
        return -1;
    return 0;
}

void csh_jobs_announce(struct csh_jobs *jobs, const struct csh_job *job)
{
    if (jobs->interactive)
        outputf(STDERR_FILENO, "[%u] %ld\n", job->id,
            (long)job->processes[job->count - 1].pid);
}

void csh_jobs_notify(struct csh_jobs *jobs)
{
    struct csh_job *job;
    if (!jobs->interactive) return;
    for (job = jobs->head; job != NULL; job = job->next) {
        if (job->background && job->changed) {
            if (print_job(jobs, job, STDERR_FILENO, 0) == -1) continue;
            job->changed = 0;
            if (complete(job)) job->reported = 1;
        }
    }
}

int csh_jobs_read_ready(void *context, int fd)
{
    struct csh_jobs *jobs = context;
    sigset_t old, waiting;
    int rc;
    if (fd >= FD_SETSIZE) { errno = EINVAL; return -1; }
    block_events(&old);
    waiting = old;
    sigdelset(&waiting, SIGCHLD);
    if (jobs->interactive) sigdelset(&waiting, SIGINT);
    for (;;) {
        fd_set input;
        struct csh_state_info info;
        if (csh_jobs_poll(jobs) == -1) { rc = -1; break; }
        csh_state_get_info(jobs->state, &info);
        if (info.options & CSH_OPT_NOTIFY) csh_jobs_notify(jobs);
        FD_ZERO(&input);
        FD_SET(fd, &input);
        rc = pselect(fd + 1, &input, NULL, NULL, NULL, &waiting);
        if (rc >= 0 || errno != EINTR) break;
    }
    sigprocmask(SIG_SETMASK, &old, NULL);
    return rc < 0 ? -1 : 0;
}

static int diagnostic(const char *name, const char *message, const char *operand)
{
    outputf(STDERR_FILENO, "cshell: %s: %s%s%s\n", name, message,
        operand == NULL ? "" : ": ", operand == NULL ? "" : operand);
    return 1;
}

static int number(const char *text, long *value)
{
    char *end;
    const char *p = text;
    if (*p == '+' || *p == '-') ++p;
    if (*p == '\0') return -1;
    while (*p >= '0' && *p <= '9') ++p;
    if (*p != '\0') return -1;
    errno = 0;
    *value = strtol(text, &end, 10);
    return errno == ERANGE || *end ? -1 : 0;
}

static struct csh_job *find_job(struct csh_jobs *jobs, const char *operand, int pid_ok)
{
    struct csh_job *job, *match = NULL;
    long value;
    if (operand == NULL || strcmp(operand, "%") == 0 ||
        strcmp(operand, "%%") == 0 || strcmp(operand, "%+") == 0)
        return current_job(jobs, 0);
    if (strcmp(operand, "%-") == 0) return current_job(jobs, 1);
    if (*operand != '%') {
        if (!pid_ok || number(operand, &value) == -1 || value <= 0) return NULL;
        for (job = jobs->head; job != NULL; job = job->next)
            if ((long)job->processes[job->count - 1].pid == value) return job;
        return NULL;
    }
    ++operand;
    if (*operand >= '0' && *operand <= '9') {
        if (number(operand, &value) == -1 || value <= 0) return NULL;
        for (job = jobs->head; job != NULL; job = job->next)
            if ((long)job->id == value &&
                (pid_ok || !complete(job) || !job->reported)) return job;
        return NULL;
    }
    for (job = jobs->head; job != NULL; job = job->next) {
        int matches = *operand == '?' ? strstr(job->text, operand + 1) != NULL :
            strncmp(job->text, operand, strlen(operand)) == 0;
        if (matches && !complete(job)) {
            if (match != NULL) return NULL; /* Ambiguous job specification. */
            match = job;
        }
    }
    return match;
}

struct signal_name { const char *name; int value; };
static const struct signal_name signal_names[] = {
    {"HUP", SIGHUP}, {"INT", SIGINT}, {"QUIT", SIGQUIT}, {"ILL", SIGILL},
    {"ABRT", SIGABRT}, {"FPE", SIGFPE}, {"KILL", SIGKILL}, {"SEGV", SIGSEGV},
    {"SYS", SIGSYS}, {"PIPE", SIGPIPE}, {"ALRM", SIGALRM}, {"TERM", SIGTERM}, {"USR1", SIGUSR1},
    {"USR2", SIGUSR2}, {"CHLD", SIGCHLD}, {"CONT", SIGCONT}, {"STOP", SIGSTOP},
    {"TSTP", SIGTSTP}, {"TTIN", SIGTTIN}, {"TTOU", SIGTTOU}, {"BUS", SIGBUS},
    {"TRAP", SIGTRAP}, {"URG", SIGURG}, {"XCPU", SIGXCPU}, {"XFSZ", SIGXFSZ},
    {"VTALRM", SIGVTALRM}, {"PROF", SIGPROF}
#ifdef SIGWINCH
    , {"WINCH", SIGWINCH}
#endif
};
#define SIGNAL_NAMES (sizeof(signal_names) / sizeof(signal_names[0]))

static int signal_number(const char *text)
{
    size_t i;
    long value;
    if (number(text, &value) == 0) {
        sigset_t set;
        if (value == 0) return 0;
        sigemptyset(&set);
        return value > 0 && value <= INT_MAX && sigaddset(&set, (int)value) == 0 ? (int)value : -1;
    }
    for (i = 0; i < SIGNAL_NAMES; ++i)
        if (strcmp(text, signal_names[i].name) == 0) return signal_names[i].value;
    return -1;
}

static int kill_builtin(struct csh_jobs *jobs, size_t argc, char *const argv[])
{
    size_t i = 1;
    int sig = SIGTERM, rc = 0;
    if (i < argc && strcmp(argv[i], "-l") == 0) {
        ++i;
        if (i == argc) {
            size_t j;
            for (j = 0; j < SIGNAL_NAMES; ++j)
                if (outputf(STDOUT_FILENO, "%s%s", signal_names[j].name,
                    j + 1 == SIGNAL_NAMES ? "\n" : " ") < 0)
                    return diagnostic("kill", "cannot write output", NULL);
            return 0;
        }
        for (; i < argc; ++i) {
            size_t j;
            long value;
            if (number(argv[i], &value) == -1) return diagnostic("kill", "invalid status", argv[i]);
            if (value > 128) value -= 128;
            for (j = 0; j < SIGNAL_NAMES && signal_names[j].value != value; ++j) {}
            if (j == SIGNAL_NAMES) return diagnostic("kill", "invalid status", argv[i]);
            if (outputf(STDOUT_FILENO, "%s\n", signal_names[j].name) < 0)
                return diagnostic("kill", "cannot write output", NULL);
        }
        return 0;
    }
    if (i < argc && strcmp(argv[i], "-s") == 0) {
        if (++i == argc) return diagnostic("kill", "signal required", NULL);
        sig = signal_number(argv[i++]);
    } else if (i < argc && argv[i][0] == '-' && strcmp(argv[i], "--") != 0)
        sig = signal_number(argv[i++] + 1);
    if (sig < 0) return diagnostic("kill", "invalid signal", NULL);
    if (i < argc && strcmp(argv[i], "--") == 0) ++i;
    if (i == argc) return diagnostic("kill", "operand required", NULL);
    for (; i < argc; ++i) {
        long value;
        if (argv[i][0] == '%') {
            struct csh_job *job = find_job(jobs, argv[i], 0);
            size_t j;
            if (job == NULL || complete(job)) { rc = diagnostic("kill", "no such job", argv[i]); continue; }
            if (job->grouped) {
                if (kill(-job->pgid, sig) == -1) rc = diagnostic("kill", strerror(errno), argv[i]);
            } else for (j = 0; j < job->count; ++j) {
                if (!job->processes[j].done && kill(job->processes[j].pid, sig) == -1)
                    rc = diagnostic("kill", strerror(errno), argv[i]);
            }
            if ((sig == SIGCONT || sig == SIGKILL) && rc == 0)
                for (j = 0; j < job->count; ++j) job->processes[j].stopped = 0;
        } else if (number(argv[i], &value) == -1 || (long)(pid_t)value != value)
            rc = diagnostic("kill", "invalid pid", argv[i]);
        else if (kill((pid_t)value, sig) == -1) rc = diagnostic("kill", strerror(errno), argv[i]);
    }
    return rc;
}

int csh_jobs_is_builtin(const char *name)
{
    return strcmp(name, "jobs") == 0 || strcmp(name, "fg") == 0 ||
        strcmp(name, "bg") == 0 || strcmp(name, "wait") == 0 ||
        strcmp(name, "kill") == 0 || strcmp(name, "set") == 0;
}

static int monitor_option(struct csh_jobs *jobs, size_t argc, char *const argv[])
{
    size_t i;
    struct csh_state_info info;
    unsigned options;
    csh_state_get_info(jobs->state, &info);
    options = info.options;
    if (argc == 2 && (strcmp(argv[1], "-o") == 0 || strcmp(argv[1], "+o") == 0)) {
        int written;
        if (argv[1][0] == '-')
            written = outputf(STDOUT_FILENO, "monitor %s\nnotify %s\n",
                options & CSH_OPT_MONITOR ? "on" : "off", options & CSH_OPT_NOTIFY ? "on" : "off");
        else written = outputf(STDOUT_FILENO, "set %cm\nset %cb\n",
                options & CSH_OPT_MONITOR ? '-' : '+', options & CSH_OPT_NOTIFY ? '-' : '+');
        return written < 0 ? diagnostic("set", "cannot write output", NULL) : 0;
    }
    if (argc == 1) return diagnostic("set", "only monitor and notify options are supported", NULL);
    for (i = 1; i < argc; ++i) {
        const char *arg = argv[i];
        unsigned flag;
        int enable = arg[0] == '-';
        size_t j;
        if ((arg[0] != '-' && arg[0] != '+') || arg[1] == '\0')
            return diagnostic("set", "invalid option", arg);
        if (strcmp(arg + 1, "o") == 0) {
            if (++i == argc) return diagnostic("set", "option name required", NULL);
            if (strcmp(argv[i], "monitor") == 0) flag = CSH_OPT_MONITOR;
            else if (strcmp(argv[i], "notify") == 0) flag = CSH_OPT_NOTIFY;
            else return diagnostic("set", "unsupported option", argv[i]);
            if (enable) options |= flag; else options &= ~flag;
        } else for (j = 1; arg[j]; ++j) {
            if (arg[j] == 'm') flag = CSH_OPT_MONITOR;
            else if (arg[j] == 'b') flag = CSH_OPT_NOTIFY;
            else return diagnostic("set", "unsupported option", arg);
            if (enable) options |= flag; else options &= ~flag;
        }
    }
    if ((options & CSH_OPT_MONITOR) && jobs->tty < 0)
        return diagnostic("set", "job control unavailable", NULL);
    csh_state_update_options(jobs->state, options & (CSH_OPT_MONITOR | CSH_OPT_NOTIFY),
        ~options & (CSH_OPT_MONITOR | CSH_OPT_NOTIFY));
    return 0;
}

int csh_jobs_builtin(struct csh_jobs *jobs, const struct csh_command *command)
{
    size_t i = 1;
    int rc = 0, format = 0;
    size_t argc = command->argc;
    char *const *argv = command->argv;
    const char *name = argv[0];
    struct csh_job *job;
    if (csh_jobs_poll(jobs) == -1) return diagnostic(name, "cannot collect child status", NULL);
    if (strcmp(name, "kill") == 0) return kill_builtin(jobs, argc, argv);
    if (strcmp(name, "set") == 0) return monitor_option(jobs, argc, argv);
    if (strcmp(name, "jobs") == 0) {
        if (i < argc && (strcmp(argv[i], "-l") == 0 || strcmp(argv[i], "-p") == 0)) format = argv[i++][1];
        if (i < argc && strcmp(argv[i], "--") == 0) ++i;
        if (i == argc) {
            for (job = jobs->head; job != NULL; job = job->next) {
                if (complete(job) && job->reported) continue;
                if (print_job(jobs, job, STDOUT_FILENO, format) == -1) {
                    rc = diagnostic(name, "cannot write output", NULL);
                    continue;
                }
                job->changed = 0;
                if (complete(job)) job->reported = 1;
            }
        } else for (; i < argc; ++i) {
            job = find_job(jobs, argv[i], 0);
            if (job == NULL) rc = diagnostic(name, "no such job", argv[i]);
            else if (print_job(jobs, job, STDOUT_FILENO, format) == -1)
                rc = diagnostic(name, "cannot write output", NULL);
            else { job->changed = 0; if (complete(job)) job->reported = 1; }
        }
        return rc;
    }
    if (i < argc && strcmp(argv[i], "--") == 0) ++i;
    if (strcmp(name, "wait") == 0) {
        if (i == argc) {
            job = jobs->head;
            while (job != NULL) {
                struct csh_job *next = job->next;
                rc = wait_job(jobs, job, 1);
                if (rc != 0) return rc < 0 ? diagnostic(name, "cannot wait", NULL) : rc;
                if (complete(job)) csh_jobs_remove(jobs, job);
                job = next;
            }
            return 0;
        }
        for (; i < argc; ++i) {
            job = find_job(jobs, argv[i], 1);
            if (job == NULL) { diagnostic(name, "unknown job or pid", argv[i]); rc = 127; continue; }
            rc = wait_job(jobs, job, 1);
            if (rc != 0) return rc < 0 ? diagnostic(name, "cannot wait", argv[i]) : rc;
            rc = job_status(job);
            if (complete(job)) csh_jobs_remove(jobs, job);
        }
        return rc;
    }
    if (!csh_jobs_monitor(jobs)) return diagnostic(name, "job control unavailable", NULL);
    if (strcmp(name, "fg") == 0 && argc - i > 1)
        return diagnostic(name, "too many operands", NULL);
    do {
        const char *operand = i < argc ? argv[i] : NULL;
        job = find_job(jobs, operand, 0);
        if (job == NULL || complete(job)) rc = diagnostic(name, "no such job", operand);
        else if (!job->grouped) rc = diagnostic(name, "job was started without job control", operand);
        else if (strcmp(name, "fg") == 0) {
            if (csh_jobs_foreground(jobs, job, 1, &rc) == -1)
                rc = diagnostic(name, "cannot foreground job", operand);
        } else {
            if (continue_job(job) == -1) rc = diagnostic(name, "cannot continue job", operand);
            else {
                job->background = 1;
                promote_job(jobs, job);
                if (print_job(jobs, job, STDOUT_FILENO, 0) == -1)
                    rc = diagnostic(name, "cannot write output", NULL);
            }
        }
        ++i;
    } while (i < argc);
    return rc;
}
