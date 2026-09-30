# Host locale and catalog qualification

CSH-076 supplies an opt-in, **bounded subset** for seven external utilities.
It does not complete their full contracts. The executable under test, public
cshell dispatch, setup capabilities, provider defects and missing coverage are
recorded separately. [Current ownership](../tests/host_contracts.json) keeps
CSH-076 open for every remaining contract and its four conditional locale IDs.

## Provider selection and setup

`make test-host-profile` includes `make test-host-catalogs`. The latter also runs
adapter/harness self-tests. No cshell builtin or system executable is replaced.

- `gencat`, `iconv`, `locale` and `localedef` use `os.defpath`.
- The GNU gettext package supplies `gettext`, `ngettext` and `msgfmt`. Darwin
  setup uses `brew install gettext` and its `bin` directory on the provisioning
  PATH; Debian installs `gettext` in the disposable Docker image. The provisioner
  only selects existing programs. `--catalog-bin` selects a specific package.
- Private native launchers adapt POSIX `msgfmt -S` to GNU `--strict`, and decode C
  simple/octal/hex escapes for `gettext -e` and `ngettext -e` before invoking
  the vendor with `-E`. Domain names and plural counts are not decoded.
  The native launcher preserves inherited signal dispositions through exec.
  Default escape processing is `-E`, a permitted default. GNU extensions are
  not the adapter's contract; unknown options diagnose and fail.
- `host-locales` uses Linux `localedef` to generate French/German/English UTF-8,
  Chinese GB18030 and French ISO-8859-1 locales under
  `build/host-profile/locales`. Generation and an independent libc consumer
  must pass before publication of a retained generation and update of that symlink. `LOCPATH` is passed to both
  the existing host runner and the new catalog runner. Darwin verifies the
  installed names, codesets and decimal separators instead; it does not claim
  generated-locale coverage.

All setup failures are fatal. `build/host-profile/locales.json` records actual
setup commands, source/charmap hashes, consumer output and generated hashes.
The profile manifest records actual launcher and provider paths and hashes and
native adapter compiler/linker command. Qualification records add provider versions,
linked-library paths, platform/package identity and all build/test source hashes.
These identities do not establish a full library dependency closure.

## Shared interface for dependent tracks

Run `make host-locales` for just the five locale capabilities; this no longer
requires unrelated host utility providers. Run `make host-catalog-fixtures` for
locales plus verified catalogs and encoding inputs. Neither target builds cshell
or runs the full utility suite. `make test-host-catalogs` includes both setup and
the independent five-mode utility qualification.

`build/host-profile/fixtures.json` is the latest schema-version-1 manifest.
Python consumers can use the shared loader from the repository's `tests` path:

```python
from pathlib import Path
from locale_catalog_fixtures import load_fixtures

fixtures = load_fixtures('build/host-profile/fixtures.json')
root = Path(fixtures['root'])
env = fixtures['profiles']['de_DE.UTF-8']['env']
# Pass env explicitly to the consuming subprocess; LC_ALL and LANGUAGE are set.
# env includes the selected PATH and Linux LOCPATH, where needed.
input_bytes = (root / 'GB18030.txt').read_bytes()
```

The loader rejects unsuccessful provisioning and changed/missing inputs. Hold
one returned record for the duration of a run. Every publication has an immutable
catalog directory, its own `manifest.json`, and (Linux) an immutable locale
generation. Reprovisioning atomically updates the latest manifest and the
compatibility `locales` symlink; it retains older generations until `make clean`.
Do not run `make clean` while another consumer uses that checkout's fixtures.
Cross-worktree consumers must use the producer's absolute manifest path and keep
that checkout available; copied manifests are not portable binary catalogs.

The manifest names locale environments, codesets and decimal separators; hashes
all supplied files; and records exact provider/probe/source identities and bounded
verification commands. Shared files include `messages.po`, `messages.msg`,
`messages.cat`, `compiled.mo`, both French and German hand-authored `demo` MO
catalogs, and literal UTF-8/Latin-1/GB18030 input bytes. The French `compiled`
domain supplies four independently checked plural outcomes. Only the French and
German UTF-8 profiles supply translations; other locale profiles supply encoding
and numeric capabilities. Catalog setup checks both independent MO-reader results
and actual gettext/ngettext consumers, libc catgets results, and four iconv
conversions. These fixture checks are a bounded qualification, not complete
utility contracts. Setup failure publishes a failed latest record and exits
nonzero; already-held successful generations remain available.

