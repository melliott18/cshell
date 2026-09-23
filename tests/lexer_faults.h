#ifndef CSHELL_TEST_LEXER_FAULTS_H
#define CSHELL_TEST_LEXER_FAULTS_H

#include <stdlib.h>

void *csh_lexer_fault_malloc(size_t size);
void *csh_lexer_fault_realloc(void *pointer, size_t size);
void csh_lexer_fault_free(void *pointer);

/* Only the dedicated lexer object gets these allocation replacements. */
#ifndef CSHELL_LEXER_FAULT_IMPLEMENTATION
#define malloc csh_lexer_fault_malloc
#define realloc csh_lexer_fault_realloc
#define free csh_lexer_fault_free
#endif

#endif
