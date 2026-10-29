"""CSH-105: default integer widths and required numeric keyword aliases.

The selected provider documents d/u as native int/unsigned int. POSIX requires
byte/short/long to mean dC/dS/dL. Native ABI widths and authored integer bytes
supply expectations independently of file/libmagic; no output is an oracle.
"""
import ctypes
import sys

from host_filesystem_cases import case

TYPES = [('d', ctypes.c_int, True), ('u', ctypes.c_uint, False),
         ('byte', ctypes.c_byte, True), ('short', ctypes.c_short, True),
         ('long', ctypes.c_long, True)]
PREFIX = b'CSH105'


def witness(name, kind, payload, predicate, matches, placement, **facts):
    rule = f'6\t{kind}\t{predicate}\tmatched\n'.encode()
    fallback = b'0\tstring\tCSH105\tfixture\n'
    if placement == 'continuation':
        magic = fallback + b'>' + rule
        message = b'fixture' + (b' matched' if matches else b'')
    else:
        magic = rule + fallback
        message = b'matched' if matches else b'fixture'
    files = dict(magic=magic, sample=PREFIX + payload)
    return case('file', 'magic-defaults-' + name + '-' + placement,
                ['-m', 'magic', 'sample'], ticket='CSH-105', files=files,
                out=b'sample: ' + message + b'\n',
                effects={key: dict(type='file', content=data) for key, data in files.items()},
                magic_environment=dict(kind=kind, offset=len(PREFIX), matches=matches,
                                       predicate=predicate, placement=placement, **facts))


def cases():
    for kind, ctype, signed in TYPES:
        width = ctypes.sizeof(ctype)
        high = 1 << (width * 8 - 1)
        minimum, maximum = (-high, high - 1) if signed else (0, 2 * high - 1)
        number = str if signed else hex
        predicates = [
            ('minimum', '', '=' + number(minimum), minimum, minimum + 1),
            ('maximum', '', '=' + number(maximum), maximum, maximum - 1),
            ('less', '', '<' + number(0 if signed else high),
             -1 if signed else high - 1, 0 if signed else high),
            ('greater', '', '>' + number(0 if signed else high - 1),
             1 if signed else high, 0 if signed else high - 1),
            ('mask-hex', '&0x7f', '=127', -1 if signed else maximum,
             -2 if signed else maximum - 1),
            ('mask-octal', '&0177', '=127', -1 if signed else maximum,
             -2 if signed else maximum - 1),
            ('bits-set', '', '&3', -1 if signed else maximum,
             -2 if signed else maximum - 1),
            ('bits-missing', '', '^3', -2 if signed else maximum - 1,
             -1 if signed else maximum),
        ]
        if not signed:
            predicates.append(('maximum-octal', '', '=' + '0' + oct(maximum)[2:],
                               maximum, maximum - 1))
        for placement in ('top', 'continuation'):
            for name, mask, predicate, good, bad in predicates:
                for matches, value in [(True, good), (False, bad)]:
                    yield witness(kind + '-' + name + ('-yes' if matches else '-no'),
                                  kind + mask, value.to_bytes(width, sys.byteorder, signed=signed),
                                  predicate, matches, placement, bytes=width,
                                  signed=signed, value=value)
            # Test every truncation boundary, including zero-filled short fields;
            # neither x nor equality may match the reader's implicit padding.
            for predicate_name, predicate in [('size', 'x'), ('equality', '=0')]:
                for length in range(width + 1):
                    yield witness(kind + '-' + predicate_name + '-length-' + str(length),
                                  kind, bytes(length), predicate, length == width,
                                  placement, bytes=width, signed=signed, available=length)
            # Extra nonzero bytes must not extend the selected integer width.
            for value in (minimum, maximum):
                yield witness(kind + '-trailing-' + str(value), kind,
                              value.to_bytes(width, sys.byteorder, signed=signed) + b'\xa5' * 8,
                              '=' + number(value), True, placement, bytes=width,
                              signed=signed, value=value, trailing=8)
