#ifndef CSHELL_TEST_STATE_FAULTS_H
#define CSHELL_TEST_STATE_FAULTS_H

#include <stdlib.h>

void *csh_state_fault_malloc(size_t size);
void csh_state_fault_free(void *pointer);

/* Injected only into the dedicated state test object with -include. */
#ifndef CSHELL_STATE_FAULT_IMPLEMENTATION
#define malloc csh_state_fault_malloc
#define free csh_state_fault_free
#endif

#endif
