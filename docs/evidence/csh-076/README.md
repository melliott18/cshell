# CSH-076 validation

This records the [bounded locale/catalog profile](../../host-locale-catalogs.md).
**CSH-076 is not complete.** Full utility contracts, retained vendor failures
and unqualified page sections remain owned by CSH-076. The native current
subset passed. Local Docker returned HTTP 500; subsequent hosted CI separately
validated the native C adapter revision on Linux (see below).

## Current native implementation

macOS 14.8.7 arm64, GNU gettext 0.26 from the installed
`/usr/local/Cellar/gettext/0.26_1` package. Provider/launcher paths, hashes,
compiler command, package version, linked libraries and actual environments are
inside each JSON record. Read records with `gzip -dc FILE.json.gz`.

| Command | Result | Record |
| --- | --- | --- |
| `make -j4 test-host-profile` | Catalog subset: 355 passed, 0 failed; existing host profile: 1,162 passed, 0 failed, 0 gaps | [catalog](native-qualified.json.gz), [existing profile](native-profile.json.gz) |
| `make test-host-catalog-contracts` | Strict audit: 355 passed, 20 failed (four conditions × five modes); make exits 2 | [audit](native-contracts.json.gz) |
| `make test-host-inventory test-host-catalog-harness` | Ownership accounting, 10 ownership self-tests, 7 catalog self-tests and native adapter fixture pass | [log](accounting.log) |
| `cc -std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer tests/catalog_adapter_fixture.c -o build/tests/catalog_adapter_sanitize` followed by `ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 ./build/tests/catalog_adapter_sanitize` | Pass | [log](adapter-sanitize.log) |
| `CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty` | 3,950 runtime cases pass. PTY notification and 30 job cases pass, then the terminal handoff fault fixture times out and cleanup reports an exhausted ps deadline/EPERM. The remaining PTY target did not run. | [full first log](native-runtime-first.log.gz) |

The strict audit retains required expectations for Darwin gencat unknown escapes
and stream operands, iconv `-s`, and locale's environment report. These are
failures, not allowed gaps. The qualified target does not execute these named
conditions and explicitly lists them as unqualified.

A focused `CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-pty`
retry repeats the same terminal handoff timeout after the 30 passing job cases:
[retry log](native-pty-retry.log). Its cause has not been established. A stock-PATH control of the same unchanged
fixture also times out: [stock control](native-pty-stock-control.log). The catalog
profile is therefore not necessary to reproduce this failure; no causal fix is claimed.

The remaining `CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime-pty`
target was then run independently and passed 33 cases:
[log](native-runtime-pty.log). This does not erase the terminal handoff failures.

The adapter was changed from an intermediate Python launcher to native C so
exec preserves inherited signal dispositions. Current native records use C.
The final native adapter self-test also adds a missing-option cleanup assertion;
the ASan/UBSan and accounting logs include that assertion.

## Linux intermediate evidence and final environment failure

`docker build -t cshell-csh076:local .` produced Debian bookworm arm64 image
`sha256:ea50f72caedcf8ec290f8fcaa387046542fe3de3737dbd694a735f3031891a07`.
The [build log](docker-build-first.log.gz) retains the base image and package
installation. GNU gettext is 0.21; exact libc/package identities are in JSON.

The intermediate qualified command used that image with read-only mounts of
`Makefile`, `tests/` and `tools/` into `/work`, and a writable evidence directory:

```sh
docker run --rm \
  -v "$PWD/Makefile:/work/Makefile:ro" \
  -v "$PWD/tests:/work/tests:ro" \
  -v "$PWD/tools:/work/tools:ro" \
  -v "$PWD/build/csh076-linux:/evidence" cshell-csh076:local sh -c \
  'make -j4 test-host-catalogs > /evidence/qualified.log 2>&1; result=$?;
   test ! -f build/tests/host-catalog-results.json || cp build/tests/host-catalog-results.json /evidence/qualified.json;
   test ! -f build/host-profile/locales.json || cp build/host-profile/locales.json /evidence/locales.json;
   exit "$result"'
```

