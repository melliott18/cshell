#!/usr/bin/env python3
"""CSH-081 strict residual terminal witnesses; no missing-capability waivers."""
from host_terminal import main


def cases():
    def c(name, utility, args=(), **kw):
        row = dict(name=name, utility=utility, args=list(args), status=0,
                   stdout=b'', stderr=b'', terminal=b'')
        row.update(kw)
        return row

    # The complete POSIX circumflex table, independently mapped to byte values.
    for char, value in [(chr(n), n - 96) for n in range(97, 123)] + [(chr(n), n - 64) for n in range(65, 91)] + [
            ('[', 27), ('\\', 28), (']', 29), ('^', 30), ('_', 31), ('?', 127)]:
        yield c('stty/circumflex-' + str(value) + ('-upper' if char.isupper() else ''), 'stty', ['eof', '^' + char],
                input_tty=True, control=['VEOF', value])
    for name, args, flags in [
            ('nl', ['icrnl', 'nl'], [(0, 'ICRNL', False)]),
            ('-nl', ['-icrnl', 'inlcr', 'igncr', '-nl'],
             [(0, 'ICRNL', True), (0, 'INLCR', False), (0, 'IGNCR', False)])]:
        yield c('stty/combination-' + name, 'stty', args, input_tty=True, flags=flags)
    # The selected Darwin/Linux defaults are ^? and ^U, not inferred from stty.
    yield c('stty/ek', 'stty', ['erase', 'x', 'kill', 'y', 'ek'], input_tty=True,
            controls={'VERASE': 127, 'VKILL': 21})
    # sane's values are unspecified. This checks the selected provider policy.
    yield c('stty/sane-policy', 'stty', ['-icanon', '-echo', '-isig', 'sane'],
            input_tty=True, flags=[(3, 'ICANON', True), (3, 'ECHO', True), (3, 'ISIG', True)])
    yield c('stty/report-content', 'stty', ['-a'], input_tty=True, stdout=None,
            report_tokens=['eof', 'eol', 'erase', 'intr', 'kill', 'quit', 'susp', 'start', 'stop', 'min', 'time'])
    for interval in range(1, 10):
        yield c('tabs/interval-' + str(interval), 'tabs', ['-' + str(interval)],
                tty_fds=[1], oracle='tabs', terminal=None, stops=list(range(0, 41, interval)))
    for label, value in [('tabs', '1\t10\t+10\t+10'), ('mixed', '1, 10\t+10 ,30')]:
        yield c('tabs/separator-' + label, 'tabs', [value], tty_fds=[1],
                oracle='tabs', terminal=None, stops=[0, 9, 19, 29])
    yield c('tabs/alternate-width', 'tabs', ['-4'], term='csh081narrow',
            tty_fds=[1], oracle='tabs', terminal=None, stops=[0, 4, 8, 12, 16], window=[24, 17])
    yield c('tabs/width-one', 'tabs', ['-1'], window=[24, 1], tty_fds=[1],
            oracle='tabs', terminal=None, stops=[0])
    for label, value in [('unset', None), ('empty', '')]:
        yield c('tabs/default-' + label, 'tabs', ['-8'], environment={'TERM': value},
                tty_fds=[1], status='positive', stderr='diagnostic')
        yield c('tabs/override-' + label, 'tabs', ['-Tcsh077', '-8'], environment={'TERM': value},
                tty_fds=[1], oracle='tabs', terminal=None, stops=[0, 8, 16, 24, 32, 40])
    for label, args in [('option', ['-@']), ('missing-type', ['-T']),
                        ('descending', ['10,1']), ('overflow', ['1,+999999999999999999999']),
                        ('newline', ['1\n10']), ('empty', ['']), ('outside-width', ['1,42'])]:
        yield c('tabs/reject-' + label, 'tabs', args, tty_fds=[1],
                status='positive', stderr='diagnostic')
    yield c('tabs/end-options', 'tabs', ['--', '1,10,20,30'], tty_fds=[1],
            oracle='tabs', terminal=None, stops=[0, 9, 19, 29])
    yield c('tabs/unsupported', 'tabs', ['-8'], term='csh077empty',
            tty_fds=[1], status='positive', stderr='diagnostic')
    for label, args in [('attached', ['-Tcsh077', '-8']),
                        ('repeated', ['-T', 'absent-csh077', '-Tcsh077', '-8'])]:
        yield c('tabs/type-' + label, 'tabs', args, term='absent-csh077',
                tty_fds=[1], oracle='tabs', terminal=None, stops=[0, 8, 16, 24, 32, 40])
    for label, args, status in [('no-operand', [], 2), ('missing-type', ['-T'], 2),
                                 ('option', ['-@', 'clear'], 2), ('empty-operand', [''], 4)]:
        yield c('tput/error-' + label, 'tput', args, tty_fds=[1], status=status, stderr='diagnostic')
    for label, term in [('unset', None), ('empty', '')]:
        yield c('tput/term-' + label, 'tput', ['clear'], environment={'TERM': term},
                tty_fds=[1])
        yield c('tput/type-overrides-' + label, 'tput', ['-Tcsh077plain', 'clear'],
                environment={'TERM': term}, tty_fds=[1], terminal=b'CLEAR')
    yield c('tput/end-options', 'tput', ['--', 'clear'], term='csh077plain', tty_fds=[1], terminal=b'CLEAR')
    # stdout remains an actual PTY, opened read-only. This is a real EBADF,
    # not the undefined tabs/tput behavior with non-terminal output.
    for utility, args, status in [('tty', [], 'gt1'), ('stty', ['-a'], 'positive'),
                                  ('tabs', ['-8'], 'positive'), ('tput', ['clear'], 5)]:
        yield c(utility + '/output-ebadf', utility, args, input_tty=True,
                readonly_stdout=True, status=status, stderr='diagnostic')
    yield c('tty/nonterminal-output-ebadf', 'tty', readonly_stdout=True,
            status='gt1', stderr='diagnostic')
    yield c('tty/device-alias', 'tty', input_tty=True, input_alias=True, oracle='ttyname')
    for label, tz, expected in [('west', 'EST5', b'Dec 31 19:00'),
                                ('east', 'JST-9', b'Jan 1 09:00')]:
        yield c('who/timezone-' + label, 'who', ['{records}'], oracle='who', stdout=None,
                environment={'TZ': tz}, who_time=expected)
    # Lower-priority locale settings conflict deliberately. C output is required
    # by LC_ALL precedence; non-C catalog completeness is a separate contract.
    for utility, args, tty, status, stdout in [
            ('tty', [], False, 1, b'not a tty\n'),
            ('stty', ['eof', '^a'], True, 0, b''),
            ('tabs', ['-0'], False, 0, b''),
            ('tput', ['clear'], False, 0, b''),
            ('mesg', ['n'], True, 1, b''),
            ('who', ['{empty}'], False, 0, b''),
            ('write', [], True, 'positive', b'')]:
        extra = dict(input_tty=tty, status=status, stdout=stdout,
                     environment={'LANG': 'fr_FR.UTF-8', 'LC_MESSAGES': 'fr_FR.UTF-8', 'LC_CTYPE': 'fr_FR.UTF-8', 'LC_ALL': 'C'})
        if utility == 'tabs':
            extra.update(tty_fds=[1], oracle='tabs', terminal=None, stops=[])
        elif utility == 'tput':
            extra.update(tty_fds=[1], term='csh077plain', terminal=b'CLEAR')
        elif utility == 'stty':
            extra['control'] = ['VEOF', 1]
        elif utility == 'mesg':
            extra['permission'] = False
        elif utility == 'write':
            extra['stderr'] = 'diagnostic'
        yield c(utility + '/lc-all-precedence', utility, args, **extra)


if __name__ == '__main__':
    raise SystemExit(main(cases_factory=cases))
