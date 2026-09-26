#ifndef CSHELL_TEST_PROMPT_FAULTS_H
#define CSHELL_TEST_PROMPT_FAULTS_H

#include <stdio.h>
#include <unistd.h>

int csh_prompt_fault_fputs(const char *text, FILE *stream);
ssize_t csh_prompt_fault_write(int fd, const void *bytes, size_t length);
int csh_prompt_fault_main(int argc, char **argv);

/* Interpose only the dedicated main object, leaving the runtime and harness
 * streams unchanged. The stdio hook preserves the pre-fix EINTR reproducer. */
#ifndef CSHELL_FAULT_IMPLEMENTATION
#define fputs csh_prompt_fault_fputs
#define write csh_prompt_fault_write
#define main csh_prompt_fault_main
#endif

#endif
