"""CSH-073 transformation, offset and large-input contracts with authored oracles."""
from host_text_cases import case

MIB = 1024 * 1024


def repeat(pattern, count, suffix=b''):
    return dict(pattern=pattern, repeat=count, suffix=suffix)


def cases():
    # Transformations use independently authored records, not round-trip tests
    # that could let two implementations agree on the same mistake.
    yield case('join', 'duplicate-cross-product', ['a', 'b'],
               inputs={'a': b'k A\nk B\n', 'b': b'k X\nk Y\n'},
               out=b'k A X\nk A Y\nk B X\nk B Y\n', category='transformations')
    yield case('join', 'unpaired-only', ['-v', '1', '-v', '2', 'a', 'b'],
               inputs={'a': b'a A\nb B\n', 'b': b'a X\nc Y\n'},
               out=b'b B\nc Y\n', category='transformations')
    yield case('join', 'empty-selected-field', ['-t', ':', '-a', '1', '-e', 'NA', '-o', '0,1.2,2.2', 'a', 'b'],
               inputs={'a': b'a:A\nb:B\n', 'b': b'a:\n'},
               out=b'a:A:NA\nb:B:NA\n', category='transformations')
    yield case('paste', 'escaped-delimiters', ['-s', '-d', r'\t\0:', 'data'],
               inputs={'data': b'a\nb\nc\nd\ne\n'}, out=b'a\tbc:d\te\n', category='transformations')
    yield case('sort', 'dictionary', ['-d'], data=b'b!\na?\na!\n', out=b'a!\na?\nb!\n', category='transformations')
    yield case('sort', 'numeric-field-reverse', ['-t', ':', '-k', '2,2nr'],
               data=b'a:2\nb:12\nc:-3\n', out=b'b:12\na:2\nc:-3\n', category='transformations')
    yield case('uniq', 'counts', ['-c'], data=b'a\na\nb\na\n',
               stdout_re=rb'[ \t]*2[ \t]+a\n[ \t]*1[ \t]+b\n[ \t]*1[ \t]+a\n', category='transformations')
    yield case('uniq', 'combined-skips', ['-f', '1', '-s', '3'],
               data=b'one xxSAME\ntwo yySAME\nthree zzOTHER\n',
               out=b'one xxSAME\nthree zzOTHER\n', category='transformations')
    yield case('tr', 'octal-byte-range', [r'\000-\003', 'ABCD'], data=b'\0\1\2\3x\n',
               out=b'ABCDx\n', category='transformations')
    yield case('tr', 'repeat-array', ['abc', '[x*3]'], data=b'cab\n', out=b'xxx\n', category='transformations')
    yield case('tr', 'character-complement-C', ['-Cd', '[:digit:]'], data=b'a12:b3\n', out=b'123', category='transformations')
    yield case('sed', 'append-insert-change', ['1i\\\nbefore\n2c\\\nchanged\n3a\\\nafter\n'],
               data=b'a\nb\nc\n', out=b'before\na\nchanged\nc\nafter\n', category='transformations')
    yield case('sed', 'hold-exchange', ['-n', '1h;2{x;G;p;}'], data=b'a\nb\n', out=b'a\nb\n', category='transformations')
    yield case('sed', 'write-read', ['-n', '1w written\n2r extra\n$p'], data=b'a\nb\nc\n',
               inputs={'extra': b'insert\n'}, out=b'insert\nc\n', files={'written': b'a\n'}, category='transformations')
    yield case('sed', 'delete-first-pattern-line', ['-n', 'N;P;D'], data=b'a\nb\nc\n',
               out=b'a\nb\n', category='transformations')
    yield case('fold', 'backspace-column', ['-w', '3'], data=b'ab\bcdx\n', out=b'ab\bcd\nx\n', category='transformations')
    yield case('unexpand', 'existing-tabs', ['-a'], data=b'\t        x\n', out=b'\t\tx\n', category='transformations')

    # Every offset is derived from the constructed bytes, with neither a second
    # host utility nor a vendor output sample involved in the expectation.
    for base, code, first, second in [('decimal', 'd', b'3', b'10'),
                                       ('octal', 'o', b'3', b'12'),
                                       ('hex', 'x', b'3', b'a')]:
        yield case('strings', 'offset-'+base, ['-a', '-n', '4', '-t', code, 'data'],
                   inputs={'data': b'\0\0\0alpha\0\0BETA\0'},
                   stdout_re=rb'[ \t]*0*'+first+rb' alpha\n[ \t]*0*'+second+rb' BETA\n', category='offsets')
    for label, skip in [('decimal', '16'), ('octal', '020'), ('hex', '0x10')]:
        yield case('od', 'skip-'+label, ['-A', 'd', '-t', 'u1', '-j', skip, '-N', '3', 'data'],
                   inputs={'data': bytes(range(32))},
                   stdout_re=rb'0*16[ \t]+16[ \t]+17[ \t]+18[ \t]*\n0*19\n', category='offsets')
    yield case('od', 'concatenated-skip', ['-A', 'n', '-t', 'u1', '-j', '4', '-N', '3', 'a', 'b'],
               inputs={'a': bytes([1, 2, 3]), 'b': bytes([4, 5, 6, 7])}, numbers=[5, 6, 7], category='offsets')
    yield case('od', 'skip-beyond-eof', ['-j', '9', 'data'], inputs={'data': b'abc'},
               status='nonzero', err='nonempty', category='offsets')
    yield case('od', 'sparse-marker', ['-A', 'd', '-t', 'u1', '-j', '2147483648', '-N', '1', 'a'],
               sparse=True, stdout_re=rb'2147483648[ \t]+88[ \t]*\n2147483649\n', category='offsets')
    yield case('cmp', 'byte-line-boundary', ['a', 'b'],
               inputs={'a': b'first\nsecond\nx\n', 'b': b'first\nsecond\ny\n'},
               out=b'a b differ: char 14, line 3\n', category='offsets', status=1)
    yield case('csplit', 'regex-positive-offset', ['-s', 'data', '/mark/+1'],
               inputs={'data': b'a\nmark\nb\nc\n'}, files={'xx00': b'a\nmark\n', 'xx01': b'b\nc\n'}, products='xx*', category='offsets')
    yield case('csplit', 'regex-negative-offset', ['-s', 'data', '/mark/-1'],
               inputs={'data': b'a\nb\nmark\nc\n'}, files={'xx00': b'a\n', 'xx01': b'b\nmark\nc\n'}, products='xx*', category='offsets')
    yield case('csplit', 'line-repetition', ['-s', 'data', '2', '{2}'],
               inputs={'data': b'1\n2\n3\n4\n5\n6\n7\n'},
               files={'xx00': b'1\n', 'xx01': b'2\n3\n', 'xx02': b'4\n5\n', 'xx03': b'6\n7\n'}, products='xx*', category='offsets')
    yield case('tail', 'from-byte', ['-c', '+3'], data=b'abcdef', out=b'cdef', category='offsets')

    # File-backed outputs lift the old 64 KiB capture ceiling without unbounded
    # pipe capture or huge JSON records. Recipes remain independent byte oracles.
    octets = repeat(bytes(range(256)), 32768)  # exactly 8 MiB
    yield case('cat', 'eight-mib-bytes', ['bulk'], generated_inputs={'bulk': octets},
               stdout_file='result', generated_files={'result': octets}, category='large-inputs')
    yield case('tee', 'eight-mib-copies', ['copy'], generated_inputs={'input': octets},
               stdout_file='result', generated_files={'result': octets, 'copy': octets}, category='large-inputs')
    yield case('wc', 'eight-mib-byte-count', ['-c', 'bulk'], generated_inputs={'bulk': octets},
               stdout_re=rb'[ \t]*8388608[ \t]+bulk\n', category='large-inputs')
    long_line = repeat(b'ab', 524288, b'\n')  # 1 MiB plus newline
    yield case('sed', 'mib-pattern-hold-transform', ['h;s/ab/XY/g;G', 'bulk'],
               generated_inputs={'bulk': long_line}, stdout_file='result',
               generated_files={'result': [repeat(b'XY', 524288, b'\n'), long_line]}, category='large-inputs')
    yield case('cut', 'mib-line-tail', ['-b', '1048574-', 'bulk'],
               generated_inputs={'bulk': long_line}, out=b'bab\n', category='large-inputs')
    yield case('tr', 'mib-transform', ['ab', 'XY'], generated_inputs={'input': long_line},
               stdout_file='result', generated_files={'result': repeat(b'XY', 524288, b'\n')}, category='large-inputs')
    yield case('fold', 'mib-byte-fold', ['-b', '-w', '64', 'bulk'],
               generated_inputs={'bulk': long_line}, stdout_file='result',
               generated_files={'result': repeat(b'ab'*32+b'\n', 16384)}, category='large-inputs')
    yield case('head', 'million-lines', ['-n', '1000000', 'bulk'],
               generated_inputs={'bulk': repeat(b'x\n', 1000001)}, stdout_file='result',
               generated_files={'result': repeat(b'x\n', 1000000)}, category='large-inputs')
    yield case('tail', 'large-input-buffer', ['-c', '131072'], generated_inputs={'input': repeat(b'x', 262144, b'end')},
               stdout_file='result', generated_files={'result': repeat(b'x', 131069, b'end')}, category='large-inputs')
    yield case('split', 'mib-units', ['-b', '1m', 'bulk', 'part'], generated_inputs={'bulk': repeat(b'x', 2*MIB, b'last')},
               generated_files={'partaa': repeat(b'x', MIB), 'partab': repeat(b'x', MIB), 'partac': repeat(b'last', 1)}, products='part*', category='large-inputs')
    yield case('sort', 'large-record-order', ['-o', 'result', 'bulk'],
               generated_inputs={'bulk': [repeat(b'b\n', 100000), repeat(b'a\n', 100000)]},
               generated_files={'result': [repeat(b'a\n', 100000), repeat(b'b\n', 100000)]}, category='large-inputs')
    yield case('uniq', 'large-adjacent-run', ['-c', 'bulk'], generated_inputs={'bulk': repeat(b'repeated\n', 200000)},
               stdout_re=rb'[ \t]*200000[ \t]+repeated\n', category='large-inputs')
