/* GNU libiconv supplies code-name conversion; the system provider retains
 * charmap-file conversion. Both are exec'ed without changing signal state. */
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include "catalog_providers.h"

int main(int argc, char **argv)
{
    int ch, charmap = 0;
    const char *provider;
    opterr = 0;
    while ((ch = getopt(argc, argv, "+csf:t:l")) != -1) {
        if ((ch == 'f' || ch == 't') && strchr(optarg, '/')) charmap = 1;
    }
    provider = charmap ? CATALOG_SYSTEM_ICONV : CATALOG_ICONV;
    argv[0] = (char *)provider;
    execv(provider, argv);
    perror("iconv");
    return 126;
}
