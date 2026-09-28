"""CSH-049 residual partitions; see docs/execution-residuals.md for oracles."""
import copy
import errno
import os
import shlex


def add_redirection_cases(cross, helper):
    def check(name, script, **expect):
        cross('execution: residual ' + name, script + '\n', **expect)

    def file(content):
        return {'type': 'file', 'content': content}

    absent = {'type': 'absent'}
    # Include IFS and existing glob matches so loss of scalar context is visible.
    operands = (
        ('quote', '', "'out *'", 'out *'),
        ('parameter', "dest='out *'; IFS=' *'; ", '$dest', 'out *'),
        ('command', '', "$(printf 'out *\\n\\n')", 'out *'),
        ('backquote', '', "`printf 'out *\\n'`", 'out *'),
        ('arithmetic', 'n=0; ', 'out$((n+=1))', 'out1'),
        ('tilde', 'HOME=.; ', '~/out', 'out'),
        ('pattern-removal', "dest='prefixout *'; ", '${dest#prefix}', 'out *'),
        ('concatenation', "dest=' *'; ", '"out"$dest', 'out *'),
    )
    for expansion, prefix, operand, path in operands:
        for op in ('<', '>', '>|', '>>', '<>', 'noclobber'):
            setup = {'out match': 'decoy'}
            if op != 'noclobber': setup[path] = 'abcd'
            actual = '>' if op == 'noclobber' else op
            prefix_options = 'set -C; ' if op in ('>|', 'noclobber') else ''
            command, output, content = {
                '<': (f'{helper} copy', 'abcd', 'abcd'),
                '>': (f'{helper} fd-write 1', '', 'fd\n'),
                '>|': (f'{helper} fd-write 1', '', 'fd\n'),
                '>>': (f'{helper} seek-write 1', '', 'abcdXY'),
                '<>': (f'{helper} read-write', 'a\n', 'aXcd'),
                'noclobber': (f'{helper} fd-write 1', '', 'fd\n'),
            }[op]
            check(f'target {expansion} {op}', prefix + prefix_options +
                  f'{command} {actual}{operand}; {helper} args "$?" "${{n-unset}}"',
                  setup=setup, stdout=output + '[0]\n' + ('[1]\n' if expansion == 'arithmetic' else '[unset]\n'),
                  files={path: file(content), 'out match': file('decoy')})

    # Empty scalar targets are errors; they must not disappear as zero fields.
    for expansion, prefix, operand in (
        ('quoted', '', "''"), ('unset', 'unset dest; ', '$dest'),
        ('empty', 'dest=; ', '$dest'), ('substitution', '', '$(printf "")'),
    ):
        for op in ('<', '>', '>|', '>>', '<>', 'noclobber'):
            actual = '>' if op == 'noclobber' else op
            check(f'empty target {expansion} {op}', prefix +
                  ('set -C; ' if op == 'noclobber' else '') +
                  f'{helper} args forbidden >early {actual}{operand} >"$(touch expanded; printf later)"; '
                  f'{helper} args "$?" restored', setup={'early': 'old'},
                  stdout='[1]\n[restored]\n',
                  stderr='cshell: cannot apply redirection: ' + os.strerror(errno.ENOENT) + '\n',
                  files={'early': file(''), 'expanded': absent, 'later': absent})

    # Descriptor operands use the same expansions but must remain a single number.
    for expansion, prefix, operand in (
        ('parameter', 'fd=7; ', '$fd'), ('command', '', '$(printf 7)'),
        ('arithmetic', 'fd=6; ', '$((fd+=1))'), ('quote', '', "'7'"),
    ):
        for op in ('<&', '>&'):
            command = f'{helper} copy 3' if op == '<&' else f'{helper} fd-write 3'
            opened = '7<input' if op == '<&' else '7>out'
            check(f'duplicate {expansion} {op}', prefix + f'{command} {opened} 3{op}{operand}',
                  setup={'input': 'body\n'}, stdout='body\n' if op == '<&' else '',
                  files={'out': file('fd\n')} if op == '>&' else {'input': file('body\n')})

    # Real object kinds and lookup failures, without saturating a host filesystem.
    for op in ('>', '>|', '>>', '<>'):
        for kind, prepare, target, number in (
            ('directory', 'mkdir target; ', 'target', errno.EISDIR),
            ('non-directory-parent', '', 'regular/child', errno.ENOTDIR),
            ('missing-parent', '', 'absent/child', errno.ENOENT),
            ('symlink-loop', 'ln -s cycle target; ln -s target cycle; ', 'target', errno.ELOOP),
        ):
            check(f'filesystem {kind} {op}', prepare +
                  f'{helper} args forbidden >early {op}{target} >"$(touch expanded; printf later)"; '
                  f'{helper} args "$?" restored', setup={'regular': 'unchanged', 'early': 'old'},
                  stdout='[1]\n[restored]\n',
                  stderr='cshell: cannot apply redirection: ' + os.strerror(number) + '\n',
                  files={'regular': file('unchanged'), 'early': file(''), 'expanded': absent, 'later': absent})
        for link in ('symbolic', 'hard'):
            prepare = 'ln -s data target; ' if link == 'symbolic' else 'ln data target; '
            cmd = f'{helper} read-write' if op == '<>' else f'{helper} fd-write 1'
            check(f'filesystem {link} {op}', prepare + f'{cmd} {op}target',
                  setup={'data': 'abcd'}, stdout='a\n' if op == '<>' else '',
                  files={'data': file('aXcd' if op == '<>' else 'abcdfd\n' if op == '>>' else 'fd\n')})
    for link in ('symbolic', 'hard'):
        prepare = 'ln -s data target; ' if link == 'symbolic' else 'ln data target; '
        check('noclobber ' + link, prepare + f'set -C; {helper} args forbidden >target; {helper} args "$?"',
              setup={'data': 'preserved'}, stdout='[1]\n',
              stderr='cshell: cannot apply redirection: ' + os.strerror(errno.EEXIST) + '\n',
              files={'data': file('preserved')})
    for op in ('>', '>|', '>>', '<>'):
        fd = 0 if op == '<>' else 1
        check('dangling link creates ' + op, f'ln -s data target; {helper} fd-write {fd} {op}target',
              files={'data': file('fd\n')})
    # For a FIFO neither endpoint may wait for the other to be launched serially.
    for noclobber in (False, True):
        check(f'FIFO concurrent noclobber={noclobber}',
              'mkfifo channel; ' + ('set -C; ' if noclobber else '') +
              f'{helper} copy <channel >out & child=$!; {helper} fd-write 1 >channel; '
              f'wait "$child"; {helper} args "$?"', stdout='[0]\n', files={'out': file('fd\n')})

    # Current/child environments, call-time redirects and unwind all share a
    # redirect target with side effects. Exercise named constructs explicitly.
    body = f'{{ {helper} copy; }} <input >"out$((n+=1))"'
    wrappers = {
        'brace': ('{ ' + body + '; }', 1),
        'subshell': ('(' + body + ')', 0),
        'function': ('f() { ' + body + '; }; f', 1),
        'function-definition': (f'f() {{ {helper} copy; }} <input >"out$((n+=1))"; f', 1),
        'eval': ('eval ' + shlex.quote(body), 1),
        'dot': ('. ./source', 1),
        'if': ('if true; then ' + body + '; fi', 1),
        'for': ('for value in once; do ' + body + '; done', 1),
        'while': ('while [ "$n" -eq 0 ]; do ' + body + '; done', 1),
        'until': ('until [ "$n" -ne 0 ]; do ' + body + '; done', 1),
        'case': ('case x in x) ' + body + ';; esac', 1),
        'pipeline': (body + f' | {helper} copy', 0),
        'substitution': ('value=$(' + body + ')', 0),
        'background': (body + ' & child=$!; wait "$child"', 0),
    }
    for name, (command, count) in wrappers.items():
        check('context ' + name, 'n=0; ' + command + f'; {helper} args "$?" "$n" restored',
              setup={'input': 'body\n', 'source': body + '\n'},
              stdout=f'[0]\n[{count}]\n[restored]\n', files={'out1': file('body\n'), 'out2': absent})
    for transfer, loop in (('break', True), ('continue', True), ('return 7', False)):
        body = f'{{ {transfer}; }} >inner; : >forbidden'
        command = f'for x in once; do {body}; done' if loop else f'f() {{ {body}; }}; f'
        check('unwind ' + transfer, command + f'; {helper} args "$?" restored',
              stdout=f'[{0 if loop else 7}]\n[restored]\n', files={'inner': file(''), 'forbidden': absent})

    for op in ('>', '>|', '>>', '<>', 'noclobber'):
        for mask in (0, 0o027, 0o077):
            for existing in (False, True):
                if existing and op == 'noclobber': continue
                prefix = 'chmod 644 out; ' if existing else ''
                actual = '>' if op == 'noclobber' else op
                prefix += 'set -C; ' if op in ('noclobber', '>|') else ''
                check(f'creation permissions {op} mask={mask:03o} existing={existing}',
                      prefix + f'umask {mask:03o}; : {actual}out; {helper} mode out',
                      setup={'out': 'old'} if existing else {},
                      stdout=f'{0o644 if existing else 0o666 & ~mask:03o}\n',
                      files={'out': file('old' if existing and op in ('>>', '<>') else '')})


def add_interactive_redirections(result):
    """Assert the selected no-globbing policy even when -i is enabled."""
    for case in tuple(result):
        if not case['name'].startswith('execution: residual target '): continue
        if case['name'].endswith('(stdin)'): continue
        interactive = copy.deepcopy(case)
        interactive['name'] = case['name'].replace('residual target ', 'residual interactive target ', 1)
        interactive['args'].insert(0, '-i')
        result.append(interactive)
