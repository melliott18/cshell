#ifndef CSHELL_AST_H
#define CSHELL_AST_H

#include "cshell/lexer.h"

struct csh_ast;

/* Every pointer is owned. A word keeps its original token, including raw
 * spelling, source positions, and quote/expansion fragments. Substitutions
 * associate parsed $(...) bodies with COMMAND fragments; begin/end are byte
 * offsets in token.raw, including the delimiters. Backquotes remain lexical
 * fragments, decoded and parsed lazily by execution when selected. */
struct csh_ast_substitution {
    size_t fragment_index;
    size_t begin;
    size_t end;
    struct csh_ast *body;
};

struct csh_ast_word {
    struct csh_token token;
    struct csh_ast_substitution *substitutions;
    size_t substitution_count;
    size_t substitution_capacity;
};

struct csh_ast_word_vector {
    struct csh_ast_word *items;
    size_t count;
    size_t capacity;
};

struct csh_ast_command_word {
    struct csh_ast_word word;
    int assignment;
};

struct csh_ast_redirection {
    enum csh_token_kind operator_kind;
    struct csh_position start;
    struct csh_position end;
    int has_io_number;
    struct csh_token io_number;
    struct csh_ast_word operand;
    /* Here-documents only: delimiter has undergone quote removal, while
     * operand retains its spelling. Body has <<- leading tabs removed but is
     * otherwise unexpanded. Lengths define bytes; buffers have a trailing NUL.
     * A NULL body denotes an as-yet uncollected document. */
    unsigned char *delimiter;
    size_t delimiter_length;
    int delimiter_quoted;
    unsigned char *body;
    size_t body_length;
    struct csh_position body_start;
    struct csh_position body_end;
};

enum csh_ast_kind {
    CSH_AST_SIMPLE, CSH_AST_PIPELINE, CSH_AST_AND, CSH_AST_OR,
    CSH_AST_LIST, CSH_AST_SUBSHELL, CSH_AST_BRACE,
    CSH_AST_IF, CSH_AST_FOR, CSH_AST_WHILE, CSH_AST_UNTIL,
    CSH_AST_CASE, CSH_AST_FUNCTION
};

enum csh_ast_separator {
    CSH_AST_END, CSH_AST_SEMI, CSH_AST_AMPERSAND, CSH_AST_NEWLINE
};

struct csh_ast_list_item {
    struct csh_ast *command;
    enum csh_ast_separator separator;
    struct csh_position separator_start;
    struct csh_position separator_end;
};

struct csh_ast_if_branch {
    /* Both children are nonempty LISTs in a parsed tree. */
    struct csh_ast *condition;
    struct csh_ast *body;
};

enum csh_ast_case_terminator {
    CSH_AST_CASE_END, CSH_AST_CASE_BREAK, CSH_AST_CASE_FALLTHROUGH
};

struct csh_ast_case_item {
    struct csh_ast_word_vector patterns;
    /* A LIST, including an empty LIST when this item has no commands. */
    struct csh_ast *body;
    /* END has zero spans; other values retain the ;; or ;& token span. */
    enum csh_ast_case_terminator terminator;
    struct csh_position terminator_start;
    struct csh_position terminator_end;
};

/* Counts describe initialized entries. Capacities are maintained by append
 * helpers. The tree must have one owner per child and contain no cycles.
 * Redirections are in source order, independently allocated so pending
 * here-document references survive growth of the pointer vector. */
struct csh_ast {
    enum csh_ast_kind kind;
    struct csh_position start;
    struct csh_position end;
    struct csh_ast_redirection **redirections;
    size_t redirection_count;
    size_t redirection_capacity;
    union {
        struct {
            struct csh_ast_command_word *words;
            size_t word_count;
            size_t word_capacity;
        } simple;
        struct {
            struct csh_ast **commands;
            size_t command_count;
            size_t command_capacity;
            int negated;
        } pipeline;
        struct {
            struct csh_ast *left;
            struct csh_ast *right;
        } binary;
        struct {
            struct csh_ast_list_item *items;
            size_t item_count;
            size_t item_capacity;
        } list;
        struct { struct csh_ast *body; } group;
        struct {
            struct csh_ast_if_branch *branches;
            size_t branch_count;
            size_t branch_capacity;
            struct csh_ast *else_body;
        } if_clause;
        struct {
            struct csh_ast_word name;
            struct csh_ast_word_vector words;
            /* An omitted list uses positional parameters; explicit in may
             * have zero words. Expansion and iteration belong to execution. */
            int has_in;
            struct csh_ast *body;
        } for_clause;
        struct {
            struct csh_ast *condition;
            struct csh_ast *body;
        } loop;
        struct {
            struct csh_ast_word word;
            struct csh_ast_case_item *items;
            size_t item_count;
            size_t item_capacity;
        } case_clause;
        struct {
            struct csh_ast_word name;
            /* A compound command; function redirects belong to this node. */
            struct csh_ast *body;
        } function;
    } data;
    /* Reserved for the allocation-free iterative destructor. */
    struct csh_ast *destroy_next;
};

/* Constructors initialize empty objects and set *out to NULL on failure.
 * Mutators return 0 on success, -1 on failure, and require error. On success
 * they move their argument into the tree and clear it (or set *child to NULL).
 * On failure both owners remain unchanged. No helper copies or expands words.
 * Scalar words and children may be moved directly to a freshly created node. */
int csh_ast_create(struct csh_ast **out, enum csh_ast_kind kind,
    struct csh_error *error);
void csh_ast_destroy(struct csh_ast *node);
const char *csh_ast_kind_name(enum csh_ast_kind kind);
void csh_ast_word_destroy(struct csh_ast_word *word);
int csh_ast_word_add_substitution(struct csh_ast_word *word,
    struct csh_ast_substitution *substitution, struct csh_error *error);
int csh_ast_add_word(struct csh_ast *node, struct csh_ast_word *word,
    int assignment, struct csh_error *error);
int csh_ast_redirection_create(struct csh_ast_redirection **out,
    enum csh_token_kind operator_kind, struct csh_error *error);
void csh_ast_redirection_destroy(struct csh_ast_redirection *redirection);
int csh_ast_add_redirection(struct csh_ast *node,
    struct csh_ast_redirection **redirection, struct csh_error *error);
int csh_ast_pipeline_add(struct csh_ast *node, struct csh_ast **child,
    struct csh_error *error);
int csh_ast_list_add(struct csh_ast *node, struct csh_ast_list_item *item,
    struct csh_error *error);
int csh_ast_if_add(struct csh_ast *node, struct csh_ast_if_branch *branch,
    struct csh_error *error);
int csh_ast_word_vector_add(struct csh_ast_word_vector *vector,
    struct csh_ast_word *word, struct csh_error *error);
int csh_ast_case_add(struct csh_ast *node, struct csh_ast_case_item *item,
    struct csh_error *error);
/* Also accepts partially constructed items and clears all owned fields. */
void csh_ast_case_item_destroy(struct csh_ast_case_item *item);

#endif
