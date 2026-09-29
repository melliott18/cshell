"""CSH-065: exact, five-second interactive recovery and exit controls."""


def recovery_cases():
    result = []

    def case(name, script, stdout, diagnostics, prompts, status=7, files=None):
        # prompts is the literal stdin transcript with diagnostic placeholders;
        # string/file modes have the same diagnostics without stdin prompts.
        for mode, source in (("string", "-c"), ("file", "script"), ("stdin", "stdin")):
            errors = [f"cshell: {source}: {where}: {message}\n"
                      for where, message in diagnostics]
            stderr = prompts if mode == "stdin" else ''.join(errors)
            if mode == "stdin":
                for i, diagnostic in enumerate(errors):
                    stderr = stderr.replace(f"@{i}@", diagnostic)
            expect = dict(stdout=stdout, stderr=stderr, status=status)
            if files:
                expect['files'] = files
            result.append(dict(name=f"syntax: recovery {name} ({mode})", timeout=5,
                               args=['-i', '-c', script] if mode == 'string' else
                                    ['-i', 'script'] if mode == 'file' else ['-i'],
                               stdin=script if mode == 'stdin' else '',
                               setup={'script': script} if mode == 'file' else {}, expect=expect))

    case('main parser', "printf 'before\\n'\n)\nprintf 'after\\n'\nexit 7\n",
         'before\nafter\n', [('2:1', 'expected command')], '$ $ @0@$ $ ')
    case('status effects and repeated positions',
         "printf before >prior\n: >bad; ) printf ignored >tail\n"
         "printf '%s\\n' \"$?\" >after\n)\nexit\n", '',
         [('2:9', 'expected command'), ('4:1', 'expected command')], '$ $ @0@$ $ @1@$ ',
         status=2, files={'prior': {'type': 'file', 'content': 'before'},
                          'after': {'type': 'file', 'content': '2\n'},
                          'bad': {'type': 'absent'}, 'tail': {'type': 'absent'}})
    case('newline operand', ": >\nprintf '%s\\n' \"$?\"\nexit 7\n", '2\n',
         [('1:4', 'expected redirection operand')], '$ @0@$ $ ')
    case('aliases survive nested failure',
         "alias good='printf good' bad=')' nested='bad'\nnested >bad\n"
         "good\nnested\ngood\nexit 7\n", 'goodgood',
         [('2:1', 'expected command'), ('4:1', 'expected command')],
         '$ $ @0@$ $ @1@$ $ ', files={'bad': {'type': 'absent'}})
    case('alias remainder discarded',
         "alias bad=')\nprintf bad >bad' good='printf good'\nbad\ngood\nexit 7\n",
         'good', [('3:1', 'expected command')], '$ > $ @0@$ $ ',
         files={'bad': {'type': 'absent'}})
    case('pending documents',
         "cat <<A <<-'B' >bad; )\n$(printf bad >expanded)\nA\n\tprintf bad >body\n\tB\n"
         "printf '%s\\n' \"$?\"\ncat <<END\nafter\nEND\nexit 7\n", '2\nafter\n',
         [('1:22', 'expected command')], '$ @0@> > > > $ $ > > $ ',
         files={name: {'type': 'absent'} for name in ('bad', 'expanded', 'body')})
    case('continued delimiter',
         "cat <<END; )\nprintf bad >body\nE\\\nND\nprintf after\nexit 7\n", 'after',
         [('1:12', 'expected command')], '$ @0@> > > $ $ ',
         files={'body': {'type': 'absent'}})
    case('nested pending documents',
         "cat <<OUT $(cat <<IN; |) >bad\nprintf bad >inner\nIN\nprintf bad >outer\nOUT\n"
         "printf after\nexit 7\n", 'after', [('1:23', 'expected command')],
         '$ @0@> > > > $ $ ', files={n: {'type': 'absent'} for n in ('bad', 'inner', 'outer')})
    case('alias pending document',
         "alias bad='cat <<END; )'\nbad\nprintf bad >body\nEND\nprintf after\nexit 7\n",
         'after', [('2:1', 'expected command')], '$ $ @0@> > $ $ ',
         files={'body': {'type': 'absent'}})
    case('alias buffered document',
         "alias bad='cat <<END; )\nprintf bad >body\nEND\nprintf bad >tail'\n"
         "bad\nprintf after\nexit 7\n", 'after', [('5:1', 'expected command')],
         '$ > > > $ @0@$ $ ', files={n: {'type': 'absent'} for n in ('body', 'tail')})
    case('completed document then syntax error',
         "{ cat <<END\nprintf bad >body\nEND\n)\nprintf after\nexit 7\n", 'after',
         [('4:1', 'expected command')], '$ > > > @0@$ $ ',
         files={'body': {'type': 'absent'}})
    case('EOF after syntax', ')\n', '', [('1:1', 'expected command')], '$ @0@$ ', status=2)
    case('EOF incomplete quote', "printf 'unfinished", '',
         [('1:8', 'unterminated single quote')], '$ > @0@', status=2)
    case('EOF pending document', 'cat <<END; )\nprintf bad >body\n', '',
         [('1:12', 'expected command'), ('1:7', 'unterminated here-document')],
         '$ @0@> > @1@', status=2, files={'body': {'type': 'absent'}})
    return result


def recovery_terminal_cases():
    diagnostic = 'cshell: stdin: 1:1: expected command\n'
    document_error = 'cshell: stdin: 3:12: expected command\n'
    return [dict(name='terminal main parser syntax recovery', transport='pty', timeout=5,
                 steps=[{'expect': '$ '}, {'send': ')\n'}, {'expect': diagnostic + '$ '},
                        {'send': "printf 'after:%s\\n' \"$?\"\n"}, {'expect': 'after:2\n$ '},
                        {'send': 'cat <<END; )\n'}, {'expect': document_error + '> '},
                        {'send': 'printf bad >body\n'}, {'expect': '> '},
                        {'send': 'END\n'}, {'expect': '$ '},
                        {'send': "printf 'ready:%s\\n' \"$?\"\n"}, {'expect': 'ready:2\n$ '},
                        {'send': 'exit 7\n'}],
                 expect=dict(output='$ ' + diagnostic + '$ after:2\n$ ' + document_error +
                                    '> > $ ready:2\n$ ', status=7, files={'body': {'type': 'absent'}}))]
