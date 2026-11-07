# Development observation

The first new-harness run passed the case matrix, corruption and marker checks,
but reported four errors in creation-timeout checks: missing created files
raised before the assertion record retained its timeout errors. The verifier now
records missing/unreadable objects as assertion errors, preserving the capture
record. The corrected focused setup/timeout tests pass, and both final platform
validation runs include the complete harness. This initial log is not a pass.
