/* CSH-081 standalone base-profile tabs. No XSI language/margin extensions.
 * Terminal capabilities are supplied by ncurses; no host state is installed. */
#define _POSIX_C_SOURCE 200809L
#include <curses.h>
#include <term.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <limits.h>
#include <locale.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int error(const char *message)
{
    fprintf(stderr, "tabs: %s\n", message);
    return 1;
}

static int emit(const char *capability)
{
    return tputs(capability, 1, putchar) == ERR || ferror(stdout);
}

static int blank(int c)
{
    return c == ' ' || c == '\t';
}

int main(int argc, char **argv)
{
    char *type = NULL, *list = NULL;
    const char *clear_capability, *tab_capability, *carriage;
    int interval = 8, width, status, i, column = 0;
    int *stops = NULL, count = 0;
    struct winsize window;
    (void)setlocale(LC_ALL, "");
    for (i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--")) {
            if (++i < argc)
                list = argv[i++];
            if (i != argc)
                return error("expected one tab list");
            break;
        }
        if (!strncmp(argv[i], "-T", 2)) {
            type = argv[i] + 2;
            if (!*type) {
                if (++i == argc)
                    return error("-T requires a terminal type");
                type = argv[i];
            }
        } else if (argv[i][0] == '-' && argv[i][1] >= '0' &&
                   argv[i][1] <= '9' && !argv[i][2]) {
            interval = argv[i][1] - '0';
        } else if (argv[i][0] != '-' && !list) {
            list = argv[i];
        } else {
            return error("invalid option or tab list");
        }
    }
    if (!type && (!getenv("TERM") || !*getenv("TERM")))
        type = "dumb";
    if (setupterm(type, STDOUT_FILENO, &status) != OK)
        return error("terminal type is unavailable");
    clear_capability = tigetstr("tbc");
    tab_capability = tigetstr("hts");
    carriage = tigetstr("cr");
    if (!clear_capability || clear_capability == (char *)-1 ||
        !tab_capability || tab_capability == (char *)-1 || !carriage || carriage == (char *)-1) {
        del_curterm(cur_term);
        return error("terminal does not support setting tabs");
    }
    width = tigetnum("cols");
    if (!ioctl(STDOUT_FILENO, TIOCGWINSZ, &window) && window.ws_col)
        width = window.ws_col;
    /* A finite bound for this provider. Real PTY widths fit in unsigned short. */
    if (width < 1 || width > 65535) {
        del_curterm(cur_term);
        return error("terminal width is unavailable or exceeds 65535 columns");
    }
    stops = calloc((size_t)width, sizeof(*stops));
    if (!stops) {
        del_curterm(cur_term);
        return error(strerror(errno));
    }
    if (list) {
        char *p = list, *end;
        long previous = 0;
        while (*p) {
            int relative = *p == '+';
            long value;
            if (relative)
                ++p;
            if (*p < '0' || *p > '9' || (relative && !count))
                goto invalid;
            errno = 0;
            value = strtol(p, &end, 10);
            if (errno || value < 1 || value > width ||
                (relative && value > width - previous))
                goto invalid;
            if (relative)
                value += previous;
            if (value <= previous || value > width)
                goto invalid;
            stops[count++] = (int)value - 1;
            previous = value;
            p = end;
            if (*p) {
                if (*p != ',' && !blank(*p))
                    goto invalid;
                while (blank(*p))
                    ++p;
                if (*p == ',')
                    ++p;
                while (blank(*p))
                    ++p;
                if (!*p)
                    goto invalid;
            }
        }
        if (!count)
            goto invalid;
    } else if (interval) {
        for (i = 0; i < width; i += interval)
            stops[count++] = i;
    }
    status = emit(carriage) || emit(clear_capability);
    for (i = 0; i < count && !status; ++i) {
        while (column < stops[i] && !status) {
            status = putchar(' ') == EOF;
            ++column;
        }
        if (!status)
            status = emit(tab_capability);
    }
    if (!status)
        status = emit(carriage);
    if (fflush(stdout) == EOF)
        status = 1;
    free(stops);
    del_curterm(cur_term);
    return status ? error("terminal output failed") : 0;
invalid:
    free(stops);
    del_curterm(cur_term);
    return error("tab stops must ascend within the terminal width");
}
