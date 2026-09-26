"""CSH-046 runtime witnesses; clause/policy map: docs/invocation-syntax-evidence.md.

All cases run in -c, file and stdin modes through the bounded shared runner.
Exact diagnostics and permitted/unspecified choices are project regressions,
not claims that POSIX prescribes their spelling or the selected alternative.
"""


def add_syntax_cases(cross, helper):
    def case(name, script, stdout='', **kwargs):
        cross('syntax: ' + name, script, stdout=stdout, **kwargs)

    case('large sequential complete command', ':; ' * 5000 + "printf 'complete\\n'\n", 'complete\n')
    case('alias direct recursion',
         "a() { printf 'function\\n'; }\nalias a=a\na\n", 'function\n')
    case('alias empty replacement',
         f"alias empty=''\nempty {helper} args after\n", '[after]\n')
    case('comments and token boundaries',
         f"{helper} args word#tail '#quoted' \\#escaped;# ignored\n"
         f"{helper}\targs\tend # ignored\n", '[word#tail]\n[#quoted]\n[#escaped]\n[end]\n')
    case('escaped newline joins word and operator',
         "printf '%s\\n' one\\\ntwo &\\\n& printf 'yes\\n'\n", 'onetwo\nyes\n')
    case('escaped metacharacters',
         f"{helper} args \\| \\& \\; \\< \\> \\( \\) \\$ \\` \\\\ \\\" \\' a\\ b\n",
         '[|]\n[&]\n[;]\n[<]\n[>]\n[(]\n[)]\n[$]\n[`]\n[\\]\n["]\n[\']\n[a b]\n')
    case('single quote adjacency', f"{helper} args '' a'b c'\"d\" '$`\\' 'one\ntwo'\n",
         '[]\n[ab cd]\n[$`\\]\n[one\ntwo]\n')
    case('double quote escapes',
         f'{helper} args "\\$x" "\\`x" "\\\\" "\\\"" "\\q" "a\\\nb" "$\'literal\'"\n',
         '[$x]\n[`x]\n[\\]\n["]\n[\\q]\n[ab]\n[$\'literal\']\n')
    case('nested quote contexts',
         f"v='a*b'; {helper} args \"${{v#'a*'}}\" \"$(printf '%s' ')')\" \"${{unset:-$(printf nested)}}\"\n",
         '[b]\n[)]\n[nested]\n')
    case('dollar quote required escapes',
         f"{helper} args $'\\\"\\\'\\\\\\a\\b\\e\\f\\n\\r\\t\\v' $'\\cA\\c?\\c\\\\' $'\\101Z\\x42Q\\7X'\n",
         '["\'\\\a\b\x1b\f\n\r\t\v]\n[\x01\x7f\x1c]\n[AZBQ\x07X]\n')
    case('dollar quote retains protection',
         f"IFS=:; {helper} args $'a:b * $HOME `echo no`' x$''y $''\n",
         '[a:b * $HOME `echo no`]\n[xy]\n[]\n', setup={'matched': ''})
    case('no expansion during token recognition',
         "false && printf '%s' \"$(printf bad >effect)\"\n"
         "if false; then printf '%s' \"${unset:=bad}\"; fi\n"
         "printf '%s\\n' \"${unset-unset}\"\n", 'unset\n',
         files={'effect': {'type': 'absent'}})
    case('reserved words as arguments and quoted commands',
         f"{helper} args if then else elif fi do done for while until case esac in ! '{{' '}}'\n"
         "'if'\n", ''.join(f'[{w}]\n' for w in
         'if then else elif fi do done for while until case esac in ! { }'.split()),
         status=127, stderr='cshell: if: command not found\n')
    case('assignment and descriptor token positions',
         f"value=before; value=after {helper} args value=literal 2 >out\n"
         f"{helper} args \"$value\"; {helper} copy <out\n", '[before]\n[value=literal]\n[2]\n',
         files={'out': {'type': 'file', 'content': '[value=literal]\n[2]\n'}})
    case('longest redirection operators',
         "printf first >out; printf second >>out; set -C; printf reset >|out\n"
         f"{helper} copy 3<>out <&3 3>&-\n", 'reset',
         files={'out': {'type': 'file', 'content': 'reset'}})
    case('shebang comment policy', '#!/not/an/interpreter\nprintf "body\\n"\n', 'body\n')
    # Unsupported extension operators reject the entire complete command.
    for operator, column, message in (
        ('|&', 12, 'expected command'),
        ('>>&', 13, 'expected redirection operand'),
    ):
        case('reject ' + operator, f': >effect {operator} :\n', status=2,
             stderr=f'cshell: @SOURCE@: 1:{column}: {message}\n',
             files={'effect': {'type': 'absent'}})
    case('optional IO_LOCATION is ordinary word',
         "printf '%s\\n' {slot}>out\ncat out\n", '{slot}\n',
         files={'out': {'type': 'file', 'content': '{slot}\n'}})
    case('invalid complete command has no effects', ': >effect; )\n', status=2,
         stderr='cshell: @SOURCE@: 1:12: expected command\n',
         files={'effect': {'type': 'absent'}})
    case('prior complete command survives syntax error',
         'printf before >prior\n: >effect; )\n', status=2,
         stderr='cshell: @SOURCE@: 2:12: expected command\n',
         files={'prior': {'type': 'file', 'content': 'before'}, 'effect': {'type': 'absent'}})
    case('alias recursion and independent reuse',
         "alias a='b' b='a'\na() { printf 'function\\n'; }\na\na\n", 'function\nfunction\n')
    case('alias quoting eligibility',
         "a() { printf 'function\\n'; }\nalias a='printf alias\\\\n'\n"
         "'a'\n\"a\"\n\\a\na''\na\\\n\n", 'function\nfunction\nfunction\nfunction\nalias\n')
    case('alias assignment redirect and argument positions',
         f"alias a='{helper} args alias' target=wrong\n"
         "V=x >target a a\ncat target\n", '[alias]\n[a]\n',
         files={'target': {'type': 'file', 'content': '[alias]\n[a]\n'},
                'wrong': {'type': 'absent'}})
    case('alias trailing blank',
         f"alias a='{helper} args ' b='expanded'\na b\n", '[expanded]\n')
    case('alias quoted trailing blank policy',
         f"alias a='{helper} args \\ ' b=expanded\na b\n", '[ ]\n[expanded]\n')
    case('alias reserved spelling policy',
         f"alias a='{helper} args ' if=changed\na if\n", '[if]\n')
    case('alias injected separator policy',
         "alias a='printf %s 0'\na>&2\n", stderr='0')
    case('alias introduces grammar',
         "alias a='{ printf first; printf second; }'\na\n", 'firstsecond')
    case('alias same complete command timing',
         "a() { printf 'function\\n'; }\nalias a='printf alias\\\\n'; a\na\n"
         "unalias a; a\na\n", 'function\nalias\nalias\nfunction\n')
    case('alias query and reusable quoting',
         "alias a=\"printf '%s\\n' \\\"two words\\\"\" b=\"line1\nline2'quote\" empty=\n"
         "alias >before\n"
         'for n in a b empty; do definition=$(alias "$n"); unalias "$n"; eval "alias $definition"; done\n'
         "alias >after\ncmp before after && printf 'same\\n'\na\n", 'same\ntwo words\n')
    case('unalias subshell and named removal',
         "alias a=one b=two\n(unalias -a; alias)\nalias a b\n"
         "unalias a\nalias\nunalias -a\nalias\n", "a='one'\nb='two'\nb='two'\n")
    case('unalias mixed missing operand',
         "alias a=one b=two\nunalias missing a; printf '%s\\n' \"$?\"\nalias\n",
         "1\nb='two'\n", stderr='unalias: missing: not found\n')
    case('alias mixed query and definition',
         "alias missing a=one; printf '%s\\n' \"$?\"\nalias a\n",
         "1\na='one'\n", stderr='alias: missing: not found\n')
