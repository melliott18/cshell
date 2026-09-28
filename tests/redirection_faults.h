#ifndef CSHELL_REDIRECTION_FAULTS_H
#define CSHELL_REDIRECTION_FAULTS_H
#include <fcntl.h>
#include <sys/stat.h>
int csh_redirection_open(const char *path, int flags, ...);
int csh_redirection_fstat(int fd, struct stat *result);
#define open csh_redirection_open
#define fstat csh_redirection_fstat
#endif
