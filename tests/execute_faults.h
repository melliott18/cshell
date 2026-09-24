#ifndef CSHELL_TEST_EXECUTE_FAULTS_H
#define CSHELL_TEST_EXECUTE_FAULTS_H

#include <fcntl.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

void *csh_execute_fault_malloc(size_t size);
void *csh_execute_fault_calloc(size_t count, size_t size);
void *csh_execute_fault_realloc(void *pointer, size_t size);
void csh_execute_fault_free(void *pointer);
int csh_execute_fault_open(const char *path, int flags, ...);
int csh_execute_fault_mkstemp(char *template_name);
int csh_execute_fault_dup2(int old_fd, int new_fd);
int csh_execute_fault_fcntl(int fd, int operation, ...);
pid_t csh_execute_fault_fork(void);
pid_t csh_execute_fault_waitpid(pid_t pid, int *status, int options);

#ifndef CSHELL_EXECUTE_FAULT_IMPLEMENTATION
#define malloc csh_execute_fault_malloc
#define calloc csh_execute_fault_calloc
#define realloc csh_execute_fault_realloc
#define free csh_execute_fault_free
#define open csh_execute_fault_open
#define mkstemp csh_execute_fault_mkstemp
#define dup2 csh_execute_fault_dup2
#define fcntl csh_execute_fault_fcntl
#define fork csh_execute_fault_fork
#define waitpid csh_execute_fault_waitpid
#endif
#endif
