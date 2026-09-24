#include "field_internal.h"

#include <dirent.h>
#include <errno.h>
#include <fnmatch.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

/* Traversal is iterative, with at most one open directory. The component
 * limit bounds work even for paths which the host accepts beyond PATH_MAX. */
#define PATHNAME_COMPONENT_LIMIT 4096

static int interrupted(const struct csh_field_options *options)
{
    return options != NULL && options->interrupted != NULL &&
        options->interrupted(options->user);
}

static void clear_paths(struct csh_fields *paths)
{
    size_t i;
    for (i = 0; i < paths->count; ++i) free(paths->values[i]);
    free(paths->values);
    memset(paths, 0, sizeof(*paths));
}

static void discard_paths(struct csh_fields *paths, size_t keep)
{
    while (paths->count > keep) free(paths->values[--paths->count]);
    if (paths->values != NULL) paths->values[paths->count] = NULL;
}

/* Missing, inaccessible, or unresolvable path components are ordinary
 * non-matches. Resource exhaustion and actual read failures remain errors. */
static enum csh_expand_result filesystem_error(int error)
{
    switch (error) {
    case ENOENT:
    case ENOTDIR:
    case EACCES:
    case ENAMETOOLONG:
    case ELOOP: return CSH_EXPAND_OK;
    case ENOMEM: return CSH_EXPAND_NOMEM;
    case EINTR: return CSH_EXPAND_INTERRUPTED;
    default: return CSH_EXPAND_IO;
    }
}

/* A closing bracket in the first list position is literal. Skip POSIX
 * bracket subexpressions so their closing brackets do not close the list. */
static int has_bracket(const char *pattern)
{
    const char *position = pattern + 1;
    if (*position == '!') ++position;
    if (*position == ']') ++position;
    while (*position != 0 && *position != '/') {
        if (*position == '\\' && position[1] != 0 && position[1] != '/') {
            position += 2;
        } else if (*position == ']') {
            return 1;
        } else if (*position == '[' && position[1] != 0 &&
            strchr(":.=", position[1]) != NULL) {
            const char *end = position + 2;
            while (*end != 0 && *end != '/' &&
                !(end[0] == position[1] && end[1] == ']')) ++end;
            if (*end == 0 || *end == '/') return 0;
            position = end + 2;
        } else ++position;
    }
    return 0;
}

static int has_pattern(const char *pattern)
{
    while (*pattern != 0) {
        if (*pattern == '\\' && pattern[1] != 0) pattern += 2;
        else if (*pattern == '*' || *pattern == '?' ||
            (*pattern == '[' && has_bracket(pattern))) return 1;
        else ++pattern;
    }
    return 0;
}

/* A pattern escape can protect a slash's literal value, but cannot turn it
 * into a filename character. Preserve escaped backslash pairs while removing
 * only the escape immediately protecting a slash. */
static char *pathname_pattern(const char *pattern)
{
    char *copy = malloc(strlen(pattern) + 1), *write;
    if (copy == NULL) return NULL;
    write = copy;
    while (*pattern != 0) {
        if (*pattern == '\\' && pattern[1] != 0) {
            if (pattern[1] != '/') *write++ = *pattern;
            ++pattern;
        }
        *write++ = *pattern++;
    }
    *write = 0;
    return copy;
}

static void unescape(char *text)
{
    char *read = text, *write = text;
    while (*read != 0) {
        if (*read == '\\' && read[1] != 0) ++read;
        *write++ = *read++;
    }
    *write = 0;
}

static char *join(const char *prefix, const char *separators, size_t count,
    const char *component)
{
    size_t prefix_length = strlen(prefix), component_length = strlen(component);
    char *path;
    if (prefix_length > SIZE_MAX - count ||
        prefix_length + count > SIZE_MAX - component_length - 1) return NULL;
    path = malloc(prefix_length + count + component_length + 1);
    if (path == NULL) return NULL;
    memcpy(path, prefix, prefix_length);
    memcpy(path + prefix_length, separators, count);
    memcpy(path + prefix_length + count, component, component_length + 1);
    return path;
}

/* Consume path on success and failure, including allocation failures. */
static enum csh_expand_result append_path(struct csh_fields *paths, char *path)
{
    char **grown;
    if (path == NULL) return CSH_EXPAND_NOMEM;
    if (paths->count > SIZE_MAX / sizeof(*grown) - 2) {
        free(path);
        return CSH_EXPAND_NOMEM;
    }
    grown = realloc(paths->values, (paths->count + 2) * sizeof(*grown));
    if (grown == NULL) {
        free(path);
        return CSH_EXPAND_NOMEM;
    }
    paths->values = grown;
    paths->values[paths->count++] = path;
    paths->values[paths->count] = NULL;
    return CSH_EXPAND_OK;
}

static enum csh_expand_result literal_path(const char *prefix,
    const char *separators, size_t separator_count, const char *component,
    int final, int directory, struct csh_fields *next)
{
    struct stat info;
    char *path = join(prefix, separators, separator_count, component);
    enum csh_expand_result result;
    if (path == NULL) return CSH_EXPAND_NOMEM;
    if (final) {
        /* lstat admits a dangling final symlink; a trailing slash must resolve
         * through symlinks to a directory. Literal prefixes need only search
         * permission, so never enumerate them. */
        int status = directory ? stat(path, &info) : lstat(path, &info);
        if (status != 0) {
            result = filesystem_error(errno);
            free(path);
            return result;
        }
        if (directory && !S_ISDIR(info.st_mode)) {
            free(path);
            return CSH_EXPAND_OK;
        }
    }
    return append_path(next, path);
}

