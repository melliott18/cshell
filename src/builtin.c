#include "cshell/builtin.h"
#include "cshell/output.h"
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int problem(const char *name, const char *message)
{
    csh_write_text(2, "cshell: ");
    csh_write_text(2, name);
    csh_write_text(2, ": ");
    csh_write_text(2, message);
    csh_write_text(2, "\n");
    return 1;
}

static int state_result(const char *name, enum csh_state_result result)
{
    if (result == CSH_STATE_OK) return 0;
    return problem(name, result == CSH_STATE_READONLY ? "readonly variable" :
        result == CSH_STATE_NOMEM ? "out of memory" : "invalid operand");
}

enum csh_execution_category csh_state_builtin_category(const char *name)
{
    static const char *const special[] = {":", "export", "readonly", "unset", "shift", "set", ".", "eval", "exec", "times"};
    size_t i;
    for (i = 0; i < sizeof(special)/sizeof(*special); ++i)
        if (!strcmp(name, special[i])) return CSH_EXEC_SPECIAL_BUILTIN;
    if (!strcmp(name, "cd") || !strcmp(name, "pwd") ||
        !strcmp(name, "command") || !strcmp(name, "type") || !strcmp(name, "hash") ||
        !strcmp(name, "alias") || !strcmp(name, "unalias") || !strcmp(name, "read") ||
        !strcmp(name, "getopts") || !strcmp(name, "umask") || !strcmp(name, "ulimit")) return CSH_EXEC_REGULAR_BUILTIN;
    return CSH_EXEC_EXTERNAL;
}

static int compare_names(const void *a, const void *b)
{
    return strcoll(*(const char *const *)a, *(const char *const *)b);
}

static int quoted(const char *value)
{
    const char *s;
    if (dprintf(1, "'") < 0) return -1;
    for (s = value; *s; ++s)
        if ((*s == '\'' ? dprintf(1, "'\\''") : dprintf(1, "%c", *s)) < 0) return -1;
    return dprintf(1, "'") < 0 ? -1 : 0;
}

static int listing(struct csh_state *state, const char *name, unsigned mask)
{
    char **names;
    size_t i, count = 0;
    int status = 0;
    if (csh_state_names(state, &names) != CSH_STATE_OK) return problem(name, "out of memory");
    while (names[count]) ++count;
    qsort(names, count, sizeof(*names), compare_names);
    for (i = 0; i < count; ++i) {
        struct csh_variable_view v;
        csh_state_get_variable(state, names[i], &v);
        if (mask ? !(v.attributes & mask) : v.value == NULL) continue;
        if ((mask && dprintf(1, "%s ", name) < 0) || dprintf(1, "%s", names[i]) < 0 ||
            (v.value && (dprintf(1, "=") < 0 || quoted(v.value) < 0)) || dprintf(1, "\n") < 0) {
            status = problem(name, "cannot write output"); break;
        }
    }
    csh_state_environment_destroy(names);
    return status;
}

static char *cwd(void)
{
    size_t size = 256;
    for (;;) {
        char *s = malloc(size);
        if (!s) return NULL;
        if (getcwd(s, size)) return s;
        free(s);
        if (errno != ERANGE || size > SIZE_MAX / 2) return NULL;
        size *= 2;
    }
}

static int logical_valid(const char *s)
{
    struct stat a, b;
    const char *t;
    if (!s || *s != '/') return 0;
    for (t = s; *t;) {
        size_t n;
        while (*t == '/') ++t;
        n = strcspn(t, "/");
        if ((n == 1 && t[0] == '.') || (n == 2 && t[0] == '.' && t[1] == '.')) return 0;
        t += n;
    }
    return stat(s, &a) == 0 && stat(".", &b) == 0 && a.st_dev == b.st_dev && a.st_ino == b.st_ino;
}

static char *current(struct csh_state *state, int physical)
{
    struct csh_variable_view v;
    csh_state_get_variable(state, "PWD", &v);
    return !physical && logical_valid(v.value) ? strdup(v.value) : cwd();
}

