#ifndef CSHELL_TEST_ARITHMETIC_FAULTS_H
#define CSHELL_TEST_ARITHMETIC_FAULTS_H

#include <stdlib.h>

void *csh_arith_fault_malloc(size_t size);
void csh_arith_fault_free(void *pointer);

/* Inject into both arithmetic.c and state.c for the dedicated fault fixture. */
#ifndef CSHELL_ARITHMETIC_FAULT_IMPLEMENTATION
#define malloc csh_arith_fault_malloc
#define free csh_arith_fault_free
#endif

#endif
