"""CSH-047 runtime evidence; clause/policy map: docs/expansion-evidence.md.

The truth tables below derive from Issue 8 2.6.2, not reference-shell output.
Every case runs in string/file/stdin modes with exact streams, status and named
filesystem assertions. Policy cases deliberately carry 'policy' in their ID.
"""
import pwd
import ctypes


def add_expansion_cases(cross, helper):
    def case(name, script, values=(), **kwargs):
        cross('expansion: ' + name, script.replace('@ARGS@', helper + ' args'),
              stdout=''.join('[' + v + ']\n' for v in values), **kwargs)

    # EXP-003: all eight operators, all three states, present/omitted word.
    for state, setup, value in (('unset', 'unset v', None), ('null', 'v=', ''),
                                ('value', 'v=value', 'value')):
        for operator in ('-', ':-', '=', ':=', '?', ':?', '+', ':+'):
            missing = value is None or (operator.startswith(':') and value == '')
            for word in ('word', ''):
                label = f'parameter {state} {operator} ' + ('word' if word else 'omitted')
                expression = '${v' + operator + word + '}'
                script = setup + '; @ARGS@ "' + expression + '" "${v-UNSET}" >result\n'
                if operator.endswith('?') and missing:
                    # The failure/nonempty diagnostic is normative; wording and 2
                    # are cshell policy. Redirection must not run before arguments.
                    message = word or 'parameter is unset or empty'
                    case(label, script, status=2, stderr='cshell: ' + message + '\n',
                         files={'result': {'type': 'absent'}})
                    continue
                selected = (not missing) if operator.endswith('+') else missing
                expanded = word if selected else ('' if operator.endswith('+') else value)
                after = word if operator.endswith('=') and missing else value
                output = ''.join('[' + v + ']\n' for v in (expanded, after if after is not None else 'UNSET'))
                case(label, script, files={'result': {'type': 'file', 'content': output}})
    for operator, setup, selected in (
        ('-', 'v=set', False), (':-', 'v=', True), ('=', 'v=set', False),
        (':=', 'unset v', True), ('?', 'v=set', False), (':?', 'v=set', False),
        ('+', 'unset v', False), (':+', 'v=set', True),
    ):
        case('lazy operator ' + operator,
             setup + '; @ARGS@ "${v' + operator + '$(printf x >>effect; printf word)}"\n',
             ('word' if selected else ('' if operator.endswith('+') else 'set'),),
             files={'effect': {'type': 'file', 'content': 'x'} if selected else {'type': 'absent'}})
    case('nested default assignment',
         'unset a b; @ARGS@ "${a:-${b:=two words}}" "$b"\n', ('two words', 'two words'))
    case('assign default stores unsplit value',
         'unset v; IFS=:; @ARGS@ ${v:=a:b} "$v"\n', ('a', 'b', 'a:b'))
    # ENV-002, EXP-001: argument fields and process/state relations.
    case('positional braces and longest name',
         'set -- a b c d e f g h i ten; v=x; vx=y; @ARGS@ "$10" "${10}" "${010}" "${008}" "${v}x" "$vx" "$#"\n',
         ('a0', 'ten', 'ten', 'h', 'xx', 'y', '10'))
    case('positional at and star IFS variants',
         'set -- a "" "b c"; IFS=:; @ARGS@ "$@" "$*" $@ $*; '
         'IFS=; @ARGS@ "$*"; unset IFS; @ARGS@ "$*"\n',
         ('a', '', 'b c', 'a::b c', 'a', 'b c', 'a', 'b c', 'ab c', 'a  b c'))
    case('zero positional fields and embedded at',
         'set --; @ARGS@ "$@" "$*" "pre$@post"; set -- a "" b; @ARGS@ "pre$@post"\n',
         ('', 'prepost', 'prea', '', 'bpost'))
    case('selected operator word preserves positional fields',
         'set -- a "" "b c"; unset v; @ARGS@ "${v:-$@}"; v=set; @ARGS@ "${v:+$@}"\n',
         ('a', '', 'b c', 'a', '', 'b c'))
    case('special PID status options and zero survive subshell',
         'parent=$$; zero=$0; set -f; (test "$$" = "$parent" && test "$0" = "$zero" && '
         'case $- in *f*) @ARGS@ inherited;; esac); '
         '(exit 17) & child=$!; test "$child" -gt 0 && test "$child" != "$$" || exit 99; '
         'wait "$child"; @ARGS@ "$?"; set +f\n', ('inherited', '17'))
    # EXP-002: protected replacements and syntactic sites. Login data is from
    # getpwuid/getpwnam on the executing host, as required by the tilde clause.
    case('tilde protection empty HOME and syntactic sites',
         'HOME="a b*"; @ARGS@ ~ ~/x; a=~:~/x; @ARGS@ "$a"; HOME=; @ARGS@ ~\n',
         ('a b*', 'a b*/x', 'a b*:a b*/x', ''), setup={'a b-match': ''})
    case('tilde expansion is not recursive',
         'HOME=/home/test; v="~"; c=:; a=x${c}~; @ARGS@ "$a" $v "~" \\~ ${unset:-~}\n',
         ('x:~', '~', '~', '~', '/home/test'))
    login = pwd.getpwuid(0)
    case('tilde known login', '@ARGS@ ~' + login.pw_name + '\n', (login.pw_dir,))
    case('policy unset HOME leaves tilde', 'unset HOME; @ARGS@ ~ ~/x\n', ('~', '~/x'))
    # EXP-004/010: minimal/maximal matches, quoted vs expanded pattern bytes.
    case('all four removal operators and empty patterns',
         'v=abcabc; @ARGS@ "${v#a*c}" "${v##a*c}" "${v%a*c}" "${v%%a*c}" '
         '"${v#}" "${v##}" "${v%}" "${v%%}" "${#v}"\n',
         ('abc', '', 'abc', '', 'abcabc', 'abcabc', 'abcabc', 'abcabc', '6'))
    case('pattern operand quote provenance and nesting',
         'v="a*b-tail"; p="a*"; @ARGS@ "${v#$p}" "${v#"$p"}" "${v#${unset:-a?b-}}"\n',
         ('*b-tail', 'b-tail', 'tail'))
    case('patterns slash dot classes and nonmatches',
         'v=".a/b1"; @ARGS@ "${v#*[/]}" "${v%[[:digit:]]}" "${v#z*}"; '
         'case "$v" in ?a/b[!a-z]) @ARGS@ match;; esac\n', ('b1', '.a/b', '.a/b1', 'match'))
    # EXP-005: both forms retain internal newlines, isolate state, and strip
    # trailing newlines. Existing CSH-026 cases cover large output/faults/replay.
    for label, expansion in (('dollar', '$(v=child; printf "a\\nb\\n\\n"; exit 7)'),
                              ('backquote', '`v=child; printf "a\\nb\\n\\n"; exit 7`')):
        case('substitution ' + label + ' newline state and status',
             'v=parent; x=' + expansion + '; @ARGS@ "$?" "$x" "$v"\n', ('7', 'a\nb', 'parent'))
    case('expansions execute beginning to end',
         'v=0; @ARGS@ "${v:=9}$((v=2))${v}$(printf x >>effect; printf end)" "$v"\n',
         ('022end', '2'), files={'effect': {'type': 'file', 'content': 'x'}})
    # EXP-006: each required operator family uses bounded, defined operands.
    for label, expression, value in (
        ('constants', '010 + 0x10 + 10', '34'), ('unary', '-2 + +3 + !0 + ~0', '1'),
        ('multiplicative', '17 / 3 * 2 + 17 % 3', '12'), ('shifts', '(3 << 2) >> 1', '6'),
        ('comparison', '(2<3)+(3>2)+(2<=2)+(3>=3)+(2==2)+(2!=3)', '6'),
        ('bitwise', '(6 & 3) | (5 ^ 1)', '6'), ('logical', '(0 || 2) && 3', '1'),
        ('conditional', '0 ? 1/0 : 7', '7'), ('short circuit', '(0 && (v=1)) + (1 || (v=2))', '1'),
    ):
        case('arithmetic ' + label, 'v=0; @ARGS@ "$((' + expression + '))"\n', (value,))
    case('arithmetic compound assignments',
         'v=8; @ARGS@ "$((v+=2))" "$((v-=1))" "$((v*=2))" "$((v/=3))" '
         '"$((v%=4))" "$((v<<=2))" "$((v>>=1))" "$((v&=6))" "$((v^=3))" "$((v|=8))" "$v"\n',
         ('10', '9', '18', '6', '2', '8', '4', '4', '7', '15', '15'))
    case('arithmetic signed variable constants and nested expansion',
         'v=-0x10; @ARGS@ "$((v))" "$(($v))" "$((2+$(printf 3)+$((4))))"\n', ('-16', '-16', '9'))
    case('policy arithmetic negative right shift and comma',
         '@ARGS@ "$((-3 >> 1))" "$((v=1,v+2))" "$v"\n', ('-2', '3', '1'))
    case('arithmetic invalid variable diagnostic',
         'v=abc; @ARGS@ "$((v))" >effect\n', status=2,
         stderr='cshell: arithmetic expansion failed\n', files={'effect': {'type': 'absent'}})
    # EXP-007/009: promote the API's Issue 8 empty-field/provenance boundaries.
    for label, setup, word, values in (
        ('unset whitespace', 'unset IFS; v=" a\tb\nc "', '$v', ('a', 'b', 'c')),
        ('empty IFS', 'IFS=; v=" a b "', '$v "$unset" $unset', (' a b ', '')),
        ('nonwhite empties', 'IFS=:; v=":a::b:"', '$v', ('', 'a', '', 'b')),
        ('mixed whitespace', 'IFS=" :"; v=" : a : : b : "', '$v', ('', 'a', '', 'b')),
        ('literal delimiter', 'IFS=:; v=a:', '$v:b', ('a', ':b')),
        ('leading quoted empty', 'v=" a"', '""$v', ('', 'a')),
        ('trailing quoted empty', 'v="a "', '$v""', ('a', '')),
        ('between expansions', 'v="a "; w=" b"', '$v""$w', ('a', '', 'b')),
        ('policy extra whitespace is nonwhite', "IFS=$'\\v'; v=$'\\va\\v\\vb\\v'", '$v', ('', 'a', '', 'b')),
    ):
        case('IFS ' + label, setup + '; @ARGS@ ' + word + '\n', values)
    case('quotes from values remain data',
         '''v='"a b"'; @ARGS@ $v "$v" a' b'" c" $'\\x2a'\n''', ('"a', 'b"', '"a b"', 'a b c', '*'))
    # EXP-008/010: match per component, including literal dot/slash boundaries.
    case('pathname order components dot and unmatched',
         '@ARGS@ d/* d/.* d/[ab]? d/no* d/*/x\n',
         ('d/a1', 'd/b2', 'd/sub', 'd/.hidden', 'd/a1', 'd/b2', 'd/no*', 'd/sub/x'),
         setup={'d/a1': '', 'd/b2': '', 'd/.hidden': '', 'd/sub/x': ''})
    case('pathname expansion results never split again',
         'IFS=:; v="a*:b*"; @ARGS@ $v; set -f; @ARGS@ $v\n',
         ('a one', 'a:two', 'b one', 'a*', 'b*'), setup={'a one': '', 'a:two': '', 'b one': ''})
    case('quoted wildcard with unquoted suffix', '@ARGS@ "a*"?\n', ('a*x',), setup={'a*x': '', 'abx': ''})
    case('policy brace expansion absent', '@ARGS@ a{b,c} x{1..3}\n', ('a{b,c}', 'x{1..3}'))
    # EXP-011: lexical and selected expanded declaration-utility recognition.
    for prefix in ('export', 'readonly', 'command export', 'command command readonly'):
        case('declaration ' + prefix, 'v="a b *"; ' + prefix + ' a=$v; @ARGS@ "$a"\n', ('a b *',))
    for prefix in ('$cmd', 'command $cmd', 'command -- export'):
        case('policy expanded declaration ' + prefix,
             'cmd=export; HOME="two words"; v="a b *"; ' + prefix + ' a=$v b=~; @ARGS@ "$a" "$b"\n',
             ('a b *', 'two words'))
    case('ordinary utility has no assignment context',
         'HOME=/home/test; v="a b"; @ARGS@ a=$v b=~\n', ('a=a', 'b', 'b=~'))

    # Runtime width follows the build host C ABI (both supported targets LP64).
    bits = ctypes.sizeof(ctypes.c_long) * 8
    maximum = (1 << (bits - 1)) - 1
    minimum = -maximum - 1
    case('arithmetic signed long boundaries',
         f'@ARGS@ "$(({maximum}))" "$((-{maximum}-1))"\n',
         (str(maximum), str(minimum)))
    for label, expression in (
        ('addition overflow', f'{maximum}+1'),
        ('division overflow', f'(-{maximum}-1)/-1'),
        ('negative shift count', '1<<-1'), ('width shift count', f'1<<{bits}'),
    ):
        case('policy arithmetic ' + label,
             '@ARGS@ "$((' + expression + '))" >effect\n', status=2,
             stderr='cshell: arithmetic expansion failed\n', files={'effect': {'type': 'absent'}})
    case('pattern portable bracket forms',
         '@ARGS@ p/[a-c] p/[!a-c] p/[]] p/[-] p/[[:digit:]] p/[[=a=]] p/[[.a.]]\n',
         ('p/a', 'p/b', 'p/c', 'p/-', 'p/1', 'p/]', 'p/z', 'p/]', 'p/-', 'p/1', 'p/a', 'p/a'),
         setup={'p/' + name: '' for name in ('a', 'b', 'c', 'z', ']', '-', '1')})
    case('pathname slash before bracket interpretation', '@ARGS@ p/a[b/c]d\n',
         ('p/a[b/c]d',), setup={'p/a[b/c]d': '', 'p/abd': ''})
    case('non-directory component is a nonmatch', '@ARGS@ regular/* missing/*\n',
         ('regular/*', 'missing/*'), setup={'regular': ''})

    case('assignment operator removes operand quotes before splitting',
         "unset v; @ARGS@ ${v:='a b'} \"$v\"\n", ('a', 'b', 'a b'))
    case('initial and subshell status',
         '@ARGS@ "$?"; false; (@ARGS@ "$?"); false; x=$(printf "%s" "$?"); @ARGS@ "$x"\n',
         ('0', '1', '1'))
