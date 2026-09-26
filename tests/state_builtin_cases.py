"""CSH-048 clause witnesses; see docs/state-builtin-evidence.md for scope/oracles."""
import errno
import os
from pathlib import Path
import shlex


def add_state_builtin_cases(cross, helper):
    shell = shlex.quote(str(Path(shlex.split(helper)[0]).parents[2] / 'cshell'))

    def case(name, script, stdout='', **kw):
        cross('state-builtin: ' + name, script + '\n', stdout=stdout, **kw)

    for initial in ('', ':hostile:'):
        case('startup IFS reset ' + repr(initial),
             f'{helper} args "$IFS"; v="a b"; {helper} args $v',
             '[ \t\n]\n[a]\n[b]\n', env={'IFS': initial})
    case('startup missing PWD', 'test "$PWD" = "$(pwd -P)"')
    for initial in ('', 'relative', '/not-the-current-directory'):
        case('startup invalid PWD ' + repr(initial), 'test "$PWD" = "$(pwd -P)"', env={'PWD': initial})
    case('startup logical PWD retained',
         f'mkdir real; ln -s real link; base=$PWD; cd real; PWD="$base/link" {shell} -c '\
         "'test \"$PWD\" = \"$1/link\"; test \"$(pwd -L)\" = \"$1/link\"' child \"$base\"")
    case('startup dot PWD normalized',
         f'PWD="$PWD/." {shell} -c \'test "$PWD" = "$(pwd -P)"\'')
    case('startup PPID and subshell stability',
         f'expected=$$ PPID=99999999 {shell} -c '\
         "'test \"$PPID\" = \"$expected\" || exit 9; (test \"$PPID\" = \"$expected\")'")
    case('startup OPTIND reset', 'printf "%s\\n" "$OPTIND"', '1\n', env={'OPTIND': '99'})
    case('import export empty and unset',
         f'{helper} args "$IMPORTED" "${{EMPTY+set}}" "${{ABSENT-unset}}"; '
         f'{helper} environment IMPORTED EMPTY ABSENT; unset IMPORTED; {helper} environment IMPORTED',
         '[a=b c]\n[set]\n[unset]\nIMPORTED=a=b c\nEMPTY=\nABSENT=<unset>\nIMPORTED=<unset>\n',
         env={'IMPORTED': 'a=b c', 'EMPTY': ''})
    case('readonly attribute not inherited',
         f'readonly value=parent; export value; {shell} -c '\
         "'value=child; printf \"%s\\n\" \"$value\"'; printf '%s\\n' \"$value\"", 'child\nparent\n')
    for utility in ('export', 'readonly'):
        case(utility + ' listing round trip',
             f"{utility} A=\"a'b\" B= C; {utility} -p >saved; "
             f"{shell} -c '. ./saved; printf \"<%s><%s><%s>\\n\" \"$A\" \"${{B+set}}\" \"${{C-unset}}\"'",
             "<a'b><set><unset>\n")
        case(utility + ' declaration fields',
             f"v='a b *'; {utility} VALUE=$v; {helper} args \"$VALUE\"", '[a b *]\n')
        case(utility + ' invalid name stops', f'{utility} 1bad=x; : >unreached', status=1,
             stderr=f'cshell: {utility}: invalid operand\n', files={'unreached': {'type': 'absent'}})
    case('readonly assignment through export stops', 'readonly A=old; export A=new; : >unreached', status=1,
         stderr='cshell: export: readonly variable\n', files={'unreached': {'type': 'absent'}})
    case('colon expands ignores and redirects',
         f': -z -- "${{a:=value}}" >created; {helper} args "$a" "$?"', '[value]\n[0]\n',
         files={'created': {'type': 'file', 'content': ''}})
    case('special assignment persistence and output',
         f'a=value : >out; {helper} args "$a"; export -p >listing; :', '[value]\n',
         files={'out': {'type': 'file', 'content': ''}})
    case('special redirect failure stops', ': >missing/out; : >unreached', status=1,
         stderr=f'cshell: cannot apply redirection: {os.strerror(errno.ENOENT)}\n',
         files={'unreached': {'type': 'absent'}})
    case('set positional empty and clear',
         f'set -- a "" c; {helper} args "$#" "$@"; set --; {helper} args "$#"',
         '[3]\n[a]\n[]\n[c]\n[0]\n')
    case('set listing round trip',
         f"A=\"a'b\"; B=; set >saved; {shell} -c '. ./saved; printf \"<%s><%s>\\n\" \"$A\" \"${{B+set}}\"'",
         "<a'b><set>\n")
    case('shift default zero count',
         f'set -- a b c; shift 0; {helper} args "$@"; shift; shift 2; {helper} args "$#"',
         '[a]\n[b]\n[c]\n[0]\n')
    for operand, error in [('9', 'count exceeds positional parameters'), ('bad', 'invalid count')]:
        case('shift error ' + operand, f'set -- a; shift {operand}; : >unreached', status=1,
             stderr=f'cshell: shift: {error}\n', files={'unreached': {'type': 'absent'}})
    case('unset namespaces and absent names',
         'same=value; same() { printf "function\\n"; }; unset -v same absent; same; '
         'same=value; unset -f same absent; printf "%s\\n" "$same"; command -v same; printf "%s\\n" "$?"',
         'function\nvalue\n1\n')
    case('unset readonly stops', 'readonly A=x; unset -v A; : >unreached', status=1,
         stderr='cshell: unset: readonly variable\n', files={'unreached': {'type': 'absent'}})
    case('dot parse error stops', '. ./source; : >unreached', status=2,
         setup={'source': 'if\n'}, stderr='cshell: unterminated command group\n',
         files={'unreached': {'type': 'absent'}})
    case('eval nested state and status', "eval 'eval \"a=inner; false\"'; printf '%s:%s\\n' \"$a\" \"$?\"", 'inner:1\n')
    case('cd HOME and OLDPWD',
         'base=$PWD; mkdir dest; HOME="$base/dest"; cd; test "$PWD" = "$HOME" || exit 9; '
         'test "$OLDPWD" = "$base" || exit 8; cd - >"$base/out"; test "$PWD" = "$base" || exit 7; '
         'read back <out; test "$back" = "$base"')
    case('cd logical physical and option order',
         'base=$PWD; mkdir -p real/child; ln -s real/child link; cd -P -L link; '
         'test "$PWD" = "$base/link" || exit 9; cd ..; test "$PWD" = "$base" || exit 8; '
         'cd -L -P link; test "$PWD" = "$base/real/child" || exit 7; cd ..; test "$PWD" = "$base/real"')
    case('cd CDPATH output and empty component',
         'base=$PWD; mkdir -p search/target local; CDPATH=search; cd target >out; '
         'read shown <"$base/out"; test "$shown" = "$PWD" || exit 9; cd "$base"; '
         'CDPATH=:search; cd local >quiet; test ! -s "$base/quiet"',
         files={'quiet': {'type': 'file', 'content': ''}})
    case('cd failure preserves directories',
         'old=$PWD; before=${OLDPWD-unset}; cd missing; printf "%s\\n" "$?"; '
         'test "$PWD" = "$old" && test "${OLDPWD-unset}" = "$before"', '1\n',
         stderr='cshell: cd: cannot change directory or update directory state\n')
    case('cd HOME missing policy', 'unset HOME; cd; printf "%s\\n" "$?"', '1\n',
         stderr='cshell: cd: HOME or OLDPWD is unset or empty\n')
    case('pwd logical physical option order',
         'base=$PWD; mkdir real; ln -s real link; cd link; '
         'test "$(pwd -P -L)" = "$base/link" && test "$(pwd -L -P)" = "$base/real"')
    case('pwd output failure continues', 'pwd >&-; printf "%s\\n" "$?"', '1\n',
         stderr='cshell: pwd: cannot write output\n')
    case('command lookup status and suppression',
         'f() { :; }; command -v f; command f 2>error; printf "%s\\n" "$?"; '
         'command export 1bad=x 2>error; printf "%s\\n" "$?"', 'f\n127\n1\n')
    case('getopts readonly processing error',
         'readonly opt; getopts a opt -a; printf "%s\\n" "$?"', '2\n',
         stderr='cshell: opt: readonly variable\n')
    case('read fewer fields and raw continuation',
         f'read -r a b c <data; {helper} args "$a" "$b" "$c"', '[one\\]\n[]\n[]\n', setup={'data': 'one\\\ntwo\n'})
    case('umask reusable default',
         'umask 027; saved=$(umask); umask 077; umask "$saved"; umask -S', 'u=rwx,g=rx,o=\n')
    case('umask reusable symbolic',
         'umask 027; saved=$(umask -S); umask 077; umask "$saved"; umask -S', 'u=rwx,g=rx,o=\n')
    # Every pipeline stage runs in a child: this asserts the documented D-007 choice.
    mutation = 'v=child; cd child; umask 077; set -f; f() { :; }; alias probe=child'
    check = ('test "$v" = parent && test "$PWD" = "$base" && '
             'test "$(umask -S)" = "u=rwx,g=rx,o=" || exit 8; '
             'case $- in *f*) exit 9;; esac; command -v f probe >leaks; test ! -s leaks')
    for context, body in [('subshell', f'( {mutation}; )'),
                          ('substitution', f'ignored=$( {mutation}; )'),
                          ('pipeline', f'{{ {mutation}; }} | cat'),
                          ('background', f'{{ {mutation}; }} & wait')]:
        case('context isolation ' + context, f'mkdir child; base=$PWD; v=parent; umask 027; {body}; {check}')
    case('current environment brace dot eval function',
         'v=initial; { v=brace; }; printf "%s\\n" "$v"; . ./source; printf "%s\\n" "$v"; '
         'eval "v=eval"; printf "%s\\n" "$v"; f() { v=function; }; f; printf "%s\\n" "$v"',
         'brace\ndot\neval\nfunction\n', setup={'source': 'v=dot\n'})