## Independent assertions and bounds

Every selected case runs by direct absolute-path execution, public cshell PATH
lookup in command-string/script-file/stdin modes, and explicit cshell `exec`.
Catalog source, expected translations and expected encoding bytes are authored
in `tests/locale_catalog_fixtures.py` and `tests/host_catalog_cases.py`; utilities never generate their own oracle.

- Hand-assembled GNU MO files test gettext independently of msgfmt. Domain
  precedence, missing messages, four plural outcomes, LANGUAGE/locale precedence,
  escape processing, output encoding and spacing/newlines have byte assertions.
- Python's MO reader checks msgfmt output independently of the selected gettext.
  Inputs cover continuation/comments, fuzzy entries, multiple files/domains,
  `-D`, `-o`, `-S`, and `-cv` newline/type errors.
- A C `catgets` consumer checks gencat contents, replacement, deletion, quoting,
  escapes, continuation and UTF-8. Binary catalog layout is vendor-owned.
- Literal Latin-1, UTF-8 and GB18030 bytes check iconv in both directions and
  file order. Locale keyword/category formatting and precedence are asserted;
  implementation-dependent lists use explicit predicates, not golden output
  copied from the utility. List completeness is not qualified.
- Linux localedef is exercised through every dispatch mode, including stdin
  source and private output consumed through `LOCPATH`. Error output is checked
  for absence of permanent generated files. This is not a claim to support
  absolute-path `setlocale` names or every locale category grammar.

Ordinary invocations have a five-second watchdog; localedef has thirty seconds.
Combined output is limited to 65,536 bytes and each output file to 8 MiB, with
smoke's CPU, descriptor, core and process-group cleanup protections. Those are
fixture bounds, not measured utility maxima. Each case has a private directory
removed after success, failure or timeout. Self-tests check timeout/assertion
cleanup, missing-provider failure, corrupted/wrong catalogs, adapter operand
boundaries and clause-map/exclusion consistency. Cleanup by the harness does
not establish the vendor's signal/temporary-file cleanup contract.

## Clause map and open boundaries

The [machine clause map](../tests/host_catalog_clauses.json) accounts separately
for all thirteen normative behavior sections of every page and XCU §§1.1–1.6.
Each section references concrete cases or states an open/conditional disposition.
The [scope manifest](../tests/host_catalog_scope.json) identifies remaining
behavior by utility and exact provider-failure reproducers. XSI NLSPATH behavior
is unselected; no missing base behavior is called optional.

`make test-host-catalogs` runs only the declared subset, with zero failure or gap
allowances. `make test-host-catalog-contracts` additionally runs the retained
strict reproducers; its nonzero exit is expected on the recorded vendors and
must never be described as passing. The actual failing assertions stay unchanged:

| Host | Strict reproducer | Unqualified behavior |
| --- | --- | --- |
| Darwin | `gencat/stdin-stdout` | Required `-` stream operands rejected |
| Darwin | `gencat/unknown-escape` | Diagnostic with success for a valid escape; XCU §1.4 STDERR requires error status for diagnostics |
| Darwin | `iconv/invalid-policy` | `-s` still emits an invalid-character diagnostic |
| Darwin | `locale/environment` | LANG and LC_ALL report differs from prescribed C-environment format |
| Linux | `gencat/merge-replace-delete` | `$delset` fails to remove a set from an existing catalog |
| Linux | `iconv/invalid-policy` | `-s` still emits an invalid-character diagnostic |

CSH-076 retains these exact failed contracts, Darwin generated locales, and the
per-section unqualified behavior in the machine map. Vendors retain implementation
ownership. Shared locale availability resolves the four conditional prerequisites
only on recorded successful profiles; printf/sed/find behavior remains with its
existing utility owners. The original stock-host inventories are immutable and
are not relabeled by these selected-profile results.

See [native and Linux evidence](evidence/csh-076/README.md).
