"""CSH-051 clause witnesses; expectations derive from Issue 8 set, not sh output.

The generated names encode option, entry point, spelling, state and input mode.
See docs/shell-option-evidence.md for applicability and policy classifications.
"""
import errno
import os
import shlex

# name, letter (hashall is a project extension name for the standard -h)
BASE_OPTIONS = (('allexport', 'a'), ('noclobber', 'C'), ('errexit', 'e'),
                ('noglob', 'f'), ('hashall', 'h'), ('noexec', 'n'),
                ('nounset', 'u'), ('pipefail', None), ('verbose', 'v'),
                ('xtrace', 'x'))


def probes(helper):
    denied = 'cshell: cannot apply redirection: ' + os.strerror(errno.EEXIST) + '\n'
    # script, setup, enabled expectation, disabled expectation
    return {
        'allexport': (f'unset csh051; csh051=value; {helper} environment csh051\n', {},
                      {'stdout': 'csh051=value\n'}, {'stdout': 'csh051=<unset>\n'}),
        'noclobber': ('echo new >out\necho "$?"\n', {'out': 'old\n'},
                      {'stdout': '1\n', 'stderr': denied, 'files': {'out': 'old\n'}},
                      {'stdout': '0\n', 'files': {'out': 'new\n'}}),
        'errexit': ('false\necho survived\n', {}, {'status': 1}, {'stdout': 'survived\n'}),
        'noglob': ('printf "<%s>\\n" *.txt\n', {'a.txt': ''},
                   {'stdout': '<*.txt>\n'}, {'stdout': '<a.txt>\n'}),
        'hashall': ('chmod +x first/csh051cmd second/csh051cmd; f() { csh051cmd; }; PATH=./first; f; PATH=./second; f\n',
                    {'first/csh051cmd': '#!/bin/sh\necho first\n',
                     'second/csh051cmd': '#!/bin/sh\necho second\n'},
                    {'stdout': 'first\nsecond\n'}, {'stdout': 'first\nsecond\n'}),
        'noexec': ('echo executed >effect\necho executed\n', {},
                   {'files': {'effect': None}},
                   {'stdout': 'executed\n', 'files': {'effect': 'executed\n'}}),
        'nounset': ('unset csh051; echo "$csh051"\necho survived\n', {},
                    {'status': 2, 'stderr': 'cshell: csh051\n'}, {'stdout': '\nsurvived\n'}),
        'pipefail': ('(exit 7) | true\necho "$?"\n', {},
                     {'stdout': '7\n'}, {'stdout': '0\n'}),
        'verbose': ('# literal input\necho "$((1+1))"\n', {},
                    {'stdout': '2\n', 'stderr': '# literal input\necho "$((1+1))"\n'},
                    {'stdout': '2\n'}),
        'xtrace': ('echo "$((1+1))"\n', {}, {'stdout': '2\n', 'stderr': '+ echo 2\n'},
                   {'stdout': '2\n'}),
    }


def file_expectation(files):
    return {path: {'type': 'absent'} if content is None else
            {'type': 'file', 'content': content} for path, content in files.items()}


