#include <stdio.h>

#include "cshell/legacy.h"

int main(void)
{
    while (1) {
        int argc = 0;
        char **args;

        printf("Shell> ");
        args = legacy_read_args();

        while (args[argc] != NULL) {
            argc++;
        }

        legacy_execute(argc, args);
    }
}
