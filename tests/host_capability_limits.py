"""Residual host contracts, emitted per run with environment and identities.

These are capability limitations, never known-gap allowances or passing tests.
CSH-064 owns the next qualification work; utility vendors own utility semantics.
"""
BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'

# Keep conditions individual: a supplied device does not establish ACL support,
# and a successful finite file does not establish a maximum accepted file size.
RESIDUAL = [
    ('U-035/locale-catalogs', 'printf', 'Standalone source has no message-catalog lookup; diagnostics fall back to untranslated text.'),
    ('U-035/other-locales', 'printf', 'C/French/UTF-8 plus available German numeric and GB18030 byte cases are bounded witnesses; other locales and translated catalogs remain unqualified.'),
    ('U-035/format-allocation-limits', 'printf', 'Test-only strdup/realloc ENOMEM branches and controls are checked when supplied; libc allocation failure, stack exhaustion and maximum accepted sizes remain untested.'),
    ('U-035/full-format', 'printf', 'Selected defined sign/base/width/precision/conversion and invalid-format cases extend the binary regression; the full combination space remains unqualified.'),
    ('U-036/alternative-policies', 'echo', 'Explicit Apple/GNU and BusyBox FEATURE_FANCY_ECHO policies have independent assertions; other builds and policies need fresh identities and expectations.'),
    ('U-036/argument-limits', 'echo', 'Single and aggregate oversized exec vectors require E2BIG with a fixed environment; exact successful thresholds and other environment sizes remain unqualified.'),
    ('U-037/ACLs', 'test', 'Opt-in Linux-root fixtures check a named-user ACL grant and denial with equal IDs for test/bracket; combined unequal-ID ACL predicates fail on Debian 12/13 and sid coreutils 9.10/glibc 2.43 (strict --unequal-acl reproducer; includes false grants as well as rejected grants); CSH-061/062 add access/default ACL read/write/execute controls, multiple named users, two supplementary groups, user precedence and masks; unequal combinations are strict opt-in assertions. Each run records its selected fixture filesystem; CSH-063 adds owner/owning-group precedence, no fallback to other, mask-independent owner/other access and creation-mode restrictions with independent operations. Darwin and other filesystems remain unqualified.'),
    ('U-037/Darwin-ACLs', 'test', 'This run has no supplied privileged Darwin identity fixture; ordered allow/deny entries, inheritance and effective-identity access remain unqualified. Requires a disposable root-controlled Darwin environment, never a modification to real user accounts.'),
    ('U-037/unequal-identities', 'test', 'Opt-in Linux-root fixtures check effective-owner/group reads with unequal UID/GID pairs and empty groups; CSH-062 covers two explicit supplementary groups (10003/10004), multiple ACL entries and named-user precedence; --unequal-acl requires the same grants with unequal IDs, without allowances. CSH-063 adds owner and owning-group selection and no-fallback controls under equal/unequal IDs. Other credentials and identity namespaces remain unqualified.'),
    ('U-037/device-namespaces', 'test', 'Explicit block and private Linux character/block nodes are stat-only witnesses; other namespaces and device I/O are unqualified and real disk contents are never fixtures.'),
    ('U-040/true-exec-resources', 'true', 'Oversized exec is rejected with E2BIG before utility entry; process/memory exhaustion and loader failure remain untested, with no utility capacity inferred.'),
    ('U-040/false-exec-resources', 'false', 'Oversized exec is rejected with E2BIG before utility entry; process/memory exhaustion and loader failure remain untested, with no utility capacity inferred.'),
    ('U-040/pwd-access-path-limits', 'pwd', 'Deleted cwd is checked; inaccessible ancestors and pathname limits need controlled permissions/filesystems.'),
    ('U-040/kill-identities-resources', 'kill', 'Cross-user denials require another identity; process-limit exhaustion is outside the owned-child signal fixture.'),
    ('U-040/cat-filesystem-limits', 'cat', 'A child-only 1024-byte RLIMIT_FSIZE with ignored SIGXFSZ checks partial output and diagnostic failure; filesystem I/O faults and maximum file size remain untested.'),
    ('U-040/env-ARG_MAX', 'env', 'Oversized single and aggregate exec vectors require E2BIG before env entry; env internal exec limits, inherited environments and exact thresholds remain unqualified.'),
    ('U-040/find-depth-locale-limits', 'find', '32 nested directories and UTF-8 single-character matching are checked; descriptor/depth exhaustion and broader locale matching remain unqualified.'),
    ('U-040/ls-size-collation', 'ls', '256 C-locale entries and one UTF-8 name are checked; larger directories and locale collation require independent locale expectations.'),
    ('U-040/stty-physical-terminal', 'stty', 'A controlled PTY cannot establish physical serial/terminal hardware capabilities.'),
    ('U-040/ed-buffer-temp-signal', 'ed', '1024 input lines are printed; maximum edit buffer, temp-file failure and signal recovery are not induced.'),
    ('U-040/sed-space-limits', 'sed', '32768-byte hold/pattern space, available UTF-8/GB18030 character matching and file-limit failure are checked; maxima and other multibyte expressions remain unqualified.'),
    ('U-040/head-count-interruption', 'head', 'Count 2147483647 on a two-line file is not a maximum-count or interrupted-input witness.'),
    ('U-040/cmp-offset-interruption', 'cmp', 'Difference at byte 65537 and EOF diagnostics are checked; larger offsets and interrupted-input behavior remain unqualified.'),
    ('U-040/chmod-ACL-identity-filesystem', 'chmod', 'Opt-in Linux-root fixtures check non-owner chmod denial; ACL effects, additional credential combinations and filesystem-specific permissions remain unqualified.'),
    ('U-040/rm-depth-mount-prompt', 'rm', '32-level removal and explicit -i yes/no prompts are checked; depth exhaustion, protected mounts and terminal-driven permission prompts remain unqualified.'),
    ('U-040/sleep-duration', 'sleep', 'Maximum duration cannot be witnessed by waiting within a five-second fixture budget.'),
    ('U-040/sh-host-semantics', 'sh', 'Selected invocation/status witnesses do not qualify the host shell parser, resource and locale semantics.'),
    ('U-040/other-interruptions', 'cat', 'Owned sleep TERM delivery does not qualify interrupted read/write or recovery for cat, head, cmp, ed or other utilities.'),
]


def limitations(environment, inventory):
    return [dict(condition=condition, source=BASE + utility + '.html',
                 environment=environment, reason=reason, owner='CSH-064',
                 implementation_owner='selected utility/libc/platform vendor',
                 executable=inventory[utility],
                 related_executable=inventory['['] if utility == 'test' else None)
            for condition, utility, reason in RESIDUAL]
