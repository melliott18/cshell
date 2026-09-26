FROM cshell-test:csh-048
ENV ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1
ENV EVIDENCE_CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' EVIDENCE_LDFLAGS='-fsanitize=address,undefined'
RUN make clean && make -j2 cshell build/tests/state_builtin_helper build/tests/execute_helper build/tests/builtin_fixture build/tests/execute_fixture build/tests/state_fixture build/tests/state_faults build/tests/execute_faults build/tests/assignment_fixture CFLAGS="$EVIDENCE_CFLAGS" LDFLAGS="$EVIDENCE_LDFLAGS"
