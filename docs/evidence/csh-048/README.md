# CSH-048 run artifacts

The [clause map](../../state-builtin-evidence.md) names every reused/new assertion
and its limits. [Ticket validation](../../tickets/CSH-048-state-builtin-evidence.md#validation-record)
summarizes outcomes, failures and retries. `validation.json` retains compiler,
flags, OS/system-library, Python, binary SHA-256, source/test manifest, generated
suite hashes, helper hashes, image identity and log hashes.

`ae993de53f2efcfd179e93ec3c632aa6b524b755` identifies the initial source/test
bytes. `1e08f41397ee978eda090d0338ea1ef2c5849009` adds checked directory output
writes after Linux LSan reproduced a glibc `dprintf` allocation leak on closed
stdout. The corrected normal/sanitizer identities identify this final code. Some runs preceded that commit on identical uncommitted bytes.
The source fingerprint is SHA-256 of `json.dumps(manifest, sort_keys=True).encode()`;
manifest maps Makefile/src/include/tests paths to file SHA-256, excluding Python
caches. Documentation/evidence additions are outside the fingerprint.

The original full normal runs preceded two fixture-only refinements: shell-path
unquoting uses `shlex.split` instead of removing outer quotes, and the ulimit
inventory predicate also checks the description words. Generated runtime cases
and compiled C bytes did not change. `full_normal_source` records that earlier
manifest; subsequent focused runs and initial sanitizer runs use the first committed
manifest; records labelled corrected/final include the later directory-output fix.
The identity timestamps are collection times; they do not purport to be exact
start times for every case. Logs preserve all failures as failures even when an
unchanged retry passes. `.log.gz` files are complete output, not just summaries:

```sh
gzip -dc docs/evidence/csh-048/native.log.gz
```

Reproduce normal checks from the source commit:

```sh
make clean
make -j4
make test test-pty test-harness
make test-state-builtins
python3 docs/evidence/csh-048/identity.py

docker build -t cshell-test:csh-048 .
docker run --rm --init cshell-test:csh-048 make test test-pty test-harness
docker run --rm --init cshell-test:csh-048 make test-state-builtins
```

The first normal runs used `make -j4 test test-pty test-harness`; the native PTY
cleanup timeout is retained, followed by a serial PTY retry. Reproducing
serially avoids deliberately adding contention without relaxing deadlines.
For instrumented runs, clean and use:

```sh
ASAN_OPTIONS=halt_on_error=1 MallocNanoZone=0 UBSAN_OPTIONS=halt_on_error=1 \
make test-state-builtins test-builtins test-state test-execute test-evaluation \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The Docker sanitizer image recipe is retained as `sanitizer.Dockerfile`; build
it against the normal image and run the same targets. Its normal base digest
and sanitizer image ID are recorded. All sanitizer runs retain five-second
case deadlines and halt-on-error. The kernel/system libraries differ between
native macOS and Docker/Linux; neither run substitutes for the other.
