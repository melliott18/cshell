#include "cshell/traps.h"
#include "cshell/jobs.h"
#include "cshell/output.h"

#include <errno.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* Covers the standard and commonly available extension signals. sigaddset
 * validates numeric operands before indexing; unsupported larger values are
 * rejected with a diagnostic rather than silently truncating them. */
#define TRAP_LIMIT CSH_TRAP_LIMIT
struct trap_entry {
    char *action;
    struct sigaction previous;
    int installed;
    int ignored;
};
struct csh_traps {
    struct trap_entry entries[TRAP_LIMIT];
    char *exit_action;
    int exit_inherited;
    unsigned char entry_ignored[TRAP_LIMIT];
};
static struct csh_traps *active;
static volatile sig_atomic_t pending[TRAP_LIMIT];

struct csh_traps *csh_traps_active(void) { return active; }

static void record_signal(int number)
{
    if (number > 0 && number < TRAP_LIMIT) pending[number] = 1;
    if (number != SIGHUP) csh_jobs_note_signal(number);
}

/* Explicit SIG_IGN for SIGCHLD can make the kernel auto-reap children. Keep a
 * no-op disposition in shell processes, then restore SIG_IGN at exec. */
static void ignore_child(int number) { (void)number; }

int csh_traps_create(struct csh_traps **out, int interactive)
{
    struct csh_traps *traps;
    int i;
    *out = NULL;
    if (active != NULL) { errno = EBUSY; return -1; }
    traps = calloc(1, sizeof(*traps));
    if (traps == NULL) return -1;
    for (i = 0; i < TRAP_LIMIT; ++i) {
        struct sigaction disposition;
        pending[i] = 0;
        if (!interactive && i > 0 &&
            sigaction(i, NULL, &disposition) == 0 &&
            disposition.sa_handler == SIG_IGN)
            traps->entry_ignored[i] = 1;
    }
    active = traps;
    *out = traps;
    return 0;
}

void csh_traps_destroy(struct csh_traps *traps)
{
    int i;
    if (traps == NULL) return;
    for (i = 1; i < TRAP_LIMIT; ++i) {
        if (traps->entries[i].installed)
            sigaction(i, &traps->entries[i].previous, NULL);
        free(traps->entries[i].action);
        pending[i] = 0;
    }
    if (active == traps) active = NULL;
    free(traps->exit_action);
    free(traps);
}

int csh_traps_pending(void)
{
    return csh_traps_first_pending() != 0;
}

int csh_traps_first_pending(void)
{
    int i;
    if (active == NULL) return 0;
    for (i = 1; i < TRAP_LIMIT; ++i)
        if (pending[i]) return i;
    return 0;
}

void csh_traps_add_caught(const struct csh_traps *traps, sigset_t *set)
{
    int i;
    if (traps == NULL) return;
    for (i = 1; i < TRAP_LIMIT; ++i)
        if (traps->entries[i].installed && !traps->entries[i].ignored)
            sigaddset(set, i);
}

int csh_traps_take(struct csh_traps *traps, char **action)
{
    int i;
    *action = NULL;
    if (traps == NULL) return 0;
    for (i = 1; i < TRAP_LIMIT; ++i) {
        if (!pending[i]) continue;
        if (traps->entries[i].action == NULL) { pending[i] = 0; continue; }
        *action = strdup(traps->entries[i].action);
        if (*action == NULL) return -1;
        pending[i] = 0;
        return i;
    }
    return 0;
}

char *csh_traps_exit_action(struct csh_traps *traps)
{
    if (traps == NULL || traps->exit_action == NULL || traps->exit_inherited) {
        errno = 0;
        return NULL;
    }
    return strdup(traps->exit_action);
}

static int diagnostic(const char *message, const char *operand)
{
    dprintf(STDERR_FILENO, "cshell: trap: %s%s%s\n", message,
        operand ? ": " : "", operand ? operand : "");
    return 1;
}

static int condition(const char *text)
{
    char *end;
    long value;
    int number;
    sigset_t set;
    if (!strcmp(text, "EXIT") || !strcmp(text, "0")) return 0;
    if (!strncmp(text, "SIG", 3)) text += 3;
    errno = 0;
    value = strtol(text, &end, 10);
    if (*text && !*end && errno != ERANGE) {
        if (value <= 0 || value >= TRAP_LIMIT) return -1;
        sigemptyset(&set);
        return sigaddset(&set, (int)value) == 0 ? (int)value : -1;
    }
    number = csh_jobs_signal_number(text);
    return number > 0 && number < TRAP_LIMIT ? number : -1;
}

static int quote_action(const char *action)
{
    const char *p;
    if (csh_write_bytes(STDOUT_FILENO, "'", 1) == -1) return -1;
    for (p = action; *p; ++p) {
        if (*p == '\'') {
            if (csh_write_bytes(STDOUT_FILENO, "'\\''", 4) == -1) return -1;
        } else if (csh_write_bytes(STDOUT_FILENO, p, 1) == -1) return -1;
    }
    return csh_write_bytes(STDOUT_FILENO, "'", 1);
}

static int list_one(struct csh_traps *traps, int number, int defaults)
{
    const char *action = number == 0 ? traps->exit_action : traps->entries[number].action;
    const char *name = number == 0 ? "EXIT" : csh_jobs_signal_name(number);
    char numeric[24];
    /* Entry ignores are part of the saved shell state even when no trap
     * command installed them. -p must also restore default conditions. */
    if (action == NULL && number > 0 && traps->entry_ignored[number]) action = "";
    if (action == NULL && !defaults) return 0;
    if (action == NULL) action = "-";
    if (name == NULL) {
        snprintf(numeric, sizeof(numeric), "%d", number);
        name = numeric;
    }
    if (csh_write_bytes(STDOUT_FILENO, "trap -- ", 8) == -1 ||
        quote_action(action) == -1 ||
        dprintf(STDOUT_FILENO, " %s\n", name) < 0)
        return diagnostic("cannot write output", NULL);
    return 0;
}

