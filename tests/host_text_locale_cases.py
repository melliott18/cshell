"""Character, display-column and whitespace contracts for UTF-8 text."""
from host_text_cases import case


def cases(utf8):
    if not utf8:
        return
    def text(tool, name, args, data, out, **kw):
        return case(tool, 'locale-'+name, args, data=data.encode(), out=out.encode(),
                    env={'LC_ALL': utf8}, **kw)
    yield text('expand', 'wide-tab', ['-t', '4'], '界\tx\n', '界  x\n')
    yield text('expand', 'combining-tab', ['-t', '4'], 'é\tx\n', 'é   x\n')
    yield text('expand', 'wide-backspace', ['-t', '4'], '界\b\tx\n', '界\b   x\n')
    yield text('unexpand', 'wide-tab', ['-a', '-t', '4'], '界  x\n', '界\tx\n')
    yield text('unexpand', 'combining-tab', ['-a', '-t', '4'], 'é   x\n', 'é\tx\n')
    yield text('fold', 'wide-columns', ['-w', '4'], '界界z\n', '界界\nz\n')
    yield text('fold', 'combining-columns', ['-w', '2'], 'éxy\n', 'éx\ny\n')
    # Even byte-count mode must not break inside a character; width >= 3.
    yield text('fold', 'bytes-whole-character', ['-b', '-w', '4'], 'é界z\n', 'é\n界z\n')
    yield text('fold', 'space-boundary', ['-s', '-w', '5'], '界 x y\n', '界 x \ny\n')
    yield text('uniq', 'skip-character', ['-s', '1'], 'éx\n界x\nzx\n', 'éx\n')
    yield text('uniq', 'combining-is-character', ['-s', '2'], 'éx\na界x\n', 'éx\n')
    yield text('uniq', 'skip-field-then-character', ['-f', '1', '-s', '2'], 'a éx\nb 界x\n', 'a éx\n')
    yield text('uniq', 'skip-past-end', ['-s', '9'], 'é\n界x\n', 'é\n')
    for name, data, words, characters in [
        ('ascii-whitespace', 'a\tb\vc\fd\re f\n', 6, 12),
        ('ideographic-space', '界\u3000語\n', 2, 4),
        ('combining-word', 'é 界\n', 2, 5),
    ]:
        yield case('wc', 'locale-'+name, ['-l', '-w', '-m'], data=data.encode(),
                   numbers=[1, words, characters], env={'LC_ALL': utf8})
