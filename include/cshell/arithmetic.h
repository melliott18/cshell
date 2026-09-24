#ifndef CSHELL_ARITHMETIC_H
#define CSHELL_ARITHMETIC_H

struct csh_state;

enum csh_arith_result {
    CSH_ARITH_OK,
    CSH_ARITH_SYNTAX,
    CSH_ARITH_RANGE,
    CSH_ARITH_NOMEM,
    CSH_ARITH_READONLY
};

/* Evaluate an already-expanded expression using signed long arithmetic. Shell
 * substitutions and their quoting belong to the caller. Decimal, octal and
 * hexadecimal constants and the integer C operators (including assignments,
 * ?: and comma) are supported; sizeof, ++, -- and integer suffixes are not.
 * Empty expressions, unset names (unless nounset), and empty values yield zero.
 * Variable values must be integer constants with an optional leading sign;
 * recursive expression-valued variables are deliberately not supported.
 * Overflow, zero divisors, and invalid shifts return RANGE. Negative right
 * shifts round toward negative infinity; negative left shifts are rejected.
 * Errors leave *out and the complete shell state unchanged. No diagnostics are
 * printed and last_status is unchanged. Expression may alias a state value.
 * NULL arguments are SYNTAX. Successful assignments invalidate state views;
 * rollback after a failed evaluation can also invalidate borrowed state views.
 * Nesting beyond 128 parser levels is rejected with SYNTAX. */
enum csh_arith_result csh_arith_eval(struct csh_state *state,
    const char *expression, long *out);

/* Grammar-only check for the parser's arithmetic-first $(( ambiguity. Input is
 * the expression body, with any nested shell expansions represented by a valid
 * arithmetic operand by the caller; this function does not parse shell syntax.
 * Checks tokens, precedence, and assignment targets, but does not look up names,
 * evaluate operations, or reject out-of-range constants. Thus 1/0 is arithmetic
 * grammar even though evaluation fails. Returns OK or SYNTAX; never mutates. */
enum csh_arith_result csh_arith_probe(const char *expression);

/* Grammar-only prefix check for EOF inside an opaque shell operand. Returns
 * nonzero if the expression is valid or only lacks trailing operands or
 * delimiters. This distinguishes an incomplete candidate from one whose
 * existing grammar already rules out arithmetic. No evaluation or allocation. */
int csh_arith_probe_prefix(const char *expression);

#endif
