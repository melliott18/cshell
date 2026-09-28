"""Residual host contracts, emitted per run with environment and identities.

These are capability limitations, never known-gap allowances or passing tests.
CSH-060 owns the next qualification work; utility vendors own utility semantics.
"""
BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'

# Keep conditions individual: a supplied device does not establish ACL support,
# and a successful finite file does not establish a maximum accepted file size.
RESIDUAL = [
    ('U-035/locale-catalogs', 'printf', 'Standalone source has no message-catalog lookup; diagnostics fall back to untranslated text.'),
    ('U-035/other-locales', 'printf', 'Only C, French numeric/messages and the recorded UTF-8 locale are selected; other installed/absent locales are unqualified.'),
    ('U-035/format-allocation-limits', 'printf', '8192-byte formats/operands and 256 conversions are finite successes; allocation failure, stack exhaustion and maximum sizes are untested.'),
    ('U-035/full-format', 'printf', 'Byte, precision and numbered cases are selected witnesses; the full width/flag/conversion/error cross-product is not qualified.'),
    ('U-036/alternative-policies', 'echo', 'Only explicitly selected Apple/GNU policies have assertions; other implementations need their own documented policy and executable identity.'),
    ('U-036/argument-limits', 'echo', '8192-byte operands and 256 arguments do not reach aggregate exec or per-argument limits.'),
    ('U-037/ACLs', 'test', 'No controlled ACL grant/deny fixture; mode bits alone cannot establish ACL access behavior for test or bracket.'),
    ('U-037/unequal-identities', 'test', 'No credential-changing test/bracket execution; recorded real/effective identities describe this run only.'),
    ('U-037/device-namespaces', 'test', 'Only /dev/null and an optional explicit stat-only block node are checked; other namespaces are unavailable to this fixture.'),
    ('U-040/true-exec-resources', 'true', 'System exec-resource failure is not induced; no utility input/output limit is inferred.'),
    ('U-040/false-exec-resources', 'false', 'System exec-resource failure is not induced; no utility input/output limit is inferred.'),
    ('U-040/pwd-access-path-limits', 'pwd', 'Deleted cwd is checked; inaccessible ancestors and pathname limits need controlled permissions/filesystems.'),
    ('U-040/kill-identities-resources', 'kill', 'Cross-user denials require another identity; process-limit exhaustion is outside the owned-child signal fixture.'),
    ('U-040/cat-filesystem-limits', 'cat', '64-KiB byte preservation does not induce filesystem I/O faults or maximum file size.'),
    ('U-040/env-ARG_MAX', 'env', 'Host ARG_MAX is queried, not reached; inherited environment and per-argument constraints also affect exec.'),
    ('U-040/find-depth-locale-limits', 'find', '32 nested directories succeed; descriptor/depth exhaustion and locale-sensitive matching remain unqualified.'),
    ('U-040/ls-size-collation', 'ls', '256 C-locale entries and one UTF-8 name are checked; larger directories and locale collation require independent locale expectations.'),
    ('U-040/stty-physical-terminal', 'stty', 'A controlled PTY cannot establish physical serial/terminal hardware capabilities.'),
    ('U-040/ed-buffer-temp-signal', 'ed', '1024 input lines are printed; maximum edit buffer, temp-file failure and signal recovery are not induced.'),
    ('U-040/sed-space-limits', 'sed', 'A 32768-byte line traverses pattern/hold space and a UTF-8 dot match is checked; maxima and other multibyte expressions remain unqualified.'),
    ('U-040/head-count-interruption', 'head', 'Count 2147483647 on a two-line file is not a maximum-count or interrupted-input witness.'),
    ('U-040/cmp-offset-interruption', 'cmp', 'Difference at byte 65537 and EOF diagnostics are checked; larger offsets and interrupted-input behavior remain unqualified.'),
    ('U-040/chmod-ACL-identity-filesystem', 'chmod', 'Mode changes do not establish ACL effects, cross-user failures or filesystem-specific permissions.'),
    ('U-040/rm-depth-mount-prompt', 'rm', '32 nested directories are removed; depth exhaustion, protected mounts and interactive prompts remain unqualified.'),
    ('U-040/sleep-duration', 'sleep', 'Maximum duration cannot be witnessed by waiting within a five-second fixture budget.'),
    ('U-040/sh-host-semantics', 'sh', 'Selected invocation/status witnesses do not qualify the host shell parser, resource and locale semantics.'),
    ('U-040/other-interruptions', 'cat', 'Owned sleep TERM delivery does not qualify interrupted read/write or recovery for cat, head, cmp, ed or other utilities.'),
]


def limitations(environment, inventory):
    return [dict(condition=condition, source=BASE + utility + '.html',
                 environment=environment, reason=reason, owner='CSH-060',
                 executable=inventory[utility],
                 related_executable=inventory['['] if utility == 'test' else None)
            for condition, utility, reason in RESIDUAL]
