"""Clause-derived CSH-075 assertions; no utility supplies its own oracle."""
import math
import os
import re
import signal

UTILITIES = tuple('env false getconf kill nice nohup ps renice sh sleep time timeout true uname'.split())
BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'


def cases(helper, directory, owned_pid):
    def row(utility, name, args=(), stdout=b'', status=0, stderr=b'', **kwargs):
        return dict(id=utility + '/' + name, utility=utility, args=list(args),
                    stdout=stdout, status=status, stderr=stderr,
                    sections=['DESCRIPTION', 'OPTIONS', 'OPERANDS', 'STDOUT', 'STDERR', 'EXIT STATUS'],
                    **kwargs)

    for utility, status in [('true', 0), ('false', 'false-status')]:
        yield row(utility, 'status', status=status, stdin=b'unused\n')
    yield row('env', 'empty', ['-i'])
    yield row('env', 'listing', ['-i', 'CSH_A=two words', 'CSH_B='],
              stdout=b'CSH_A=two words\nCSH_B=\n', unordered=True)
    yield row('env', 'exact-environment', ['-i', 'CSH_A=value', helper, 'env'], b'CSH_A=value\n')
    yield row('env', 'replace', ['CSH_A=new', helper, 'getenv', 'CSH_A'], b'new\n', env={'CSH_A': 'old'})
    yield row('env', 'inherit', [helper, 'getenv', 'CSH_A'], b'old\n', env={'CSH_A': 'old'})
    yield row('env', 'remove-inherited', ['-i', helper, 'getenv', 'CSH_A'], b'missing\n', env={'CSH_A': 'old'})
    yield row('env', 'operand-path', ['-i', 'PATH=' + str(directory), 'argument-probe', 'args', 'found'], b'5:found\n')
    for utility in ('env', 'nice', 'nohup', 'time', 'timeout'):
        prefix = ['-p'] if utility == 'time' else ['0'] if utility == 'timeout' else []
        timing = 'timing' if utility == 'time' else b''
        yield row(utility, 'child-status', prefix + [helper, 'exit', '23'], status=23, stderr=timing)
        yield row(utility, 'arguments', prefix + [helper, 'args', '', 'two words'],
                  b'0:\n9:two words\n', stderr=timing)
        yield row(utility, 'missing', prefix + ['csh-075-no-such-command'], status=127, stderr='nonempty')
        yield row(utility, 'not-executable', prefix + ['./denied'], status=126, stderr='nonempty')
    yield row('nice', 'increment', ['-n', '3', helper, 'nice'],
              (str(min(19, os.getpriority(os.PRIO_PROCESS, 0) + 3)) + '\n').encode())
    yield row('nohup', 'hangup-disposition', [helper, 'hup'], b'ignored\n', absent=['nohup.out'])
    yield row('getconf', 'ARG_MAX', ['ARG_MAX'], (str(os.sysconf('SC_ARG_MAX')) + '\n').encode())
    yield row('getconf', 'PATH', ['PATH'], (os.confstr('CS_PATH') + '\n').encode())
    yield row('getconf', 'NAME_MAX', ['NAME_MAX', '.'], (str(os.pathconf(directory, 'PC_NAME_MAX')) + '\n').encode())
    yield row('getconf', 'invalid-variable', ['CSH_075_INVALID'], status='nonzero', stderr='nonempty')
    yield row('getconf', 'issue8-environment', ['_POSIX_V8_LP64_OFF64'], stdout='configuration')
    yield row('kill', 'signal-number', ['-l', str(signal.SIGTERM)], b'TERM\n')
    yield row('kill', 'probe-owned', ['-s', '0', str(owned_pid)], alive=True)
    yield row('kill', 'deliver-owned', ['-s', 'tErM', str(owned_pid)], terminated=signal.SIGTERM)
    yield row('ps', 'owned-pid', ['-p', str(owned_pid), '-o', 'pid='], stdout='pid', pid=owned_pid)
    yield row('renice', 'relative-increment', ['-n', '1', '-p', str(owned_pid)], priority_delta=1)
    yield row('sleep', 'zero', ['0'])
    yield row('sleep', 'one-second', ['1'], minimum_seconds=1)
    yield row('sleep', 'invalid', ['invalid'], status='nonzero', stderr='nonempty')
    yield row('sh', 'command-parameters', ['-c', 'printf "%s\\n" "$0" "$#" "$1" "$2"', 'name', 'a', 'two words'],
              b'name\n2\na\ntwo words\n')
    yield row('sh', 'stdin', ['-s', 'a'], b'1:a\n', stdin=b'printf "%s:%s\\n" "$#" "$1"\n')
    yield row('sh', 'file', ['./host-script', 'a'], b'a\n')
    yield row('sh', 'noexec', ['-n', './host-script'], absent=['effect'])
    yield row('sh', 'syntax-error', ['-c', 'if'], status='nonzero', stderr='nonempty')
    yield row('timeout', 'expiry', ['1', helper, 'timed-park'], b'ready\n', 124, minimum_seconds=1)
    yield row('timeout', 'foreground', ['-f', '1', helper, 'timed-park'], b'ready\n', 124, minimum_seconds=1)
    yield row('timeout', 'preserve', ['-p', '1', helper, 'timed-park'], b'ready\n', 'term-status', minimum_seconds=1)
    yield row('timeout', 'signal-case', ['-s', 'tErM', '1', helper, 'timed-park'], b'ready\n', 124, minimum_seconds=1)
    yield row('timeout', 'kill-after', ['-k', '0.2', '1', helper, 'timed-ignore-term'], b'ready\n', 'kill-status', minimum_seconds=1.2)
    yield row('timeout', 'invalid-duration', ['invalid', helper, 'exit', '0'], status=125, stderr='nonempty')
    system = os.uname()
    for option, field in [('', 'sysname'), ('-s', 'sysname'), ('-n', 'nodename'),
                          ('-r', 'release'), ('-v', 'version'), ('-m', 'machine')]:
        yield row('uname', field + ('-default' if not option else ''), [option] if option else [],
                  (getattr(system, field) + '\n').encode())
    yield row('uname', 'ordered-selection', ['-mrns'],
              (' '.join(getattr(system, field) for field in ('sysname', 'nodename', 'release', 'machine')) + '\n').encode())


def matches(expected, actual, mode, case):
    if expected == 'false-status':
        return 1 <= actual <= 125
    if expected == 'nonzero':
        return actual > 0
    if expected == 'term-status':
        return actual == (-signal.SIGTERM if mode == 'direct' else 128 + signal.SIGTERM)
    if expected == 'kill-status':
        return actual in (124, -signal.SIGKILL) if mode == 'direct' else actual in (124, 128 + signal.SIGKILL)
    if expected == 'nonempty':
        return bool(actual)
    if expected == 'configuration':
        return re.fullmatch(rb'(?:-?[0-9]+|undefined)\n', actual) is not None
    if expected == 'pid':
        return re.fullmatch(rb'[ \t]*' + str(case['pid']).encode() + rb'\n', actual) is not None
    if expected == 'timing':
        matcher = re.search if case['status'] != 0 else re.match
        match = matcher(rb'(?m)^\n?real ([0-9]+\.[0-9]+)\nuser ([0-9]+\.[0-9]+)\nsys ([0-9]+\.[0-9]+)\n', actual)
        if not match:
            return False
        digits = math.ceil(math.log10(os.sysconf('SC_CLK_TCK')))
        return all(len(value.split(b'.')[1]) >= max(1, digits) for value in match.groups())
    return expected == actual
