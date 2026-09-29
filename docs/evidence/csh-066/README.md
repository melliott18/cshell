# CSH-066 validation

[results.json](results.json) records source/binary hashes, platforms, commands,
exit statuses and result summaries. The broad native and Docker regression runs
preceded the last cache change from process-global to thread-local bounds; final
source checks then repeated resource/thread-stack coverage on both platforms,
with and without sanitizers. This distinction is intentional: the record does
not claim every broad suite ran again after the small cache change.

Selected final nesting output is retained for
[native ASan/UBSan](final-asan.txt), [native optimized](final-native.txt),
and [Linux optimized](final-linux.txt). Each public run has 42 exact
status/output/resource witnesses; the API fixture additionally covers 12,000
plan levels, stack-limit refresh, rollback, interrupted parsing and successive
custom thread stacks. The native broad runtime suite has 3,905 passing cases.
Linux sanitizer validation enables leak detection; native sanitizer validation
uses the project's macOS `detect_leaks=0` setting and allocation-fault accounting.

The original nine brace probes are now successful expectations in
`tests/invocation.py`; historical failures remain in the CSH-012 baseline
artifacts. These are finite witnesses, not an unlimited capacity claim.
See the [resource contract](../../nesting-resources.md) and
[ticket](../../tickets/CSH-066-resource-bounded-nesting.md).
