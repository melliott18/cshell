# CSH-129: Investigate intermittent ed SIGINT response capture

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: None
- Branch: test/CSH-129-ed-signal-capture
- Issue: [#269](https://github.com/melliott18/cshell/issues/269)

## Goal

Determine and repair the intermittent final-response failure in the existing
CSH-074 `ed/signal-int` witness without weakening its output or cleanup oracle.

## Evidence and scope

The first CSH-127 Linux run failed only `ed/signal-int` in command-string mode:
`read_until(b'recovered\n')` raised `ed exited before response`; the retained
stdout was `recovered\n*?\n*`, the child status was zero, and the child and fixture
were cleaned up. An unchanged isolated rerun passed direct, string and file
modes. See [initial language report](../evidence/csh-129/original-linux-language-initial.json.gz)
and [initial command log](../evidence/csh-129/original-linux-initial-command-0.log.gz).

Inspect `tests/host_language_helper.py` and the selected ed provider. The helper
raises on EOF from either descriptor before necessarily draining the other;
readiness and EOF ordering is a hypothesis to test, not an established cause.
CSH-127 changes no language helper or provider source. Related scope:
[CSH-074](CSH-074-host-languages-editors.md).

## Acceptance criteria

- [x] Reproduce and identify the failed response boundary with retained stdout,
      stderr, status, saved-file contents and descriptor/event ordering.
- [x] Add a deterministic regression for the identified cause and repair its
      owning component; preserve exact signal-response and saved-file assertions.
- [x] Bound waits and output, reap every child and remove every fixture on EOF,
      timeout, setup failure and success; do not introduce retries or allowances
      as substitutes for a correct oracle.
- [x] Verify direct, command-string and script-file signal witnesses on native
      macOS and unprivileged Linux, and retain the original failure evidence.

## Validation

Run the focused `tests/host_languages.py --case ed/signal-int` selection with
the public cshell binary and selected provider path, the relevant harness
regressions, and `make test-host-languages test-host-profile`. Retain failure
and successful records separately and document any remaining uncertainty.

## Implementation and diagnosis

The deterministic real-provider probe reproduces the original final-response
boundary: after ed exits normally with the correct saved file, stderr EOF is
presented before readable stdout. The old helper raises immediately. On Linux,
the probe then drains `recovered\n` from the still-unread PTY, proving the
reader discarded a pending response. The original CSH-127 run has no descriptor
trace, so its exact scheduling cannot be reconstructed; this reproduces and
repairs the demonstrated failure mechanism, without claiming a historical trace.

Native macOS reveals a second capture boundary: waiting until the editor exits
can lose the last PTY output at slave closure. Merely unregistering stderr at
EOF still fails that controlled run. The helper now keeps terminal input and
captures stdout through a pipe. Both output streams stay registered until their
own EOF, and a bounded final drain retains trailing bytes for exact assertions.
No ed provider or cshell production source changes.

`EdCapture` uses nonblocking descriptor reads, a two-second deadline per response
or drain, a combined 64-KiB output cap and a 512-event trace cap. Command writes
are bounded and handle partial writes. Setup is inside the cleanup region;
failures close PTY descriptors and reap an already-created editor. Incomplete
records include the response phase, streams, status, saved files and events.
The outer runner continues to own descendant cleanup and fixture removal.

The real-provider ordering regression and protocol-peer controls cover EOF,
split/fresh responses, trailing stdout/stderr, missing output, bad saved bytes,
signal death, floods, timeouts and setup failures before/after spawning.
Readiness, exact SIGINT transcript, unchanged original operand, saved-file bytes
and non-signal exit requirements remain strict. There are no retries or added
allowances in the witness.

## Retained validation

See [all attempts, commands and limitations](../evidence/csh-129/README.md).
Native macOS and unprivileged Linux/Docker both reproduce the pre-fix failure,
pass the repaired forced-order regression, and pass direct, command-string and
script-file `ed/signal-int` witnesses using the selected private ed provider.
The original CSH-127 report/log are copied byte-for-byte into that evidence
folder so this branch can target `main` independently of the filesystem stack.

`make test-host-languages test-host-profile` exits zero on both platforms:
1089 language assertions per run, 1162 general host assertions, and 12443 native /
12483 Linux filesystem assertions pass. The text suite has its existing two
unavailable disposable-filesystem ENOSPC cases. All 13 language harness tests
pass. Additional `make test-harness` passes on Linux (107 pass, one Darwin-only
skip); native has three retained startup timeouts out of 108 tests. The same
three tests pass in a separately retained isolated diagnostic run, without
reclassifying the initial full-suite failure. Ticket and live identity checks
pass.

The branch is ready for review; `done` remains gated on integration.
