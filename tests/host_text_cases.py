"""CSH-073 independent POSIX.1-2024 text/byte oracles (never vendor output)."""
BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'
UTILITIES = tuple('cat cksum cmp comm csplit cut diff expand fold head join od paste pr sed sort split strings tail tee tr tsort unexpand uniq wc'.split())


def crc(data):
    """Polynomial long division, including little-endian length, per cksum."""
    length = len(data)
    suffix = bytearray()
    while length:
        suffix.append(length & 255)
        length >>= 8
    value = 0
    for byte in data + suffix:
        value ^= byte << 24
        for _ in range(8):
            value = ((value << 1) ^ (0x04c11db7 if value & 0x80000000 else 0)) & 0xffffffff
    return value ^ 0xffffffff


def case(tool, name, args=(), data=b'', out=b'', status=0, err=b'', **kw):
    return dict(id=tool + '/' + name, utility=tool, args=list(args), input=data,
                stdout=out, stderr=err, status=status, source=BASE + tool + '.html', **kw)


def cases(utf8=None, audit=False):
    from host_text_extended import cases as extended_cases
    yield from extended_cases()
    binary = bytes(range(256))
    lines = b'one\ntwo\nthree\n'
    yield case('cat', 'bytes', data=binary, out=binary)
    yield case('cat', 'ordered-stdin', ['first', '-', 'last', '-'], data=b'input\n', out=b'first\ninput\nlast\n', inputs={'first': b'first\n', 'last': b'last\n'})
    yield case('cat', 'unbuffered', ['-u'], data=binary, out=binary)
    for name, data in [('empty', b''), ('text', b'123456789'), ('all-bytes', binary * 3)]:
        yield case('cksum', name, data=data, out=f'{crc(data)} {len(data)}\n'.encode())
    yield case('cksum', 'files', ['a', 'b'], inputs={'a': b'', 'b': binary}, out=f'{crc(b"")} 0 a\n{crc(binary)} 256 b\n'.encode())
    yield case('cmp', 'equal', ['-', 'a'], data=binary, inputs={'a': binary})
    yield case('cmp', 'silent-difference', ['-s', 'a', 'b'], inputs={'a': b'aa', 'b': b'ab'}, status=1)
    yield case('cmp', 'eof', ['a', 'b'], inputs={'a': b'a', 'b': b'ab'}, status=1, stderr_re=rb'cmp: EOF on a(?:[ \t][^\n]*)?\n')
    yield case('cmp', 'large-offset', ['-l', 'a', 'b'], sparse=True, status=1, stdout_re=rb'[ \t]*2147483649[ \t]+130[ \t]+131\n')
    for suppress in ('', '1', '2', '3', '12', '13', '23', '123'):
        rows = [(0, b'a'), (2, b'b'), (1, b'c')]
        out = b''.join(b'\t' * sum(str(i+1) not in suppress for i in range(column)) + word + b'\n' for column, word in rows if str(column+1) not in suppress)
        yield case('comm', 'columns-' + (suppress or 'all'), (['-' + suppress] if suppress else []) + ['a', 'b'], inputs={'a': b'a\nb\n', 'b': b'b\nc\n'}, out=out)
    yield case('csplit', 'line', ['data', '3'], inputs={'data': lines}, out=b'8\n6\n', files={'xx00': b'one\ntwo\n', 'xx01': b'three\n'}, products='xx*')
    yield case('csplit', 'regex-prefix', ['-s', '-f', 'part', '-n', '3', 'data', '/two/'], inputs={'data': lines}, files={'part000': b'one\n', 'part001': b'two\nthree\n'}, products='part*')
    yield case('csplit', 'discard', ['-s', 'data', '%two%'], inputs={'data': lines}, files={'xx00': b'two\nthree\n'}, products='xx*')
    yield case('csplit', 'cleanup', ['-s', 'data', '2', '99'], inputs={'data': lines}, status='nonzero', err='nonempty', files={}, products='xx*')
    yield case('csplit', 'keep', ['-ks', 'data', '2', '99'], inputs={'data': lines}, status='nonzero', err='nonempty', files={'xx00': b'one\n'})
    for flag in ('-b', '-c'):
        yield case('cut', flag[1:]+'-overlap', [flag, '4-,1-2,2'], data=b'abcdef\nxy\n', out=b'abdef\nxy\n')
    yield case('cut', 'fields', ['-d', ':', '-f', '3,1'], data=b'a:b:c\nplain\nx:y\n', out=b'a:c\nplain\nx\n')
    yield case('cut', 'suppress', ['-s', '-f', '2'], data=b'a\tb\nplain\n', out=b'b\n')
    yield case('diff', 'equal', ['a', 'b'], inputs={'a': lines, 'b': lines})
    yield case('diff', 'normal', ['a', 'b'], inputs={'a': b'a\nb\n', 'b': b'a\nc\n'}, out=b'2c2\n< b\n---\n> c\n', status=1)
    yield case('diff', 'ed', ['-e', 'a', 'b'], inputs={'a': b'a\nb\n', 'b': b'a\nc\n'}, out=b'2c\nc\n.\n', status=1)
    yield case('diff', 'forward', ['-f', 'a', 'b'], inputs={'a': b'a\nb\n', 'b': b'a\nc\n'}, out=b'c2\nc\n.\n', status=1)
    yield case('diff', 'blanks', ['-b', 'a', 'b'], inputs={'a': b'a b \n', 'b': b'a\t b\n'})
    yield case('expand', 'default', data=b'a\tb\n', out=b'a       b\n')
    yield case('expand', 'stops', ['-t', '4,6'], data=b'a\tb\tc\td\n', out=b'a   b c d\n')
    yield case('expand', 'backspace', ['-t', '4'], data=b'ab\b\tc\n', out=b'ab\b   c\n')
    yield case('fold', 'default', data=b'x'*81+b'\n', out=b'x'*80+b'\nx\n')
    yield case('fold', 'bytes', ['-b', '-w', '3'], data=b'ab\tcde\n', out=b'ab\t\ncde\n')
    yield case('fold', 'spaces', ['-s', '-w', '5'], data=b'ab cd ef\n', out=b'ab \ncd ef\n')
    yield case('fold', 'carriage', ['-w', '3'], data=b'abc\rde\n', out=b'abc\rde\n')
    yield case('head', 'default', data=b''.join(f'{i}\n'.encode() for i in range(12)), out=b''.join(f'{i}\n'.encode() for i in range(10)))
    yield case('head', 'lines', ['-n', '2'], data=lines, out=b'one\ntwo\n')
    yield case('head', 'bytes', ['-c', '3'], data=binary, out=binary[:3])
    yield case('head', 'large-count', ['-n', '2147483647'], data=lines, out=lines)
    yield case('head', 'files', ['-n', '1', 'a', 'b'], inputs={'a': lines, 'b': b'last\n'}, out=b'==> a <==\none\n\n==> b <==\nlast\n')
    yield case('join', 'default', ['a', 'b'], inputs={'a': b'a A\nb B\n', 'b': b'a X\nc Y\n'}, out=b'a A X\n')
    yield case('join', 'unpaired', ['-a', '1', '-a', '2', 'a', 'b'], inputs={'a': b'a A\nb B\n', 'b': b'a X\nc Y\n'}, out=b'a A X\nb B\nc Y\n')
    yield case('join', 'fields', ['-t', ':', '-1', '2', '-2', '1', '-o', '1.1,2.2', 'a', 'b'], inputs={'a': b'A:a\n', 'b': b'a:X\n'}, out=b'A:X\n')
    # od explicitly allows blank separation, implementation-selected line width,
    # and an optional final empty line with -A n. No other output is ignored.
    yield case('od', 'octets', ['-A', 'n', '-t', 'u1', '-v'], data=binary, numbers=list(range(256)))
    yield case('od', 'skip-count', ['-A', 'n', '-t', 'u1', '-j', '3', '-N', '4'], data=binary, numbers=[3,4,5,6])
    yield case('paste', 'parallel', ['a', 'b'], inputs={'a': b'a\nb\n', 'b': b'c\n'}, out=b'a\tc\nb\t\n')
    yield case('paste', 'serial-delimiters', ['-s', '-d', ',:', 'a'], inputs={'a': b'a\nb\nc\nd\n'}, out=b'a,b:c,d\n')
    yield case('paste', 'stdin-twice', ['-', '-'], data=b'a\nb\nc\nd\n', out=b'a\tb\nc\td\n')
    yield case('pr', 'no-header', ['-t'], data=lines, out=lines)
    yield case('pr', 'double-space', ['-t', '-d'], data=b'a\nb\n', out=b'a\n\nb\n\n')
    yield case('pr', 'numbered', ['-t', '-n:2'], data=b'a\nb\n', out=b' 1:a\n 2:b\n')
    for name, script, data, out in [
        ('substitution', 's/\\([a-z]\\)\\1/[\\1]/g', b'aabbc\n', b'[a][b]c\n'),
        ('hold', 'h;s/one/ONE/;G', b'one\n', b'ONE\none\n'),
        ('range', '2,3d', b'1\n2\n3\n4\n', b'1\n4\n'),
        ('translate', 'y/abc/ABC/', b'abc\n', b'ABC\n'),
        ('pattern-next', 'N;s/\\n/:/', b'a\nb\n', b'a:b\n'),
        ('branch', 's/a/A/\nt end\ns/b/B/\n:end', b'a\nb\n', b'A\nB\n')]:
        yield case('sed', name, [script], data=data, out=out)
    yield case('sed', 'script-file', ['-n', '-f', 'program'], data=lines, inputs={'program': b'2p\n'}, out=b'two\n')
    for name,args,data,out in [
        ('default',[],b'b\na\nc\n',b'a\nb\nc\n'),
        ('numeric',['-n'],b'10\n-2\n3\n',b'-2\n3\n10\n'),
        ('reverse',['-r'],b'a\nc\nb\n',b'c\nb\na\n'),
        ('unique',['-u'],b'b\na\nb\n',b'a\nb\n'),
        ('key',['-t',':','-k','2,2n'],b'a:10\nb:2\n',b'b:2\na:10\n'),
        ('fold',['-f'],b'b\nA\n',b'A\nb\n')]:
        yield case('sort',name,args,data=data,out=out)
    yield case('sort', 'check', ['-c'], data=b'b\na\n', status=1, err='nonempty')
    yield case('sort', 'merge-output', ['-m', '-o', 'out', 'a', 'b'], inputs={'a': b'a\nc\n', 'b': b'b\nd\n'}, files={'out': b'a\nb\nc\nd\n'})
    yield case('split', 'lines', ['-l', '2'], data=lines, files={'xaa': b'one\ntwo\n', 'xab': b'three\n'}, products='x*')
    yield case('split', 'bytes', ['-b', '3', '-a', '1', '-', 'p'], data=b'abcdefg', files={'pa': b'abc', 'pb': b'def', 'pc': b'g'}, products='p*')
    yield case('split', 'empty', data=b'', files={}, products='x*')
    yield case('split', 'exhausted-suffix', ['-b', '1', '-a', '1', '-', 'p'], data=b'x'*27, status='nonzero', err='nonempty', files={'p'+chr(97+i): b'x' for i in range(26)}, products='p*')
    yield case('strings', 'all', ['-a', 'data'], inputs={'data': b'\0abc\0hello\0world\n'}, out=b'hello\nworld\n')
    yield case('strings', 'length', ['-a', '-n', '3', 'data'], inputs={'data': b'\0ab\0abc\0abcd\n'}, out=b'abc\nabcd\n')
    yield case('tail', 'lines', ['-n', '2'], data=lines, out=b'two\nthree\n')
    yield case('tail', 'from-start', ['-n', '+2'], data=lines, out=b'two\nthree\n')
    yield case('tail', 'bytes', ['-c', '3'], data=binary, out=binary[-3:])
    yield case('tail', 'zero', ['-c', '0'], data=binary)
    yield case('tail', 'large-offset', ['-c', '+2147483649', 'a'], sparse=True, out=b'X')
    yield case('tee', 'files', ['one', 'two', '-'], data=binary, out=binary, files={'one': binary, 'two': binary, '-': binary})
    yield case('tee', 'append', ['-a', 'out'], data=b'new\n', out=b'new\n', inputs={'out': b'old\n'}, files={'out': b'old\nnew\n'})
    yield case('tee', 'thirteen', ['o'+str(i) for i in range(13)], data=b'x', out=b'x', files={'o'+str(i):b'x' for i in range(13)})
    yield case('tr', 'translate', ['abc', 'XYZ'], data=b'abc cab\n', out=b'XYZ ZXY\n')
    yield case('tr', 'delete', ['-d', '\\000'], data=b'a\0b\0', out=b'ab')
    yield case('tr', 'squeeze', ['-s', 'a'], data=b'aaabbba\n', out=b'abbba\n')
    yield case('tr', 'complement', ['-cd', '[:digit:]'], data=b'a1b23\n', out=b'123')
    yield case('tr', 'class', ['[:lower:]', '[:upper:]'], data=b'Hello\n', out=b'HELLO\n')
    yield case('tr', 'delete-squeeze', ['-ds', 'x', 'a'], data=b'axaxa\n', out=b'a\n')
    yield case('tsort', 'chain', data=b'a b\nb c\nc c\n', out=b'a\nb\nc\n')
    yield case('unexpand', 'leading', data=b'        x        y\n', out=b'\tx        y\n')
    yield case('unexpand', 'all', ['-a'], data=b'        x       y\n', out=b'\tx\ty\n')
    yield case('unexpand', 'stops', ['-t', '4,8'], data=b'    a   b    c\n', out=b'\ta\tb    c\n')
    yield case('uniq', 'adjacent', data=b'a\na\nb\na\n', out=b'a\nb\na\n')
    yield case('uniq', 'duplicates', ['-d'], data=b'a\na\nb\n', out=b'a\n')
    yield case('uniq', 'unique', ['-u'], data=b'a\na\nb\n', out=b'b\n')
    yield case('uniq', 'fields', ['-f', '1'], data=b'x same\ny same\nz different\n', out=b'x same\nz different\n')
    yield case('uniq', 'characters', ['-s', '2'], data=b'xxsame\nyysame\nzzother\n', out=b'xxsame\nzzother\n')
    yield case('uniq', 'output', ['data', 'out'], inputs={'data': b'a\na\n'}, files={'out': b'a\n'})
    # XBD 5 permits field widths in numeric printf-style output formats.
    yield case('wc', 'counts', data=b'one two\nthree', stdout_re=rb'[ \t]*1[ \t]+3[ \t]+13\n')
    yield case('wc', 'bytes', ['-c'], data=binary, stdout_re=rb'[ \t]*256\n')
    yield case('wc', 'lines', ['-l'], data=b'a\nb', stdout_re=rb'[ \t]*1\n')
    yield case('wc', 'totals', ['-l', 'a', 'b'], inputs={'a': b'a\n', 'b': b'b\nc\n'}, stdout_re=rb'[ \t]*1 a\n[ \t]*2 b\n[ \t]*3 total\n')
    if utf8:
        env={'LC_ALL':utf8}
        yield case('sed', 'utf8-class-repeat', ['s/[[:alpha:]]\\{2\\}/X/g'], data='éa12\n'.encode(), out=b'X12\n', env=env)
        yield case('wc', 'utf8-characters', ['-m'], data='é界\n'.encode(), stdout_re=rb'[ \t]*3\n', env=env)
    # Required Issue 8/provider contracts kept strict in an explicit audit.
    if audit:
        yield case('head', 'beyond-int32', ['-n', '2147483648'], data=lines, out=lines)
        yield case('tail', 'reverse-required', ['-r'], data=lines, out=b'three\ntwo\none\n')
        yield case('tail', 'reverse-count-required', ['-r', '-n', '2'], data=lines, out=b'three\ntwo\n')
        yield case('tail', 'reverse-zero-required', ['-r', '-n', '0'], data=lines, out=b'')
        from host_text_extended import repeat
        yield case('tail', 'reverse-large-required', ['-r', 'input'], stdout_file='result',
                   generated_inputs={'input': [repeat(b'first\n', 1), repeat(b'middle\n', 20000), repeat(b'last\n', 1)]},
                   generated_files={'result': [repeat(b'last\n', 1), repeat(b'middle\n', 20000), repeat(b'first\n', 1)]})
        yield case('tsort', 'acyclic-w-required', ['-w'], data=b'a b\nb c\n', out=b'a\nb\nc\n')
        yield case('tsort', 'cycle-count-required', ['-w'], data=b'a b\nb a\n', status=1, err='nonempty', stdout_re=rb'(?:a\nb\n|b\na\n)')
        yield case('cmp', 'default-format', ['a','b'], inputs={'a':b'a\n','b':b'b\n'}, out=b'a b differ: char 1, line 1\n', status=1)
        if utf8:
            yield case('sed', 'utf8-backreference', [r's/\(.\)\1/[\1]/g'], data='éé界界\n'.encode(), out='[é][界]\n'.encode(), env={'LC_ALL':utf8})
            yield case('cut', 'utf8-characters-required', ['-c','2'], data='é界x\n'.encode(), out='界\n'.encode(), env={'LC_ALL':utf8})
            yield case('cut', 'utf8-no-split-required', ['-b','1','-n'], data='éx\n'.encode(), out=b'\n', env={'LC_ALL':utf8})
            yield case('cut', 'utf8-character-ranges-required', ['-c','1,3-4'],
                       data='é界e\u0301z\n'.encode(), out='ée\u0301\n'.encode(), env={'LC_ALL':utf8})
            yield case('cut', 'utf8-byte-end-required', ['-b','2','-n'],
                       data='é界x\n'.encode(), out='é\n'.encode(), env={'LC_ALL':utf8})
            yield case('cut', 'utf8-byte-range-required', ['-b','4-6','-n'],
                       data='é界x\n'.encode(), out='界x\n'.encode(), env={'LC_ALL':utf8})
    # Missing-file consequences for every utility with input file operands;
    # tr has none and tee's operands are outputs.
    args={'cmp':['missing','other'], 'comm':['missing','other'], 'csplit':['missing','2'], 'cut':['-b','1','missing'], 'diff':['missing','other'], 'join':['missing','other'], 'sed':['p','missing']}
    for tool in UTILITIES:
        if tool in ('tr','tee'):
            continue
        yield case(tool,'missing-input',args.get(tool,['missing']), status='error' if tool in ('cmp','diff') else 'nonzero', err='nonempty')
    yield case('tee','output-error',['absent/out'],data=b'data\n',out=b'data\n',status='nonzero',err='nonempty')
