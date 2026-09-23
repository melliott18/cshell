#ifndef CSHELL_QUOTE_H
#define CSHELL_QUOTE_H

#include <stddef.h>

enum csh_quote_result {
    CSH_QUOTE_OK,
    CSH_QUOTE_INVALID,
    CSH_QUOTE_NOMEM
};

/* Decode the contents of one dollar-single-quoted region, excluding its $'
 * and closing ' delimiters. This never parses or expands shell syntax.
 * bytes is borrowed; NULL is allowed only for an empty region. Raw NUL bytes
 * are invalid. out and out_length are required and are cleared on failure.
 * On success, *out is malloc-owned (even when empty), NUL-terminated, and has
 * *out_length bytes excluding that terminator. The caller frees it.
 *
 * Issue 8 choices: a decoded NUL and the remainder of this region are
 * discarded; callers must still process adjacent regions. Hex consumes at
 * most two digits; octal consumes at most three, reduced modulo 256.
 * Unknown escapes, backslash-newline and a trailing backslash are preserved.
 * Control escapes accept a-z/A-Z, [, ], ^, _, ?, and the two backslashes in
 * \c\\. Other \c operands, including @, are left literal.
 *
 * Character escapes use the C/POSIX and ASCII-compatible locale encodings.
 * \e and \cX produce ASCII control bytes; INVALID is returned if the active
 * LC_CTYPE cannot represent the resulting byte as a single-byte character.
 * No locale is changed and no multibyte text is otherwise interpreted. */
enum csh_quote_result csh_quote_decode(const unsigned char *bytes, size_t length,
    char **out, size_t *out_length);

#endif