int csh_builtin_initialize(struct csh_state *state)
{
    char parent[32];
    char *directory_name;
    enum csh_state_result result;
    snprintf(parent, sizeof(parent), "%ld", (long)getppid());
    if (csh_state_set_variable(state, "IFS", " \t\n") != CSH_STATE_OK ||
        csh_state_set_variable(state, "PPID", parent) != CSH_STATE_OK ||
        csh_state_set_variable(state, "OPTIND", "1") != CSH_STATE_OK)
        return 1;
    /* Keep a valid logical path, including symlinks. For over-PATH_MAX
     * imported paths this chooses the permitted retain-path alternative. */
    errno = 0;
    directory_name = current(state, 0);
    if (!directory_name) {
        if (errno == ENOMEM) return 1;
        /* When the physical cwd cannot be determined POSIX leaves PWD
         * unspecified. Select unset rather than retaining an invalid path. */
        return csh_state_unset_variable(state, "PWD") != CSH_STATE_OK;
    }
    result = csh_state_set_variable(state, "PWD", directory_name);
    free(directory_name);
    if (result != CSH_STATE_OK) return 1;
    return csh_state_update_attributes(state, "PWD", CSH_VAR_EXPORT, 0) != CSH_STATE_OK;
}

static char *join(const char *a, const char *b)
{
    size_t n = strlen(a), m = strlen(b);
    char *s;
    if (n > SIZE_MAX - m - 2) return NULL;
    s = malloc(n + m + 2);
    if (s) { memcpy(s, a, n); s[n] = '/'; memcpy(s+n+1, b, m+1); }
    return s;
}

/* Resolve dot components before chdir, but verify that a preceding component
 * is a directory: missing/.. and regular-file/.. must not disappear. */
static int normalize(char *s)
{
    size_t read = 0, used = (s[0] == '/' && s[1] == '/' && s[2] != '/') ? 2 : 1;
    while (s[read] == '/') ++read;
    while (s[read]) {
        size_t n = strcspn(s + read, "/"), next = read + n;
        while (s[next] == '/') ++next;
        if (n == 1 && s[read] == '.') { read = next; continue; }
        if (n == 2 && s[read] == '.' && s[read+1] == '.') {
            struct stat st;
            char saved = s[used];
            s[used] = 0;
            if (stat(s, &st) < 0 || !S_ISDIR(st.st_mode)) { s[used] = saved; return -1; }
            s[used] = saved;
            if (used > 1) {
                while (used > 1 && s[used-1] != '/') --used;
                if (used > 1) --used;
            }
        } else {
            if (s[used-1] != '/') s[used++] = '/';
            memmove(s+used, s+read, n); used += n;
        }
        read = next;
    }
    s[used] = 0;
    return 0;
}

