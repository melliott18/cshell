#ifndef CSHELL_LEGACY_H
#define CSHELL_LEGACY_H

/*
 * Transitional interface for the original shell implementation.
 * New parser, expansion, and execution modules will replace this interface;
 * these functions do not implement the POSIX shell language.
 */

/* Borrowed, NULL-terminated arguments, valid until the next read. */
char **legacy_read_args(void);

/* May modify the argument vector; retains the original executor semantics. */
int legacy_execute(int argc, char **args);

#endif
