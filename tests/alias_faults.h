#ifndef CSHELL_TEST_ALIAS_FAULTS_H
#define CSHELL_TEST_ALIAS_FAULTS_H

#include <stdlib.h>

void *csh_alias_fault_malloc(size_t size);
void csh_alias_fault_free(void *pointer);

/* Injected only into the dedicated alias test object with -include. */
#ifndef CSHELL_ALIAS_FAULT_IMPLEMENTATION
#define malloc csh_alias_fault_malloc
#define free csh_alias_fault_free
#endif

#endif
