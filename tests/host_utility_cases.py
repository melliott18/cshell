"""CSH-052 specification-derived host integration assertions.

Expected output is fixed here, never copied from the executable under test.
Errors use status/diagnostic predicates where POSIX leaves the wording open.
"""
import shlex
import signal
import sys

# Deliberately scoped integration dependencies, not the complete POSIX utility set.
HOSTS = ('printf', 'echo', 'test', '[', 'true', 'false', 'pwd', 'kill',
         'cat', 'env', 'find', 'ls', 'stty', 'ed', 'sed', 'head', 'cmp',
         'chmod', 'rm', 'sleep', 'sh')
INTRINSICS = ('alias', 'bg', 'cd', 'command', 'fg', 'getopts', 'hash', 'jobs',
              'kill', 'read', 'type', 'ulimit', 'umask', 'unalias', 'wait')
SPECIALS = (':', '.', 'break', 'continue', 'eval', 'exec', 'exit', 'export',
            'readonly', 'return', 'set', 'shift', 'times', 'trap', 'unset')


def cases(paths, helper, echo_policy=None):
    def case(name, script, out=b'', status=0, err=b'', **kw):
        return dict(name=name, script=script + '\n', stdout=out, status=status,
                    stderr=err, **kw)

    # Each pathname is independently inventoried, then used with exec to prove
    # that even intrinsic kill has an executable implementation on the host.
    commands = {
        'printf': ("'%s\\n' reachable", b'reachable\n', 0),
        'echo': ('reachable', b'reachable\n', 0),
        'test': ('a = a', b'', 0), '[': ('a = a ]', b'', 0),
        'true': ('', b'', 0), 'false': ('', b'', 'nonzero'),
        'pwd': ('-P >pwd; read p <pwd; case $p in /*) :;; *) exit 9;; esac', b'', 0),
        'kill': ('-l 15', b'TERM\n', 0),
        'cat': ('data', b'one\ntwo\n', 0),
        'env': (f'-i CSH_HOST=value {helper} env CSH_HOST', b'value\n', 0),
        'find': ('tree -type f', b'tree/leaf\n', 0),
        'ls': ('-1 tree', b'leaf\n', 0),
        'stty': ('-a </dev/null', b'', 'nonzero'),
        'ed': ("-s edit <<'END'\n1p\nq\nEND", b'edit\n', 0),
        'sed': ("-n '1p' data", b'one\n', 0),
        'head': ('-n 1 data', b'one\n', 0),
        'cmp': ('data data', b'', 0),
        'chmod': ('600 edit', b'', 0),
        'rm': ('remove', b'', 0), 'sleep': ('0', b'', 0),
        'sh': ("-c 'exit 17'", b'', 17),
    }
    for name in HOSTS:
        path = paths[name]
        operands, out, status = commands[name]
        yield case('U-034 exec ' + name,
                   ('exec ' if name != 'pwd' else '') + shlex.quote(path or name) + ' ' + operands,
                   out, status, 'nonempty' if name == 'stty' else b'',
                   requires=name, files={'remove': None} if name == 'rm' else {})
        if path:
            # kill is intrinsic, pwd may use its regular builtin; slash exec above
            # distinguishes these from the PATH report for external names.
            if name not in ('kill',):
                yield case('U-034 lookup ' + name, 'command -v ' + shlex.quote(name),
                           (path + '\n').encode())

    for name in ('printf', 'echo', 'test', '[', 'true', 'false', 'pwd'):
        quoted = shlex.quote(name)
        yield case('U-041 external PATH ' + name, f'PATH=shadow; {quoted}', status=73)
        yield case('U-041 external missing ' + name, f'PATH=/missing; {quoted}',
                   status=127, err=f'cshell: {name}: command not found\n'.encode())
    yield case('U-041 fc excluded UP', 'PATH=/missing; command -v fc', status=1)

    actions = {
        'alias': "alias csh_host=value; alias csh_host", 'bg': 'bg', 'cd': 'cd tree',
        'command': 'command :', 'fg': 'fg', 'getopts': 'getopts a opt -a',
        'hash': 'hash -r', 'jobs': 'jobs', 'kill': 'kill -l 15',
        'read': 'read line <data', 'type': 'type read', 'ulimit': 'ulimit -S -f 128',
        'umask': 'umask 027', 'unalias': 'unalias -a', 'wait': 'wait',
    }
    for name in INTRINSICS:
        yield case('U-041 intrinsic report ' + name,
                   f'PATH=/missing; command -v {name}', (name + '\n').encode())
        action = actions[name]
        out = {'alias': b"csh_host='value'\n", 'kill': b'TERM\n',
               'type': b'read is a shell builtin\n'}.get(name, b'')
        err = f'cshell: {name}: job control unavailable\n'.encode() if name in ('bg', 'fg') else b''
        status = 1 if name in ('bg', 'fg') else 0
        for path in ('/missing', 'shadow'):
            yield case('U-041 intrinsic execute ' + name + ' ' + path,
                       f'PATH={path}; {action}', out, status, err)
        # A function precedes an intrinsic; command suppresses that function.
        yield case('U-041 function precedence ' + name,
                   f'{name}() {{ return 61; }}; PATH=/missing; {name}', status=61)
        # command itself would suppress its own function only if invoked through
        # a different entry point; its function-precedence witness is sufficient.
        if name != 'command':
            yield case('U-041 command bypass ' + name,
                       f'{name}() {{ return 61; }}; PATH=/missing; command ' + action.replace('; ', '; command '),
                       out, status, err)
    yield case('U-041 special reports', 'PATH=/missing; command -v ' + ' '.join(SPECIALS),
               ('\n'.join(SPECIALS) + '\n').encode())
    yield case('U-041 assignment categories',
               "v=old; v=intrinsic command :; command -p printf '%s\\n' \"$v\"; v=special :; command -p printf '%s\\n' \"$v\"",
               b'old\nspecial\n')

    printf_cases = (
        ('reuse', "'<%s>\\n' '' 'two words' last", b'<>\n<two words>\n<last>\n'),
        ('missing operands', "'%s/%d/%b/END\\n'", b'/0//END\n'),
        ('literal percent', "'a %% b\\n'", b'a % b\n'),
        ('integer conversions', "'%d %i %u %o %x %X\\n' -12 010 12 9 31 31", b'-12 8 12 11 1f 1F\n'),
        ('character constants', ''''%d %d %c\\n' "'A" '\"B' xyz''', b'65 66 x\n'),
        ('width precision', "'[%5.2s][%-4s][%04d]\\n' abc x 7", b'[   ab][x   ][0007]\n'),
        ('format escapes', r"'\a\b\f\n\r\t\v\\\101'", b'\a\b\f\n\r\t\v\\A'),
        ('b escapes', r"'%b' '\a\b\f\n\r\t\v\\\0101'", b'\a\b\f\n\r\t\v\\A'),
        ('b stop', r"'%bTAIL%s' 'one\ctwo' ignored", b'one'),
        ('b precision', r"'[%.3b]' 'ab\tcd'", b'[ab\t]'),
        ('end options', "-- '-%s\\n' value", b'-value\n'),
        ('C numeric optional float', "'%.2f\\n' 1.5", b'1.50\n'),
    )
    for name, operands, out in printf_cases:
        yield case('U-035 printf ' + name, 'printf ' + operands, out,
                   gap='printf-b-precision' if name == 'b precision' else None)
    yield case('U-035 printf numbered reuse', "printf '%2$s:%1$s\\n' a b c d", b'b:a\nd:c\n',
               gap='printf-numbered')
    for name, operands, out in (
            ('invalid number', "'%d' invalid", b'0'),
            ('partial number', "'%d' 12x", b'12'),
            ('overflow', "'%d' 999999999999999999999999999999999999", None),
            ('missing format', '', b'')):
        yield case('U-035 printf ' + name, 'printf ' + operands,
                   'any' if out is None else out, 'nonzero', 'nonempty')

    for name, operands, out in (('empty', '', b'\n'), ('ordinary', "'' a 'two words'", b' a two words\n'),
                                ('literal --', '-- -x', b'-- -x\n')):
        yield case('U-036 echo ' + name, 'echo ' + operands, out)
    # Documented platform policies, not portable-language fixture oracles.
    for name, operands, darwin, linux in (
        ('n', '-n value', b'value', b'value'),
        ('e', r"-e 'a\nb'", b'-e a\\nb\n', b'a\nb\n'),
        ('E', r"-E 'a\nb'", b'-E a\\nb\n', b'a\\nb\n'),
        ('ne', r"-ne 'a\nb'", b'-ne a\\nb\n', b'a\nb'),
        ('backslash', r"'a\nb'", b'a\\nb\n', b'a\\nb\n')):
        yield case('U-036 echo policy ' + name, 'echo ' + operands,
                   darwin if (echo_policy or ('darwin' if sys.platform == 'darwin' else 'gnu')) == 'darwin' else linux)

    expressions = [('zero', '', 1), ('empty', "''", 1), ('one', "'two words'", 0),
                   ('literal --', '--', 0), ('not empty', "! ''", 0), ('not word', '! x', 1),
                   ('nonempty', '-n x', 0), ('zero string', "-z ''", 0),
                   ('equal', "'a b' = 'a b'", 0), ('unequal', 'a != b', 0),
                   ('equal false', 'a = b', 1), ('negated primary', '! -f data', 1),
                   ('negated binary', '! 1 -eq 2', 0)]
    for operator in ('eq', 'ne', 'gt', 'ge', 'lt', 'le'):
        expressions.append(('integer ' + operator, '2 -' + operator + ' 1',
                            0 if operator in ('ne', 'gt', 'ge') else 1))
    for primary, operand in (('b', 'data'), ('c', '/dev/null'), ('d', 'tree'), ('e', 'data'),
                              ('f', 'data'), ('g', 'setgid'), ('h', 'link'), ('L', 'dangling'),
                              ('p', 'fifo'), ('r', 'data'), ('s', 'data'), ('S', 'socket'),
                              ('u', 'setuid'), ('w', 'data'), ('x', 'executable'), ('t', '0')):
        expressions.append(('primary ' + primary, '-' + primary + ' ' + operand,
                            1 if primary in ('b', 't') else 0))
    for expression, status in (('data -ef hardlink', 0), ('new -nt old', 0),
                                ('old -ot new', 0), ('new -nt absent', 0), ('absent -ot new', 0),
                                ('-e dangling', 1), ('-e absent', 1)):
        expressions.append((expression, expression, status))
    for utility in ('test', '['):
        for name, expression, status in expressions:
            yield case('U-037 ' + utility + ' ' + name,
                       utility + ' ' + expression + (' ]' if utility == '[' else ''), status=status,
                       gap='test-missing-time' if expression in ('new -nt absent', 'absent -ot new') else None)
    yield case('U-037 bracket missing close', '[ a = a', status='error', err='nonempty')
    yield case('U-037 invalid integer', 'test x -eq 1', status='error', err='nonempty')
    # No -a/-o or arbitrary >4 argument expressions: unspecified in the base profile.
    yield case('U-038 true', 'true')
    yield case('U-039 false', 'false', status='nonzero')
    yield case('U-038 U-039 control', 'if true; then false || :; else exit 9; fi')

    for command in ('printf x', 'echo x', 'test a = a', '[ a = a ]', 'true', 'false'):
        yield case('U-040 unused stdin ' + command,
                   '{ ' + command + ' >/dev/null; read first; printf "%s\\n" "$first"; } <data', b'one\n')
    for command in ('head -n 1', 'sed -n 1q'):
        yield case('U-040 seekable offset ' + command,
                   '{ ' + command + '; cat; } <data', b'two\n' if command.startswith('sed') else b'one\ntwo\n')
    yield case('U-040 operand order', 'cat second first', b'second\nfirst\n')
    yield case('U-040 eight bit argv', 'v=$(cat high); printf %s "$v" >bytes', files={'bytes': bytes(range(128, 256))})
    yield case('U-040 eight bit input', 'cat binary >bytes', files={'bytes': bytes(range(256))})
    yield case('U-040 environment scope',
               f"CSH_HOST=old; export CSH_HOST; CSH_HOST='two words' {helper} env CSH_HOST; "
               f"{helper} env CSH_HOST", b'two words\nold\n')
    yield case('U-040 resource inheritance',
               f'ulimit -S -f 128; {helper} file-limit', b'65536\n')
    for name, command in (('invalid option', 'cat -Z'), ('missing option argument', 'head -n')):
        yield case('U-040 ' + name, command, status='nonzero', err='nonempty')
    yield case('U-040 special syntax exception', ': -- -Z ignored; eval ":"')
    yield case('U-026 host kill signal number', f'exec {shlex.quote(paths["kill"] or "/missing-host-kill")} -l {signal.SIGTERM}', b'TERM\n')
    yield case('U-026 host kill exit status', f'exec {shlex.quote(paths["kill"] or "/missing-host-kill")} -l {128 + signal.SIGTERM}',
               b'TERM\n', gap='kill-status')
    yield case('U-026 host kill delivery',
               f"{helper} signal-child & p=$!; {shlex.quote(paths['kill'] or '/missing-host-kill')} -s TERM \"$p\"; wait \"$p\"",
               status=128 + signal.SIGTERM)

    yield case('U-034 stty terminal roundtrip',
               'saved=$(stty -g); stty echo; stty "$saved"; current=$(stty -g); '
               'test "$saved" = "$current"', modes=('pty',))
