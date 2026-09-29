/* CSH-072 Issue-8 readlink/realpath providers for the opt-in PATH only.
 * libc retains filesystem/permission ownership. No shell runtime linkage.
 */
#define _XOPEN_SOURCE 700
#include <errno.h>
#include <locale.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static char *join(const char *a, const char *b)
{
    size_t x = strlen(a), y = strlen(b);
    char *result;
    if (y > SIZE_MAX - 2 || x > SIZE_MAX - y - 2) {
        errno = ENOMEM;
        return NULL;
    }
    result = malloc(x + y + 2);
    if (result) {
        memcpy(result, a, x);
        result[x] = '/';
        memcpy(result + x + 1, b, y + 1);
    }
    return result;
}

static char *link_text(const char *path)
{
    size_t capacity = 256;
    for (;;) {
        char *text = malloc(capacity + 1);
        ssize_t size;
        if (!text) return NULL;
        size = readlink(path, text, capacity);
        if (size < 0) {
            int error = errno;
            free(text);
            errno = error;
            return NULL;
        }
        if ((size_t)size < capacity) {
            text[size] = '\0';
            return text;
        }
        free(text);
        if (capacity > (size_t)-1 / 2 - 1) {
            errno = ENOMEM;
            return NULL;
        }
        capacity *= 2;
    }
}

/* Called only after libc realpath reports ENOENT. Resolve each component,
 * expanding links before handling dot-dot. Only a missing final component is
 * accepted; missing intermediate components never become imaginary directories.
 */
static char *missing_final(const char *path)
{
    char *pending = strdup(path), *resolved = NULL;
    unsigned links = 0;
    if (!pending) return NULL;
    resolved = path[0] == '/' ? strdup("/") : getcwd(NULL, 0);
    if (!resolved) goto fail;
    while (strlen(pending) > 1 && pending[strlen(pending) - 1] == '/')
        pending[strlen(pending) - 1] = '\0';
    while (*pending) {
        char *start = pending, *end, *rest, *candidate;
        struct stat info;
        while (*start == '/') ++start;
        if (!*start) break;
        end = strchr(start, '/');
        rest = strdup(end ? end + 1 : "");
        if (!rest) goto fail;
        if (end) *end = '\0';
        if (!strcmp(start, ".") || !strcmp(start, "..")) {
            if (!strcmp(start, "..")) {
                char *slash = strrchr(resolved, '/');
                if (slash == resolved) resolved[1] = '\0';
                else *slash = '\0';
            }
            free(pending);
            pending = rest;
            continue;
        }
        candidate = !strcmp(resolved, "/") ? join("", start) : join(resolved, start);
        if (!candidate) { free(rest); goto fail; }
        if (lstat(candidate, &info) < 0) {
            int error = errno;
            if (error == ENOENT && !*rest) {
                free(resolved); free(pending); free(rest);
                return candidate;
            }
            free(candidate); free(rest); errno = error; goto fail;
        }
        if (S_ISLNK(info.st_mode)) {
            char *target, *next;
            if (++links > 40) {
                free(candidate); free(rest); errno = ELOOP; goto fail;
            }
            target = link_text(candidate);
            free(candidate);
            if (!target) { free(rest); goto fail; }
            next = *rest ? join(target, rest) : strdup(target);
            if (target[0] == '/') {
                free(resolved);
                resolved = strdup("/");
            }
            free(target); free(rest);
            if (!next || !resolved) { free(next); goto fail; }
            free(pending);
            pending = next;
            continue;
        }
        if (*rest && !S_ISDIR(info.st_mode)) {
            free(candidate); free(rest); errno = ENOTDIR; goto fail;
        }
        free(resolved); free(pending);
        resolved = candidate;
        pending = rest;
    }
    free(pending);
    return resolved;
fail:
    {
        int error = errno;
        free(pending); free(resolved);
        errno = error;
        return NULL;
    }
}

int main(int argc, char **argv)
{
    const char *name = strrchr(argv[0], '/');
    int is_link, newline = 1, require_existing = 0, option;
    char *result;
    name = name ? name + 1 : argv[0];
    is_link = !strcmp(name, "readlink");
    (void)setlocale(LC_ALL, "");
    opterr = 0;
    /* Leading '+' prevents GNU argument permutation; BSD stops at operands. */
#ifdef __linux__
    const char *options = is_link ? "+n" : "+Ee";
#else
    const char *options = is_link ? "n" : "Ee";
#endif
    while ((option = getopt(argc, argv, options)) != -1) {
        if (option == 'n' && is_link) newline = 0;
        else if (option == 'e' && !is_link) require_existing = 1;
        else if (option == 'E' && !is_link) require_existing = 0;
        else {
            fprintf(stderr, "%s: invalid option\n", name);
            return 1;
        }
    }
    if (argc - optind != 1) {
        fprintf(stderr, "%s: expected one pathname\n", name);
        return 1;
    }
    if (is_link) result = link_text(argv[optind]);
    else {
        struct stat info;
        result = realpath(argv[optind], NULL);
        /* Some libc versions discard a trailing slash on a regular file.
         * Ask pathname resolution itself to enforce directory components. */
        if (result && stat(argv[optind], &info) < 0) {
            int error = errno;
            free(result);
            result = NULL;
            errno = error;
        }
        if (!result && errno == ENOENT && !require_existing && *argv[optind])
            result = missing_final(argv[optind]);
    }
    if (!result) {
        fprintf(stderr, "%s: %s: %s\n", name, argv[optind], strerror(errno));
        return 1;
    }
    if (fputs(result, stdout) == EOF || (newline && putchar('\n') == EOF) || fflush(stdout) == EOF) {
        fprintf(stderr, "%s: write: %s\n", name, strerror(errno));
        free(result);
        return 1;
    }
    free(result);
    return 0;
}
