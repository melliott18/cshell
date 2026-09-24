# Alias APIs and substitution

[CSH-030](tickets/CSH-030-alias-substitution.md) adds
[`cshell/alias.h`](../include/cshell/alias.h), direct `alias`/`unalias` handlers,
and substitution in the replacement lexer/parser. These APIs do not execute
commands. CSH-031 owns dispatcher integration and executed-script evidence;
the public `cshell` executable does not gain alias support from this change.

The contract follows POSIX.1-2024
[alias substitution](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_03_01),
[alias names](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap03.html#tag_03_10),
and the [alias](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/alias.html)
and [unalias](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/unalias.html)
utility pages. Passing module fixtures is separate from runtime conformance.

## Storage and handlers

`csh_aliases_create()` returns an empty owned table. `csh_aliases_set()` copies
both name and replacement; failed allocation leaves the previous table intact.
`csh_aliases_get()` borrows a replacement until mutation or destruction. Remove
one definition with `csh_aliases_unset()`, all definitions with
`csh_aliases_clear()`, and release the table with `csh_aliases_destroy()`.
Storage mutators report failures through `csh_error` and never print diagnostics.

Names contain one or more ASCII letters, digits, or `!%,@_-`; they need not be
variable names. The table supplies no predefined aliases. A dispatcher must
keep it local to the shell environment rather than exporting it to external
utilities or new shell invocations.

`csh_builtin_alias()` and `csh_builtin_unalias()` accept the table, `argc` and
`argv` including the command name, and borrowed output/error `FILE` streams.
They return status 0 on success, 1 for lookup/storage/output failures, and 2 for
usage errors. They do not close streams, exit, or acquire input.

`alias` accepts `name=value` definitions and name queries; no operands list the
table in name order. Output uses `name='value'` with embedded single quotes
escaped so the replacement can be read back as shell text. Values preserve
spaces, newlines, metacharacters, and empty strings. Missing queries and invalid
definitions produce diagnostics while other operands are processed.
`unalias name...` removes named definitions and reports absent names;
`unalias -a` clears the table. Both handlers support `--` to end options.

## Parser eligibility and timing

Create a parser normally, then call `csh_parser_set_aliases(parser, aliases)`.
The parser borrows the table; detach with NULL, or keep it alive until parser
destruction. Attach or mutate it only between `csh_parser_next()` calls.

An unquoted valid alias name is substituted when it could be the command name,
or when a preceding alias replacement makes it eligible through a trailing
blank. Assignment prefixes and redirection operands do not become command
names. Descriptor numbers immediately adjacent to redirection operators remain
IO_NUMBER tokens. Removed backslash-newline pairs do not quote a name; escapes
and quoted fragments prevent substitution. Ordinary arguments are unchanged
unless trailing-blank eligibility applies. Replacement text is retokenized, so
it may introduce words, operators, groups, redirections, or newlines.

Each `csh_parser_next()` returns one complete command. Semicolon-separated
commands on one line and multiline groups are parsed together; an alias change
after that returned tree does not rewrite it. Definitions and removals are
visible when the caller requests the next complete command. The parser never
executes an `alias` command found in the input. The future dispatcher must
execute each returned complete command before requesting another.

## Recursive replacement and source ownership

The lexer copies injected replacement input and tracks active alias names.
Direct and indirect self-reference leave the recursively encountered name
unexpanded, so `a=a` terminates at `a`, and `a=b; b=a` terminates at `a` when
expanding `a`. Distinct aliases can form arbitrarily long finite chains subject
to available storage. Consuming an earlier invocation does not disable a later
independent invocation of the same alias.

Alias tokens own replacement-source provenance and the physical invocation
location in addition to their raw spelling and fragments. If a word crosses an
alias boundary, its coordinates continue from the starting source over its
captured spelling; they never mix alias-local offsets with script offsets.
Parser and lexer diagnostics map generated syntax back to its physical invocation. Tokens and ASTs stay
valid after the alias table, parser, and input are destroyed. Enclosing words
retain the original spelling of command substitutions, while their parsed
child ASTs contain substituted commands. Fragment ranges index the enclosing
word's raw bytes rather than subtracting positions from different sources.

## Specified choices and boundaries

POSIX allows choices at several alias boundaries. This implementation excludes
reserved-word spellings from alias substitution, including where they would
otherwise be ordinary words. It inserts a separating space after replacement
text. It also treats a final quoted blank as requesting next-token eligibility,
as Issue 8 permits. The next token consumes that eligibility; an intervening
operator or newline prevents it reaching a later word. Recursive suppression
applies while the replacement and its nested replacements remain active.

The supported compound grammar remains the CSH-005 subset; aliases do not add
`if`, `case`, loops, or function definitions. CSH-009 owns those constructs.
Backquoted substitutions remain syntax for later expansion work. No claim is
made for dispatcher behavior before CSH-031.

Run `make test-alias` for storage, handlers, and token/AST behavior, and
`make test-parser` for allocation-failure sweeps through alias injection and the
full parser stack. See [Testing](testing.md) for sanitizer commands.
