#ifndef CSHELL_EXPAND_H
#define CSHELL_EXPAND_H

#include "cshell/lexer.h"
#include "cshell/state.h"

/* ASSIGNMENT takes the value word, without NAME=. PATTERN is an operand with
 * splitting/globbing suppressed. This is an intermediate, not an argv API. */
enum csh_expand_context { CSH_EXPAND_ARGUMENT, CSH_EXPAND_ASSIGNMENT,
    CSH_EXPAND_PATTERN };
enum csh_expand_origin { CSH_EXPAND_LITERAL, CSH_EXPAND_TILDE,
    CSH_EXPAND_PARAMETER, CSH_EXPAND_ARITHMETIC, CSH_EXPAND_SUBSTITUTION };
enum csh_expand_result { CSH_EXPAND_OK, CSH_EXPAND_INVALID, CSH_EXPAND_NOMEM,
    CSH_EXPAND_UNSET, CSH_EXPAND_READONLY, CSH_EXPAND_ARITHMETIC_ERROR,
    CSH_EXPAND_DEFERRED, CSH_EXPAND_LIMIT };

struct csh_expand_span {
    char *text;                 /* owned, NUL-terminated; length excludes NUL */
    size_t length;
    enum csh_quote quote;       /* ESCAPE and tilde use SINGLE protection */
    enum csh_expand_origin origin;
    int split;                 /* eligible for later IFS splitting */
    int keep_empty;             /* an explicit quoted empty value */
};
struct csh_expand_field {
    struct csh_expand_span *spans;
    size_t span_count;
};
struct csh_expansion {
    struct csh_expand_field *fields;
    size_t field_count;
    enum csh_expand_context context;
};
struct csh_expand_error {
    enum csh_expand_result code;
    size_t fragment;            /* CSH_FRAGMENT_ROOT when not fragment-local */
    struct csh_position position;
    char message[256];          /* owned inline; diagnostic may be truncated */
};

/* CSH-026 supplies command/backquote execution lazily, only for selected
 * operands. token and fragment are borrowed. On success return borrowed bytes
 * valid until the next callback (copied immediately), with trailing newlines
 * already removed and no NUL bytes. A missing callback returns DEFERRED with
 * the fragment index. No subprocess or grammar guessing occurs here. State
 * changes roll back on failure; external callback effects cannot be undone. */
typedef enum csh_expand_result (*csh_expand_substitute)(void *user,
    struct csh_state *state, const struct csh_token *token, size_t fragment,
    const char **bytes, size_t *length, struct csh_expand_error *error);
struct csh_expand_options {
    enum csh_expand_context context;
    csh_expand_substitute substitute;
    void *user;
};

/* Borrows a WORD token and state. options NULL means ARGUMENT/no callback.
 * out must not own a previous result; cleared on every error. The result owns
 * all bytes independently of token/state. No printing, exiting, status update,
 * field splitting, globbing, or final provenance removal. Every failure rolls
 * back shell-state mutations made while expanding this word. */
enum csh_expand_result csh_expand_word(struct csh_state *state,
    const struct csh_token *word, const struct csh_expand_options *options,
    struct csh_expansion *out, struct csh_expand_error *error);
void csh_expansion_destroy(struct csh_expansion *expansion);

#endif
