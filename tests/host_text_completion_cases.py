"""Operand, boundary and layout oracles for previously retained text contracts."""
import sys
from host_text_cases import case


def cases(audit=False):
    for side in (1, 2):
        yield case('comm', 'stdin-'+str(side), ['-' if side == 1 else 'data', '-' if side == 2 else 'data'],
                   data=b'a\nc\n', inputs={'data': b'b\nc\n'},
                   out=(b'a\n\tb\n' if side == 1 else b'\ta\nb\n')+b'\t\tc\n')
        yield case('join', 'stdin-'+str(side), ['-' if side == 1 else 'data', '-' if side == 2 else 'data'],
                   data=b'a A\nb B\n', inputs={'data': b'a X\nc Y\n'},
                   out=b'a A X\n' if side == 1 else b'a X A\n')
    for empty in ('first', 'second', 'both'):
        inputs={'a': b'' if empty in ('first', 'both') else b'a\nb\n',
                'b': b'' if empty in ('second', 'both') else b'x\ny\n'}
        yield case('paste', 'empty-'+empty, ['a', 'b'], inputs=inputs,
                   out={'first': b'\tx\n\ty\n', 'second': b'a\t\nb\t\n', 'both': b''}[empty])
        # Keep the stock-host subset distinct from required-contract audits,
        # as for cut/tsort below. Every repaired audit requires these cases.
        if audit:
            yield case('paste', 'serial-empty-'+empty, ['-s', 'a', 'b'], inputs=inputs,
                       out=(b'\n' if not inputs['a'] else b'a\tb\n')+(b'\n' if not inputs['b'] else b'x\ty\n'))
    yield case('sort', 'same-input-output', ['-o', 'data', 'data'],
               inputs={'data': b'z\na\nm\n'}, files={'data': b'a\nm\nz\n'})
    yield case('sort', 'same-input-merge-output', ['-m', '-o', 'a', 'a', 'b'],
               inputs={'a': b'a\nc\n', 'b': b'b\nd\n'}, files={'a': b'a\nb\nc\nd\n', 'b': b'b\nd\n'})
    yield case('sort', 'fold-key-unique', ['-f', '-u'], data=b'alpha\nALPHA\nbeta\n',
               stdout_re=rb'(?:alpha|ALPHA)\nbeta\n')  # Choice of equal-key representative is unspecified.
    yield case('split', 'default-thousand', ['data'], inputs={'data': b'a\n'*1000+b'last\n'},
               products='x*', files={'xaa': b'a\n'*1000, 'xab': b'last\n'})
    yield case('split', 'kibibyte-units', ['-b', '1k', 'data'], inputs={'data': b'a'*1024+b'last'},
               products='x*', files={'xaa': b'a'*1024, 'xab': b'last'})
    yield case('split', 'empty-input', ['data'], inputs={'data': b''}, products='x*', files={})
    # od uses native byte order for multi-byte values; the input is constructed
    # in that order, rather than adopting any utility's formatted output.
    for width in (1, 2, 4):
        values=[0, 1, (1 << (8*width))-1]
        yield case('od', 'unsigned-'+str(width), ['-A', 'n', '-t', 'u'+str(width)],
                   data=b''.join(v.to_bytes(width, sys.byteorder) for v in values), numbers=values)
    yield case('od', 'partial-element-zero-padding', ['-A', 'n', '-t', 'u4'],
               data=b'\x01\x02\x03', numbers=[int.from_bytes(b'\x01\x02\x03\0', sys.byteorder)])
    yield case('od', 'signed-byte', ['-A', 'n', '-t', 'd1'], data=b'\x80\xff\0\x7f',
               stdout_re=rb'[ \t]*-128[ \t]+-1[ \t]+0[ \t]+127[ \t]*\n(?:\n)?')
    # -v must print every element, independently of implementation line width.
    yield case('od', 'no-repeat-suppression', ['-A', 'n', '-v', '-t', 'u1'],
               data=b'\x07'*64, numbers=[7]*64)
    yield case('pr', 'columns-down', ['-2', '-t', '-l', '3', '-s|'],
               data=b'1\n2\n3\n4\n5\n6\n', out=b'1|4\n2|5\n3|6\n')
    yield case('pr', 'columns-across', ['-2', '-a', '-t', '-l', '3', '-s|'],
               data=b'1\n2\n3\n4\n5\n6\n', out=b'1|2\n3|4\n5|6\n')
    yield case('pr', 'merge-nine-files', ['-m', '-t', '-s|']+[str(i) for i in range(9)],
               inputs={str(i): str(i).encode()+b'\n' for i in range(9)}, out=b'0|1|2|3|4|5|6|7|8\n')
    yield case('pr', 'start-second-page', ['+2', '-t', '-l', '2'],
               data=b'1\n2\n3\n4\n5\n', out=b'3\n4\n5\n')
    yield case('pr', 'short-page-suppresses-header', ['-l', '10'], data=b'one\ntwo\n', out=b'one\ntwo\n')
    yield case('pr', 'custom-tabs-offset', ['-t', '-e@4', '-i#4', '-o', '2'],
               data=b'a@b\n', out=b'  a#  b\n')
    yield case('pr', 'single-column-not-truncated', ['-t', '-w', '2'], data=b'abcdef\n', out=b'abcdef\n')
    yield case('tr', 'octal-longest-sequence', [r'\1012', 'XY'], data=b'A2A\n', out=b'XYX\n')
    yield case('tr', 'C-equivalence-class', ['[=a=]', 'X'], data=b'abcaa\n', out=b'XbcXX\n')
    yield case('unexpand', 'backspace-column', ['-a', '-t', '4'], data=b'ab\b   x\n', out=b'ab\b\tx\n')
    yield case('unexpand', 'tab-stops-exhausted', ['-a', '-t', '4,8'],
               data=b'    x   y    z\n', out=b'\tx\ty    z\n')
