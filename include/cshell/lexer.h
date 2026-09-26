#ifndef CSHELL_LEXER_H
#define CSHELL_LEXER_H

#include "cshell/input.h"

enum csh_token_kind {
    CSH_TOKEN_WORD, CSH_TOKEN_NEWLINE,
    CSH_TOKEN_AND_IF, CSH_TOKEN_OR_IF, CSH_TOKEN_DSEMI, CSH_TOKEN_SEMI_AND,
    CSH_TOKEN_DLESS, CSH_TOKEN_DGREAT, CSH_TOKEN_LESS_AND,
    CSH_TOKEN_GREAT_AND, CSH_TOKEN_LESS_GREAT, CSH_TOKEN_DLESS_DASH,
    CSH_TOKEN_CLOBBER, CSH_TOKEN_PIPE, CSH_TOKEN_AMPERSAND,
    CSH_TOKEN_SEMI, CSH_TOKEN_LPAREN, CSH_TOKEN_RPAREN,
    CSH_TOKEN_LESS, CSH_TOKEN_GREAT
};

enum csh_quote {
    CSH_QUOTE_NONE, CSH_QUOTE_SINGLE, CSH_QUOTE_DOUBLE, CSH_QUOTE_DOLLAR_SINGLE
};

enum csh_fragment_kind {
    CSH_FRAGMENT_TEXT, CSH_FRAGMENT_QUOTED, CSH_FRAGMENT_ESCAPE,
    CSH_FRAGMENT_CONTINUATION, CSH_FRAGMENT_PARAMETER,
    CSH_FRAGMENT_COMMAND, CSH_FRAGMENT_ARITHMETIC, CSH_FRAGMENT_BACKQUOTE
};

/* Fragments are a flat, preorder tree. parent == CSH_FRAGMENT_ROOT means a
 * direct child of the word. begin/end index token.raw, including delimiters.
 * ESCAPE spans a backslash and one complete character, possibly >2 bytes.
 * Text inside a command substitution is retained by its COMMAND fragment;
 * its grammar is supplied by the parser, not duplicated in this tree. */
#define CSH_FRAGMENT_ROOT ((size_t)-1)
struct csh_fragment {
    enum csh_fragment_kind kind;
    enum csh_quote quote;
    size_t parent;
    size_t begin;
    size_t end;
    struct csh_position start;
    struct csh_position finish;
};

struct csh_token {
    enum csh_token_kind kind;
    char *source_name;
    unsigned char *raw;
    size_t length;
    struct csh_position start;
    struct csh_position end;
    struct csh_fragment *fragments;
    size_t fragment_count;
    /* Alias tokens own their replacement source identity and the outermost
     * invocation provenance. NULL names identify ordinary input tokens. */
    char *alias_name;
    char *invocation_source;
    struct csh_position invocation;
    int alias_eligible;
};

struct csh_lexer;
enum csh_lex_result {
    CSH_LEX_ERROR = -1, CSH_LEX_EOF = 0, CSH_LEX_TOKEN = 1,
    CSH_LEX_MORE = 2, CSH_LEX_COMMAND = 3, CSH_LEX_REPLAY = 4
};

/* Constructors copy the name; *out is NULL on failure. The lexer owns fed
 * bytes. No input acquisition, expansion, diagnostics or execution occurs. */
int csh_lexer_create(struct csh_lexer **out, const char *source_name,
    struct csh_error *error);
/* Destroy the root, including unfinished child frames. Child frames are
 * released by command_end; callers must not destroy them separately. */
void csh_lexer_destroy(struct csh_lexer *lexer);
/* Fresh lexer only: read the entire source as a here-document value word.
 * Top-level quotes are literal; only $, backquotes and body escapes are active.
 * Command children retain ordinary shell tokenization. */
void csh_lexer_document(struct csh_lexer *lexer);
/* Append bytes to the shared source; final marks EOF, including an empty feed.
 * Feed one physical line at a time to preserve parser/executor read boundaries.
 * All frames use the same stream. No feed is allowed after final or failure. */
int csh_lexer_feed(struct csh_lexer *lexer, const void *bytes, size_t length,
    int final, struct csh_error *error);
/* TOKEN transfers ownership to an empty destination. All other results clear
 * it. Errors are sticky; speculative storage remains owned until replay or
 * destruction. MORE preserves state until another feed; COMMAND requests
 * grammar-assisted $(...) parsing. REPLAY discards an arithmetic candidate.
 * Call only on the active (deepest) frame. */
