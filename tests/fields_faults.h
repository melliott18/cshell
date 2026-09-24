#ifndef CSHELL_TEST_FIELDS_FAULTS_H
#define CSHELL_TEST_FIELDS_FAULTS_H

#include <dirent.h>
#include <stdlib.h>
#include <sys/stat.h>

void *csh_fields_fault_malloc(size_t size);
void *csh_fields_fault_realloc(void *pointer, size_t size);
void csh_fields_fault_free(void *pointer);
DIR *csh_fields_fault_opendir(const char *path);
struct dirent *csh_fields_fault_readdir(DIR *directory);
int csh_fields_fault_closedir(DIR *directory);
int csh_fields_fault_stat(const char *path, struct stat *status);
int csh_fields_fault_lstat(const char *path, struct stat *status);

/* Inject only into fields.c and pathname.c; borrowed state and intermediate
 * expansion allocations remain outside the tracked ownership domain. */
#ifndef CSHELL_FIELDS_FAULT_IMPLEMENTATION
#define malloc csh_fields_fault_malloc
#define realloc csh_fields_fault_realloc
#define free csh_fields_fault_free
#define opendir csh_fields_fault_opendir
#define readdir csh_fields_fault_readdir
#define closedir csh_fields_fault_closedir
#define stat(path, status) csh_fields_fault_stat(path, status)
#define lstat(path, status) csh_fields_fault_lstat(path, status)
#endif

#endif
