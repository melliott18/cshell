#ifndef CSHELL_PARSER_H
#define CSHELL_PARSER_H

#include "cshell/ast.h"

struct csh_parser;
struct csh_aliases;
enum csh_parse_result {
    CSH_PARSE_ERROR = -1, CSH_PARSE_EOF = 0, CSH_PARSE_TREE = 1,
    CSH_PARSE_INCOMPLETE = 2, CSH_PARSE_INTERRUPTED = 3
};

/* The parser borrows input, which must be unread and outlive it, and owns its
 * lexer. It reads
 * physical lines only as grammar requires. next returns one complete command
 * list at a newline boundary (including its here-documents), or a final list
 * at EOF. Empty lines are skipped. Optional alias substitution occurs during
 * token reading; no word expansion or execution occurs. */
int csh_parser_create(struct csh_parser **out, struct csh_input *input,
    struct csh_error *error);
/* Optional alias table, borrowed until detached or parser destruction. Attach
 * or mutate only between next calls; changes apply to the next complete command.
 * The caller owns the table and may detach it with NULL. */
void csh_parser_set_aliases(struct csh_parser *parser,
    const struct csh_aliases *aliases);
/* Optional notification immediately before each physical input read. The
 * callback may print a prompt, but must not read input or reenter the parser.
 * continuation is zero at a fresh command (including after blank/comment
 * lines), nonzero within unfinished syntax or a here-document. Context is
 * borrowed; NULL callback detaches it. The parser itself never prints. */
void csh_parser_set_read_hook(struct csh_parser *parser,
    void (*before_read)(void *context, int continuation), void *context);
void csh_parser_destroy(struct csh_parser *parser);
const char *csh_parser_source_name(const struct csh_parser *parser);
/* TREE transfers a fully owned tree; every other result sets *out to NULL.
 * INCOMPLETE means final EOF within unfinished syntax. ERROR means invalid
 * syntax, acquisition, allocation or an explicit nesting-limit failure.
 * EOF and failures are sticky. error is cleared on TREE/EOF. Diagnostics use
 * the input source name and byte positions; this module never prints them. */
enum csh_parse_result csh_parser_next(struct csh_parser *parser,
    struct csh_ast **out, struct csh_error *error);

/* Tokenize an unquoted here-document body using body-specific rules and the
 * normal nested-command parser. Output owns the word and substitution ASTs. */
int csh_parser_document(const void *bytes, size_t length,
    struct csh_ast_word *out, struct csh_error *error);

#endif
