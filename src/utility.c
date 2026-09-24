/* Utilities which mutate or inspect the current shell environment. */
#include "cshell/builtin.h"
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/times.h>
#include <unistd.h>

static int problem(const char *name, const char *message)
{
    dprintf(2, "cshell: %s: %s\n", name, message);
    return 2;
}
static int assign(struct csh_state *state, const char *name, const char *value)
{
    enum csh_state_result rc = value ? csh_state_set_variable(state, name, value) :
        csh_state_unset_variable(state, name);
    return rc == CSH_STATE_OK ? 0 : problem(name, rc == CSH_STATE_READONLY ?
        "readonly variable" : rc == CSH_STATE_NOMEM ? "out of memory" : "invalid variable name");
}
static int white(unsigned char c) { return c == ' ' || c == '\t' || c == '\n'; }
static int delimiter(const char *ifs, unsigned char c, unsigned char quoted)
{
    return c && !quoted && strchr(ifs, c) != NULL;
}
static int read_builtin(struct csh_state *state, size_t argc, char *const argv[])
{
    size_t first = 1, used = 0, capacity = 128, i, pos = 0;
    int raw = 0, escaped = 0, status = 1;
    unsigned char end = '\n', *quoted;
    char *line;
    struct csh_variable_view view;
    char *ifs;
    while (first < argc && argv[first][0] == '-' && argv[first][1]) {
        const char *opt = argv[first++] + 1;
        if (!strcmp(opt, "-")) break;
        while (*opt) {
            if (*opt == 'r') { raw = 1; ++opt; }
            else if (*opt == 'd') {
                ++opt;
                if (!*opt) {
                    if (first == argc) return problem("read", "-d requires a delimiter");
                    opt = argv[first++];
                }
                end = (unsigned char)*opt;
                break;
            } else return problem("read", "invalid option");
        }
    }
    if (first == argc) return problem("read", "variable required");
    for (i = first; i < argc; ++i) {
        if (csh_state_get_variable(state, argv[i], &view) != CSH_STATE_OK)
            return problem("read", "invalid variable name");
        if (view.attributes & CSH_VAR_READONLY) return problem("read", "readonly variable");
    }
    csh_state_get_variable(state, "IFS", &view);
    ifs = strdup(view.value ? view.value : " \t\n");
    line = malloc(capacity); quoted = malloc(capacity);
    if (!line || !quoted || !ifs) { free(line); free(quoted); free(ifs); return problem("read", "out of memory"); }
    for (;;) {
        unsigned char byte;
        ssize_t n = read(0, &byte, 1);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { status = problem("read", "cannot read input"); break; }
        if (n == 0) break;
        if (!escaped && byte == end) { status = 0; break; }
        if (!raw && !escaped && byte == '\\') { escaped = 1; continue; }
        if (escaped && byte == '\n') {
            struct csh_state_info info;
            csh_state_get_info(state, &info);
            if ((info.options & CSH_OPT_INTERACTIVE) && isatty(0)) {
                csh_state_get_variable(state, "PS2", &view);
                dprintf(2, "%s", view.value ? view.value : "> ");
            }
            escaped = 0; continue;
        }
        if (!byte) { escaped = 0; continue; }
        if (used + 1 == capacity) {
            char *next;
            unsigned char *q;
            if (capacity > SIZE_MAX / 2) { status = problem("read", "input too large"); break; }
            capacity *= 2;
            next = realloc(line, capacity);
            if (!next) { status = problem("read", "out of memory"); break; }
            line = next;
            q = realloc(quoted, capacity);
            if (!q) { status = problem("read", "out of memory"); break; }
            quoted = q;
        }
        line[used] = (char)byte; quoted[used++] = (unsigned char)escaped; escaped = 0;
    }
    line[used] = 0;
    if (status <= 1) for (i = first; i < argc; ++i) {
        size_t start, finish, next;
        while (pos < used && white((unsigned char)line[pos]) && delimiter(ifs, line[pos], quoted[pos])) ++pos;
        start = pos;
        while (pos < used && !delimiter(ifs, line[pos], quoted[pos])) ++pos;
        finish = pos;
        if (i + 1 == argc) {
            /* Last variable receives the remaining fields and intervening separators.
             * A lone terminating separator is removed just as for one field. */
            next = pos;
            while (next < used && white((unsigned char)line[next]) && delimiter(ifs, line[next], quoted[next])) ++next;
            if (next < used && delimiter(ifs, line[next], quoted[next])) ++next;
            while (next < used && white((unsigned char)line[next]) && delimiter(ifs, line[next], quoted[next])) ++next;
            if (next < used) {
                finish = used;
                while (finish > start && white((unsigned char)line[finish-1]) && delimiter(ifs, line[finish-1], quoted[finish-1])) --finish;
            }
        } else {
            while (pos < used && white((unsigned char)line[pos]) && delimiter(ifs, line[pos], quoted[pos])) ++pos;
            if (pos < used && delimiter(ifs, line[pos], quoted[pos])) ++pos;
        }
        { char saved = line[finish]; line[finish] = 0;
          if (assign(state, argv[i], line + start)) status = 2;
          line[finish] = saved; }
        if (status > 1) break;
    }
    free(ifs); free(line); free(quoted);
    return status;
}