static int install(struct csh_traps *traps, int number, const char *action)
{
    struct trap_entry *entry;
    struct sigaction disposition;
    char *copy = action == NULL ? NULL : strdup(action);
    if (action != NULL && copy == NULL) return diagnostic("cannot allocate action", NULL);
    if (number == 0) {
        free(traps->exit_action);
        traps->exit_action = copy;
        traps->exit_inherited = 0;
        return 0;
    }
    /* POSIX preserves signals ignored on entry to a non-interactive shell. */
    if (traps->entry_ignored[number]) { free(copy); return 0; }
    entry = &traps->entries[number];
    if (action == NULL) {
        if (entry->installed && sigaction(number, &entry->previous, NULL) == -1) {
            free(copy); return diagnostic("cannot reset signal", NULL);
        }
        entry->installed = 0;
        entry->ignored = 0;
        free(entry->action);
        entry->action = NULL;
        pending[number] = 0;
        return 0;
    }
    memset(&disposition, 0, sizeof(disposition));
    sigemptyset(&disposition.sa_mask);
    disposition.sa_handler = *action ? record_signal :
        number == SIGCHLD ? ignore_child : SIG_IGN;
    if (sigaction(number, &disposition,
        entry->installed ? NULL : &entry->previous) == -1) {
        free(copy); return diagnostic("cannot install signal", NULL);
    }
    entry->installed = 1;
    entry->ignored = !*action;
    free(entry->action);
    entry->action = copy;
    pending[number] = 0;
    return 0;
}

int csh_traps_builtin(struct csh_traps *traps, size_t argc, char *const argv[])
{
    size_t first = 1, i;
    int listing = 0, rc = 0;
    if (traps == NULL) return diagnostic("trap table unavailable", NULL);
    if (first < argc && !strcmp(argv[first], "-p")) { listing = 1; ++first; }
    else if (first < argc && !strcmp(argv[first], "--")) ++first;
    else if (first < argc && argv[first][0] == '-' && strcmp(argv[first], "-"))
        return diagnostic("invalid option", argv[first]);
    if (listing && first < argc && !strcmp(argv[first], "--")) ++first;
    if (listing || first == argc) {
        if (first == argc) {
            for (i = 0; i < TRAP_LIMIT; ++i) {
                struct sigaction disposition;
                /* KILL/STOP may be omitted; never emit unreinputable traps.
                 * Probe the host so Linux real-time signals are included. */
                if (i == SIGKILL || i == SIGSTOP ||
                    (i > 0 && sigaction((int)i, NULL, &disposition) == -1)) continue;
                if (list_one(traps, (int)i, listing)) rc = 1;
            }
        } else for (i = first; i < argc; ++i) {
            int number = condition(argv[i]);
            if (number < 0) { diagnostic("invalid condition", argv[i]); rc = 1; }
            else if (list_one(traps, number, 1)) rc = 1;
        }
        return rc;
    }
    {
        const char *action = argv[first];
        /* An unsigned decimal first operand is a condition, not an action.
         * In particular, `trap 0` resets EXIT in the base profile. */
        if (*action && strspn(action, "0123456789") == strlen(action)) action = "-";
        else ++first;
        if (first == argc) return diagnostic("missing condition", NULL);
        for (i = first; i < argc; ++i) {
            int number = condition(argv[i]);
            if (number < 0) { diagnostic("invalid condition", argv[i]); rc = 1; }
            else if (install(traps, number, !strcmp(action, "-") ? NULL : action)) rc = 1;
        }
    }
    return rc;
}

void csh_traps_after_fork(struct csh_traps *traps, int asynchronous,
    int preserve_listing)
{
    int i;
    struct sigaction disposition;
    if (traps == NULL) return;
    active = traps;
    if (!preserve_listing) {
        free(traps->exit_action);
        traps->exit_action = NULL;
    } else traps->exit_inherited = 1;
    memset(&disposition, 0, sizeof(disposition));
    sigemptyset(&disposition.sa_mask);
    for (i = 1; i < TRAP_LIMIT; ++i) {
        struct trap_entry *entry = &traps->entries[i];
        pending[i] = 0;
        if (!entry->installed) continue;
        disposition.sa_handler = entry->ignored ?
            (i == SIGCHLD ? ignore_child : SIG_IGN) : SIG_DFL;
        if (asynchronous && (i == SIGINT || i == SIGQUIT)) disposition.sa_handler = SIG_IGN;
        sigaction(i, &disposition, NULL);
        if (!preserve_listing && !entry->ignored) {
            free(entry->action);
            entry->action = NULL;
        }
        if (!entry->ignored) entry->installed = 0;
    }
}

void csh_traps_exec_signals(struct csh_traps *traps, int recover)
{
    int i;
    struct sigaction disposition;
    if (traps == NULL) return;
    memset(&disposition, 0, sizeof(disposition));
    sigemptyset(&disposition.sa_mask);
    disposition.sa_handler = SIG_DFL;
    for (i = 1; i < TRAP_LIMIT; ++i) {
        struct trap_entry *entry = &traps->entries[i];
        struct sigaction current;
        if (!entry->installed) continue;
        if (!recover && (i == SIGINT || i == SIGQUIT) &&
            sigaction(i, NULL, &current) == 0 &&
            current.sa_handler == SIG_IGN)
            continue;
        disposition.sa_handler = entry->ignored ?
            (recover && i == SIGCHLD ? ignore_child : SIG_IGN) :
            recover ? record_signal : SIG_DFL;
        sigaction(i, &disposition, NULL);
    }
}
