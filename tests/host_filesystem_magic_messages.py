"""CSH-103: independently authored printf-style magic message witnesses.

Expected renderings are literal bytes, never produced by printf, Python's
formatter, or the selected provider. Numeric inputs use native signed byte and
short storage; only nonnegative values are used with unsigned conversions.
"""
import struct

from host_filesystem_cases import case

PREFIX = b'CSH103'
NUMBERS = [
    ('decimal', 42, b'%d', b'42'),
    ('integer', -7, b'%i', b'-7'),
    ('negative', -7, b'%d', b'-7'),
    ('plus', 42, b'%+d', b'+42'),
    ('space', 42, b'% d', b' 42'),
    ('right', 42, b'%6d', b'    42'),
    ('left', 42, b'%-6d', b'42    '),
    ('zero-pad', -7, b'%06d', b'-00007'),
    ('precision', 42, b'%.4d', b'0042'),
    ('width-precision', -7, b'%8.4d', b'   -0007'),
    ('zero-precision-zero', 0, b'%.0d', b''),
    ('unsigned', 42, b'%u', b'42'),
    ('octal', 42, b'%o', b'52'),
    ('octal-alternate', 42, b'%#o', b'052'),
    ('octal-zero', 0, b'%#.0o', b'0'),
    ('hex', 42, b'%x', b'2a'),
    ('hex-upper', 42, b'%X', b'2A'),
    ('hex-alternate', 42, b'%#x', b'0x2a'),
    ('hex-upper-alternate', 42, b'%#X', b'0X2A'),
    ('hex-zero-pad', 42, b'%#08x', b'0x00002a'),
    ('character', 65, b'%c', b'A'),
    ('percent', 42, b'%%:%d:%%', b'%:42:%'),
]
STRINGS = [
    ('plain', b'%s', b'Alpha'),
    ('right', b'%8s', b'   Alpha'),
    ('left', b'%-8s', b'Alpha   '),
    ('precision', b'%.3s', b'Alp'),
    ('width-precision', b'%8.3s', b'     Alp'),
    ('left-precision', b'%-8.3s', b'Alp     '),
    ('zero-precision', b'%.0s', b''),
    ('width-zero-precision', b'%4.0s', b'    '),
    ('long-precision', b'%.8s', b'Alpha'),
    ('percent', b'%%:%s:%%', b'%:Alpha:%'),
]


def witness(name, kind, predicate, payload, message, rendered, placement, **facts):
    # Brackets make padding and empty conversions visible. A trailing payload
    # must not leak into the matched string argument.
    offset = 6 if placement == 'continuation' else 0
    prefix = b'0\tstring\tCSH103\tfixture\n' if offset else b''
    rule = (b'>' if offset else b'') + str(offset).encode() + b'\t' + kind
    magic = prefix + rule + b'\t' + predicate + b'\t[' + message + b']\n'
    sample = (PREFIX if offset else b'') + payload
    files = dict(magic=magic, sample=sample)
    return case('file', 'magic-messages-' + name + '-' + placement,
                ['-m', 'magic', 'sample'], ticket='CSH-103', files=files,
                out=b'sample: ' + (b'fixture ' if offset else b'') + b'[' + rendered + b']\n',
                effects={key: dict(type='file', content=data) for key, data in files.items()},
                magic_environment=dict(kind=kind.decode(), offset=offset,
                                       placement=placement, message_hex=message.hex(),
                                       rendered_hex=rendered.hex(), **facts))


def cases():
    for placement in ('top', 'continuation'):
        for kind, fmt in [('byte', 'b'), ('short', 'h')]:
            for name, value, message, rendered in NUMBERS:
                yield witness(kind + '-' + name, kind.encode(), ('=' + str(value)).encode(),
                              struct.pack('@' + fmt, value), message, rendered, placement,
                              value=value, bytes=struct.calcsize('@' + fmt))
        for name, message, rendered in STRINGS:
            yield witness('string-' + name, b'string', b'Alpha', b'AlphaTRAILING',
                          message, rendered, placement, matched_hex=b'Alpha'.hex())
