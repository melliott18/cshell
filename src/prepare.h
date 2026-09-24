#ifndef CSHELL_PREPARE_H
#define CSHELL_PREPARE_H

#include "cshell/execute.h"
#include "cshell/expand.h"

/* Runtime preparation is phased: arguments, ordered redirects, assignments.
 * Callers own the partially built command even when a phase fails. */
int csh_prepare_word(struct csh_state *state, const struct csh_ast_word *word,
    enum csh_expand_context mode, struct csh_fields *out, struct csh_error *error);
int csh_command_arguments(struct csh_state *state, const struct csh_ast *tree,
    struct csh_command *out, struct csh_error *error);
int csh_command_assignments(struct csh_state *state, const struct csh_ast *tree,
    struct csh_command *out, struct csh_error *error);
/* -2 is an invalid expanded descriptor operand (a redirection failure);
 * -1 is expansion/preparation failure. Neither prints a diagnostic. */
int csh_command_redirect(struct csh_state *state,
    const struct csh_ast_redirection *source, struct csh_command *command,
    struct csh_redirect *out, struct csh_error *error);
int csh_execute_substitution(struct csh_state *state, const struct csh_ast *tree,
    char **bytes, size_t *length, int *status, struct csh_error *error);
int csh_descriptor(const unsigned char *text, size_t length, int *out);

#endif
