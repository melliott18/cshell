"""CSH-049 exact runtime witnesses; provenance in docs/execution-evidence.md.

Required outcomes and project-policy witnesses are distinguished in that map.
All cases use the shared bounded runner in each of the three input modes.
"""
import errno
import os
import signal


def add_execution_cases(cross, helper):
    def check(name, script, **expect):
        cross('execution: ' + name, script + '\n', **expect)

    def file(content):
        return {'type': 'file', 'content': content}

    args = helper + ' args'
    badfd = 'cshell: cannot apply redirection: ' + os.strerror(errno.EBADF) + '\n'
    missing = 'cshell: cannot apply redirection: ' + os.strerror(errno.ENOENT) + '\n'
    # RED-001/005, D-002: every required numeric descriptor, including 0.
    for fd in range(10):
        check(f'RED-001 numeric descriptor {fd}',
              f'{helper} fd-write {fd} {fd}>out; {args} restored',
              stdout='[restored]\n', files={'out': file('fd\n')})
    check('RED-001 rollback retains file effects',
          f'{args} never >first <missing >last; {args} "$?" restored',
          stdout='[1]\n[restored]\n', stderr=missing,
          setup={'first': 'old'}, files={'first': file(''), 'last': {'type': 'absent'}})
    check('RED-002 default input and truncation',
          f'{helper} copy <input >out; {helper} copy <out',
          setup={'input': 'new\n', 'out': 'long previous contents\n'},
          stdout='new\n', files={'input': file('new\n'), 'out': file('new\n')})
    check('RED-003 append ignores seek',
          f'{helper} seek-write 1 >>out; {helper} seek-write 1 >>out',
          files={'out': file('XYXY')})
    check('RED-005 shared input offset',
          f'{{ {helper} one; {helper} copy 3; }} <input 3<&0',
          setup={'input': 'abcd'}, stdout='bcd')
    for op in ('<&', '>&'):
        check(f'RED-005 close twice {op}',
              f'{helper} closed 9 9{op}- 9{op}-; {args} "$?"', stdout='[0]\n')
        check(f'RED-005 closed source {op}',
              f'{args} never 9{op}- 3{op}9; {args} "$?"',
              stdout='[1]\n', stderr=badfd)
    # POSIX permits these direction errors; cshell deliberately rejects them.
    for redirs in ('3>out 0<&3', '3<input 1>&3'):
        check('RED-005 direction policy ' + redirs,
              f'{args} never {redirs}; {args} "$?"', setup={'input': 'data'},
              stdout='[1]\n', stderr=badfd)
    check('RED-006 default read write preserves tail',
          f'{helper} read-write <>out', setup={'out': 'abcd'},
          stdout='a\n', files={'out': file('aXcd')})
    check('RED-006 default read write creates',
          f'{helper} fd-write 0 <>out', files={'out': file('fd\n')})
    check('EXEC-001 expansion redirection assignment phases',
          f'v=old; v=$(printf new) {args} "$v" >"$v"; {args} "$v"',
          stdout='[old]\n', files={'old': file('[old]\n'), 'new': {'type': 'absent'}})
    check('EXEC-001 argument failure precedes redirection',
          f'{args} "${{absent:?required}}" >effect', status=2,
          stderr='cshell: required\n', files={'effect': {'type': 'absent'}})
    check('EXEC-002 external export and restore',
          f'unset v; v=child {helper} environment v; {helper} environment v; {args} "${{v-unset}}"',
          stdout='v=child\nv=<unset>\n[unset]\n')
    check('EXEC-002 regular builtin restores prefix only',
          f'v=old; v=temp read answer <input; {args} "$v" "$answer"',
          setup={'input': 'kept\n'}, stdout='[old]\n[kept]\n')
    check('EXEC-002 special builtin keeps further changes',
          f'v=old; v=prefix eval "v=changed"; {args} "$v"', stdout='[changed]\n')
    check('EXEC-002 function export policy',
          f'v=old; f() {{ {helper} environment v; v=changed; }}; v=prefix f; '
          f'{args} "$v"; {helper} environment v',
          stdout='v=prefix\n[old]\nv=<unset>\n')
    for command in ('', ':', 'read answer', f'{helper} status 0', 'f'):
        check('EXEC-002 readonly category ' + (command or 'empty'),
              f'f() {{ : >body; }}; readonly v=old; v=new {command}\n: >later',
              status=1, stderr='cshell: cannot assign to readonly variable\n',
              files={'body': {'type': 'absent'}, 'later': {'type': 'absent'}})
    check('EXEC-003 last substitution status',
          f'a=$({helper} status 3) b=$({helper} status 7); {args} "$?"; '
          f'>"$({helper} args target; {helper} status 9)"; {args} "$?"; >empty; {args} "$?"',
          stdout='[7]\n[9]\n[0]\n', files={'[target]': file(''), 'empty': file('')})
    check('EXEC-003 vanished command keeps assignments',
          f'unset absent; v=value $absent; {args} "$v" "$?"', stdout='[value]\n[0]\n')
    # A pathname command bypasses functions; ENOEXEC is tested as a host dependency.
    check('EXEC-004 pathname bypass and format fallback',
          f'probe() {{ {args} function; }}; chmod +x probe; ./probe "two words"',
          setup={'probe': 'printf "fallback:%s:%s\\n" "$0" "$1"\nexit 17\n'},
          stdout='fallback:./probe:two words\n', status=17)
    check('EXEC-004 PATH refresh after assignment',
          'chmod +x one/probe two/probe; PATH=one; probe; PATH=two; probe',
          setup={'one/probe': 'echo one\n', 'two/probe': 'echo two\n'}, stdout='one\ntwo\n')
    check('EXEC-006 pipe connected before output redirection',
          f'{helper} both 2>&1 >out | {helper} copy',
          stdout='err\n', files={'out': file('out\n')})
    check('EXEC-006 pipe connected before input redirection',
          f'{helper} status 0 | {helper} copy <input', setup={'input': 'override\n'}, stdout='override\n')
    # All four pipefail/negation combinations and both success/failure selections.
    for pipefail in (False, True):
        for negate in (False, True):
            for statuses in ((0, 0, 0), (7, 0, 0), (7, 9, 0), (7, 0, 3)):
                selected = next((s for s in reversed(statuses) if s), 0) if pipefail else statuses[-1]
                expected = int(selected == 0) if negate else selected
                pipeline = ' | '.join(f'{helper} status {s}' for s in statuses)
                check(f'EXEC-007 pipefail={pipefail} negate={negate} statuses={statuses}',
                      ('set -o pipefail; ' if pipefail else '') + ('! ' if negate else '') + pipeline,
                      status=expected)
    check('EXEC-007 option sampled before launch',
          f'{helper} status 7 | set -o pipefail; {args} "$?"; '
          f'set -o pipefail; {helper} status 9 | set +o pipefail; {args} "$?"',
          stdout='[0]\n[9]\n')
    check('EXEC-008 skipped branch has no expansions',
          f'false && : >"${{absent:?never}}"; true || v=$(>effect); {args} end',
          stdout='[end]\n', files={'effect': {'type': 'absent'}})
    check('EXEC-011 implicit empty for status',
          f'x=before; set --; false; for x; do : >effect; done; {args} "$?" "$x"',
          stdout='[0]\n[before]\n', files={'effect': {'type': 'absent'}})
    check('EXEC-012 subject once and later clauses skipped',
          f'n=0; case $((n+=1)) in 1) {args} "$n";; ${{absent:?never}}) :;; esac', stdout='[1]\n')
    check('EXEC-013 until body status and condition visibility',
          f'n=0; until {helper} status "$((1-n))"; do {args} "$?"; n=1; '
          f'{helper} status 19; done; {args} "$?"', stdout='[1]\n[19]\n')
    check('EXEC-014 variable and function namespaces',
          f'f=value; f() {{ {args} "$f"; }}; {args} "$?"; f; unset -f f; {args} "$f"',
          stdout='[0]\n[value]\n[value]\n')
    check('EXEC-014 zero unchanged and empty parameters restored',
          f'original=$0; f() {{ test "$0" = "$original"; {args} "$?" "$#"; }}; '
          f'set -- "" caller; f; {args} "$#" "$1" "$2"', stdout='[0]\n[0]\n[2]\n[]\n[caller]\n')
    check('U-003 default break status',
          f'for x in a b; do for y in 1 2; do {args} "$x$y"; break; done; {args} "$?"; done',
          stdout='[a1]\n[0]\n[b1]\n[0]\n')
    check('U-004 default continue and success status',
          f'for x in a b; do {args} "$x"; continue; : >effect; done; {args} "$?"',
          stdout='[a]\n[b]\n[0]\n', files={'effect': {'type': 'absent'}})
    check('U-004 clamp to outermost lexical loop',
          f'for x in a b; do for y in 1 2; do {args} "$x$y"; continue 999; done; : >effect; done',
          stdout='[a1]\n[b1]\n', files={'effect': {'type': 'absent'}})
    check('EXEC-016 signal selected by pipefail',
          f'set -o pipefail; {helper} signal | {helper} status 0', status=128 + signal.SIGTERM)


