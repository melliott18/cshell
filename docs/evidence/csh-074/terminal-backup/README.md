# CSH-074 terminal and backup continuation

These records extend the bounded operation subset; the complete normative pages
and the native macOS job-control failure remain open. All records retain failed
attempts rather than replacing them with corrected results.

| Record | Result |
| --- | --- |
| `terminal-attempt-1.json.gz` | 44 new terminal assertions pass on macOS |
| `patch-followup-attempt-1.json.gz` | macOS system patch: 20 pass, 4 first-backup failures |
| `patch-private-attempt-1.json.gz` | Unmodified GNU patch 2.8: 72 pass, 4 output-backup failures |
| `native-ordinary.json.gz`, `linux-ordinary.json.gz` | Corrected profile: 773 pass each |
| `native-sanitizer.json.gz`, `linux-sanitizer.json.gz` | ASan/UBSan: 773 pass each |
| `native-profile.json.gz`, `linux-profile.json.gz` | Existing host profile: 1162 pass each, no failures or gaps |
| `native-runtime.log.gz` | Selected-PATH runtime: 3950 pass |
| `terminal-controls-final.log.gz` | Eight harness controls pass |
| `terminal-fault-recheck.log.gz`, `terminal-fault-long.log.gz` | Local job-control fixture still fails; default bound and extended diagnostic attempt |
| `terminal-fault-child.sample.txt.gz`, `terminal-fault-context.json` | Owned child sampled in macOS `sigprocmask`; identities and commands retained |

The ordinary and sanitizer macOS and Debian 12 Docker records share source-input SHA-256
`18f5b754058d67c1d9b9cd4bca40532545eabd6741975386a993e0c3fc4ac4e2`.
The JSON includes the actual selected executables and binary hashes, complete
arguments, source/input/oracles, both output channels, status, file effects,
resource bounds, filesystem, credentials, cleanup and build flags. The private
patch build includes its source archive and correction hashes.

## Reproduction

```sh
make -j4 test-host-profile
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime
make -B -j4 test-host-languages \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'

docker build -t cshell-csh074:terminal-followup .
docker run --name csh074-terminal-validation cshell-csh074:terminal-followup \
  make -j4 test-host-profile
docker run --name csh074-terminal-sanitizer cshell-csh074:terminal-followup \
  sh -c "make clean && make -j4 test-host-languages CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'"
```

Containers are disposable, run as UID 10001, and use their own toolchains. Their
records are copied before removal. Docker availability in this continuation
supersedes only the previous local availability limitation, not its historical
results. No manual prompt entry was used.

The [environment assessment](../../../host-languages-evidence.md#remaining-work-and-environment-requirements)
distinguishes remaining automated coverage from locale/filesystem setup and a
clean macOS comparison. The old job-control failure is not waived by successful
language-provider tests.

`records.json` hashes each uncompressed gzip payload and records its byte count.
Gzip timestamps are fixed at zero. Source and provider identities are inside
qualification JSON, not inferred from filenames or package names.
