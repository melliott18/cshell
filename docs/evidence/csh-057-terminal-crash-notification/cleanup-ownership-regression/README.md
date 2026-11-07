# Intermediate cleanup controls

[results.json](results.json) records the exact-child wait cleanup version before
the final SIGCHLD ownership hardening. [artifacts.tar.gz](artifacts.tar.gz)
retains its logs, source snapshots, mutation and earlier preexec-ignore attempt.
The preexec attempt did not preserve SIGCHLD ignore on Darwin and did not
exercise ECHILD. The subsequent constructor control did. Final shipping-source
validation is in [final-regression](../final-regression/README.md).
