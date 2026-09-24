#ifndef CSHELL_ALIAS_H
#define CSHELL_ALIAS_H

#include <stdio.h>
#include "cshell/input.h"

struct csh_aliases;

/* Names contain one or more portable alphabetics, digits, or ! % , - @ _.
 * No locale-dependent extensions are accepted. */
int csh_alias_name_valid(const char *name);

/* Tables initially contain no definitions. All retained strings are copied.
 * Mutations return 0 on success and -1 on failure; error is required and is
 * cleared on success. A failed mutation leaves the table unchanged. Names and
 * values supplied to one mutation may borrow strings from this same table.
 * No operation prints, exits, or modifies the process environment.
 * create sets *out to NULL on failure; out must not own an earlier table. */
int csh_aliases_create(struct csh_aliases **out, struct csh_error *error);
void csh_aliases_destroy(struct csh_aliases *aliases); /* NULL accepted */
int csh_aliases_set(struct csh_aliases *aliases, const char *name,
    const char *value, struct csh_error *error);
/* NULL means absent/invalid name or NULL table; "" is a defined empty value.
 * The borrowed result expires on successful mutation or destruction. */
const char *csh_aliases_get(const struct csh_aliases *aliases, const char *name);
/* A valid but absent name succeeds. clear accepts NULL and never allocates. */
int csh_aliases_unset(struct csh_aliases *aliases, const char *name,
    struct csh_error *error);
void csh_aliases_clear(struct csh_aliases *aliases);

/* Dispatch-ready handlers: argc includes argv[0]; argv needs no terminator.
 * All arguments and both borrowed streams must remain valid through the call.
 * Neither stream is closed. Returns 0 on success, 1 for failed operands or
 * allocation/output errors, and 2 for usage errors. Operands are processed in
 * order, continuing after operand errors; successful operands are retained.
 * Options precede operands; -- terminates options. alias has no options;
 * unalias accepts -a only without operands. Missing unalias operands fail.
 * Output is name='value' with shell-reusable quoting, sorted by name when
 * listing all definitions. The caller must add `alias -- ` before reinput.
 * These handlers do not execute replacement text or change shell status. */
int csh_builtin_alias(struct csh_aliases *aliases, int argc,
    const char *const argv[], FILE *out, FILE *err);
int csh_builtin_unalias(struct csh_aliases *aliases, int argc,
    const char *const argv[], FILE *out, FILE *err);

#endif
