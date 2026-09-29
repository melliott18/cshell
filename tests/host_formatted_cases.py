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


def additional_cases(catalogs, catalog_policy):
    """Required conversions and independently declared catalog fallback policy."""
    def row(name, argv, out, status=0, err=b'', env=None):
        return dict(name=name, utility='printf', argv=argv, stdout=out,
                    status=status, stderr=err, env=env or {})

    # Highest consumed argument determines reuse; ordering and repeated indexes
    # must not make the next cycle consume a different operand group.
    for name, argv, out in [
        ('numbered ninth argument reuse', ['%9$s:%1$d|'] +
         ['7', 'unused', 'unused', 'unused', 'unused', 'unused', 'unused', 'unused', 'a'] +
         ['8', 'unused', 'unused', 'unused', 'unused', 'unused', 'unused', 'unused', 'b'], b'a:7|b:8|'),
        ('numbered repeated integer', ['%2$+06d:%2$04x:%1$s|', 'a', '31', 'b', '32'], b'+00031:001f:a|+00032:0020:b|'),
        ('missing numbered selected defaults', ['%3$s:%1$d:%2$s', '7'], b':7:'),
        ('integer sign and base reuse', ['%d:%i:%o:%x:%X:%u|', '-0x10', '+010', '010', '31', '31', '12',
                                         '0', '0', '0', '0', '0', '0'], b'-16:8:10:1f:1F:12|0:0:0:0:0:0|'),
        ('numeric width precision reuse', ['[%+08.4d][%-#8.4x]|', '-12', '31', '0', '0'], b'[   -0012][0x001f  ]|[   +0000][0000    ]|'),
        ('zero precision suppression', ['[%.0d][%.0i][%.0u][%#.0o][%#.0x][%#.0X]', '0', '0', '0', '0', '0', '0'], b'[][][][0][][]'),
        ('binary stop in reused format', ['[%4.3b]:%s|', r'a\000bZ', 'first', r'x\cignored', 'unused'], b'[ a\0b]:first|[   x'),
        ('binary width after zero precision', ['[%4.0b][%-4.2b]', r'a\000b', r'a\000b'], b'[    ][a\0  ]'),
        ('format octal percent literal', [r'\045s:%s', 'value'], b'%s:value'),
        ('float strtod decimal hexadecimal reuse', ['%.2f|', '010', '0x10', '10.1e2', '0x10.1p2'], b'10.00|16.00|1010.00|64.25|'),
        ('float missing numbered selected defaults', ['[%2$.2f][%1$s]', 'x'], b'[0.00][x]'),
    ]:
        yield row(name, argv, out)
    for operand, out, diagnostic in [
        ('09', b'0', '09: not completely converted'),
        ('0xg', b'0', '0xg: not completely converted'),
        ('12u', b'12', '12u: not completely converted'),
        ('"Ztail', b'90', '"Ztail: not completely converted'),
    ]:
        yield row('conversion failure continues ' + operand, ['%d:%s:%d', operand, 'after', '7'],
                  out + b':after:7', 1, ('{program}: ' + diagnostic + '\n').encode())
    yield row('multiple conversion failures continue', ['%d:%d:%s', '12x', 'bad', 'after'],
              b'12:0:after', 1, b'{program}: 12x: not completely converted\n{program}: bad: expected numeric value\n')
    yield row('partial float continues', ['%.2f:%s', '1.5x', 'after'], b'1.50:after', 1,
              b'{program}: 1.5x: not completely converted\n')
    for locale, lang, message in [('fr_FR.UTF-8', 'fr', '12x : conversion incomplète'),
                                   ('de_DE.UTF-8', 'de', '12x: unvollständige Konvertierung')]:
        env = dict(LC_ALL=locale)
        yield row('locale hex float ' + lang, ['%.1a|%.1A', '1,5', '1,5'], b'0x1,8p+0|0X1,8P+0', env=env)
        for suffix, pattern in [
            ('language and name', str(catalogs / '%l' / '%N.cat')),
            ('full locale and name', str(catalogs / '%L' / '%N.cat')),
            ('search missing first', str(catalogs / 'absent.cat') + ':' + str(catalogs / lang / '%N.cat')),
        ]:
            yield row('catalog lookup ' + lang + ' ' + suffix, ['%d:%s', '12x', 'after'], b'12:after', 1,
                      ('{program}: ' + message + '\n').encode(), dict(env, NLSPATH=pattern))
        for invalid in ('empty.cat', 'invalid.cat', 'directory.cat', 'incomplete.cat'):
            # Apple Libc-1592.100.35 nls/FreeBSD/msgcat.c CORRUPT() writes
            # this diagnostic before returning an error. glibc is silent.
            prefix = (b'Message Catalog System: corrupt file.'
                      if catalog_policy == 'darwin' and invalid != 'incomplete.cat' else b'')
            yield row('catalog fallback ' + lang + ' ' + invalid, ['%d:%s', '12x', 'after'], b'12:after', 1,
                      prefix + b'{program}: 12x: not completely converted\n', dict(env, NLSPATH=str(catalogs / invalid)))
        yield row('locale character trailing text ' + lang, ['%d:%s', "'érest", 'after'], b'233:after', 1,
                  ('{program}: ' + ("'érest : conversion incomplète" if lang == 'fr' else "'érest: unvollständige Konvertierung") + '\n').encode(),
                  dict(env, NLSPATH=str(catalogs / lang / '%N.cat')))

    for argv, expected in [
        (['-nneEEn', r'\c', '--'], b'-nneEEn \\c --\n'),
        (['line\nbreak', '\tend\r'], b'line\nbreak \tend\r\n'),
        (["'\"%", '\\', ''], b"'\"% \\ \n"),
    ]:
        yield dict(name='literal echo control bytes ' + repr(argv), utility='echo',
                   argv=argv, stdout=expected, status=0, stderr=b'', env={})