It passed **395 cases**, with five private locales generated and independently
verified: [subset record](linux-qualified-intermediate.json.gz),
[locale setup](linux-locales-intermediate.json.gz). These records precede the
native C adapter replacement and therefore do **not** qualify the final Linux
implementation. The underlying GNU programs and locale setup have independent
recorded identities; no result is promoted to a newer source hash.

The final `docker build -t cshell-csh076:final .` failed before building because
the daemon returned HTTP 500 from `/_ping`. Subsequent `docker info` and a direct
socket health check also failed. [Build failure](docker-final-build-failure.log)
and [health response](docker-health-failure.log.gz) are retained; a later
[final health check](docker-health-final.log.gz) still returns HTTP 500. Other active
workloads used the shared engine, so it was not restarted. Final Linux adapter,
combined-profile, runtime and sanitizer checks were unverified locally at that
point. Subsequent hosted results below resolve that gap for commit 4460922.

## Shared fixture publication update

Native `make host-catalog-fixtures` publishes five verified locale profiles and
passes 16 bounded provider/consumer checks, plus independent MO parsing:
[fixture record](native-shared-fixtures.json.gz). `make test-host-catalogs`
passes 355 cases with the shared module and setup dependency:
[subset record](native-shared-qualified.json.gz). The existing host profile
passes 1,162 cases with zero gaps: [profile record](native-shared-profile.json.gz).
Each retains its actual source hash; the profile run precedes the last harness
failure-publication test, while the subset and fixture records include it.

The native adapter fixture and nine Python harness tests pass:
[harness log](native-shared-harness.log). The deliberate missing-provider test
prints a FAIL diagnostic and verifies that provisioning publishes failure,
cleans its temporary setup directory, and preserves an existing consumer's data.
A second `make host-catalog-fixtures` followed by `load_fixtures` on both the old
immutable manifest and latest manifest also passed; the generated roots differed
and all retained input hashes remained valid. Linux publication of retained
locale generations awaits validation of this update.

## Hosted CI for native adapter revision 4460922

[PR run 36631063411](https://github.com/melliott18/cshell/actions/runs/36631063411)
ran exact head `446092248d5725f2512f66dd3529579898ccfe58`.
The retained [job/step metadata](ci-4460922.json) records successful Ubuntu 24.04
and Docker jobs, including host profile, runtime, PTY and sanitizer checks.
The macOS job passed its ordinary build, tests, PTY, selected profile and harness
steps, then its sanitizer step was cancelled. The overall run is **cancelled**;
this is not an all-platform sanitizer pass. These results qualify that commit's
bounded subset and do not cover later shared-fixture publication changes.

## Earlier attempts and oracle corrections

[First native](native-first.json.gz) and [first Linux](linux-first.json.gz)
records retain both real defects and fixture mistakes; they are not current
qualification. Corrections were made from the normative contracts:

- An empty gettext key retrieves the header; it does not produce empty text.
- The gencat unknown-escape case was separated from the main grammar fixture.
  Its diagnostic with success remains a strict native failure under XCU §1.4.
- Missing gencat operands were replaced by a genuinely unrecognized option:
  accepting an extension outside the synopsis is not itself a failed assertion.
- Linux generated locales are consumed by their documented LOCPATH/name lookup,
  rather than by an absolute `setlocale` name. Absolute-name behavior is not
  qualified. French ISO-8859-1 is supplied explicitly for output conversion.
- Linux `$delset` against an existing catalog and iconv `-s` remain strict open
  reproductions, excluded by name from the declared passing subset.

The [record index](records.json) records uncompressed hashes, source identities
and totals. [Normative source hashes](sources.json) identify the official pages
read for these assertions. No historical stock-host evidence was edited.
