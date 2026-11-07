/* Standalone glibc gencat with checked I/O and a bounded direct-file loader.
 * The included GNU program is GPL-2.0-or-later; see vendor/gencat-glibc/COPYING.
 * It remains an external provider, never linked into cshell. */
#define _GNU_SOURCE
#define N_(text) text
#define libc_hidden_proto(name)
#include <sys/mman.h>
#include <sys/stat.h>
#include <stdint.h>
#include <errno.h>
#include <unistd.h>
#include <err.h>

static ssize_t checked_write(int fd, const void *data, size_t length)
{
    size_t done = 0;
    while (done < length) {
        ssize_t n = write(fd, (const char *)data + done, length - done);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) err(1, "gencat: write");
        done += (size_t)n;
    }
    return (ssize_t)done;
}
#define write checked_write
/* Keep upstream GNU extensions/warnings confined to the vendored program. */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wpedantic"
#pragma GCC diagnostic ignored "-Wshadow"
#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wmissing-field-initializers"
#if defined(__GNUC__) && !defined(__clang__)
/* GCC ASan diagnoses the upstream gettext format in --version as nullable. */
#pragma GCC diagnostic ignored "-Wformat-overflow"
#endif
#include "vendor/gencat-glibc/gencat.c"
#pragma GCC diagnostic pop
#undef write

/* GNU gencat needs only an explicit old catalog, never a search through
 * NLSPATH. Validate all table/string bounds before its merge loop sees them. */
int __open_catalog(const char *name, const char *nlspath, const char *env,
                   __nl_catd catalog)
{
    int fd, saved, swap;
    struct stat st;
    size_t slots, tables, strings, i;
    void *mapping;
    (void)nlspath; (void)env;
    fd = open(name, O_RDONLY);
    if (fd < 0) return -1;
    if (fstat(fd, &st) < 0) { saved = errno; close(fd); errno = saved; return -1; }
    if (!S_ISREG(st.st_mode) || st.st_size < 12 || (uintmax_t)st.st_size > SIZE_MAX) {
        close(fd); errno = EINVAL; return -1;
    }
    mapping = mmap(NULL, (size_t)st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    saved = errno; close(fd); errno = saved;
    if (mapping == MAP_FAILED) return -1;
    catalog->file_ptr = mapping;
    catalog->file_size = (size_t)st.st_size;
    swap = catalog->file_ptr->magic == SWAPU32(CATGETS_MAGIC);
    if (!swap && catalog->file_ptr->magic != CATGETS_MAGIC) goto invalid;
    catalog->plane_size = swap ? SWAPU32(catalog->file_ptr->plane_size) : catalog->file_ptr->plane_size;
    catalog->plane_depth = swap ? SWAPU32(catalog->file_ptr->plane_depth) : catalog->file_ptr->plane_depth;
    if (!catalog->plane_size || !catalog->plane_depth ||
        catalog->plane_size > (catalog->file_size - 12) / 24 / catalog->plane_depth) goto invalid;
    slots = catalog->plane_size * catalog->plane_depth;
    tables = slots * 24;
    catalog->name_ptr = catalog->file_ptr->name_ptr;
#if __BYTE_ORDER == __BIG_ENDIAN
    catalog->name_ptr += slots * 3;
#endif
    catalog->strings = (char *)mapping + 12 + tables;
    strings = catalog->file_size - 12 - tables;
    for (i = 0; i < slots; ++i) {
        uint32_t offset = catalog->name_ptr[i * 3 + 2];
        if (!catalog->name_ptr[i * 3]) continue;
        if (offset >= strings || !memchr(catalog->strings + offset, 0, strings - offset)) goto invalid;
    }
    catalog->status = mmapped;
    return 0;
invalid:
    munmap(mapping, catalog->file_size); errno = EINVAL; return -1;
}
