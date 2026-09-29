/* Narrow Issue 8 adapters around GNU gettext programs. Translation/PO/MO
 * handling remains vendor-owned. A native launcher preserves inherited signal
 * dispositions across exec, including SIGPIPE (a Python launcher would not).
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#ifndef CATALOG_ADAPTER_TEST
#include "catalog_providers.h"
#endif

static char *c_string(const char *source)
{
    char *result = malloc(strlen(source) + 1), *out;
    if (!result) return NULL;
    out = result;
    while (*source) {
        unsigned int value;
        const char *simple, *found, *digits = "0123456789abcdefABCDEF";
        if (*source != '\\' || !source[1]) { *out++ = *source++; continue; }
        ++source;
        simple = "abfnrtv\\\"'?";
        found = strchr(simple, *source);
        if (found) {
            *out++ = "\a\b\f\n\r\t\v\\\"'?"[found - simple];
            ++source;
        } else if (*source >= '0' && *source <= '7') {
            int count = 0;
            value = 0;
            while (count++ < 3 && *source >= '0' && *source <= '7')
                value = value * 8 + (unsigned int)(*source++ - '0');
            *out++ = (char)value;
        } else if (*source == 'x' && source[1] &&
                   strchr(digits, source[1])) {
            ++source;
            value = 0;
            while (*source && (found = strchr(digits, *source)) != NULL) {
                unsigned int digit = (unsigned int)(found - digits);
                value = value * 16 + (digit >= 16 ? digit - 6 : digit);
                ++source;
            }
            *out++ = (char)value;
        } else {
            /* Non-C escapes have no portable contract; preserve literally. */
            *out++ = '\\'; *out++ = *source++;
        }
    }
    *out = 0;
    return result;
}

/* Stores owned decoded operands separately from borrowed/static argv entries. */
static int adapt(const char *name, int argc, char **argv, char ***arguments, char ***owned)
{
    size_t capacity = (size_t)argc + 4, used = 0, allocated = 0;
    int index, many = 0, escape = 0, msgfmt = !strcmp(name, "msgfmt");
    char **out, **copies;
    for (index = 0; index < argc; ++index) capacity += strlen(argv[index]);
    out = calloc(capacity, sizeof(*out));
    copies = calloc((size_t)argc + 1, sizeof(*copies));
    if (!out || !copies) { free(out); free(copies); return -1; }
    *arguments = out; *owned = copies;
    for (index = 0; index < argc; ++index) {
        const char *option = argv[index];
        if (option[0] != '-' || !option[1]) break;
        if (!strcmp(option, "--")) { ++index; break; }
        for (++option; *option; ++option) {
            char flag = *option;
            const char *value;
            if ((msgfmt && (flag == 'o' || flag == 'D')) || (!msgfmt && flag == 'd')) {
                if (option[1]) value = option + 1;
                else if (++index < argc) value = argv[index];
                else { fprintf(stderr, "%s: option -%c requires an argument\n", name, flag); return 2; }
                out[used++] = flag == 'o' ? "-o" : flag == 'D' ? "-D" : "-d";
                out[used++] = (char *)value;
                break;
            }
            if (msgfmt && flag == 'S') out[used++] = "--strict";
            else if (msgfmt && flag == 'c') out[used++] = "-c";
            else if (msgfmt && flag == 'f') out[used++] = "-f";
            else if (msgfmt && flag == 'v') out[used++] = "-v";
            else if (!msgfmt && (flag == 'e' || flag == 'E')) escape = flag == 'e';
            else if (!strcmp(name, "gettext") && flag == 's') { many = 1; out[used++] = "-s"; }
            else if (!strcmp(name, "gettext") && flag == 'n') out[used++] = "-n";
            else { fprintf(stderr, "%s: unrecognized option -%c\n", name, flag); return 2; }
        }
    }
    if (!msgfmt) out[used++] = "-E"; /* permitted default, also disables vendor decoding */
    out[used++] = "--";
    {
        int plural = !strcmp(name, "ngettext");
        int start = index + (!many && argc - index == (plural ? 4 : 2));
        int end = argc - plural;
        for (; index < argc; ++index) {
            if (escape && index >= start && index < end) {
                char *decoded = c_string(argv[index]);
                if (!decoded) return -1;
                copies[allocated++] = decoded;
                out[used++] = decoded;
            } else out[used++] = argv[index];
        }
    }
    return 0;
}

static void release(char **arguments, char **owned)
{
    size_t index;
    if (owned) for (index = 0; owned[index]; ++index) free(owned[index]);
    free(owned); free(arguments);
}

#ifndef CATALOG_ADAPTER_TEST
int main(int argc, char **argv)
{
    const char *name = strrchr(argv[0], '/'), *provider;
    char **arguments = NULL, **owned = NULL, **command;
    size_t count = 0, index;
    int status;
    name = name ? name + 1 : argv[0];
    if (!strcmp(name, "gettext")) provider = CATALOG_GETTEXT;
    else if (!strcmp(name, "ngettext")) provider = CATALOG_NGETTEXT;
    else if (!strcmp(name, "msgfmt")) provider = CATALOG_MSGFMT;
    else { fprintf(stderr, "catalog adapter: invoke as gettext, ngettext or msgfmt\n"); return 2; }
    status = adapt(name, argc - 1, argv + 1, &arguments, &owned);
    if (status) {
        if (status < 0) perror(name);
        release(arguments, owned);
        return status < 0 ? 1 : status;
    }
    while (arguments[count]) ++count;
    command = calloc(count + 2, sizeof(*command));
    if (!command) { perror(name); release(arguments, owned); return 1; }
    command[0] = (char *)provider;
    for (index = 0; index < count; ++index) command[index + 1] = arguments[index];
    execv(provider, command);
    perror(name);
    free(command); release(arguments, owned);
    return 126;
}
#endif
