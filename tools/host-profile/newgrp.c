#define _POSIX_C_SOURCE 200809L
#include <sys/types.h>
#include <errno.h>
#include <grp.h>
#include <inttypes.h>
#include <pwd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "host-newgrp-provider.h"

/* Unprivileged dispatch adapter. The vendor retains all group authorization,
 * password handling and credential changes. Never install this binary set-ID. */
int main(int argc, char **argv)
{
    if (argc == 2 && argv[1][0] != '-') {
        struct group *group = getgrnam(argv[1]);
        if (!group) {
            const char *digit = argv[1];
            while (*digit >= '0' && *digit <= '9') digit++;
            if (*argv[1] && !*digit) {
                char *end;
                uintmax_t id;
                errno = 0;
                id = strtoumax(argv[1], &end, 10);
                if (!errno && !*end && id == (uintmax_t)(gid_t)id &&
                    (group = getgrgid((gid_t)id)) != NULL)
                    argv[1] = group->gr_name;
                /* Unknown/overflow numeric IDs retain vendor authorization. */
            } else {
                struct passwd *user;
                const char *shell, *name;
                /* No credential transition was attempted. This failure must
                 * still create a shell with the existing process environment. */
                fprintf(stderr, "newgrp: unknown group: %s\n", argv[1]);
                user = getpwuid(getuid());
                if (!user) { fputs("newgrp: unknown user\n", stderr); return 1; }
                shell = *user->pw_shell ? user->pw_shell : "/bin/sh";
                name = strrchr(shell, '/');
                execl(shell, name ? name + 1 : shell, (char *)NULL);
                perror("newgrp: shell");
                return 1;
            }
        }
    }
    argv[0] = (char *)"newgrp";
    execv(CSH_NEWGRP_PROVIDER, argv);
    perror("newgrp: selected provider");
    return 1;
}