def add_execution_errors(cross, result):
    """2.8.1 categories with mode-specific continuation and exact diagnostics."""
    missing = 'cshell: cannot apply redirection: ' + os.strerror(errno.ENOENT) + '\n'
    errors = (
        ('special utility', 'shift 99', 1, 'cshell: shift: count exceeds positional parameters\n', True),
        ('regular utility', 'read -z', 2, 'cshell: read: invalid option\n', False),
        ('special redirect', ': <missing', 1, missing, True),
        ('compound redirect', '{ :; } <missing', 1, missing, False),
        ('function redirect', 'f() { :; }; f <missing', 1, missing, False),
        ('external redirect', '/bin/cat <missing', 1, missing, False),
        ('assignment', 'readonly v=old; v=new', 1, 'cshell: cannot assign to readonly variable\n', True),
        ('expansion', ': "${absent:?required}"', 2, 'cshell: required\n', True),
        ('not found', 'no-such-cshell-command', 127, 'cshell: no-such-cshell-command: command not found\n', False),
        ('command special exception', 'command shift 99', 1, 'cshell: shift: count exceeds positional parameters\n', False),
    )
    for name, failing, status, diagnostic, fatal in errors:
        script = failing + '\nprintf "continued:%s\\n" "$?"\n'
        cross('execution: EXEC-015 noninteractive ' + name, script,
              stdout='' if fatal else f'continued:{status}\n', stderr=diagnostic,
              status=status if fatal else 0)
        for mode in ('string', 'file'):
            result.append({'name': f'execution: EXEC-015 interactive {name} ({mode})',
                           'args': ['-ic', script] if mode == 'string' else ['-i', 'script'],
                           'stdin': '', 'setup': {'script': script} if mode == 'file' else {},
                           'expect': {'stdout': f'continued:{status}\n', 'stderr': diagnostic, 'status': 0}})