static enum csh_expand_result pattern_paths(const char *prefix,
    const char *separators, size_t separator_count, const char *component,
    const struct csh_field_options *options, struct csh_fields *next)
{
    char *directory = join(prefix, separators, separator_count, "");
    struct dirent *entry;
    DIR *stream;
    enum csh_expand_result result = CSH_EXPAND_OK;
    size_t previous_count = next->count;
    int saved_error, no_match = 0;
    if (directory == NULL) return CSH_EXPAND_NOMEM;
    stream = opendir(directory[0] == 0 ? "." : directory);
    saved_error = errno;
    free(directory);
    if (stream == NULL) return filesystem_error(saved_error);
    for (;;) {
        if (interrupted(options)) {
            result = CSH_EXPAND_INTERRUPTED;
            break;
        }
        errno = 0;
        entry = readdir(stream);
        if (entry == NULL) {
            if (errno != 0) {
                result = filesystem_error(errno);
                no_match = result == CSH_EXPAND_OK;
            }
            break;
        }
        /* POSIX.1-2024 permits ignoring dot and dot-dot; use that choice even
         * when the pattern starts with an explicit dot. Literal components
         * still permit ./ and ../. */
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0 ||
            fnmatch(component, entry->d_name, FNM_PERIOD) != 0) continue;
        result = append_path(next,
            join(prefix, separators, separator_count, entry->d_name));
        if (result != CSH_EXPAND_OK) break;
    }
    if (closedir(stream) != 0 && result == CSH_EXPAND_OK) {
        result = filesystem_error(errno);
        no_match = result == CSH_EXPAND_OK;
    }
    /* A content-related read failure means this directory supplied no
     * matches, including any entries read before that failure. */
    if (no_match) discard_paths(next, previous_count);
    return result;
}

static int compare_paths(const void *left, const void *right)
{
    const char *a = *(const char *const *)left;
    const char *b = *(const char *const *)right;
    int order = strcoll(a, b);
    /* A byte comparison makes ties in the active collation deterministic. */
    return order != 0 ? order : strcmp(a, b);
}

enum csh_expand_result csh_pathname_expand(const char *raw, const char *pattern,
    const struct csh_field_options *options, struct csh_fields *out)
{
    struct csh_fields paths = {0}, next = {0};
    enum csh_expand_result result = CSH_EXPAND_OK;
    const char *position;
    size_t components = 0, i;
    char *component = NULL, *normalized = NULL;
    if (interrupted(options)) return CSH_EXPAND_INTERRUPTED;
    if (!has_pattern(pattern)) return csh_fields_append(out, raw, strlen(raw));
    normalized = pathname_pattern(pattern);
    if (normalized == NULL) return CSH_EXPAND_NOMEM;
    position = normalized;
    result = append_path(&paths, join("", "", 0, ""));
    if (result != CSH_EXPAND_OK) goto done;
    while (*position != 0 && paths.count != 0) {
        const char *separators = position, *begin;
        size_t separator_count, length;
        int pattern_component, final, directory;
        while (*position == '/') ++position;
        separator_count = (size_t)(position - separators);
        begin = position;
        while (*position != 0 && *position != '/') ++position;
        length = (size_t)(position - begin);
        if (++components > PATHNAME_COMPONENT_LIMIT) {
            result = CSH_EXPAND_LIMIT;
            goto done;
        }
        component = malloc(length + 1);
        if (component == NULL) { result = CSH_EXPAND_NOMEM; goto done; }
        memcpy(component, begin, length);
        component[length] = 0;
        pattern_component = has_pattern(component);
        final = *position == 0;
        directory = length == 0 && separator_count != 0;
        if (!pattern_component) unescape(component);
        for (i = 0; i < paths.count; ++i) {
            if (interrupted(options)) { result = CSH_EXPAND_INTERRUPTED; goto done; }
            if (pattern_component)
                result = pattern_paths(paths.values[i], separators, separator_count,
                    component, options, &next);
            else
                result = literal_path(paths.values[i], separators, separator_count,
                    component, final, directory, &next);
            if (result != CSH_EXPAND_OK) goto done;
        }
        free(component);
        component = NULL;
        clear_paths(&paths);
        paths = next;
        memset(&next, 0, sizeof(next));
    }
    if (interrupted(options)) { result = CSH_EXPAND_INTERRUPTED; goto done; }
    if (paths.count == 0) {
        result = csh_fields_append(out, raw, strlen(raw));
        goto done;
    }
    if (paths.count > 1) qsort(paths.values, paths.count, sizeof(*paths.values), compare_paths);
    for (i = 0; i < paths.count; ++i) {
        if (interrupted(options)) { result = CSH_EXPAND_INTERRUPTED; goto done; }
        result = csh_fields_append(out, paths.values[i], strlen(paths.values[i]));
        if (result != CSH_EXPAND_OK) goto done;
    }
 done:
    free(component);
    free(normalized);
    clear_paths(&paths);
    clear_paths(&next);
    return result;
}
