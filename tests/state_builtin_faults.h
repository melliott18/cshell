#ifndef CSHELL_TEST_STATE_BUILTIN_FAULTS_H
#define CSHELL_TEST_STATE_BUILTIN_FAULTS_H
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "cshell/builtin.h"
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/times.h>
#include <unistd.h>
int csh_state_fault_main(int argc, char **argv);
int csh_state_fault_initialize(struct csh_state *state);
void *csh_state_fault_malloc(size_t size);
void *csh_state_fault_calloc(size_t count, size_t size);
void *csh_state_fault_realloc(void *data, size_t size);
char *csh_state_fault_strdup(const char *text);
char *csh_state_fault_strndup(const char *text, size_t size);
char *csh_state_fault_getcwd(char *data, size_t size);
clock_t csh_state_fault_times(struct tms *times);
long csh_state_fault_sysconf(int name);
int csh_state_fault_getrlimit(int resource, struct rlimit *limit);
int csh_state_fault_setrlimit(int resource, const struct rlimit *limit);
ssize_t csh_state_fault_read(int fd, void *data, size_t size);
ssize_t csh_state_fault_write(int fd, const void *data, size_t size);
#ifndef CSHELL_STATE_FAULT_IMPLEMENTATION
#ifdef CSHELL_STATE_FAULT_MAIN
#define main csh_state_fault_main
#define csh_builtin_initialize csh_state_fault_initialize
#else
#define malloc csh_state_fault_malloc
#define calloc csh_state_fault_calloc
#define realloc csh_state_fault_realloc
#define strdup csh_state_fault_strdup
#define strndup csh_state_fault_strndup
#define getcwd csh_state_fault_getcwd
#define times csh_state_fault_times
#define sysconf csh_state_fault_sysconf
#define getrlimit csh_state_fault_getrlimit
#define setrlimit csh_state_fault_setrlimit
#define read csh_state_fault_read
#define write csh_state_fault_write
#endif
#endif
#endif
