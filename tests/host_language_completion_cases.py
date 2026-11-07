"""Remaining patch contracts, derived from Issue 8 rather than vendor output."""
BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/patch.html'


def cases():
    delta = b'1c1\n< old\n---\n> new\n'

    def case(name, args, **kw):
        row = dict(id='patch/'+name, utility='patch', args=args, stdin=b'',
                   stdout=b'', stderr=b'', status=0, source=BASE,
                   input_files={'data': b'old\n', 'delta': delta}, files={'data': b'new\n'},
                   clauses=['OPTIONS', 'STDOUT', 'STDERR', 'OUTPUT FILES', 'Patch Application'])
        row.update(kw)
        return row

    # POSIX reserves stdout for the exceptional filename prompt. Ordinary
    # progress and reverse confirmation belong on stderr. Wording here pins
    # the selected GNU provider's English policy; stream/effect rules are POSIX.
    yield case('progress-stream', ['-i', 'delta', 'data'], stderr=b'patching file data\n')
    yield case('tty-filename', ['-s', '-i', 'delta'], terminal='stdout',
               stdout=b'File to patch: ',
               steps=[{'expect': 'File to patch: '}, {'send': 'data\n'}],
               clauses=['Filename Determination', 'INPUT FILES', 'STDOUT', 'STDERR', 'OUTPUT FILES'])
    for name, response in [('lowercase', 'y\n'), ('uppercase', 'YES\n')]:
        yield case('tty-reverse-'+name, ['-s', '-i', 'delta', 'data'], terminal='stderr',
                   input_files={'data': b'new\n', 'delta': delta}, files={'data': b'old\n'},
                   stderr=b'Reversed (or previously applied) patch detected!  Assume -R? [n] ',
                   steps=[{'expect': 'Assume -R? [n] '}, {'send': response}],
                   clauses=['OPTIONS', 'ENVIRONMENT VARIABLES', 'STDOUT', 'STDERR', 'OUTPUT FILES'])
    for name, locale, response in [('french', 'fr_FR.UTF-8', 'oui\n'),
                                    ('german', 'de_DE.UTF-8', 'ja\n')]:
        yield case('tty-reverse-'+name, ['-s', '-i', 'delta', 'data'], terminal='stderr',
                   env={'LC_ALL': locale}, input_files={'data': b'new\n', 'delta': delta},
                   files={'data': b'old\n'},
                   stderr=b'Reversed (or previously applied) patch detected!  Assume -R? [n] ',
                   steps=[{'expect': 'Assume -R? [n] '}, {'send': response}],
                   clauses=['OPTIONS', 'ENVIRONMENT VARIABLES', 'STDOUT', 'STDERR', 'OUTPUT FILES'])
    yield case('tty-reverse-decline', ['-s', '-i', 'delta', 'data'], terminal='stderr',
               input_files={'data': b'new\n', 'delta': delta}, files={'data': b'new\n'}, status=1,
               stderr=b'Reversed (or previously applied) patch detected!  Assume -R? [n] Apply anyway? [n] 1 out of 1 hunk ignored -- saving rejects to file data.rej\n',
               steps=[{'expect': 'Assume -R? [n] '}, {'send': 'n\n'},
                      {'expect': 'Apply anyway? [n] '}, {'send': 'n\n'}],
               file_rules=[dict(pattern='data.rej', count=1, data={'regex': rb'\*\*\* [^\n]+\n--- [^\n]+\n\*{15}\n\*\*\* 1(?: \*{4})?\n- old\n--- 1 ----(?:-)?\n\+ new\n'})])
    for name, headers, files, changed in [
        ('old-header-first', b'--- first\n+++ second\n', {'first': b'old\n', 'second': b'old\n'}, 'first'),
        ('new-header-fallback', b'--- missing\n+++ second\n', {'second': b'old\n'}, 'second'),
        ('index-header-fallback', b'Index: data\n--- missing\n+++ absent\n', {'data': b'old\n'}, 'data'),
    ]:
        yield case(name, ['-s', '-p', '0'],
                   stdin=headers+b'@@ -1 +1 @@\n-old\n+new\n', input_files=files,
                   files=dict(files, **{changed: b'new\n'}),
                   clauses=['Filename Determination', 'Patch File Format', 'OUTPUT FILES'])
    yield case('indented-normal', ['-s', 'data'],
               stdin=b''.join(b' \t'+line for line in delta.splitlines(keepends=True)),
               clauses=['Patch File Format', 'OUTPUT FILES'])
    yield case('output-multiple-versions', ['-s', '-o', 'result', '-p', '0'],
               stdin=b'--- data\n+++ data\n@@ -1 +1 @@\n-old\n+middle\n'
                     b'--- data\n+++ data\n@@ -1 +1 @@\n-middle\n+new\n',
               files={'data': b'old\n', 'result': b'middle\nnew\n'})
    yield case('output-interleaved-versions', ['-s', '-o', 'result', '-p', '0'],
               input_files={'one': b'a\n', 'two': b'b\n'},
               stdin=b'--- one\n+++ one\n@@ -1 +1 @@\n-a\n+A\n'
                     b'--- two\n+++ two\n@@ -1 +1 @@\n-b\n+B\n'
                     b'--- one\n+++ one\n@@ -1 +1 @@\n-A\n+last\n',
               files={'one': b'a\n', 'two': b'b\n', 'result': b'A\nB\nlast\n'})
    yield case('output-empty-intermediate', ['-s', '-o', 'result', '-p', '0'],
               stdin=b'--- data\n+++ data\n@@ -1 +0,0 @@\n-old\n'
                     b'--- data\n+++ data\n@@ -0,0 +1 @@\n+new\n',
               files={'data': b'old\n', 'result': b'new\n'})
    yield case('output-ed-versions', ['-s', '-e', '-o', 'result', 'data'],
               stdin=b'1c\nmiddle\n.\nIndex: data\n1c\nnew\n.\n',
               files={'data': b'old\n', 'result': b'middle\nnew\n'})
