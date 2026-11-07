/* CSH-078 standalone Apple/FreeBSD uudecode; see README.md for provenance. */
#ifndef __APPLE__
#define _DEFAULT_SOURCE
#include <bsd/err.h>
#include <bsd/unistd.h>
#endif
/* Use the vendor's POSIX path, mode and overwrite behavior on both hosts. */
#define CSH_POSIX_PROFILE 1
#include "vendor/uudecode.c"

int main(int argc, char **argv)
{
    return main_decode(argc, argv);
}
