#include <sys/types.h>
#include <unistd.h>
ssize_t csh_command_read(int fd, void *buffer, size_t size);
#define read csh_command_read
