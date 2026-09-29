#ifndef CSHELL_PATHNAME_RUNTIME_FAULTS_H
#define CSHELL_PATHNAME_RUNTIME_FAULTS_H
#include <dirent.h>
DIR *csh_path_test_opendir(const char *path);
struct dirent *csh_path_test_readdir(DIR *directory);
int csh_path_test_closedir(DIR *directory);
#define opendir csh_path_test_opendir
#define readdir csh_path_test_readdir
#define closedir csh_path_test_closedir
#endif
