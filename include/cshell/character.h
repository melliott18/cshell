#ifndef CSHELL_CHARACTER_H
#define CSHELL_CHARACTER_H

#include <stddef.h>

/* Capture once, after startup setlocale and before parsing. The immutable
 * process-owned context is inherited by fork, including eval/dot parsers.
 * Module clients that do not initialize it decode in their current locale.
 * Initialization failure is fatal to the runtime; destroy only at shutdown. */
int csh_character_startup(void);
void csh_character_shutdown(void);
/* ASCII-compatible, stateless encodings. Return a whole character's byte
 * length; invalid/final incomplete sequences use a one-byte fallback.
 * lexical selects the startup context; otherwise use current LC_CTYPE.
 * Return zero for an incomplete character when final is false. */
size_t csh_character_length(const void *text, size_t length, int lexical, int final);

#endif
