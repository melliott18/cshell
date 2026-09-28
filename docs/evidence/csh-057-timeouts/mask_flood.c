/* Diagnostic of pselect mask restoration under concurrent readable input/CHLD. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/select.h>
#include <sys/wait.h>
#include <unistd.h>
static void received(int number) { (void)number; }
int main(int argc, char **argv)
{
    struct sigaction action = {0};
    int pipefd[2], status, iterations = 0;
    pid_t parent = getpid(), child;
    sigset_t events, old, waiting, current;
    action.sa_handler = received; sigemptyset(&action.sa_mask);
    assert(sigaction(SIGCHLD, &action, NULL) == 0);
    sigemptyset(&events); sigaddset(&events, SIGCHLD); sigaddset(&events, SIGINT);
    assert(pipe(pipefd) == 0);
    child = fork(); assert(child >= 0);
    if (!child) {
        close(pipefd[0]);
        for (;;) { assert(write(pipefd[1], "x", 1) == 1); kill(parent, SIGCHLD); }
    }
    close(pipefd[1]);
    alarm(10);
    for (; iterations < 100000; ++iterations) {
        fd_set fds; char byte;
        sigprocmask(SIG_BLOCK, &events, &old);
        waiting = old; sigdelset(&waiting, SIGCHLD); sigdelset(&waiting, SIGINT);
        if (argc > 2) sigsuspend(&waiting);
        FD_ZERO(&fds); FD_SET(pipefd[0], &fds);
        int rc = pselect(pipefd[0]+1, &fds, NULL, NULL, NULL, &waiting);
        if (argc > 1 && atoi(argv[1])) {
            struct timespec zero = {0};
            pselect(0, NULL, NULL, NULL, &zero, NULL);
        }
        sigprocmask(SIG_SETMASK, &old, NULL);
        if (rc > 0) { ssize_t n; do { n=read(pipefd[0], &byte, 1); } while (n < 0 && errno==EINTR); assert(n==1); }
        sigprocmask(SIG_SETMASK, NULL, &current);
        if (sigismember(&current, SIGINT) || sigismember(&current, SIGCHLD)) {
            printf("leak iteration=%d oldINT=%d currentINT=%d currentCHLD=%d\n", iterations,
                sigismember(&old,SIGINT),sigismember(&current,SIGINT),sigismember(&current,SIGCHLD));
            break;
        }
    }
    kill(child,SIGKILL);
    while (waitpid(child,&status,0)<0) {}
    printf("iterations=%d\n",iterations);
    return iterations == 100000 ? 0 : 1;
}
