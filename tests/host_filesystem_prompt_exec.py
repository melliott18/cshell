#!/usr/bin/env python3
"""Preserve owned PTY input/stderr, separate stdout, then exec the exact provider."""
import json
import os
import sys

provider = sys.argv[1]
# An unavailable/wrong terminal is setup failure, never a successful decision.
if not os.isatty(0) or not os.isatty(2) or os.tcgetpgrp(0) != os.getpgrp():
    raise OSError('owned foreground PTY required')
fd = os.open('.prompt-stdout', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.dup2(fd, 1)
os.close(fd)
with open('.prompt-environment.json', 'x') as marker:
    json.dump(dict(phase='armed', provider=provider, stdin_tty=True, stderr_tty=True,
                   stdout_tty=os.isatty(1), foreground=True), marker)
os.execv(provider, sys.argv[1:])
