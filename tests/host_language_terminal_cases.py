"""Controlling-terminal contracts with independent data and output channels."""

BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'


def cases():
    def editor(name, commands, output, clauses, **kw):
        return dict(id='ed/tty-'+name, utility='ed', args=['-p', '@', 'data'],
                    stdin=b'', stdout=output, stderr=b'', status='normal',
                    terminal='stdout', steps=[{'expect': '4\n@'}, {'send': commands}],
                    input_files={'data': b'old\n', 'other': b'next\n'},
                    files={'data': b'old\n', 'other': b'next\n'},
                    clauses=clauses+['STDOUT'], source=BASE+'ed.html', **kw)

    yield editor('quit-warning', '1s/old/new/\nq\n1p\nq\n',
                 b'4\n@@?\n@new\n@', ['Commands in ed', 'Quit Command'])
    yield editor('edit-warning', '1s/old/new/\ne other\n1p\ne other\n1p\nq\n',
                 b'4\n@@?\n@new\n@5\n@next\n@', ['Commands in ed', 'Edit Command'])
    yield editor('warning-rearmed', '1s/old/new/\nq\n1s/new/last/\nq\n1p\nq\n',
                 b'4\n@@?\n@@?\n@last\n@', ['Commands in ed', 'Quit Command'])
    row = editor('help-toggle', '99p\nh\n.=\nH\n99p\nH\n99p\nQ\n',
                 {'regex': rb'4\n@\?\n@[^\n]+\n@1\n@[^\n]+\n@\?\n[^\n]+\n@@\?\n@'},
                 ['Help Command', 'Help-Mode Command', 'CONSEQUENCES OF ERRORS'])
    row['status'] = 'nonzero'
    yield row
    # VEOF is delivered only after the prompt confirms command mode. A second
    # EOF accepts the warning; it is not a terminal disconnect or SIGHUP test.
    row = editor('eof-warning', '', b'4\n@@?\n@', ['Commands in ed', 'Quit Command'])
    row['steps'] = [{'expect': '4\n@'}, {'send': '1s/old/new/\n'}, {'expect': '@'},
                    {'control': 'D'}, {'expect': '?\n@'}, {'control': 'D'}]
    yield row
    row = editor('quit-signal-ignored', '', b'4\n@old\n@', ['ASYNCHRONOUS EVENTS'])
    row['steps'] = [{'expect': '4\n@'}, {'control': '\\'}, {'send': '1p\nq\n'}]
    row['status'] = 0
    yield row

    for name, response, output in [('yes', 'y\n', b'item\n'),
                                   ('uppercase-yes', 'YES\n', b'item\n'),
                                   ('no', 'n\n', b''), ('empty', '\n', b'')]:
        yield dict(id='xargs/tty-prompt-'+name, utility='xargs',
                   args=['-p', 'echo'], stdin=b'item\n', stdout=output,
                   stderr=b'echo item?...', status=0, terminal='stderr',
                   steps=[{'expect': 'echo item?...'}, {'send': response}],
                   clauses=['OPTIONS', 'STDERR', 'INPUT FILES', 'ENVIRONMENT VARIABLES'], source=BASE+'xargs.html')
    yield dict(id='xargs/tty-prompt-each-batch', utility='xargs',
               args=['-p', '-n', '1', 'echo'], stdin=b'first second third\n',
               stdout=b'first\nthird\n', stderr=b'echo first?...echo second?...echo third?...',
               status=0, terminal='stderr',
               steps=[{'expect': 'echo first?...'}, {'send': 'y\n'},
                      {'expect': 'echo second?...'}, {'send': 'n\n'},
                      {'expect': 'echo third?...'}, {'send': 'y\n'}],
               clauses=['OPTIONS', 'STDERR', 'INPUT FILES'], source=BASE+'xargs.html')
