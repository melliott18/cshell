#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

extern const char * const * getargs();

// Redirect input using <
int redirect_input(char **args, int i) {
    int infd;
    int status;
    int pid = fork(); 
 
    if (pid < 0) {
        perror(""); 
        return -1;
    } else if (pid == 0 && args[i + 1] != NULL) {
        infd = open(args[i + 1], O_RDONLY);
        
        if (dup2(infd, 0) < 0) { // Redirect stdin
            perror("");
            return -1;
        }
        
        close(infd);
        args[i] = NULL;
        execvp(args[0], args); 
    } else {
        pid = wait(&status);
    }
    
    return 0;
}

// Redirect output using >, >&, >> or >>&
int redirect_output(char **args, int i, int option) {
    int outfd;
    int status;
    int pid = fork(); 
 
    if (pid < 0) {
        perror(""); 
        return -1;
    } else if (pid == 0 && args[i + 1] != NULL) {
        if (option & (1 << 1)) { // >> or >>&
            outfd = open(args[i + 1], O_APPEND | O_WRONLY, 0644);
        } else { // > or >&
            outfd = open(args[i + 1], O_CREAT | O_TRUNC | O_WRONLY, 0644);
        }

        if (outfd < 0) {
            perror("");
            return -1;
        }

        if (dup2(outfd, 1) < 0) { // Redirect stdout
            perror("");
            return -1;
        }

        if (option & 1) { // >& or >>&
            if (dup2(outfd, 2) < 0) { // Redirect stderr
                perror("");
                return -1;
            }
        }

        if (close(outfd) < 0) {
            perror("");
            return -1;
        }

        args[i] = NULL;
 
        if (execvp(args[0], args) < 0) {
            perror("");
            return -1;
        }
    } else {
        pid = wait(&status);
    }
    
    return 0;
}

// Run two programs in series using ;
int shell_series(int argc, char **args, int i) {
    int status;
    int pid;

    char **left = calloc(i + 1, sizeof(char*)); // String for left side of ;
    char **right = calloc(argc - i, sizeof(char*)); // String for right side of ;

    args[i] = NULL;

    for (int j = 0; j < i; j++) {
        left[j] = strdup(args[j]);  
    }

    left[i] = NULL;

    int index = 0;
    for (int k = i + 1; args[k] != NULL; k++) {
        right[index] = strdup(args[k]);
        index++;        
    }

    right[argc - i] = NULL;

    pid = fork();

    if (pid < 0) {
        perror("");
    } else if (pid == 0) {
        if (execvp(left[0], left) < 0) { // Execute the left command
            perror("");
        }
    } else {
        pid = wait(&status);
        if (execvp(right[0], right) < 0) { // Execute the right command
            perror(""); 
        }
    }

    return 0;
}

// Pipe the output of one process to the input of another process
int shell_pipe(int argc, char **args, int i, int option) {
    int pipefd[3];
    pipe(pipefd);
    int pid1, pid2;

    char **left = calloc(i + 1, sizeof(char*)); // String for left side of |
    char **right = calloc(argc - i, sizeof(char*)); // String for right side of |

    args[i] = NULL;

    for (int j = 0; j < i; j++) {
        left[j] = strdup(args[j]);
    }

    left[i] = NULL;

    int index = 0;
    for (int k = i + 1; k < argc; k++) {
        right[index] = strdup(args[k]);
        index++;        
    }

    right[argc - i] = NULL;

    if (option & 1) { // |& option
        if (dup2(pipefd[2], 2) < 0) { // Redirect stderr
            perror("");
        }
    }

    pid1 = fork();

    if (pid1 < 0) { // Child process #1
        perror("");
    } else if (pid1 == 0) {
        dup2(pipefd[0], 0); // Redirect stdin
        close(pipefd[1]);
        if (execvp(right[0], right) < 0) { // Execute the right command
            perror(""); 
        }
    } else if ((pid2 = fork()) == 0) { // Child process #2
        dup2(pipefd[1], 1); // Redirect stdout
        close(pipefd[0]);
        if (execvp(left[0], left) < 0) { // Execute the left command
            perror(""); 
        }
    } else {
        waitpid(pid2, NULL, 0);
    }

    close(pipefd[0]);
    close(pipefd[1]);

    return 0;
}

int shell_exec(int argc, char **args) {
    if (args[0] == NULL) {
        return -1;
    } else if (strcmp(args[0], "cd") == 0 && args[1] != NULL) {
        if (chdir(args[1]) != 0) { // Change the current working directory
            perror(args[0]);
            return -1;
        }
    } else if (strcmp(args[0], "exit") == 0) {
        exit(0); // Exit the program cleanly
    } else {
        for (int i = 1; args[i] != NULL; i++) {
            if (args[i] == NULL) {
                return -1;
            } else if ((strcmp(args[i], "|") == 0)) {
                // Pipe
                return shell_pipe(argc, args, i, 0);
            } else if (strcmp(args[i], "|&") == 0) {
                // Pipe and redirect stderr
                return shell_pipe(argc, args, i, 1);
            } else if (strcmp(args[i], "<") == 0) {
                // Redirect stdin
                return redirect_input(args, i);
            } else if (strcmp(args[i], ">") == 0) {
                // Redirect stdout
                return redirect_output(args, i, 0);
            } else if (strcmp(args[i], ">&") == 0) {
                // Redirect stdout and stderr
                return redirect_output(args, i, 1);
            } else if (strcmp(args[i], ">>") == 0) {
                // Redirect stdout and append to the file
                return redirect_output(args, i, 2);
            } else if (strcmp(args[i], ">>&") == 0) {
                // Redirect stdout and stderr and append to the file
                return redirect_output(args, i, 3);
            } else if (strcmp(args[i], ";") == 0) {
                // Run two programs in series
            }
        }
    }

    int status;
    int pid = fork();

    if (pid < 0) {
        perror("");
        return -1;

    } else if (pid == 0) { 
        if (execvp(args[0], args) < 0) {
            perror("");
            return -1;
        }
    } else { 
        pid = wait(&status);
    }

    return 0;
}

int main() {
    int i;
    int argc = 0;
    char **args;

    while (1) {
        printf ("Shell> ");
        args = (char **)getargs();

        for (i = 0; args[i] != NULL; i++) {
            argc++;
        }

        shell_exec(argc, args);
    }
}
