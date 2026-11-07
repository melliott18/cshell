"""CSH-104: portable native signed/unsigned numeric magic type witnesses.

The C ABI supplies widths; Python integer arithmetic supplies independent
comparison oracles. Literal messages avoid coupling type tests to printf.
Each predicate has a matching and nonmatching sample in a private database.
"""
import ctypes
import sys

from host_filesystem_cases import case

TYPES = [('C', ctypes.c_byte), ('S', ctypes.c_short),
         ('I', ctypes.c_int), ('L', ctypes.c_long)]
PREFIX = b'CSH104'


def witness(name, kind, payload, predicate, matches, **facts):
    magic = (b'0\tstring\tCSH104\tfixture\n>6\t' + kind.encode() + b'\t' +
             predicate.encode() + b'\tmatched\n')
    files = dict(magic=magic, sample=PREFIX + payload)
    return case('file', 'magic-types-' + name, ['-m', 'magic', 'sample'],
                ticket='CSH-104', files=files,
                out=b'sample: fixture' + (b' matched' if matches else b'') + b'\n',
                effects={key: dict(type='file', content=data) for key, data in files.items()},
                magic_environment=dict(kind=kind, offset=len(PREFIX), matches=matches,
                                       predicate=predicate, **facts))


def cases():
    for letter, ctype in TYPES:
        width = ctypes.sizeof(ctype)
        for signed in (True, False):
            high = 1 << (width * 8 - 1)
            minimum, maximum = (-high, high - 1) if signed else (0, 2 * high - 1)
            # Hex/octal constants cover the full unsigned range without
            # depending on conversion of an out-of-range signed decimal.
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
            for spelling, suffix in [('native', letter), ('bytes', str(width))]:
                kind = ('d' if signed else 'u') + suffix
                stem = ('signed-' if signed else 'unsigned-') + letter + '-' + spelling
                for name, mask, predicate, good, bad in predicates:
                    for matches, value in [(True, good), (False, bad)]:
                        yield witness(stem + '-' + name + ('-yes' if matches else '-no'),
                                      kind + mask, value.to_bytes(width, sys.byteorder, signed=signed),
                                      predicate, matches, c_type=letter, bytes=width,
                                      signed=signed, value=value)
                # Both x and equality must reject incomplete values, including
                # zero-filled prefixes that a padded read could falsely match.
                for predicate_name, predicate in [('size', 'x'), ('equality', '=0')]:
                    for length in sorted({0, width - 1, width}):
                        yield witness(stem + '-' + predicate_name + '-length-' + str(length),
                                      kind, bytes(length), predicate, length == width,
                                      c_type=letter, bytes=width, signed=signed,
                                      available=length)