static const char *option_argument(struct csh_state *state, size_t argc,
    char *const argv[], size_t first, size_t index)
{
    return first < argc ? (index <= argc - first ? argv[first + index - 1] : NULL) :
        csh_state_parameter(state, index);
}
static int getopts_builtin(struct csh_state *state, size_t argc, char *const argv[])
{
    size_t first = 1, index = 1, offset = csh_state_getopts_offset(state);
    const char *spec, *name, *arg, *found, *value = NULL;
    struct csh_variable_view view;
    char output[2] = {'?', 0}, number[32], bad[2] = {0};
    int status = 0, silent;
    if (first < argc && !strcmp(argv[first], "--")) ++first;
    if (argc - first < 2) return problem("getopts", "optstring and variable required");
    spec = argv[first++]; name = argv[first++]; silent = spec[0] == ':';
    csh_state_get_variable(state, "OPTIND", &view);
    if (view.value) {
        char *tail;
        uintmax_t n;
        errno = 0; n = strtoumax(view.value, &tail, 10);
        if (!*view.value || *tail || *view.value == '-' || !n || n > SIZE_MAX || errno)
            return problem("getopts", "invalid OPTIND");
        index = (size_t)n;
    }
    arg = option_argument(state, argc, argv, first, index);
    if (!arg || arg[0] != '-' || !arg[1] || !strcmp(arg, "--")) {
        if (arg && !strcmp(arg, "--")) ++index;
        status = 1; offset = 0; goto publish;
    }
    if (!offset || offset >= strlen(arg)) offset = 1;
    bad[0] = arg[offset++]; output[0] = bad[0];
    if (!arg[offset]) { ++index; offset = 0; }
    found = bad[0] == ':' || bad[0] == '?' ? NULL : strchr(spec + silent, bad[0]);
    if (!found) {
        output[0] = '?';
        if (silent) value = bad;
        else dprintf(2, "cshell: getopts: illegal option -- %c\n", bad[0]);
    } else if (found[1] == ':') {
        if (offset) { value = arg + offset; ++index; offset = 0; }
        else { value = option_argument(state, argc, argv, first, index); if (value) ++index; }
        if (!value) {
            output[0] = silent ? ':' : '?';
            if (silent) value = bad;
            else dprintf(2, "cshell: getopts: option requires an argument -- %c\n", bad[0]);
        }
    }
publish:
    /* Copy before assignments: explicit args may be borrowed, positionals stable. */
    snprintf(number, sizeof(number), "%zu", index);
    if (assign(state, name, output) || assign(state, "OPTARG", value) || assign(state, "OPTIND", number)) return 2;
    csh_state_set_getopts_offset(state, offset);
    return status;
}

static int umask_builtin(size_t argc, char *const argv[])
{
    size_t first = 1;
    int symbolic = 0;
    mode_t old, mode;
    if (first < argc && !strcmp(argv[first], "-S")) { symbolic = 1; ++first; }
    if (first < argc && !strcmp(argv[first], "--")) ++first;
    if (argc - first > 1) return problem("umask", "too many operands");
    old = umask(0); umask(old);
    if (first == argc) {
        if (!symbolic) return dprintf(1, "%04o\n", (unsigned)old) < 0;
        mode = ~old;
        return dprintf(1, "u=%s%s%s,g=%s%s%s,o=%s%s%s\n",
            mode&0400?"r":"", mode&0200?"w":"", mode&0100?"x":"",
            mode&0040?"r":"", mode&0020?"w":"", mode&0010?"x":"",
            mode&0004?"r":"", mode&0002?"w":"", mode&0001?"x":"") < 0;
    }
    { const char *p = argv[first];
      if (*p >= '0' && *p <= '7') {
          unsigned n = 0;
          do { n = n * 8 + (unsigned)(*p++ - '0'); if (n > 0777) return problem("umask", "invalid mask"); }
          while (*p >= '0' && *p <= '7');
          if (*p) return problem("umask", "invalid mask");
          umask((mode_t)n); return 0;
      }
      mode = (~old) & 0777;
      do {
          mode_t who = 0;
          while (*p && strchr("ugoa", *p)) {
              who |= *p == 'u' ? 0700 : *p == 'g' ? 0070 : *p == 'o' ? 0007 : 0777; ++p;
          }
          if (!who) who = 0777;
          if (!*p || !strchr("+-=", *p)) return problem("umask", "invalid mask");
          do {
              char op = *p++;
              mode_t bits = 0;
              while (*p && strchr("rwxXstugo", *p)) {
                  if (*p == 'r') bits |= 0444;
                  else if (*p == 'w') bits |= 0222;
                  else if (*p == 'x' || (*p == 'X' && (mode & 0111))) bits |= 0111;
                  else if (strchr("ugo", *p)) {
                      mode_t group = (mode >> (*p == 'u' ? 6 : *p == 'g' ? 3 : 0)) & 7;
                      bits |= group | (group << 3) | (group << 6);
                  }
                  ++p;
              }
              bits &= who;
              if (op == '=') mode = (mode & ~who) | bits;
              else if (op == '+') mode |= bits;
              else mode &= ~bits;
          } while (*p && strchr("+-=", *p));
          if (!*p) break;
          if (*p++ != ',' || !*p) return problem("umask", "invalid mask");
      } while (*p);
      umask((~mode) & 0777);
    }
    return 0;
}

