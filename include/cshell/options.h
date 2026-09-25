#ifndef CSHELL_OPTIONS_H
#define CSHELL_OPTIONS_H

#include <string.h>

/* Shared invocation/runtime option bits. */
enum csh_shell_option {
    CSH_OPT_INTERACTIVE = 1u << 0,
    CSH_OPT_ALLEXPORT = 1u << 1,
    CSH_OPT_ERREXIT = 1u << 2,
    CSH_OPT_NOGLOB = 1u << 3,
    CSH_OPT_NOEXEC = 1u << 4,
    CSH_OPT_NOUNSET = 1u << 5,
    CSH_OPT_VERBOSE = 1u << 6,
    CSH_OPT_XTRACE = 1u << 7,
    CSH_OPT_NOCLOBBER = 1u << 8,
    CSH_OPT_PIPEFAIL = 1u << 9,
    CSH_OPT_MONITOR = 1u << 10,
    CSH_OPT_NOTIFY = 1u << 11,
    CSH_OPT_HASHALL = 1u << 12,
    CSH_OPT_IGNOREEOF = 1u << 13,
    CSH_OPT_NOLOG = 1u << 14
};

/* One inventory for parsing, reports and $-. Zero denotes a named-only option.
 * hashall is the descriptive extension name for the standard's -h. */
#define CSH_OPTION_LIST(X) \
    X(ALLEXPORT, "allexport", 'a') \
    X(NOTIFY, "notify", 'b') \
    X(NOCLOBBER, "noclobber", 'C') \
    X(ERREXIT, "errexit", 'e') \
    X(NOGLOB, "noglob", 'f') \
    X(HASHALL, "hashall", 'h') \
    X(MONITOR, "monitor", 'm') \
    X(NOEXEC, "noexec", 'n') \
    X(NOUNSET, "nounset", 'u') \
    X(VERBOSE, "verbose", 'v') \
    X(XTRACE, "xtrace", 'x') \
    X(PIPEFAIL, "pipefail", 0) \
    X(IGNOREEOF, "ignoreeof", 0) \
    X(NOLOG, "nolog", 0)

static inline unsigned csh_option_letter(char letter)
{
#define LETTER(bit, name, ch) if ((ch) && letter == (ch)) return CSH_OPT_##bit;
    CSH_OPTION_LIST(LETTER)
#undef LETTER
    return 0;
}

static inline unsigned csh_option_name(const char *value)
{
#define NAME(bit, name, ch) if (!strcmp(value, name)) return CSH_OPT_##bit;
    CSH_OPTION_LIST(NAME)
#undef NAME
    return 0;
}

#define CSH_OPTION_MASK(bit, name, ch) | CSH_OPT_##bit
#define CSH_SETTABLE_OPTIONS (0 CSH_OPTION_LIST(CSH_OPTION_MASK))

#endif
