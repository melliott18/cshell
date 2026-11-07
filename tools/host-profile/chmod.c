#define _DEFAULT_SOURCE
#define _DARWIN_C_SOURCE
#include <sys/stat.h>
#include <errno.h>
#include <fts.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#ifdef __linux__
#include <bsd/unistd.h>
#endif

/* Selected POSIX profile. BSD setmode/getmode retains the original mode for X
 * while permission copies use the mode produced by preceding actions. The
 * kernel owns ACL, ownership and set-ID semantics; never install set-ID. */
int main(int argc, char **argv)
{
    int index = 1, recursive = 0, failed = 0;
    void *mode;
    FTS *tree;
    FTSENT *entry;
    while (index < argc && !strcmp(argv[index], "-R")) {
        recursive = 1;
        index++;
    }
    if (index < argc && !strcmp(argv[index], "--")) index++;
    if (argc - index < 2) {
        fputs("usage: chmod [-R] mode file ...\n", stderr);
        return 1;
    }
    mode = setmode(argv[index++]);
    if (!mode) {
        fputs("chmod: invalid mode or mode allocation failure\n", stderr);
        return 1;
    }
    tree = fts_open(argv + index, FTS_PHYSICAL | FTS_COMFOLLOW | FTS_NOCHDIR, NULL);
    if (!tree) {
        perror("chmod: traversal");
        free(mode);
        return 1;
    }
    for (;;) {
        errno = 0;
        entry = fts_read(tree);
        if (!entry) {
            if (errno) { perror("chmod: traversal"); failed = 1; }
            break;
        }
        if (entry->fts_info == FTS_D) {
            if (!recursive && fts_set(tree, entry, FTS_SKIP) != 0) {
                perror("chmod: skip subtree"); failed = 1;
            }
            /* Change directories after their children, including skipped ones. */
            continue;
        }
        if (entry->fts_info == FTS_ERR || entry->fts_info == FTS_NS ||
            entry->fts_info == FTS_DNR || entry->fts_info == FTS_DC) {
            fprintf(stderr, "chmod: %s: %s\n", entry->fts_path,
                    strerror(entry->fts_errno ? entry->fts_errno : ELOOP));
            failed = 1;
            if (entry->fts_info != FTS_DNR) continue;
        }
        if (entry->fts_info == FTS_SL || entry->fts_info == FTS_SLNONE) {
            if (entry->fts_level == FTS_ROOTLEVEL) {
                fprintf(stderr, "chmod: %s: cannot resolve operand\n", entry->fts_path);
                failed = 1;
            }
            continue;
        }
        if (chmod(entry->fts_accpath, getmode(mode, entry->fts_statp->st_mode)) != 0) {
            fprintf(stderr, "chmod: %s: %s\n", entry->fts_path, strerror(errno));
            failed = 1;
        }
    }
    if (fts_close(tree) != 0) { perror("chmod: close traversal"); failed = 1; }
    free(mode);
    return failed;
}
