# CSH-073 transformation and stream-boundary extension

This record extends, and does not replace, the [original CSH-073 evidence](../csh-073/README.md).
The [four-group contract map](../../host-text-contracts.md#transformation-offset-large-input-and-interruption-qualification)
defines the qualified slices and remaining scope. All 194 new assertions pass
in the retained macOS 14.8.7, Ubuntu and Debian runs: transformations 68,
offsets 56, large inputs 48, interruptions 22. They have no gap allowances.

## Reproduction and limits

```sh
make test-host-inventory test-host-text-harness
python3 tests/host_text.py ./cshell --boundaries --record build/text-subset.json
python3 tests/host_text.py ./cshell --boundaries --audit --record build/text-audit.json
```

The explicit audit is expected to return nonzero on the retained providers;
its vendor failures do not qualify those requirements. The normal declared
subset returns zero only if every executed assertion passes. The eight native
unavailable conditions and two Ubuntu unavailable capacity conditions remain
separate from the four new groups, which have no unavailable rows.

Debian qualification uses the repository Dockerfile, a dedicated disposable
`--tmpfs /capacity:rw,size=1m,mode=1777`, and `--capacity-root /capacity`.
Local Docker returned HTTP 500 for both API versions tried; the retained
`text-extension-docker-unavailable.log.gz` is a setup failure, not Linux
qualification. The dedicated GitHub workflow supplies the Linux environments
and uploads the complete results and exact image inspection separately.

Every normal case runs as direct exec and through public cshell string/file/stdin
modes. Signal probes run directly and through cshell exec. New large-file cases
use an adapter that changes only private descriptors before exec. Python's
startup SIGPIPE/SIGXFZ/SIGXFSZ ignores are reset to the ordinary subprocess
exec defaults; a negative-control test requires SIGPIPE from a readerless pipe.
Signal tests use owned PIDs/FIFOs/pipes, verify stopped state via waitpid, and
check continued bytes/file effects instead of treating a delay as survival.

Large output oracles compare every byte and file length in bounded chunks.
The 16 MiB generated-file ceiling and 20-second large-case deadline are
harness protections. Pipe capture remains 65536 bytes. Output records include
expected/actual lengths and SHA-256 plus first mismatch offset; hashes are
provenance, not a substitute for the byte comparison. Fixtures are removed and
owned leaders reaped after success or failure.

## Validation record

The native initial full subset passed 726 assertions with eight unavailable
capabilities. The native strict audit passed 742, failed 14, and retained eight
unavailable capabilities; all four extension groups passed. Both runs report
exact source/provider identities, argv, outputs, effects and case limits.
The first hosted Ubuntu subset passed 732 with two unavailable capacity rows;
Debian passed 734 with zero unavailable rows. Their audits retained 18 existing
failures (Ubuntu 744 passes, Debian 746 passes).

The first hosted run is
[36644609139](https://github.com/melliott18/cshell/actions/runs/36644609139),
source `708f9654ce9f4d031e13ad1556f9394bc0bfed44`. Its successful Ubuntu/Debian
artifacts are retained under `hosted-initial/`. It preceded the small I/O adapter
signal-default repair. Final validation uses source
`cc6d43984edc4e97416c12be3fb97dc0e602bd29` and is retained separately; audit
expectations and the 194 asserted contracts are unchanged.

Final hosted validation is
[36644920521](https://github.com/melliott18/cshell/actions/runs/36644920521).
The Ubuntu and Debian jobs completed successfully; macOS 15 remained queued
when the evidence was captured and is not claimed as a completed result.
The completed local native run uses macOS 14.8.7.

| Final environment | Subset pass | Fail | Unavailable | New assertions passing |
| --- | ---: | ---: | ---: | ---: |
| macOS 14.8.7 | 726 | 0 | 8 | 194 |
| Ubuntu 24.04 | 732 | 0 | 2 | 194 |
| Debian container | 734 | 0 | 0 | 194 |

All three final subset records match the tested source files at `cc6d439`.
The final hosted audits retain their nonzero exit statuses: Ubuntu has
744 passes, 18 failures and two unavailable rows; Debian has 746 passes,
18 failures and no unavailable rows. The native audit above was captured
at `708f965`, before the adapter signal-default repair. These audit failures
remain outside the declared passing subset. The final Ubuntu providers include
coreutils 9.4, sed 4.9 and ed 1.20.1; Debian uses coreutils 9.1, sed 4.9 and
ed 1.19. Exact package revisions and environment identities are in the records.

[artifacts.json](artifacts.json) records source identity checks and SHA-256
checksums for all retained raw artifacts. Final hosted records are under
`hosted-final/`; the final native subset is
`text-extension-native-signal-final.json.gz`.

There are 12 harness regressions, including corrupt/truncated/appended large
output, wrong direct-exec output, missing group accounting, a fake tee that
does not ignore SIGINT, and the adapter's default SIGPIPE. Existing inventory
and section-accounting checks remain strict. No complete utility page, maximum
input size, arbitrary EINTR-return retry policy, or ed SIGINT recovery is claimed.

## Exploratory attempts

`text-extension-exploratory.json.gz` retains each first direct-mode result. Its
one failure was a fixture that omitted the required newline terminating sed's
appended text; the source was corrected, not the expected output. The N/P/D
case was subsequently made explicitly `-n` so it asserts those commands without
relying on end-of-input automatic printing. All other first direct-mode extension
assertions passed. The first 22 interruption assertions also passed and are in
`text-interruption-exploratory.json.gz`.

The tee readiness condition was tightened to require the first marker in both
stdout and its file before signalling; this avoids conflating a pre-write signal
with the intended policy assertion. No vendor expectations were relaxed. The
I/O adapter signal-default change has a dedicated regression and separate final
runs. Earlier snapshots remain immutable, and their source digests refer to
those recorded revisions, not a claim that the current tree is identical.
