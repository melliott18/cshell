/* Small external program: observable effects without host utility differences. */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int copy_fd(int input, int output)
{
    unsigned char buffer[8192];
    ssize_t amount;
    while ((amount = read(input, buffer, sizeof(buffer))) != 0) {
        ssize_t offset = 0;
        if (amount < 0) { if (errno == EINTR) continue; return 81; }
        while (offset < amount) {
            ssize_t written = write(output, buffer + offset, (size_t)(amount - offset));
            if (written < 0) { if (errno == EINTR) continue; return 82; }
            offset += written;
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    int index;
    if (argc < 2) return 80;
    if (strcmp(argv[1], "both") == 0) {
        if (write(1, "out\n", 4) != 4 || write(2, "err\n", 4) != 4) return 83;
    } else if (strcmp(argv[1], "args") == 0) {
        for (index = 2; index < argc; ++index) printf("[%s]\n", argv[index]);
    } else if (strcmp(argv[1], "copy") == 0) {
        return copy_fd(argc > 2 ? atoi(argv[2]) : 0, 1);
    } else if (strcmp(argv[1], "closed") == 0) {
        errno = 0;
        return fcntl(atoi(argv[2]), F_GETFD) == -1 && errno == EBADF ? 0 : 84;
    } else if (strcmp(argv[1], "environment") == 0) {
        for (index = 2; index < argc; ++index) {
            const char *value = getenv(argv[index]);
            printf("%s=%s\n", argv[index], value == NULL ? "<unset>" : value);
        }
    } else if (strcmp(argv[1], "disposition") == 0) {
        struct sigaction action;
        int number;
        if (argc != 3) return 96;
        if (!strcmp(argv[2], "CHLD")) number = SIGCHLD;
        else if (!strcmp(argv[2], "INT")) number = SIGINT;
        else if (!strcmp(argv[2], "QUIT")) number = SIGQUIT;
        else if (!strcmp(argv[2], "USR1")) number = SIGUSR1;
        else return 96;
        if (sigaction(number, NULL, &action) == -1) return 96;
        puts(action.sa_handler == SIG_IGN ? "ignored" :
            action.sa_handler == SIG_DFL ? "default" : "caught");
    } else if (strcmp(argv[1], "pwd") == 0) {
        char buffer[4096];
        if (getcwd(buffer, sizeof(buffer)) == NULL) return 85;
        puts(buffer);
    } else if (strcmp(argv[1], "generate") == 0) {
        unsigned char buffer[8192];
        size_t left = (size_t)strtoul(argv[2], NULL, 10);
        memset(buffer, 'x', sizeof(buffer));
        while (left != 0) {
            size_t amount = left < sizeof(buffer) ? left : sizeof(buffer);
            ssize_t written = write(1, buffer, amount);
            if (written < 0) { if (errno == EINTR) continue; return 89; }
            if (written == 0) return 89;
            left -= (size_t)written;
        }
    } else if (strcmp(argv[1], "count") == 0) {
        unsigned char buffer[8192];
        size_t count = 0;
        ssize_t amount;
        while ((amount = read(0, buffer, sizeof(buffer))) != 0) {
            if (amount < 0) { if (errno == EINTR) continue; return 90; }
            count += (size_t)amount;
        }
        printf("%lu\n", (unsigned long)count);
    } else if (strcmp(argv[1], "one") == 0) {
        char byte;
        return read(0, &byte, 1) == 1 ? 0 : 91;
    } else if (strcmp(argv[1], "mode") == 0) {
        struct stat st;
        if (argc != 3 || stat(argv[2], &st)) return 95;
        printf("%03o\n", (unsigned)(st.st_mode & 0777));
    } else if (strcmp(argv[1], "private-fds") == 0) {
        for (index = 3; index < 256; ++index)
            if (fcntl(index, F_GETFD) != -1 || errno != EBADF) return 92;
    } else if (strcmp(argv[1], "status") == 0) {
        return atoi(argv[2]);
    } else if (strcmp(argv[1], "signal") == 0) {
        raise(SIGTERM);
        return 86;
    } else if (strcmp(argv[1], "gate") == 0) {
        char byte;
        pid_t pid = getpid();
        if (write(atoi(argv[2]), &pid, sizeof(pid)) != sizeof(pid)) return 93;
        return read(atoi(argv[3]), &byte, 1) == 1 ? 0 : 94;
    } else if (strcmp(argv[1], "fd-write") == 0) {
        return write(atoi(argv[2]), "fd\n", 3) == 3 ? 0 : 87;
    } else return 88;
    return 0;
}
