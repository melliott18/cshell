/* Test-only interposition; the selected production ed has no fault controls. */
#include <stdio.h>
FILE *csh_ed_tmpfile(void);
size_t csh_ed_fwrite(const void *, size_t, size_t, FILE *);
#define tmpfile csh_ed_tmpfile
#define fwrite csh_ed_fwrite
