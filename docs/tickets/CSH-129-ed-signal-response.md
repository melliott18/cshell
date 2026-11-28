# CSH-129: Investigate intermittent ed SIGINT response capture

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: None
- Branch: Assigned when work starts
- Issue: [#269](https://github.com/melliott18/cshell/issues/269)

## Goal

Determine and repair the intermittent final-response failure in the existing
CSH-074 `ed/signal-int` witness without weakening its output or cleanup oracle.

## Evidence and scope

The first CSH-127 Linux run failed only `ed/signal-int` in command-string mode:
`read_until(b'recovered\n')` raised `ed exited before response`; the retained
stdout was `recovered\n*?\n*`, the child status was zero, and the child and fixture
were cleaned up. An unchanged isolated rerun passed direct, string and file
modes. See [initial language report](../evidence/csh-127/linux-language-initial.json.gz)
and [initial command log](../evidence/csh-127/linux-initial-command-0.log.gz).

Inspect `tests/host_language_helper.py` and the selected ed provider. The helper
raises on EOF from either descriptor before necessarily draining the other;
readiness and EOF ordering is a hypothesis to test, not an established cause.
CSH-127 changes no language helper or provider source. Related scope:
[CSH-074](CSH-074-host-languages-editors.md).

## Acceptance criteria

- [ ] Reproduce and identify the failed response boundary with retained stdout,
      stderr, status, saved-file contents and descriptor/event ordering.
- [ ] Add a deterministic regression for the identified cause and repair its
      owning component; preserve exact signal-response and saved-file assertions.
- [ ] Bound waits and output, reap every child and remove every fixture on EOF,
      timeout, setup failure and success; do not introduce retries or allowances
      as substitutes for a correct oracle.
- [ ] Verify direct, command-string and script-file signal witnesses on native
      macOS and unprivileged Linux, and retain the original failure evidence.

## Validation

Run the focused `tests/host_languages.py --case ed/signal-int` selection with
the public cshell binary and selected provider path, the relevant harness
regressions, and `make test-host-languages test-host-profile`. Retain failure
and successful records separately and document any remaining uncertainty.