enum csh_lex_result csh_lexer_next(struct csh_lexer *lexer,
    struct csh_token *token, struct csh_error *error);
void csh_token_destroy(struct csh_token *token);
const char *csh_token_kind_name(enum csh_token_kind kind);
const char *csh_fragment_kind_name(enum csh_fragment_kind kind);
const char *csh_quote_name(enum csh_quote quote);

/* On MORE, returns 1 and the innermost opening context if a word is unfinished,
 * or 0 at an ordinary input boundary. Strings are static. */
int csh_lexer_context(const struct csh_lexer *lexer, const char **context,
    struct csh_position *opening);

/* After COMMAND, begin creates a child sharing the cursor just after $(.
 * The parser owns grammar decisions, including case patterns and here-docs.
 * When it accepts the matching RPAREN, end verifies that token is the last
 * consumed token of child, destroys child, and resumes the parent's word.
 * Parent owns child lifetime; on failure destroy only the root. The parser
 * supplies grammar and alias eligibility. Nested COMMAND requests repeat this protocol. */
/* Index of the pending COMMAND fragment, or CSH_FRAGMENT_ROOT. Use this
 * stable index to attach child ASTs; alias sources have independent positions. */
size_t csh_lexer_command_fragment(const struct csh_lexer *lexer);
/* REPLAY invalidates speculative substitutions at or after command_fragment()
 * in the pending word. Discard those ASTs, then resume next() (which requests
 * COMMAND). Already-fed physical bytes and alias provenance are retained.
 * After a nested parser syntax error, replay_arithmetic() offers the same
 * recovery on its parent frame: 1 replayed, 0 no candidate/resource error,
 * -1 allocation failure. Unwind child parser storage before calling; recovery
 * destroys child lexers. Pass the original error; success clears it. */
int csh_lexer_replay_arithmetic(struct csh_lexer *lexer, struct csh_error *error);
int csh_lexer_command_begin(struct csh_lexer *parent, struct csh_lexer **child,
    struct csh_error *error);
int csh_lexer_command_end(struct csh_lexer *parent, struct csh_lexer *child,
    const struct csh_token *closing, struct csh_error *error);

/* Substitute only the last delimited WORD, before any subsequent read.
 * Copies name/value; a synthetic space follows every replacement (an Issue 8
 * permitted choice). Alias names remain active through their replacement,
 * including nested command frames. The parser decides eligibility and rejects
 * quoted names. Push fails for an active name; active() lets it suppress such
 * recursive substitution without producing an error. All failures are sticky.
 * alias_eligible marks the next token after a value ending in blank, including
 * the permitted quoted-blank case. Operators/newlines consume that eligibility.
 * Positions in alias tokens are local to source_name; invocation identifies
 * the outermost physical call site. Original input positions resume unchanged.
 * A token spanning an alias boundary retains its starting source identity;
 * its end and fragment positions advance through its captured raw spelling. */
int csh_lexer_alias_active(const struct csh_lexer *lexer, const char *name);
int csh_lexer_alias_push(struct csh_lexer *lexer, const struct csh_token *token,
    const char *name, const char *value, struct csh_error *error);
/* True when the just-delimited word immediately precedes < or >. This does
 * not consume input or request further input; use to classify IO_NUMBER. */
int csh_lexer_follows_redirection(struct csh_lexer *lexer);
/* Map a current source/context position to the outer physical invocation when
 * reading alias input or a pending word that began there. Call while the
 * corresponding context is active; saved tokens carry their own provenance. */
struct csh_position csh_lexer_diagnostic_position(const struct csh_lexer *lexer,
    struct csh_position position);

/* Here-document handoff: after NEWLINE, the parser can inspect pending raw
 * bytes and consume body/delimiter bytes without tokenization. skip_raw is
 * allowed only at a token boundary in the active frame. Feed more physical
 * lines as needed; normal tokenization resumes at the updated position.
 * The view is borrowed until feed, next, skip, command operations or destroy. */
const unsigned char *csh_lexer_pending(const struct csh_lexer *lexer,
    size_t *length, struct csh_position *position, int *final);
int csh_lexer_skip_raw(struct csh_lexer *lexer, size_t length,
    struct csh_error *error);

#endif
