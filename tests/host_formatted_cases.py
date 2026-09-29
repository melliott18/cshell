"""CSH-070 independent finite oracles for the selected provider contracts.

No expected byte is obtained by invoking printf or echo. The tables cover
interactions beyond CSH-060; declarations in docs/host-formatted-output.md
separate requirements, optional conversions and implementation policies.
"""

def cases(catalogs):
    def row(name, utility, argv, out=b'', status=0, err=b'', env=None):
        return dict(name=name, utility=utility, argv=argv, stdout=out,
                    status=status, stderr=err, env=env or {})

    matrix = [('%+08.5d', '-12', '  -00012'), ('% 08.5i', '012', '   00010'),
              ('%-#8.4x', '31', '0x001f  '), ('%#08X', '31', '0X00001F'),
              ('%-#8.4o', '10', '0012    '), ('%08.5u', '12', '   00012'),
              ('%#.0x', '0', ''), ('%#.0X', '0', ''), ('%#.0o', '0', '0'),
              ('%+d', '+0x10', '+16'), ('%i', '-010', '-8'),
              ('%-7.3s', 'abcdef', 'abc    '), ('%7.3b', r'a\000bcd', '    a\0b'),
              ('%-7.3b', r'a\000bcd', 'a\0b    '), ('%3c', 'word', '  w'),
              ('%#.0f', '1.5', '2.'), ('%+010.2f', '-1.5', '-000001.50'),
              ('%.2e', '1.5', '1.50e+00'), ('%.2E', '1.5', '1.50E+00'),
              ('%#.4g', '1.5', '1.500'), ('%#.4G', '1.5', '1.500'),
              ('%.2F', '1.5', '1.50'), ('%.1a', '1.5', '0x1.8p+0'),
              ('%.1A', '1.5', '0X1.8P+0')]
    for fmt, operand, expected in matrix:
        yield row('format ' + fmt, 'printf', ['[' + fmt + ']', operand],
                  ('[' + expected + ']').encode())
    for name, argv, expected in [
        ('numbered gaps reuse', ['%3$s:%1$04d:%3$s%%|', '7', 'unused', 'a', '8', 'unused', 'b'], b'a:0007:a%|b:0008:b%|'),
        ('numbered binary', ['%2$5.3b:%1$s|', 'x', r'a\000bz', 'y', r'c\000dz'], b'  a\0b:x|  c\0d:y|'),
        ('missing values', ['[%d][%u][%o][%x][%b][%s][%c][%.1f]'], b'[0][0][0][0][][][][0.0]'),
        ('b stop before precision', ['%.8bTAIL%s', r'ab\cignored', 'unused'], b'ab'),
        ('octal lengths', [r'\1\12\1234:%b', r'\0\01\012\01234'], b'\x01\nS4:\0\x01\nS4'),
        ('literal spaces', [' a  %s %% ', 'b'], b' a  b % '),
        ('options delimiter', ['--', '-%s', '-n'], b'--n'),
        ('signed limits', ['%d:%d', '9223372036854775807', '-9223372036854775808'], b'9223372036854775807:-9223372036854775808'),
        ('unsigned limit', ['%u', '18446744073709551615'], b'18446744073709551615'),
    ]:
        yield row(name, 'printf', argv, expected)
    for operand, expected, diagnostic in [
        ('invalid', b'0', 'invalid: expected numeric value'),
        ('12x', b'12', '12x: not completely converted'),
        ("'Aextra", b'65', "'Aextra: not completely converted"),
    ]:
        yield row('integer diagnostic ' + operand, 'printf', ['%d:%s', operand, 'after'],
                  expected + b':after', 1, ('{program}: ' + diagnostic + '\n').encode())
    yield row('float follows strtod', 'printf', ['%.1f:%s', "'A", 'after'], b'0.0:after', 1,
              b"{program}: 'A: expected numeric value\n")
    for lang, locale, diagnostic in [('fr', 'fr_FR.UTF-8', '12x : conversion incomplète'),
                                      ('de', 'de_DE.UTF-8', '12x: unvollständige Konvertierung')]:
        for precedence, env in [
            ('all', dict(LC_ALL=locale, LANG='C', LC_MESSAGES='C', LC_NUMERIC='C')),
            ('categories', dict(LC_ALL='', LANG='C', LC_MESSAGES=locale, LC_NUMERIC=locale)),
            ('lang', dict(LC_ALL='', LANG=locale, LC_MESSAGES='', LC_NUMERIC=''))]:
            env['NLSPATH'] = str(catalogs / (lang + '.cat'))
            yield row('catalog ' + lang + ' ' + precedence, 'printf', ['%d:%.2f', '12x', '1,5'],
                      b'12:1,50', 1, ('{program}: ' + diagnostic + '\n').encode(), env)
        yield row('catalog missing ' + lang, 'printf', ['%d', '12x'], b'12', 1,
                  b'{program}: 12x: not completely converted\n',
                  dict(LC_ALL=locale, NLSPATH=str(catalogs / 'missing.cat')))
        yield row('ctype ' + lang, 'printf', ['%d:[%.1s][%c]', "'é", 'é', 'é'],
                  b'233:[\xc3][\xc3]', env=dict(LC_ALL=locale))
    yield row('locale override C', 'printf', ['%.2f', '1.5'], b'1.50',
              env=dict(LC_ALL='C', LC_NUMERIC='fr_FR.UTF-8', LANG='de_DE.UTF-8'))
    for argv in ([], [''], ['', 'a', 'two words'], ['--', '-n'], ['-n', 'x'],
                 ['-e', r'a\nb'], ['-E', r'a\nb'], ['-ne', r'a\cb'],
                 [r'\0\0101\a\b\f\n\r\t\v\\'], ['é', '中']):
        for posix in ('', '1'):
            yield row('literal echo ' + repr(argv) + ' POSIXLY_CORRECT=' + posix,
                      'echo', argv, (' '.join(argv) + '\n').encode(),
                      env={'POSIXLY_CORRECT': posix})
