# CSH-016: Introduce input sources and shell invocation modes

- Status: ready
- Type: feat
- Kind: implementation
- Parent: CSH-003
- Depends on: CSH-001
- Branch: Assigned when work starts
- Issue: [#17](https://github.com/melliott18/cshell/issues/17)

## Goal

Provide a reusable input interface for command strings, script files, and stdin,
with explicit invocation data that later parsing and state modules can consume.

## Scope

- Add owned input-source APIs independent of direct scanner access to stdin.
- Parse `-c`, script-file, and stdin invocation into owned input sources; keep
  command execution and default-binary wiring in CSH-018 and CSH-039.
- Retain POSIX invocation operands for `$0` and positional-parameter storage.
- Select interactive mode and prompting according to documented POSIX rules.
- Preserve source location and input continuity needed for multiline parsing.

## Acceptance criteria

- [ ] API fixtures read command strings, script files, and redirected stdin
  correctly; empty sources and a final line without newline reach explicit EOF
  without stale data, busy loops, or dropped bytes. No command execution is
  required to validate this input layer.
- [ ] Non-interactive modes emit no startup banner or prompt; terminal detection
  and explicitly selected interactive behavior have focused tests.
- [ ] Missing command-string operands, invalid usage, and unreadable scripts
  produce diagnostics and failure statuses without leaking input resources.
- [ ] Invocation tests inspect the correct `$0` and argument vector at the API
  boundary, even though language-level parameter expansion is not yet present.
- [ ] Long input, repeated reads, and injected allocation/read failures release
  owned storage and never expose partial command data as complete input.
- [ ] The input module and fixtures build without the legacy header, scanner,
  or executor; no compatibility adapter is required.
- [ ] Input ownership, error reporting, and source-position interfaces are
  documented for the lexer/parser and CSH-022 state-storage consumers.

## Validation

Build API fixtures natively and in Docker; read empty, single-command,
multi-command, long, and unterminated-final-line sources under bounded timeouts.
Use ASan/UBSan and controlled allocation/read failure fixtures for cleanup.
Test invocation operand mapping with API fixtures and prompt selection with a
small pseudo-terminal fixture. Check source cleanup with sanitizer diagnostics.
CSH-018 supplies the final cross-mode status matrix using the CSH-017 harness.

## Implementation notes/evidence

This ticket establishes input and invocation contracts, not parameter expansion.
Retain argument strings with explicit ownership so CSH-022 can build on this API
without waiting for the entire CSH-003 milestone. Keep multiline syntax rules in
the lexer/parser tickets while ensuring input acquisition does not discard data.
