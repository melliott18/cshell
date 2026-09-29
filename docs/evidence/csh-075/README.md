# CSH-075 retained execution/process evidence

These records are bounded qualification evidence, not completion of CSH-075.
See the [clause map](../../host-execution-evidence.md) and
[ticket](../../tickets/CSH-075-host-execution-processes.md). The six original
conditions and all 14 whole-page contracts remain open. Records retain raw
stream bytes, status, invocation, effects, executable/package/source identities,
limits and failures. [runs.json](runs.json) summarizes each distinct source snapshot.

## Results

| Run | Passed | Failed | Boundary |
| --- | ---: | ---: | --- |
| Native stock execution | 210 | 44 | Forty missing-timeout assertions and four unsupported Issue 8 getconf-name assertions; exit 1. |
| Native supplied full execution | 242 | 12 | getconf name plus timeout `-f`/`-p`, each in four modes; exit 1. |
| Native declared execution subset | 242 | 0 | Explicit Darwin case list; exit 0. |
| Docker supplied full execution + controls | 251 | 16 | Same three failures plus renice relative-increment, in four modes; exit 1. Eight virtual-duration and five credential/process-limit controls pass. |
| Docker declared execution subset | 238 | 0 | Explicit Linux case list; exit 0. |
| Native existing host profile, serial rerun | 1162 | 0 | Zero gaps; exit 0. |
| Docker existing host profile | 1144 | 0 | Root run; zero gaps, separately retained capability limitations; exit 0. |
| Native earlier host profile | 1161 | 1 | PTY cleanup `/bin/ps -axo pid=,stat=` exceeded its deadline; retained as a failed run, not a waived assertion. |

`make test-host-inventory` passes the inventory check, ten ownership regressions,
and eight execution evidence regressions. The existing host-harness unit suite
passes 18 tests. Native Clang and Docker GCC compile the helper without warnings;
Linux also compiles the clock library.

The native PTY failure had shell status 0 and correct empty output, but the
cleanup subprocess timed out. A serial full rerun passes. Concurrency was present
in the failed run; that does not establish a root cause or justify a new gap
allowance. Both records remain available.

The final full native and Docker runs share source digest
`bc34762274b6c36d4a7d9036b6deb5b2fd0fc3cd5835f928e6bf0c93484cd0c5`.
The native subset has that same digest. The earlier Docker subset/profile records
retain their own source identities, preceding the final cleanup regression and
section-ledger refinements. Every selected Linux subset assertion also passes in
the final full run; the full run still exits 1 for its 16 additional failures.
A requested repeat of the Docker profile after the final full run could not start:
the Docker daemon returned an HTTP 500 on container creation. Its CLI failure is
retained in `docker-rerun-unavailable.log.gz`, not reported as a passing rerun.

## Reproduction and environment

Native commands, from the separate worktree:

```sh
make test-host-inventory
python3 -m unittest discover -s tests -p test_host_harness.py
make test-host-execution
make test-host-execution-profile
make test-host-profile HOST_EXECUTION_SUBSET=tests/host_execution_subset_darwin.json
```

Native platform: macOS 14.8.7, arm64. The full record's `package_environment`
contains the OS build; `additional_packages` records Homebrew coreutils 9.3.
The selected timeout is a private profile symlink to installed `gtimeout`.
`/bin/sh` is measured independently, including during a shadow-PATH fallback
witness. Stock evidence uses `os.defpath`, not the qualified prefix.

Docker image build:

```sh
docker build -t cshell:csh-075 .
```

Image `sha256:27fea854cb18595c563f80a13656539949f5705be235a166da6b4c70dc8e8661`
uses Debian bookworm, glibc 2.36 and the LinuxKit aarch64 kernel. The build log
and every installed package version are retained. The final runs mounted the
worktree's tests, Makefile and tools read-only into `/work`, and a disposable
result directory at `/results`; runtime source is unchanged from the built image.
This lets the final record hash the actual test inputs instead of implying that
the earlier image contains subsequent test edits.

Inside that disposable container, as root:

```sh
make test-host-profile HOST_EXECUTION_SUBSET=tests/host_execution_subset_linux.json
make test-host-inventory build/tests/host_execution_helper build/tests/host_execution_clock.so
make host-profile HOST_PROFILE_PROVISION_FLAGS=--execution
python3 tests/host_execution.py ./cshell build/tests/host_execution_helper \
  --path /work/build/host-profile/bin:/bin:/usr/bin \
  --clock-library build/tests/host_execution_clock.so --controlled-identities \
  --record /results/full-final.json
```

The selected external kill is the existing BusyBox profile override. Credential
controls drop only owned children to numeric IDs 60001–60003 and remove
supplementary groups; no account database, host clock or unrelated process is
modified. The final records confirm cleanup of all recorded timeout helpers and
credential/signal/priority targets. Source and executable hashes qualify only
these measured implementations and environments.

`python3 docs/evidence/csh-075/verify.py` checks retained counts, exact strict
failure IDs, declared subset coverage in the final full runs, and artifact hashes.
