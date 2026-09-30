"""CSH-076 byte oracles. No selected utility supplies expected bytes."""
from locale_catalog_fixtures import HEADER, MESSAGES, PO, mo_bytes

UTILITIES = ('gencat', 'gettext', 'iconv', 'locale', 'localedef', 'msgfmt', 'ngettext')

def step(utility, args=(), out=b'', status=0, err=b'', **kw):
    return dict(utility=utility, args=list(args), stdout=out, status=status, stderr=err, **kw)


def cases(system):
    def case(name, utility, steps, **kw):
        return dict(name=utility + '/' + name, utility=utility, steps=steps, **kw)

    source = (b'$ comment\n\n$set 1 comment\n$quote "\n'
              b'1 "first  "\n2 \n3 old\n4 delete\n'
              b'5 "tab\\tline\\n\\v\\b\\r\\f\\\\\\101\\12\\1"\n'
              b'6 long\\\nline\n$quote\n7 "literal"\n$set 3\n1 third\n')
    expected = [(1, 1, b'first  '), (1, 2, b''), (1, 5, b'tab\tline\n\v\b\r\f\\A\n\x01'),
                (1, 6, b'longline'), (1, 7, b'"literal"'), (3, 1, b'third')]
    reads = [step('@probe', ['catalog', './out.cat', str(s), str(m)], out)
             for s, m, out in expected]
    yield case('source-grammar', 'gencat', [step('gencat', ['out.cat', 'source'])] + reads,
               files={'source': source})
    yield case('unknown-escape', 'gencat', [step('gencat', ['out.cat', 'source']),
        step('@probe', ['catalog', './out.cat', '1', '1'], b'q')],
        files={'source': b'$set 1\n1 \\q\n'})
    yield case('merge-replace-delete', 'gencat', [step('gencat', ['out.cat', 'source']),
        step('gencat', ['out.cat', 'update', 'extra']),
        step('@probe', ['catalog', './out.cat', '1', '1'], b'first  '),
        step('@probe', ['catalog', './out.cat', '1', '3'], b'new'),
        step('@probe', ['catalog', './out.cat', '1', '4'], b'<missing>'),
        step('@probe', ['catalog', './out.cat', '3', '1'], b'<missing>'),
        step('@probe', ['catalog', './out.cat', '4', '1'], b'fourth')],
        files={'source': source, 'update': b'$set 1\n3 new\n4\n$delset 3\n',
               'extra': b'$set 4\n1 fourth\n'})
    yield case('stdin-stdout', 'gencat', [step('gencat', ['-', '-'], stdin=b'$set 1\n1 pipe\n',
        redirect='out.cat'), step('@probe', ['catalog', './out.cat', '1', '1'], b'pipe')])
    yield case('utf8', 'gencat', [step('gencat', ['out.cat', 'source']),
        step('@probe', ['catalog', './out.cat', '1', '1'], 'café'.encode())],
        files={'source': '$set 1\n1 café\n'.encode()}, env={'LC_ALL': 'fr_FR.UTF-8'})

    # gettext reads independently authored MO files, not msgfmt output.
    catalogs = {'messages/fr_FR.UTF-8/LC_MESSAGES/demo.mo': mo_bytes(MESSAGES),
                'messages/de_DE.UTF-8/LC_MESSAGES/demo.mo': mo_bytes({'': HEADER, 'hello': 'hallo'}),
                'messages/fr_FR.UTF-8/LC_MESSAGES/other.mo': mo_bytes({'': HEADER, 'hello': 'autre'})}
    translated = {'LC_ALL': 'fr_FR.UTF-8', 'TEXTDOMAIN': 'demo', 'TEXTDOMAINDIR': '@ROOT/messages'}
    for name, args, out, overrides in (
        ('environment-domain', ['hello'], b'bonjour', {}),
        ('option-domain', ['-d', 'demo', 'hello'], b'bonjour', {'TEXTDOMAIN': 'other'}),
        ('operand-precedence', ['-d', 'other', 'demo', 'hello'], b'bonjour', {'TEXTDOMAIN': 'absent'}),
        ('missing-domain', ['-d', 'absent', 'hello'], b'hello', {}),
        ('missing-message', ['untranslated'], b'untranslated', {}),
        ('separation', ['-s', '', 'hello', 'cafe'], (HEADER + ' bonjour café\n').encode(), {}),
        ('no-newline', ['-sn', 'hello', 'cafe'], 'bonjour café'.encode(), {}),
        ('literal-escapes', ['-E', 'line\\n'], b'line\\n', {}),
        ('s-default-literal', ['-s', 'line\\n'], b'line\\n\n', {}),
        ('escape-lookup', ['-e', 'line\\n'], b'ligne\n', {}),
        ('c-escapes', ['-e', r'\a\b\f\n\r\t\v\\\"\?\101\12\1\x42'],
         b'\a\b\f\n\r\t\v\\"?A\n\x01B', {}),
        ('end-options', ['--', '-dash'], b'-dash', {}),
        ('LANG', ['hello'], b'bonjour', {'LC_ALL': '', 'LANG': 'fr_FR.UTF-8'}),
        ('LC_MESSAGES', ['hello'], b'hallo', {'LC_ALL': '', 'LANG': 'fr_FR.UTF-8', 'LC_MESSAGES': 'de_DE.UTF-8'}),
        ('LC_ALL-precedence', ['hello'], b'bonjour', {'LC_MESSAGES': 'de_DE.UTF-8', 'LANG': 'de_DE.UTF-8'}),
        ('LANGUAGE', ['hello'], b'hallo', {'LANGUAGE': 'de_DE.UTF-8:fr_FR.UTF-8'}),
        ('C-fallback', ['hello'], b'hello', {'LC_ALL': 'C'}),
        ('output-encoding', ['cafe'], b'caf\xe9', {'LC_ALL': '', 'LANG': 'fr_FR.UTF-8', 'LC_CTYPE': 'fr_FR.ISO8859-1'}),
    ):
        yield case(name, 'gettext', [step('gettext', args, out)], files=catalogs,
                   env=dict(translated, **overrides))
    for n, out in ((0, b'aucun'), (1, b'un'), (2, b'deux'), (3, b'plusieurs'), (101, b'plusieurs')):
        yield case('plural-' + str(n), 'ngettext', [step('ngettext', ['one', 'IGNORED', str(n)], out)],
                   files=catalogs, env=translated)
    for name, args, out in (
        ('option-domain', ['-d', 'demo', 'one', 'many', '2'], b'deux'),
        ('operand-domain', ['-d', 'other', 'demo', 'one', 'many', '1'], b'un'),
        ('missing-singular', ['absent', 'absents', '1'], b'absent'),
        ('missing-plural', ['absent', 'absents', '0'], b'absents'),
        ('literal-escapes', ['-E', 'single\\t', 'plural\\n', '2'], b'plural\\n'),
        ('plural-escapes', ['-e', 'single', r'\x42\101\n', '2'], b'BA\n'),
    ):
        yield case(name, 'ngettext', [step('ngettext', args, out)], files=catalogs, env=translated)

    # PO compilation is checked by Python's independent MO reader, not gettext.
    for name, args, fuzzy in (('output', ['-o', 'out.mo', 'source.po'], False),
                              ('fuzzy', ['-f', '-o', 'out.mo', 'source.po'], True),
                              ('search', ['-D', 'inputs', '-o', 'out.mo', 'source.po'], False),
                              ('suffix', ['-S', '-o', 'out', 'source.po'], False)):
        messages = dict(MESSAGES)
        if fuzzy:
            messages['draft'] = 'brouillon'
        yield case(name, 'msgfmt', [step('msgfmt', args)],
                   files={'source.po': PO, 'inputs/source.po': PO}, mo={'out.mo': messages})
    yield case('domains', 'msgfmt', [step('msgfmt', ['-S', 'source.po'])],
        files={'source.po': b'domain "first"\nmsgid "a"\nmsgstr "A"\ndomain "second"\nmsgid "b"\nmsgstr "B"\ndomain "first"\nmsgid "c"\nmsgstr "C"\n'},
        mo={'first.mo': {'a': 'A', 'c': 'C'}, 'second.mo': {'b': 'B'}})
    yield case('multiple-inputs', 'msgfmt', [step('msgfmt', ['-S', 'one.po', 'two.po'])],
        files={'one.po': b'msgid "a"\nmsgstr "A"\n', 'two.po': b'msgid "b"\nmsgstr "B"\n'},
        mo={'messages.mo': {'a': 'A', 'b': 'B'}})
    for name, content in (
        ('bad-syntax', b'msgid "unterminated\n'),
        ('newline-check', b'msgid "a\\n"\nmsgstr "b"\n'),
        ('format-check', b'#, c-format\nmsgid "%d"\nmsgstr "%s"\n')):
        yield case(name, 'msgfmt', [step('msgfmt', ['-c', '-v', '-o', 'out.mo', 'source.po'],
            status='nonzero', err='nonempty')], files={'source.po': content})

    for name, args, data, out in (
        ('latin1', ['-f', 'ISO-8859-1', '-t', 'UTF-8'], b'caf\xe9\n', b'caf\xc3\xa9\n'),
        ('reverse', ['-f', 'UTF-8', '-t', 'ISO-8859-1'], b'caf\xc3\xa9\n', b'caf\xe9\n'),
        ('gb18030', ['-f', 'UTF-8', '-t', 'GB18030'], '中国\n'.encode(), b'\xd6\xd0\xb9\xfa\n'),
        ('gb18030-reverse', ['-f', 'GB18030', '-t', 'UTF-8'], b'\xd6\xd0\xb9\xfa\n', '中国\n'.encode()),
        ('stdin-dash', ['-f', 'UTF-8', '-t', 'UTF-8', '-'], b'hello\n', b'hello\n'),
        ('empty', ['-f', 'UTF-8', '-t', 'UTF-8'], b'', b''),
    ):
        yield case(name, 'iconv', [step('iconv', args, out, stdin=data)])
    yield case('ordered-files', 'iconv', [step('iconv', ['-f', 'ISO-8859-1', '-t', 'UTF-8', 'a', 'b'],
        b'caf\xc3\xa9\nend\n')], files={'a': b'caf\xe9\n', 'b': b'end\n'})
    for option in ('-f', '-t'):
        yield case('locale-default-' + option, 'iconv', [step('iconv', [option, 'UTF-8'],
            'café\n'.encode(), stdin='café\n'.encode())], env={'LC_ALL': 'fr_FR.UTF-8'})
    yield case('list', 'iconv', [step('iconv', ['-l'], out='codesets')])
    # Invalid-character policy is vendor-specific; require -c/-s not to change status.
    yield case('invalid-policy', 'iconv', [step('iconv', ['-f', 'UTF-8', '-t', 'UTF-8'] + flags,
        out=b'ab\n' if '-c' in flags else b'a', status='nonzero',
        err=b'' if '-s' in flags else 'nonempty', stdin=b'a\xffb\n')
        for flags in ([], ['-s'], ['-c'], ['-c', '-s'])])

    for name, args, out in (
        ('keyword', ['decimal_point'], b'.\n'),
        ('named-keyword', ['-k', 'decimal_point'], b'decimal_point="."\n'),
        ('category-keyword', ['-c', 'decimal_point'], b'LC_NUMERIC\n.\n'),
        ('both-options', ['-ck', 'decimal_point'], b'LC_NUMERIC\ndecimal_point="."\n'),
        ('operand-order', ['decimal_point', 'thousands_sep'], b'.\n\n'),
        ('list', ['-a'], 'locales'),
        ('charmaps', ['-m'], 'charmaps'),
        ('environment', [], 'locale-environment'),
    ):
        yield case(name, 'locale', [step('locale', args, out)])
    for env_name, env in (
        ('LANG', {'LC_ALL': '', 'LANG': 'fr_FR.UTF-8'}),
        ('category', {'LC_ALL': '', 'LANG': 'C', 'LC_NUMERIC': 'de_DE.UTF-8'}),
        ('LC_ALL', {'LC_ALL': 'fr_FR.UTF-8', 'LANG': 'C', 'LC_NUMERIC': 'C'}),
    ):
        yield case(env_name, 'locale', [step('locale', ['-k', 'decimal_point'], b'decimal_point=","\n')], env=env)

    # Linux locale sources ship in the locales package. All output stays private.
    if system == 'Linux':
        for source, encoding, point in (('fr_FR', 'UTF-8', ','), ('de_DE', 'UTF-8', ','),
                                        ('en_US', 'UTF-8', '.'), ('zh_CN', 'GB18030', '.')):
            yield case('private-' + source, 'localedef', [
                step('localedef', ['-i', source, '-f', encoding, '@ROOT/private'], out='any', timeout=30),
                step('@probe', ['locale', 'private'], f'{encoding}\n{point}\n'.encode())], env={'LOCPATH': '@ROOT'})
        yield case('stdin-source', 'localedef', [step('localedef', ['-f', 'UTF-8', '@ROOT/private'],
            out='any', stdin_from='/usr/share/i18n/locales/en_US', timeout=30),
            step('@probe', ['locale', 'private'], b'UTF-8\n.\n')], env={'LOCPATH': '@ROOT'})
        yield case('error-no-output', 'localedef', [step('localedef', ['-f', 'UTF-8', '-i', 'absent', '@ROOT/private'],
            status='greater3', err='nonempty')], no_output='private')

    # Base defaults: argument errors, missing files, actual exec in every mode.
    invalid = {'gencat': ['-Z'], 'gettext': ['-d'], 'ngettext': ['one'], 'msgfmt': ['-o'],
               'iconv': ['-f'], 'locale': ['-Z'], 'localedef': ['-i']}
    for utility, args in invalid.items():
        yield case('usage-error', utility, [step(utility, args, status='nonzero', err='nonempty')])
    for utility, args in (
        ('gencat', ['out.cat', 'absent']), ('msgfmt', ['-o', 'out.mo', 'absent']),
        ('iconv', ['-f', 'UTF-8', '-t', 'UTF-8', 'absent'])):
        yield case('missing-file', utility, [step(utility, args, status='nonzero', err='nonempty')])