def evidence_cases(helper):
    cases = []
    def add(name, script, *, flags=(), setup=None, stdout='', stderr='', status=0, files=None):
        for mode in ('string', 'file', 'stdin'):
            initial = dict(setup or {})
            args = list(flags)
            stdin = ''
            if mode == 'string':
                args += ['-c', script]
            elif mode == 'file':
                args += ['script']
                initial['script'] = script
            else:
                args += ['-s']
                stdin = script
            expected = dict(stdout=stdout, stderr=stderr, status=status)
            if files:
                expected['files'] = file_expectation(files)
            cases.append(dict(name=f'options: CSH-051 {name} ({mode})', args=args,
                              stdin=stdin, setup=initial, expect=expected))

    for option, letter in BASE_OPTIONS:
        script, setup, on, off = probes(helper)[option]
        for spelling in ('letter', 'name') if letter else ('name',):
            enable = ['-' + letter] if spelling == 'letter' else ['-o', option]
            disable = ['+' + letter] if spelling == 'letter' else ['+o', option]
            for entry in ('invocation', 'set'):
                for enabled, expected in ((True, on), (False, off)):
                    state = 'on' if enabled else 'off'
                    flags, prefix = [], ''
                    if entry == 'invocation':
                        flags = enable if enabled else enable + disable
                    else:
                        if enabled:
                            prefix = 'set ' + ' '.join(enable) + '\n'
                        elif option == 'noexec':
                            # Once active, set +n cannot run. Test acceptance in
                            # the off state; invocation tests the on->off switch.
                            prefix = 'set ' + ' '.join(disable) + '\n'
                        else:
                            # Silence the unspecified disable-command trace.
                            prefix = 'set ' + ' '.join(enable) + '; set ' + ' '.join(disable) + ' 2>/dev/null\n'
                    add(f'O-001 {option} {entry} {spelling} {state}', prefix + script,
                        flags=flags, setup=setup, **expected)

    # Effect inheritance: every base option in each execution environment.
    # Dot is the input boundary for verbose; set -n must execute inside the
    # environment to allow entering it. Other options are inherited at entry.
    for option, letter in BASE_OPTIONS:
        script, setup, on, _ = probes(helper)[option]
        for context in ('function', 'braces', 'subshell', 'substitution', 'eval', 'dot', 'alias', 'pipeline', 'background'):
            initial = dict(setup)
            if option == 'noexec':
                body, prefix = 'set -n\n' + script, ''
            else:
                body, prefix = script, 'set -' + letter + '\n' if letter else 'set -o pipefail\n'
            # Trace only the probe, so wrapper formatting is not the oracle.
            if option == 'xtrace':
                body, prefix = 'set -x\n' + script, ''
            if option == 'verbose':
                body, prefix = 'set -v\n. ./input\n', ''
                initial['input'] = script
            initial['probe'] = body
            command = '. ./probe'
            wrapper = {
                'function': 'f() { . ./probe; }; f',
                'braces': '{ . ./probe; }',
                'subshell': '(. ./probe)',
                'substitution': 'value=$(. ./probe); result=$?; printf "%s" "$value"; exit "$result"',
                'eval': 'eval ' + shlex.quote(command),
                'dot': command,
                'alias': "alias probe='. ./probe'\nprobe",
                'pipeline': '. ./probe | cat',
                'background': '. ./probe >captured & wait "$!"; result=$?; cat captured; exit "$result"',
            }[context]
            expected = dict(on)
            if option == 'verbose':
                expected['stderr'] = '. ./input\n' + expected['stderr']
            if context == 'substitution':
                expected['stdout'] = expected.get('stdout', '').rstrip('\n')
                # errexit exits on failed assignment before printing; already
                # empty for that probe. nounset does not imply errexit.
            if context == 'pipeline' and option != 'pipefail':
                expected['status'] = 0
            # For shared noexec, wrapper tail never runs. For xtrace/verbose,
            # wrapper tail is avoided in the shared environments.
            add(f'O-017 {option} {context} effect', prefix + wrapper + '\n', setup=initial, **expected)

    # These two options observe input/dispatch, so keep wrapper diagnostics out
    # of the trace assertion while testing inheritance separately from activation.
    for option, letter in (('verbose', 'v'), ('xtrace', 'x')):
        script, setup, on, _ = probes(helper)[option]
        command = '. ./probe' + (' 2>trace' if option == 'xtrace' else '')
        for context, wrapper in (
                ('function', 'f() { COMMAND; }; f'),
                ('braces', '{ COMMAND; }'),
                ('subshell', '(COMMAND)'),
                ('substitution', 'value=$(COMMAND); printf "%s" "$value"'),
                ('eval', "eval 'COMMAND'"),
                ('dot', 'COMMAND'),
                ('alias', 'probe'),
                ('pipeline', 'COMMAND | cat'),
                ('background', 'COMMAND >captured & wait "$!"; cat captured')):
            wrapper = wrapper.replace('COMMAND', command)
            prefix = ("alias probe=" + shlex.quote(command) + '\n') if context == 'alias' else ''
            prefix += 'set -' + letter + '; '
            expected = dict(on)
            if option == 'verbose' and context == 'eval':
                expected['stderr'] = command + expected['stderr']
            if option == 'xtrace':
                wrapper = '{ ' + wrapper + '; } 2>/dev/null'
                expected['stderr'] = ''
                expected['files'] = {'trace': '+ . ./probe\n+ echo 2\n'}
            if context == 'substitution':
                expected['stdout'] = '2'
            add(f'O-017 {option} {context} inherited effect', prefix + wrapper + '\n',
                setup={'probe': script}, **expected)

    for option, _ in BASE_OPTIONS:
        if option == 'noexec':
            continue  # An active noexec shell cannot execute a report command.
        add(f'O-001 {option} enabled report round trip',
            '{ set -o ' + option + '; saved=$(set +o); set +o ' + option +
            '; eval "$saved"; set +o; } 2>/dev/null\n', stdout=option_report(option))

    # State lifetime uses the actual report for named-only options too. noexec
    # cannot be inspected after activation; its effect cases assert the boundary.
    for option, letter in BASE_OPTIONS:
        if option == 'noexec':
            continue
        for context, command, shared in (
                ('function', 'f() { set -o OPTION; }; f', True),
                ('eval', "eval 'set -o OPTION'", True),
                ('dot', '. ./enable', True),
                ('alias', "alias enable='set -o OPTION'\nenable", True),
                ('subshell', '(set -o OPTION)', False),
                ('substitution', 'v=$(set -o OPTION)', False),
                ('pipeline', 'set -o OPTION | cat', False),
                ('background', 'set -o OPTION & wait "$!"', False)):
            command = command.replace('OPTION', option)
            # Reports expose named-only settings as well as letter options.
            add(f'O-017 {option} {context} lifetime', command + '; set +o 2>/dev/null; set +v +x 2>/dev/null\n',
                setup={'enable': f'set -o {option}\n'}, stdout=option_report(option if shared else None))
    return cases


def option_report(enabled):
    # Reuse the existing inventory without introducing a runtime import cycle.
    from option_cases import report
    return report(*([enabled] if enabled else []), reusable=True)
