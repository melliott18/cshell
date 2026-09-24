"""CSH-028 behavior shared by -c, script, and stdin runtime fixtures."""
import errno
import os


def add_control_cases(cross, helper):
    def check(name, script, **expect):
        cross('control: ' + name, script + '\n', **expect)

    args = helper + ' args'
    status = helper + ' status'
    check('if elif else selection', f'if {status} 1; then {args} bad; elif {status} 0; then '
          f'if {status} 1; then :; else {args} selected; fi; else {args} bad; fi', stdout='[selected]\n')
    check('unselected expansions', f'if {status} 0; then :; elif ${{missing:?bad}}; then :; '
          f'else : >effect; fi; {args} okay', stdout='[okay]\n', files={'effect': {'type': 'absent'}})
    check('if no branch status', f'if {status} 3; then :; fi; {args} "$?"', stdout='[0]\n')
    check('selected branch status', f'if :; then {status} 17; fi', status=17)
    check('zero loops', f'while {status} 1; do :; done; {args} "$?"; '
          f'until :; do :; done; {args} "$?"; for x in; do :; done; {args} "$?"',
          stdout='[0]\n[0]\n[0]\n')
    check('while until arithmetic', f'n=0; while test "$n" -lt 2; do n=$((n+1)); {args} "$n"; done; '
          f'until test "$n" -eq 0; do n=$((n-1)); {args} "$n"; done', stdout='[1]\n[2]\n[1]\n[0]\n')
    check('loop body status', f'n=0; while test "$n" -eq 0; do n=1; {status} 9; done', status=9)
    check('for expansion snapshot', f'v="a b"; for x in $v "c d" *.item; do v=changed; {args} "$x"; done',
          setup={'b.item': '', 'a.item': ''}, stdout='[a]\n[b]\n[c d]\n[a.item]\n[b.item]\n')
    check('for implicit parameter snapshot', f'set -- one "two three" ""; for x; do set -- changed; {args} "$x"; done',
          stdout='[one]\n[two three]\n[]\n')
    check('for explicit empty leaves variable', f'x=before; set -- ignored; for x in; do :; done; {args} "$x"',
          stdout='[before]\n')
    check('for last status', f'for x in a b; do {status} 13; done', status=13)
    check('for list expanded once', f'n=0; for x in "$((n+=1))" "$((n+=1))"; do {args} "$x" "$n"; done',
          stdout='[1]\n[2]\n[2]\n[2]\n')
    check('case quoted and unquoted patterns', f'p="a*"; case abc in "$p") {args} bad;; $p) {args} glob;; esac; '
          f'case "a*" in "a*") {args} literal;; esac', stdout='[glob]\n[literal]\n')
    check('case alternatives lazy expansion', f'case abc in a*|${{missing:?bad}}) {args} yes;; '
          '${missing:?bad}) :;; esac', stdout='[yes]\n')
    check('case subject scalar and pattern substitution', f'v="a b"; case $v in "$(printf "a b")") {args} yes;; esac',
          stdout='[yes]\n')
    check('case bracket slash dot', f'case .a/b in .[ab]/*) {args} yes;; esac', stdout='[yes]\n')
    check('case no match and empty body', f'case z in a) :;; esac; {args} "$?"; case x in x) ;; esac; {args} "$?"',
          stdout='[0]\n[0]\n')
    check('case fallthrough skips patterns', f'case x in x) {args} first ;& ${{missing:?bad}}) {args} second;; esac',
          stdout='[first]\n[second]\n')
    check('case fallthrough empty body retains status', f'case x in x) {status} 19 ;& y) ;; esac', status=19)
    check('case selected status', f'case x in x) {status} 21;; esac', status=21)
    check('break nested levels', f'for x in a b; do for y in 1 2; do {args} "$x$y"; break 2; '
          f'{args} bad; done; {args} bad; done; {args} end', stdout='[a1]\n[end]\n')
    check('continue nested levels', f'for x in a b; do for y in 1 2; do {args} "$x$y"; continue 2; '
          f'{args} bad; done; {args} bad; done', stdout='[a1]\n[b1]\n')
    check('loop count clamps', f'for x in a b; do {args} "$x"; break 999; done', stdout='[a]\n')
    check('control through condition lists', f'while if :; then break; fi; do {args} bad; done; {args} end',
          stdout='[end]\n')
    check('control through negation and and-or', f'for x in a b; do ! continue && {args} bad; {args} bad; done; '
          f'for x in a b; do : && break || {args} bad; done; {args} end', stdout='[end]\n')
    for name in ('break', 'continue', 'return'):
        context = 'function' if name == 'return' else 'loop'
        check(name + ' outside context', name + '\n' + args + ' bad', status=2,
              stderr=f'cshell: {name}: not in a {context}\n')
        for operand in ('bad', '0' if name != 'return' else '--bad', '999999999999999999999999999', '1 2'):
            message = 'too many arguments' if operand == '1 2' else (
                'numeric status required' if name == 'return' else 'positive loop count required')
            body = f'{name} {operand}; {args} bad'
            script = f'f() {{ {body}; }}; f' if name == 'return' else f'for x in a; do {body}; done'
            check(name + ' invalid ' + operand, script, status=2, stderr=f'cshell: {name}: {message}\n')
    check('function parser lifetime', f'f() {{ {args} "$1"; }}\nf first\nf second',
          stdout='[first]\n[second]\n')
    check('function nested parameters and return', f'g() {{ set -- inner; return 7; }}; '
          f'f() {{ {args} "$#" "$1"; g; {args} "$?" "$1"; shift; return 13; }}; '
          f'set -- caller; f one two; {args} "$?" "$#" "$1"',
          stdout='[2]\n[one]\n[7]\n[one]\n[13]\n[1]\n[caller]\n')
    check('return implicit status', f'f() {{ {status} 17; return; {args} bad; }}; f', status=17)
    check('return status modulo', 'f() { return -- -1; }; f', status=255)
    check('return through loop case', f'f() {{ for x in a; do case $x in a) return 12;; esac; done; }}; f', status=12)
    check('function redefines active body', f'f() {{ f() {{ {args} new; }}; {args} old; }}; f; f',
          stdout='[old]\n[new]\n')
    check('function unsets active body', f'f() {{ unset -f f; {args} old; }}; f; f', status=127,
          stdout='[old]\n', stderr='cshell: f: command not found\n')
    check('function lookup before regular builtin', f'pwd() {{ {args} function; }}; pwd', stdout='[function]\n')
    check('function name validation deferred until reached', 'if false; then export() { :; }; fi')
    check('function special name rejected', 'export() { :; } >effect\n: >later', status=2,
          stderr='cshell: invalid function name: special builtin names are reserved\n',
          files={'effect': {'type': 'absent'}, 'later': {'type': 'absent'}})
    check('function definitions defer redirection', 'f() { :; } >effect', files={'effect': {'type': 'absent'}})
    check('function definition redirect uses parameters', f'f() {{ {args} "$2"; }} >"$1"; f one first; f two second; {args} restored',
          stdout='[restored]\n', files={'one': {'type': 'file', 'content': '[first]\n'},
                                       'two': {'type': 'file', 'content': '[second]\n'}})
    check('call and definition redirect order', f'f() {{ {args} body; }} >definition; f >call; {args} restored',
          stdout='[restored]\n', files={'definition': {'type': 'file', 'content': '[body]\n'},
                                       'call': {'type': 'file', 'content': ''}})
    check('compound redirect spans iterations', f'for x in a b; do {args} "$x"; done >loop; {args} restored',
          stdout='[restored]\n', files={'loop': {'type': 'file', 'content': '[a]\n[b]\n'}})
    check('function state and prefix lifetime', f'v=parent; f() {{ {args} "$v"; v=changed; other=kept; }}; '
          f'v=prefix f; {args} "$v" "$other"', stdout='[prefix]\n[parent]\n[kept]\n')
    check('function recursive parameters', f'f() {{ if test "$1" -gt 0; then f "$(( $1 - 1 ))"; fi; {args} "$1"; }}; f 3',
          stdout='[0]\n[1]\n[2]\n[3]\n')
    check('function recursion limit', 'f() { f; }; f', status=2,
          stderr='cshell: function nesting limit exceeded\n')
    check('function definition heredoc invocation', f'f() {{ {helper} copy; }} <<END\nhello $1\nEND\nf world',
          stdout='hello world\n')
    check('function in substitutions and pipelines', f'f() {{ {args} "$1"; }}; {args} "$(f sub)"; f pipe | {helper} copy',
          stdout='[[sub]]\n[pipe]\n')
    check('function subshell definition isolation', f'f() {{ {args} parent; }}; (f() {{ {args} child; }}; f); f',
          stdout='[child]\n[parent]\n')
    check('function subshell body return', f'f() (return 8); f; {args} "$?"; '
          f'g() {{ (return 9); {args} "$?"; {args} "$(return 10)"; {args} alive; }}; g',
          stdout='[8]\n[9]\n[]\n[alive]\n')
    check('break cannot cross function boundary', f'f() {{ break; }}; for x in a; do f; done', status=2,
          stderr='cshell: break: not in a loop\n')
    check('break in subshell isolated', f'for x in a b; do (break); {args} "$x"; done',
          stdout='[a]\n[b]\n', stderr='cshell: break: not in a loop\n' * 2)
    check('function loop does not consume caller loop', f'f() {{ for i in a b; do break; done; }}; '
          f'for x in one two; do f; {args} "$x"; done', stdout='[one]\n[two]\n')
    redirection_error = f'cshell: cannot apply redirection: {os.strerror(errno.ENOENT)}\n'
    check('failed function redirect restores parameters', f'f() {{ :; }} >missing/file; set -- caller; '
          f'f child || {args} "$?" "$1"', stdout='[1]\n[caller]\n', stderr=redirection_error)
    check('failed compound redirect skips body', f'if :; then : >effect; fi <missing || {args} recovered',
          stdout='[recovered]\n', stderr=redirection_error, files={'effect': {'type': 'absent'}})
    check('compound expansion error stops input', f'for x in ${{missing:?required}}; do :; done\n{args} bad',
          status=2, stderr='cshell: required\n')
    check('readonly loop variable', f'readonly x=old; for x in new; do {args} bad; done\n{args} bad',
          status=1, stderr='cshell: cannot assign loop variable\n')
    check('return restores enclosing redirects', f'f() {{ for x in a; do return 4; done >loop; }} >function; '
          f'f; {args} "$?"', stdout='[4]\n', files={'loop': {'type': 'file', 'content': ''},
                                                                 'function': {'type': 'file', 'content': ''}})
    check('background function isolated and waited', f'f() {{ x=child; {args} "$x"; }}; x=parent; f >child & wait; {args} "$x"',
          stdout='[parent]\n', files={'child': {'type': 'file', 'content': '[child]\n'}})
