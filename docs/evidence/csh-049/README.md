# CSH-049 run artifacts

See the [clause map](../../execution-evidence.md) and
[ticket run record](../../tickets/CSH-049-execution-evidence.md#validation-record).

`validation.json` records source and binary identity, generated-suite hashes,
compiler/flags, OS/libc/Python, Docker image/base digest, controlled-environment
context and artifact hashes. Source hashes cover Makefile, src, include and tests,
excluding Python caches; they agree across native, Docker and native ASan copies.
Normal Docker generated-suite/helper hashes were reconstructed from the same
immutable image after the test container exited; the native copies are retained.

The `.log.gz` files retain raw results. Read one with `gzip -dc FILE.log.gz`.
`native-harness.log.gz` is a failed attempt, followed by an unchanged passing
retry. `*-known-gaps.log.gz` are **failing** strict CSH-055 reproductions and
must not be counted as passes. Normal test logs include capability skips with
explicit owners. No diagnostic or prompt normalization is applied.

Reproduce normal validation from the worktree:

```sh
make -j4 test
make test-pty
make test-harness
make docker-build DOCKER_IMAGE=cshell-test:csh-049
docker run --rm --init cshell-test:csh-049 sh -c 'make -j4 test && make test-pty && make test-harness'
docker run --rm --init --user 0 cshell-test:csh-049 python3 tests/invocation.py ./cshell
```

The focused new cases are `make test-execution-evidence`. Sanitizer flags and
scope are in the ticket. Generated helper paths differ by worktree; source
fixture bytes and the recorded hashes identify the exact assertions.