static int directory(struct csh_state *state, size_t argc, char *const argv[])
{
    int physical = 0, require_cwd = 0, print = 0, fd = -1, status = 1;
    size_t i = 1;
    char *old = NULL, *target = NULL, *newpwd = NULL;
    const char *operand;
    struct csh_variable_view v;
    struct csh_state_checkpoint *checkpoint = NULL;
    int is_cd = !strcmp(argv[0], "cd");
    for (; i < argc && argv[i][0] == '-' && argv[i][1]; ++i) {
        const char *o = argv[i]+1;
        if (!strcmp(argv[i], "--")) { ++i; break; }
        for (; *o; ++o) {
            if (*o == 'L') physical = 0;
            else if (*o == 'P') physical = 1;
            else if (*o == 'e' && is_cd) require_cwd = 1;
            else return problem(argv[0], "invalid option");
        }
    }
    if (argc-i > (is_cd ? 1u : 0u)) return problem(argv[0], "too many operands");
    if (!is_cd) {
        newpwd = current(state, physical);
        if (newpwd) {
            status = csh_write_text(1, newpwd) < 0 || csh_write_text(1, "\n") < 0;
            if (status) problem("pwd", "cannot write output");
        }
        else problem("pwd", "cannot determine current directory");
        free(newpwd); return status;
    }
    if (i == argc || !strcmp(argv[i], "-")) {
        print = i != argc;
        csh_state_get_variable(state, print ? "OLDPWD" : "HOME", &v);
        operand = v.value;
        if (!operand || !*operand) return problem("cd", "HOME or OLDPWD is unset or empty");
    } else operand = argv[i];
    if (!*operand) return problem("cd", "empty directory operand");
    old = current(state, 0);
    if (*operand != '/' && strncmp(operand, "./", 2) && strcmp(operand, ".") &&
        strncmp(operand, "../", 3) && strcmp(operand, "..") && !print) {
        const char *part;
        csh_state_get_variable(state, "CDPATH", &v);
        part = v.value;
        while (part) {
            const char *end = strchr(part, ':');
            size_t n = end ? (size_t)(end-part) : strlen(part);
            char *prefix = strndup(part, n);
            struct stat st;
            if (!prefix) goto done;
            target = join(n ? prefix : ".", operand); free(prefix);
            if (!target) goto done;
            if (stat(target, &st) == 0 && S_ISDIR(st.st_mode)) { print = n != 0; break; }
            free(target); target = NULL; part = end ? end+1 : NULL;
        }
    }
    if (!target) target = strdup(operand);
    if (!target) goto done;
    if (!physical) {
        if (target[0] != '/' && old) {
            char *absolute = join(old, target);
            free(target); target = absolute;
            if (!target) goto done;
        }
        if (target[0] == '/' && normalize(target) < 0) goto done;
    }
    fd = open(".", O_RDONLY);
    if (fd < 0 || csh_state_save(state, &checkpoint) != CSH_STATE_OK) goto done;
    if (chdir(target) < 0) goto done;
    newpwd = !physical && target[0] == '/' ? strdup(target) : cwd();
    if (!newpwd) {
        /* Without -e, POSIX permits success when physical cwd is unavailable. */
        if (physical && !require_cwd && !print) {
            if (csh_state_unset_variable(state, "PWD") == CSH_STATE_OK &&
                csh_state_set_variable(state, "OLDPWD", old ? old : "") == CSH_STATE_OK) status = 0;
        }
    } else if (csh_state_set_variable(state, "OLDPWD", old ? old : "") == CSH_STATE_OK &&
               csh_state_set_variable(state, "PWD", newpwd) == CSH_STATE_OK) status = 0;
    if (status) {
        if (fchdir(fd) < 0) problem("cd", "cannot restore directory after state failure");
        csh_state_restore(state, &checkpoint);
    } else if (print && (csh_write_text(1, newpwd) < 0 ||
        csh_write_text(1, "\n") < 0)) status = 1;
done:
    if (status) problem("cd", "cannot change directory or update directory state");
    if (fd >= 0) close(fd);
    csh_state_checkpoint_destroy(checkpoint);
    free(old); free(target); free(newpwd);
    return status;
}

static int report_option(const char *name, int enabled, int reusable)
{
    char line[64];
    int length = reusable ? snprintf(line, sizeof(line), "set %co %s\n", enabled ? '-' : '+', name) :
        snprintf(line, sizeof(line), "%s %s\n", name, enabled ? "on" : "off");
    if (length < 0 || (size_t)length >= sizeof(line)) return -1;
    return csh_write_bytes(STDOUT_FILENO, line, (size_t)length);
}

