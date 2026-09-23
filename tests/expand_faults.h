#ifndef CSHELL_TEST_EXPAND_FAULTS_H
#define CSHELL_TEST_EXPAND_FAULTS_H

#include <stdlib.h>

void *csh_expand_fault_malloc(size_t size);
void *csh_expand_fault_realloc(void *pointer, size_t size);
void csh_expand_fault_free(void *pointer);

/* Instrument only the expansion and quote-decoder translation units. The
 * state, lexer, and arithmetic modules keep their independent allocators. */
#ifndef CSHELL_EXPAND_FAULT_IMPLEMENTATION
#define malloc csh_expand_fault_malloc
#define realloc csh_expand_fault_realloc
#define free csh_expand_fault_free
#endif

#endif
