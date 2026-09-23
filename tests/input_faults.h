#ifndef CSHELL_TEST_INPUT_FAULTS_H
#define CSHELL_TEST_INPUT_FAULTS_H

#include <stdlib.h>
#include <unistd.h>

void *csh_fault_malloc(size_t size);
void *csh_fault_realloc(void *pointer, size_t size);
void csh_fault_free(void *pointer);
ssize_t csh_fault_read(int fd, void *buffer, size_t size);

/* Injected only into dedicated test objects by the compiler's -include flag. */
#ifndef CSHELL_FAULT_IMPLEMENTATION
#define malloc csh_fault_malloc
#define realloc csh_fault_realloc
#define free csh_fault_free
#define read csh_fault_read
#endif

#endif
