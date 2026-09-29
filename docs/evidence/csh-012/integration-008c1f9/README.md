# Closure integration with main 008c1f9

Main advanced while closure was being prepared. PR #140 integrated CSH-064's
project-owned probe timeout cleanup; PR #141 accepted its bounded work. This
integration preserves those changes and moves further host qualification to
the open CSH-068 inventory contracts. The closed CSH-064 issue is not reopened.

`verify.py` checks the final closure tree against integration base `008c1f9` for
production, tests, build and workflow bytes; it rechecks the complete utility
inventory, disposition evidence and all changed-document links, plus the
bidirectional ownership and retained artifact audit. `verification.json` is its
retained result. There are 449 ownership pairs after adding CSH-068 to the six
additional host rows; original 443-pair snapshots remain unchanged.

`host-cleanup-audit.json` is the output of the existing CSH-064 completion audit:
it independently checks the exact current source identity against original
before/after regression and native/Linux integration records. It confirms two
before failures and three fixed passes while retaining failed external profiles.
No new runtime execution or sanitizer claim is made by these consistency checks.

Earlier `closure-5b56328/verify.py` compares its original review tree with c8c1c91;
run it on its original commit if reproducing that snapshot. The current verifier
here deliberately recognizes the separately reviewed upstream test/CI repair.
Historical manifests and source hashes are not rewritten.
