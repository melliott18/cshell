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
    # Issue 8 read assigns the last operand the unsplit remainder, trimming only
    # IFS white space. Earlier operands survive a later assignment error.
    for label, ifs, line, names, expected in (
        ('one trailing separator', ':', 'one:\n', 'a', '[one:]\n'),
        ('only separator', ':', ':\n', 'a', '[:]\n'),
        ('last trailing separator', ':', 'one:two:\n', 'a b', '[one]\n[two:]\n'),
        ('last empty field', ':', 'one::\n', 'a b', '[one]\n[:]\n'),
        ('mixed trailing whitespace', ' :', ' one : two:  \n', 'a b', '[one]\n[two:]\n'),
        ('escaped trailing whitespace', ' ', ' one\\ \n', 'a', '[one ]\n'),
        ('repeated operand clears', ' ', 'one\n', 'a a', '[]\n'),
        ('empty IFS extra operands', '', ' one two \n', 'a b', '[ one two ]\n[]\n'),
    ):
        values = ' '.join('"$' + name + '"' for name in dict.fromkeys(names.split()))
        case('read ' + label, f'IFS={shlex.quote(ifs)}; read {names} <data; {helper} args {values}',
             expected, setup={'data': line})
    for bad, diagnostic in [('b', 'readonly variable'), ('1bad', 'invalid variable name')]:
        case('read ordered assignment ' + bad,
             f'a=old; readonly b=locked; c=untouched; exec 3<data; read a {bad} c <&3; '
             f'{helper} args "$?" "$a" "$b" "$c"; read rest <&3; {helper} args "$rest"',
             '[2]\n[one]\n[locked]\n[untouched]\n[next]\n',
             setup={'data': 'one two three\nnext\n'}, stderr=f'cshell: read: {diagnostic}\n')
    case('read EOF ordered assignment',
         f'a=old; readonly b=locked; read a b <data; {helper} args "$?" "$a" "$b"',
         '[2]\n[one]\n[locked]\n', setup={'data': 'one two'}, stderr='cshell: read: readonly variable\n')
    # The error status and diagnostics are project choices within the required
    # nonzero class; command and -i must recover from special-builtin errors.
    for utility, setup, status in [('export -p', 'export A=x;', 1), ('readonly -p', 'readonly A=x;', 1),
                                    ('set', 'A=x;', 1), ('times', '', 2), ('umask', '', 2),
                                    ('umask -S', '', 2), ('ulimit -a', '', 2), ('ulimit -f', '', 2)]:
        name = utility.split()[0]
        diagnostic = f'cshell: {name}: cannot write output\n'
        case(utility + ' output failure suppressed',
             f'{setup} command {utility} >&-; printf "%s\\n" "$?"', f'{status}\n', stderr=diagnostic)
        if name in ('export', 'readonly', 'set', 'times'):
            case(utility + ' output failure fatal', f'{setup} {utility} >&-; : >unreached',
                 status=status, stderr=diagnostic, files={'unreached': {'type': 'absent'}})
            script = f'{setup} {utility} >&-; printf "%s\\n" "$?"'
            case(utility + ' output failure interactive', f'{shell} -i -c {shlex.quote(script)}',
                 f'{status}\n', stderr=diagnostic)
    for name in ('export', 'readonly'):
        case(name + ' reinput attributes',
             f'{name} A=original B; {name} -p >saved; '
             f'{shell} -c ' + shlex.quote(
                 '. ./saved; command export A=changed B=changed; printf "%s:%s:%s\\n" "$?" "$A" "${B-unset}"'
                 if name == 'readonly' else
                 f'. ./saved; {helper} environment A B; B=now; {helper} environment B'),
             '1:original:unset\n' if name == 'readonly' else 'A=original\nB=<unset>\nB=now\n',
             stderr='cshell: export: readonly variable\ncshell: export: readonly variable\n' if name == 'readonly' else '')
    case('readonly repeat preserves protection',
         'readonly A=x; readonly A; command readonly A=x; printf "%s:%s\\n" "$?" "$A"',
         '1:x\n', stderr='cshell: readonly: readonly variable\n')
    for operand, error in [('-z', 'invalid option'), ('-v -f x', 'invalid option'), ('1bad', 'invalid operand')]:
        case('unset error ' + operand, f'command unset {operand}; printf "%s\\n" "$?"',
             '1\n', stderr=f'cshell: unset: {error}\n')
    case('unset end options and absent function', 'unset -v -- absent; unset -f -- absent; echo "$?"', '0\n')
    for variable, value, expected in [('OPTARG', 'keep', '[a]\n[keep]\n[1]\n'),
                                      ('OPTIND', '1', '[a]\n[value]\n[1]\n')]:
        case('getopts partial readonly ' + variable,
             f'readonly {variable}={value}; getopts a: opt -a value; {helper} args "$?" "$opt" "$OPTARG" "$OPTIND"',
             '[2]\n' + expected, stderr=f'cshell: {variable}: readonly variable\n')
    case('getopts invalid name leaves cursor',
         f'getopts a 1bad -a; {helper} args "$?" "$OPTIND" "${{OPTARG-unset}}"',
         '[2]\n[1]\n[unset]\n', stderr='cshell: 1bad: invalid variable name\n')
    for value in ('184467440737095516160', '-1', '1x', ''):
        case('ulimit rejects ' + repr(value),
             f'before=$(ulimit -f); ulimit -f -- {shlex.quote(value)}; printf "%s\\n" "$?"; '
             'test "$(ulimit -f)" = "$before"', '2\n', stderr='cshell: ulimit: invalid limit\n')
    for operand, expected in [('u=rw,g=r,o=', 'u=rw,g=r,o=\n'), ('a+r-w', 'u=rx,g=rx,o=rx\n'),
                               ('u=rwx,g=u,o=g', 'u=rwx,g=rwx,o=rwx\n'), ('u=,g=,o=', 'u=,g=,o=\n'),
                               ('=rw', 'u=rw,g=rw,o=rw\n'), ('u-x,g+w', 'u=rw,g=rwx,o=rx\n')]:
        case('umask symbolic ' + operand, f'umask 022; umask {shlex.quote(operand)}; umask -S', expected)
    for operand in ('888', '1000', 'u=bad', 'u+r,', 'u', ',u=r', ''):
        case('umask invalid ' + repr(operand),
             f'umask 027; umask {shlex.quote(operand)}; echo "$?"; umask -S',
             '2\nu=rwx,g=rx,o=\n', stderr='cshell: umask: invalid mask\n')
    for utility, operand, diagnostic in [('pwd', '-e', 'invalid option'), ('pwd', 'extra', 'too many operands'),
                                        ('cd', '-z', 'invalid option'), ('cd', 'a b', 'too many operands')]:
        case(utility + ' operand ' + operand,
             f'before=$PWD; {utility} {operand}; echo "$?"; test "$PWD" = "$before"',
             '1\n', stderr=f'cshell: {utility}: {diagnostic}\n')
    case('cd deleted cwd recovery',
         'base=$PWD; mkdir gone; cd gone; rmdir "$base/gone"; pwd -P; echo "$?"; '
         'cd "$base"; test "$PWD" = "$base"', '1\n', stderr='cshell: pwd: cannot determine current directory\n')
    case('startup deleted cwd selects unset',
         f'base=$PWD; mkdir gone; cd gone; rmdir "$base/gone"; {shell} -c '\
         "'test \"${PWD-unset}\" = unset; cd \"$1\"; test \"$PWD\" = \"$1\"' child \"$base\"")
    case('cd output error keeps changed cwd',
         'base=$PWD; mkdir dest; cd dest; cd - >&-; echo "$?"; test "$PWD" = "$base"', '1\n',
         stderr='cshell: cd: cannot change directory or update directory state\n')
    # Descriptor ownership across nested current/child contexts and failure.
    case('nested context descriptors and state',
         'exec 3>parent; v=parent; f() { (exec 3>child; v=child; echo child >&3); '
         'eval \'echo eval >&3; command export 1bad=x\'; echo function >&3; }; '
         'f 4>temporary; echo "$v" >&3; exec 3>&-; cat parent child',
         'eval\nfunction\nparent\nchild\n', stderr='cshell: export: invalid operand\n',
         files={'temporary': {'type': 'file', 'content': ''}})
    for label, command, diagnostic, expected_status in (
        ('permission', 'exec ./denied', f'cshell: ./denied: cannot execute: {os.strerror(errno.EACCES)}\n', 126),
        ('redirection', 'exec >missing/output', f'cshell: cannot apply redirection: {os.strerror(errno.ENOENT)}\n', 1),
    ):
        script = command + '; printf "%s\\n" "$?"'
        case('exec interactive ' + label, f'{shell} -i -c {shlex.quote(script)}',
             f'{expected_status}\n', stderr=diagnostic, setup={'denied': 'exit 0\n'})
