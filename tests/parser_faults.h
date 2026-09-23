#ifndef CSHELL_TEST_PARSER_FAULTS_H
#define CSHELL_TEST_PARSER_FAULTS_H

#include <stdlib.h>

void *csh_parser_fault_malloc(size_t size);
void *csh_parser_fault_realloc(void *pointer, size_t size);
void *csh_parser_fault_calloc(size_t count, size_t size);
void csh_parser_fault_free(void *pointer);

/* Only the dedicated input/lexer/parser/AST test objects include this file. */
#ifndef CSHELL_PARSER_FAULT_IMPLEMENTATION
#define malloc csh_parser_fault_malloc
#define realloc csh_parser_fault_realloc
#define calloc csh_parser_fault_calloc
#define free csh_parser_fault_free
#endif

#endif
