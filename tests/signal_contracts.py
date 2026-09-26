#!/usr/bin/env python3
"""CSH-054 / SIG-001/003, U-008/015/026 strict bounded runtime witnesses."""
import argparse
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile

from execute import bounded_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('binary')
    parser.add_argument('helper')
    args = parser.parse_args()
    binary = str(Path(args.binary).resolve())
    helper_path = str(Path(args.helper).resolve())
    helper = shlex.quote(helper_path)
    cases = []

    def add(name, script, stdout='', stderr='', status=0, interactive=False):
        for mode in (('string',) if interactive else ('string', 'file', 'stdin')):
            case = dict(name=f'signal contracts: {name} ({mode})', stdin='',
                        expect=dict(stdout=stdout, stderr=stderr, status=status))
            if mode == 'string':
                case['args'] = ['-ic' if interactive else '-c', script]
            elif mode == 'file':
                case.update(args=['script'], setup={'script': script})
            else:
                case['stdin'] = script
            cases.append(case)

    add('interactive TERM ignored', 'kill -s TERM $$; echo alive\n', 'alive\n', interactive=True)
    add('lowercase TERM delivered', 'kill -s term $$\n', status=-signal.SIGTERM)
    for name in ('TERM', 'QUIT', 'TSTP', 'TTIN', 'TTOU'):
        add(f'interactive {name} override and reset',
            f"trap 'echo caught' {name}; kill -s {name} $$; trap - {name}; "
            f"kill -s {name} $$; echo alive\n", 'caught\nalive\n', interactive=True)
        for operation in ('', 'exec '):
            add(f'interactive child {operation or "fork "}{name} defaults',
                f'{operation}{helper} disposition {name}\n', 'default\n', interactive=True)
        add(f'interactive explicit ignore reaches exec {name}',
            f"trap '' {name}; exec {helper} disposition {name}\n", 'ignored\n', interactive=True)
    add('failed interactive exec restores TERM action',
        "trap 'echo caught' TERM; exec /no-csh-054-executable; kill -s TERM $$; echo alive\n",
        'caught\nalive\n', 'cshell: /no-csh-054-executable: command not found\n', interactive=True)
    for shape, script in (
        ('pipeline', 'trap -p USR1 | /bin/cat'),
        ('background', 'trap -p USR1 & wait'),
        ('general substitution', 'value=$(trap -p USR1; :); echo "$value"'),
    ):
        add(f'caught action resets in {shape}', "trap 'echo parent' USR1; " + script + '\n',
            "trap -- '-' USR1\n")
    for action in ('false; exit', 'true; exit', 'f() { false; exit; }; f', 'eval "false; exit"'):
        add(f'EXIT omitted status after {action}', f"trap '{action}' EXIT; exit 7\n", status=7)
    add('signal action omitted exit status', "trap 'false; exit' USR1; kill -s USR1 $$\n")
    add('subshell inside EXIT uses its own status',
        "trap '(false; exit); printf \"sub:%s\\n\" \"$?\"; exit' EXIT; exit 7\n",
        'sub:1\n', status=7)
    # All selected signal-derived statuses are <=255 (128 + host signal).
    # Thus the >256 signal-termination clause has no operands in this policy.
    # Keep each case below the normal five-second bound even with sanitizer
    # fork/exec startup under load; each batch still checks every exact status.
    for start in range(0, 256, 16):
        add(f'exit operands {start} through {start + 15}',
            ''.join(f'(exit {n}); printf "%s\\n" "$?"\n' for n in range(start, start + 16)),
            ''.join(f'{n}\n' for n in range(start, start + 16)))
    add('mixed invalid trap operands continue',
        "trap ':' USR1 CSH_BAD USR2; echo $?; trap -p USR1 CSH_BAD USR2\n",
        "1\ntrap -- ':' USR1\ntrap -- ':' USR2\n",
        'cshell: trap: invalid condition: CSH_BAD\n' * 2, status=1)
    add('trap output failure', "trap -p USR1 >&-\n", status=1,
        stderr='cshell: trap: cannot write output\n')
    add('zero signal and group operands', 'kill -s 0 0; a=$?; kill -s 0 -- -$$; echo "$a:$?"\n', '0:0\n')
    add('mixed invalid kill operands continue',
        "trap 'echo delivered' USR1; kill -s uSr1 bad $$; echo $?\n", 'delivered\n1\n',
        'cshell: kill: invalid pid: bad\n')
    # Required symbolic signals from XBD signal.h; noncatchable KILL/STOP are
    # checked by name/status conversion, never delivered to the runner.
    names = 'ABRT ALRM BUS CHLD CONT FPE HUP ILL INT KILL PIPE QUIT SEGV STOP TERM TSTP TTIN TTOU USR1 USR2 POLL PROF SYS TRAP URG VTALRM XCPU XFSZ'.split()
    for name in names:
        if name == 'POLL' and sys.platform == 'darwin':
            number = 7  # _POSIX_C_SOURCE signal.h defines SIGPOLL as 7.
        elif hasattr(signal, 'SIG' + name):
            number = int(getattr(signal, 'SIG' + name))
        else:
            continue  # Optional host signal; recorded by the platform name set.
        add(f'kill name/status {name}', f'kill -l {number} {128 + number}\n', f'{name}\n{name}\n')
        if name not in ('KILL', 'STOP'):
            mixed = ''.join(c.lower() if i % 2 else c for i, c in enumerate(name))
            add(f'kill mixed case {name}', f"trap 'value=delivered' {name}; kill -s {mixed} $$; echo \"$value\"\n", 'delivered\n')
    with tempfile.TemporaryDirectory(prefix='cshell-signal-contracts-') as directory:
        env = dict(PATH=os.defpath, HOME=directory, TMPDIR=directory, LC_ALL='C', LANG='C')
        # Host sigaction probes supply the set of installable signal numbers;
        # listing/reinput must preserve every one, including numeric extensions.
        probe = bounded_run([helper_path, 'signal-conditions'], cwd=Path(directory), env=env, timeout=5)
        assert (probe.returncode, probe.stderr) == (0, b''), probe
        numbers = list(map(int, probe.stdout.split()))
        for number in numbers:
            add(f'host condition reinput {number}',
                f"trap ':' {number}; saved=$(trap -p {number}); trap - {number}; "
                f'eval "$saved"; trap -p {number}\n',
                # Query spelling is separately validated below; no reference shell.
                f"trap -- ':' {signal_name(number)}\n")
        listing = bounded_run([binary, '-c', 'trap -p'], cwd=Path(directory), env=env, timeout=5)
        assert (listing.returncode, listing.stderr) == (0, b''), listing
        expected = {"trap -- '-' EXIT", *(f"trap -- '-' {signal_name(n)}" for n in numbers)}
        assert set(listing.stdout.decode().splitlines()) == expected, listing
        assert len(listing.stdout.decode().splitlines()) == len(expected), listing
        suite = Path(directory) / 'signals.json'
        suite.write_text(json.dumps(dict(version=1, name='CSH-054 signals', kind='replacement', cases=cases)))
        subprocess.run([sys.executable, str(Path(__file__).with_name('smoke.py')), binary,
                        '--suite', str(suite)], check=True, timeout=180)


def signal_name(number):
    # Canonical POSIX names (SIGIO is the host synonym for POLL).
    # Darwin's POSIX header exposes POLL as 7, hides WINCH, and Python uses
    # the unrestricted header (EMT=7). Linux exposes POLL/IO and WINCH.
    if sys.platform == 'darwin' and number == 7:
        return 'POLL'
    names = 'HUP INT QUIT ILL ABRT FPE KILL SEGV SYS PIPE ALRM TERM USR1 USR2 CHLD CONT STOP TSTP TTIN TTOU BUS TRAP URG XCPU XFSZ VTALRM PROF POLL'.split()
    if sys.platform != 'darwin':
        names.append('WINCH')
    for name in names:
        if getattr(signal, 'SIG' + name, None) == number:
            return name
    return str(number)


if __name__ == '__main__':
    main()