int csh_builtin_set(struct csh_state *state, size_t argc, char *const argv[], int monitor_available)
{
    struct csh_state_info info;
    size_t i = 1;
    int replace = 0, report = 0;
    unsigned options;
    csh_state_get_info(state, &info);
    if (argc == 1) return listing(state, "set", 0);
    options = info.options & CSH_SETTABLE_OPTIONS;
    while (i < argc) {
        const char *arg = argv[i++];
        size_t j;
        int enable = arg[0] == '-';
        if (!strcmp(arg, "--")) { replace = 1; break; }
        /* Unspecified lone '-' follows the traditional disable-v/x choice. */
        if (!strcmp(arg, "-")) { options &= ~(CSH_OPT_VERBOSE | CSH_OPT_XTRACE); break; }
        if ((arg[0] != '-' && arg[0] != '+') || !arg[1]) { --i; break; }
        for (j = 1; arg[j]; ++j) {
            unsigned bit;
            if (arg[j] == 'o') {
                const char *name = arg + j + 1;
                if (!*name && (i == argc || argv[i][0] == '-' || argv[i][0] == '+')) {
                    report = enable ? 1 : 2;
                    break;
                }
                if (!*name) name = argv[i++];
                bit = csh_option_name(name);
                j = strlen(arg) - 1;
            } else bit = csh_option_letter(arg[j]);
            if (!bit) return problem("set", "invalid option");
            if (enable) options |= bit; else options &= ~bit;
        }
    }
    if ((options & CSH_OPT_MONITOR) && !monitor_available)
        return problem("set", "job control unavailable");
    if (replace || i < argc) {
        int status = state_result("set", csh_state_set_parameters(state, argc - i,
            (const char *const *)(argv + i)));
        if (status) return status;
    }
    csh_state_update_options(state, options, CSH_SETTABLE_OPTIONS & ~options);
    if (report) {
#define REPORT(bit, name, ch) \
        if (report_option(name, (options & CSH_OPT_##bit) != 0, report == 2) < 0) \
            return problem("set", "cannot write output");
        CSH_OPTION_LIST(REPORT)
#undef REPORT
    }
    return 0;
}

int csh_state_builtin_run(struct csh_state *state, size_t argc, char *const argv[])
{
    if (!strcmp(argv[0], "cd")) csh_state_hash_clear(state);
    const char *name = argv[0];
    size_t i = 1;
    int status = 0;
    if (!strcmp(name, ":")) return 0;
    if (!strcmp(name, "cd") || !strcmp(name, "pwd") ||
        !strcmp(name, "command") || !strcmp(name, "type") || !strcmp(name, "hash") ||
        !strcmp(name, "alias") || !strcmp(name, "unalias") || !strcmp(name, "read") ||
        !strcmp(name, "getopts") || !strcmp(name, "umask") || !strcmp(name, "ulimit")) return directory(state, argc, argv);
    if (!strcmp(name, "set")) {
        if (argc == 1) return listing(state, name, 0);
        return csh_builtin_set(state, argc, argv, 1);
    }
    if (!strcmp(name, "shift")) {
        struct csh_state_info info;
        size_t n = 1, j, count;
        const char **args;
        if (argc > 2) return problem(name, "too many operands");
        if (argc == 2) {
            const unsigned char *s = (const unsigned char *)argv[1];
            n = 0;
            if (!*s) return problem(name, "invalid count");
            for (; *s; ++s) {
                if (*s < '0' || *s > '9' || n > (SIZE_MAX-(*s-'0'))/10) return problem(name, "invalid count");
                n = n*10 + (*s-'0');
            }
        }
        csh_state_get_info(state, &info);
        if (n > info.argument_count) return problem(name, "count exceeds positional parameters");
        count = info.argument_count-n;
        args = count ? malloc(count*sizeof(*args)) : NULL;
        if (count && !args) return problem(name, "out of memory");
        for (j = 0; j < count; ++j) args[j] = csh_state_parameter(state, n+j+1);
        status = state_result(name, csh_state_set_parameters(state, count, args));
        free(args); return status;
    }
    if (!strcmp(name, "unset")) {
        int functions = i < argc && !strcmp(argv[i], "-f");
        if (functions || (i < argc && !strcmp(argv[i], "-v"))) ++i;
        if (i < argc && !strcmp(argv[i], "--")) ++i;
        else if (i < argc && argv[i][0] == '-') return problem(name, "invalid option");
        for (; i < argc; ++i) status |= state_result(name, functions ?
            csh_state_set_function(state, argv[i], NULL) : csh_state_unset_variable(state, argv[i]));
        return status;
    }
    if (!strcmp(name, "export") || !strcmp(name, "readonly")) {
        unsigned mask = !strcmp(name, "export") ? CSH_VAR_EXPORT : CSH_VAR_READONLY;
        if (argc == 1 || (argc == 2 && !strcmp(argv[1], "-p"))) return listing(state, name, mask);
        if (!strcmp(argv[i], "--")) ++i;
        else if (argv[i][0] == '-') return problem(name, "invalid option");
        for (; i < argc; ++i) {
            char *copy = strdup(argv[i]), *equal;
            struct csh_state_checkpoint *save = NULL;
            enum csh_state_result r;
            if (!copy) { status = problem(name, "out of memory"); break; }
            equal = strchr(copy, '=');
            if (equal) *equal++ = 0;
            r = csh_state_save(state, &save);
            if (r == CSH_STATE_OK && equal) r = csh_state_set_variable(state, copy, equal);
            if (r == CSH_STATE_OK) r = csh_state_update_attributes(state, copy, mask, 0);
            if (r != CSH_STATE_OK && save) csh_state_restore(state, &save);
            csh_state_checkpoint_destroy(save);
            status |= state_result(name, r); free(copy);
        }
        return status;
    }
    return problem(name, "unknown state builtin");
}