static int times_builtin(size_t argc, char *const argv[])
{
    struct tms t;
    long ticks = sysconf(_SC_CLK_TCK);
    clock_t values[4];
    size_t i;
    if (argc > 1 && !(argc == 2 && !strcmp(argv[1], "--"))) return problem("times", "unexpected operand");
    if (ticks <= 0 || times(&t) == (clock_t)-1) return problem("times", "cannot obtain process times");
    values[0] = t.tms_utime; values[1] = t.tms_stime; values[2] = t.tms_cutime; values[3] = t.tms_cstime;
    for (i = 0; i < 4; ++i) {
        double seconds = (double)values[i] / ticks;
        long minutes = (long)(seconds / 60);
        if (dprintf(1, "%ldm%.3fs%c", minutes, seconds - minutes * 60, i % 2 ? '\n' : ' ') < 0) return 1;
    }
    return 0;
}
struct resource { char option; int resource; unsigned unit; };
static const struct resource resources[] = {
    {'c', RLIMIT_CORE, 512}, {'d', RLIMIT_DATA, 1024}, {'f', RLIMIT_FSIZE, 512},
    {'n', RLIMIT_NOFILE, 1}, {'s', RLIMIT_STACK, 1024}, {'v', RLIMIT_AS, 1024}, {'t', RLIMIT_CPU, 1}
};
static int ulimit_builtin(size_t argc, char *const argv[])
{
    size_t first = 1, i, selected = 2;
    int hard = 0, soft = 0, all = 0;
    struct rlimit limit;
    while (first < argc && argv[first][0] == '-' && argv[first][1]) {
        const char *p = argv[first++] + 1;
        if (!strcmp(p, "-")) break;
        for (; *p; ++p) {
            if (*p == 'H') hard = 1;
            else if (*p == 'S') soft = 1;
            else if (*p == 'a') all = 1;
            else {
                for (i = 0; i < sizeof(resources)/sizeof(*resources) && resources[i].option != *p; ++i) {}
                if (i == sizeof(resources)/sizeof(*resources)) return problem("ulimit", "invalid option");
                selected = i;
            }
        }
    }
    if (argc - first > 1 || (all && first != argc)) return problem("ulimit", "invalid operands");
    for (i = 0; i < sizeof(resources)/sizeof(*resources); ++i) {
        const struct resource *r = &resources[i];
        rlim_t value;
        if (!all && i != selected) continue;
        if (getrlimit(r->resource, &limit)) return problem("ulimit", "cannot get resource limit");
        if (first < argc) {
            const char *s = argv[first]; char *end;
            uintmax_t n;
            if (!strcmp(s, "unlimited")) value = RLIM_INFINITY;
            else {
                errno = 0; n = strtoumax(s, &end, 10);
                if (!*s || *s == '-' || *end || errno || n > (uintmax_t)RLIM_INFINITY / r->unit)
                    return problem("ulimit", "invalid limit");
                value = (rlim_t)(n * r->unit);
            }
            if (hard || !soft) limit.rlim_max = value;
            if (soft || !hard) limit.rlim_cur = value;
            if (setrlimit(r->resource, &limit)) return problem("ulimit", "cannot set resource limit");
        } else {
            value = hard ? limit.rlim_max : limit.rlim_cur;
            if (all && dprintf(1, "-%c ", r->option) < 0) return 1;
            if ((value == RLIM_INFINITY ? dprintf(1, "unlimited\n") :
                dprintf(1, "%ju\n", (uintmax_t)value / r->unit)) < 0) return 1;
        }
    }
    return 0;
}
int csh_utility_run(struct csh_state *state, size_t argc, char *const argv[])
{
    if (!strcmp(argv[0], "read")) return read_builtin(state, argc, argv);
    if (!strcmp(argv[0], "getopts")) return getopts_builtin(state, argc, argv);
    if (!strcmp(argv[0], "umask")) return umask_builtin(argc, argv);
    if (!strcmp(argv[0], "ulimit")) return ulimit_builtin(argc, argv);
    return times_builtin(argc, argv);
}
