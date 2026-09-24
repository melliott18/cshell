"""CSH-026 integration cases shared by all three public input modes."""
import errno
import os


def add_cases(cross, helper):
    def args(name, script, output, **kwargs):
        cross(name, script.replace('@ARGS@', helper + ' args'), stdout=output, **kwargs)

    args('parameter values and empty fields',
         'v="a b"; @ARGS@ $v "$v" $unset "$unset" ""\n',
         '[a]\n[b]\n[a b]\n[]\n[]\n')
    args('substitution splitting and protection',
         '@ARGS@ $(printf "a b\\n\\n") "$(printf "a b\\n\\n")"\n',
         '[a]\n[b]\n[a b]\n')
    args('nested substitutions and embedded newline bytes',
         '@ARGS@ "pre$(printf "%s\\n\\n" "$(printf "a\\nb\\n")")post"\n',
         '[prea\nbpost]\n')
    args('backquote execution and nesting',
         r'@ARGS@ "`printf "%s" \`printf nested\``"' + '\n', '[nested]\n')
    args('empty substitution fields',
         '@ARGS@ $(printf "\\n\\n") "$(printf "\\n\\n")" x$(exit 0)y\n',
         '[]\n[xy]\n')
    args('substitution output is never shell syntax',
         '''v='$(>forbidden) ; * "'; @ARGS@ "$(printf '%s' "$v")"\n''',
         '[$(>forbidden) ; * "]\n', files={'forbidden': {'type': 'absent'}})
    args('last substitution status without command',
         'x=$(exit 7) y=$(exit 19); @ARGS@ "$?" "$x" "$y"\n', '[19]\n[]\n[]\n')
    args('argument expansion retains prior pipeline status',
         'false; @ARGS@ "$(exit 7)" "$?"; @ARGS@ "$?"\n', '[]\n[1]\n[0]\n')
    args('assignment expansion retains prior pipeline status',
         'false; x=$(exit 7) y=$?; @ARGS@ "$y" "$?"\n', '[1]\n[7]\n')
    args('command status overrides substitution status',
         f'{helper} status "$(printf 11; exit 23)"; @ARGS@ "$?"\n', '[11]\n')
    args('assignment status after redirection substitution',
         '>"$(printf target; exit 17)"; @ARGS@ "$?"\n', '[17]\n',
         files={'target': {'type': 'file', 'content': ''}})
    args('substitution state cwd and parameters isolated',
         'v=outer; set -- parent; x=$(v=inner; cd nested; set -- child; printf "%s/%s/%s" "$v" "$#" "$-"); '
         '@ARGS@ "$v" "$x" "$-"; >proof\n',
         '[outer]\n[inner/1/]\n[]\n', setup={'nested/seed': ''},
         files={'proof': {'type': 'file', 'content': ''}})
    args('large capture drains before wait',
         f'v=$({helper} generate 1048576); @ARGS@ "${{#v}}"\n', '[1048576]\n')
    args('large nested capture',
         f'v=$(n=$({helper} generate 1048576); printf "%s" "${{#n}}"); @ARGS@ "$v"\n', '[1048576]\n')
    args('substitution pipeline capture',
         f'v=$({helper} generate 1048576 | {helper} count); @ARGS@ "$v"\n', '[1048576]\n')
    args('lazy parameter operands',
         'v=set; @ARGS@ "${v:-$(>forbidden)}" "${unset:+`>also-forbidden`}"\n',
         '[set]\n[]\n', files={name: {'type': 'absent'} for name in ('forbidden', 'also-forbidden')})
    args('short circuit does not expand skipped commands',
         'false && @ARGS@ "${unset:?never}"; true || @ARGS@ "$(>forbidden)"; @ARGS@ okay\n',
         '[okay]\n', files={'forbidden': {'type': 'absent'}})
    args('assignment expansion is scalar and sequential',
         'v="a b *"; a=$v b=$a; @ARGS@ "$a" "$b"\n', '[a b *]\n[a b *]\n', setup={'match': ''})
    args('assignment tilde sites',
         'HOME="/home/test path"; a=~:~/dir; @ARGS@ "$a"\n', '[/home/test path:/home/test path/dir]\n')
    args('declaration operands use assignment context',
         'v="a b *"; export a=$v; readonly b=$v; @ARGS@ "$a" "$b"\n', '[a b *]\n[a b *]\n')
    args('assignment substitution sees preceding redirects',
         f'x=$({helper} both) {helper} environment x 2>errors\n', 'x=out\n',
         files={'errors': {'type': 'file', 'content': 'err\n'}})
    args('redirection operands do not split or glob',
         'p="two words *"; printf data >$p; @ARGS@ "$(cat < $p)"\n', '[data]\n',
         files={'two words *': {'type': 'file', 'content': 'data'}})
    cross('redirection expansion observes previous redirection',
          f'{helper} args value >"$(printf first)" 2>"$(printf second)"\n',
          files={'first': {'type': 'file', 'content': '[value]\n'}, 'second': {'type': 'file', 'content': ''}})
    args('empty command redirection environment isolated',
         '>"${made:=created}"; @ARGS@ "${made-unset}"\n', '[unset]\n',
         files={'created': {'type': 'file', 'content': ''}})
    cross('unquoted heredoc body rules',
          'v=value; cat <<END\n~ "double" \'single\' $v $((2+3)) $(printf nested)\n'
          '\\$v \\`literal\\` \\q \\" \\\\\nEND\n',
          stdout='~ "double" \'single\' value 5 nested\n$v `literal` \\q \\" \\\n')
    cross('quoted heredoc suppresses expansion',
          'cat <<\'END\'\n${unset:?bad} $(>forbidden) `>also-forbidden` \\keep\nEND\n',
          stdout='${unset:?bad} $(>forbidden) `>also-forbidden` \\keep\n',
          files={name: {'type': 'absent'} for name in ('forbidden', 'also-forbidden')})
    cross('partially quoted heredoc suppresses expansion',
          'cat <<E"N"D\n$HOME\nEND\n', stdout='$HOME\n')
    cross('dollar quoted delimiter suppresses expansion',
          "cat <<$'E\\x4eD'\n$HOME\nEND\n", stdout='$HOME\n')
    cross('heredoc continuations and tab stripping',
          'v=body; cat <<-END\n\t$v\\\n\tcontinued\n\tEND\n', stdout='body\tcontinued\n')
    cross('ordered expanded heredocs',
          'cat <<ONE <<TWO\n$(printf first >proof)\nONE\n$(cat proof; printf second)\nTWO\n',
          stdout='firstsecond\n', files={'proof': {'type': 'file', 'content': 'first'}})
    args('nested heredoc inside substitution',
         '@ARGS@ "$(cat <<END\n$(printf inner)\nEND\n)"\n', '[inner]\n')
    cross('large expanded heredoc',
          f'{helper} count <<END\n$({helper} generate 524288)\nEND\n', stdout='524289\n')
    cross('skipped heredoc does not parse or expand body',
          'true || cat <<END\n${unset:?bad} $(unfinished\nEND\n', stdout='')
    args('pattern removal uses quote protection',
         '''v='abc'; @ARGS@ "${v#a*}" "${v#'a*'}" "${v%*c}" "${v%%b*}" "${v#}"\n''',
         '[bc]\n[abc]\n[ab]\n[a]\n[abc]\n')
    args('quoted POSIX class name remains literal in removal pattern',
         '''v=alpha; @ARGS@ "${v#[[:alpha:]]}" "${v#[[:'alpha':]]}"\n''', '[lpha]\n[alpha]\n')
    args('substitution in removal pattern',
         'v=prefix-tail; @ARGS@ "${v#$(printf "*-" )}"\n', '[tail]\n')
    args('IFS fields then sorted pathname generation',
         'IFS=:; v="a*:b*:"; @ARGS@ $v\n', '[a one]\n[a-two]\n[b-one]\n',
         setup={'a one': '', 'a-two': '', 'b-one': '', '.hidden': ''})
    args('quoted positional expansion keeps empty arguments',
         'set -- a "" "b c"; @ARGS@ "pre$@post"; set --; @ARGS@ "$@" "$*"\n',
         '[prea]\n[]\n[b cpost]\n[]\n')
    args('pipeline expansion state remains in its stage',
         f'@ARGS@ "${{v:=child}}" | {helper} copy; @ARGS@ "${{v-parent}}"\n', '[child]\n[parent]\n')
    args('pipeline substitution reads pipeline input',
         f'printf data | @ARGS@ "$(cat)"\n', '[data]\n')
    args('substitution exit and child expansion failure isolated',
         'v=$(printf before; printf "%s" "${unset:?inner}"; printf never); @ARGS@ "$v" "$?"\n',
         '[before]\n[2]\n', stderr='cshell: substitution: inner\n')
    for label, word, message in (
        ('required parameter', '${unset:?required}', 'required'),
        ('arithmetic', '$((1/0))', 'arithmetic expansion failed'),
        ('invalid backquote', '` ) `', 'expected command'),
        ('NUL capture', "$(printf '\\000')", 'NUL byte in command substitution output'),
    ):
        cross('expansion failure prevents command: ' + label,
              f'{helper} args "{word}" >forbidden\n{helper} args never\n',
              status=2, stderr=f'cshell: {message}\n', files={'forbidden': {'type': 'absent'}})
    cross('heredoc expansion error prevents execution',
          f'{helper} args never <<END\n${{missing:?body failed}}\nEND\n{helper} args never\n',
          status=2, stderr='cshell: body failed\n')
    cross('assignment expansion diagnostic follows active redirects',
          f'x=${{missing:?required}} : 2>errors\n{helper} args never\n',
          status=2, files={'errors': {'type': 'file', 'content': 'cshell: required\n'}})
    cross('heredoc diagnostic follows earlier redirects',
          'cat 2>errors <<END\n${missing:?body failed}\nEND\n',
          status=2, files={'errors': {'type': 'file', 'content': 'cshell: body failed\n'}})
    args('invalid expanded descriptor remains command failure',
         'fd=bad; cd . 1>&$fd || @ARGS@ recovered\n', '[recovered]\n',
         stderr="cshell: descriptor operand must be digits or '-'\n")
    # A dynamically selected descriptor may equal a nested group's private backup.
    for fd in range(3, 9):
        cross(f'private group descriptor cannot become expanded dup source {fd}',
              f'fd={fd}; {{ cd . 1>&$fd; {helper} args restored; }} >captured\n',
              stderr=f'cshell: cannot apply redirection: {os.strerror(errno.EBADF)}\n',
              files={'captured': {'type': 'file', 'content': '[restored]\n'}})
    cross('substitution child has no private inherited descriptors',
          f'{{ x=$({helper} private-fds); {helper} args "$?"; }} >captured\n',
          files={'captured': {'type': 'file', 'content': '[0]\n'}})
