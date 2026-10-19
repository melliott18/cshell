"""CSH-095 authored signed-byte/short magic boundaries and rule precedence.

Sample bytes come from the host C ABI, independently of file/libmagic. Each
numeric predicate has a matching and a nonmatching sample; messages are literal.
These private regular files do not qualify other numeric types or databases.
"""
import ctypes
import struct
import sys

from host_filesystem_cases import case

PREFIX = b'CSH95'


def witness(name, magic, sample, message, **facts):
    files = {'magic': magic, 'sample': sample}
    return case('file', 'magic-' + name, ['-m', 'magic', 'sample'],
                ticket='CSH-095', files=files, out=b'sample: ' + message + b'\n',
                effects={name: {'type': 'file', 'content': data} for name, data in files.items()},
                magic_environment=facts)


def cases():
    for kind, fmt in [('byte', 'b'), ('short', 'h')]:
        size = struct.calcsize('@' + fmt)
        maximum = (1 << (8 * size - 1)) - 1
        minimum = -maximum - 1
        for name, type_field, comparison, good, bad in [
            ('minimum', kind, '=' + str(minimum), minimum, minimum + 1),
            ('maximum', kind, '=' + str(maximum), maximum, maximum - 1),
            ('negative', kind, '<0', -1, 0),
            ('positive', kind, '>0', 1, 0),
            ('mask-hex', kind + '&0x7f', '=127', -1, -2),
            ('mask-octal', kind + '&0177', '=127', -1, -2),
            ('bits-set', kind, '&3', -1, -2),
            ('bits-missing', kind, '^3', -2, -1),
        ]:
            magic = b'0\tstring\tCSH95\tfixture\n' + f'>5\t{type_field}\t{comparison}\tmatched\n'.encode()
            for matches, value in [(True, good), (False, bad)]:
                yield witness(kind + '-' + name + ('-yes' if matches else '-no'), magic,
                              PREFIX + struct.pack('@' + fmt, value),
                              b'fixture matched' if matches else b'fixture',
                              kind=kind, bytes=size, value=value, matches=matches)
        # x is a size test, not an unconditional match at/past EOF.
        for complete in (True, False):
            payload = struct.pack('@' + fmt, 1)
            yield witness(kind + '-size-' + ('complete' if complete else 'short'),
                          b'0\tstring\tCSH95\tfixture\n' + f'>5\t{kind}\tx\tmatched\n'.encode(),
                          PREFIX + (payload if complete else payload[:-1]),
                          b'fixture matched' if complete else b'fixture',
                          kind=kind, bytes=size, complete=complete)
    for radix, number in [('hex', '0x1234'), ('octal', '011064')]:
        for matches, value in [(True, 4660), (False, 4661)]:
            yield witness('short-value-' + radix + ('-yes' if matches else '-no'),
                          b'0\tstring\tCSH95\tfixture\n' + f'>5\tshort\t={number}\tmatched\n'.encode(),
                          PREFIX + struct.pack('@h', value),
                          b'fixture matched' if matches else b'fixture',
                          kind='short', bytes=struct.calcsize('@h'), value=value, matches=matches)
    # Equality must also fail on insufficient data; no zero padding at EOF.
    for complete in (True, False):
        payload = struct.pack('@h', 7)
        yield witness('short-equality-' + ('complete' if complete else 'short'),
                      b'0\tstring\tCSH95\tfixture\n>5\tshort\t=7\tmatched\n',
                      PREFIX + (payload if complete else payload[:-1]),
                      b'fixture matched' if complete else b'fixture',
                      kind='short', bytes=struct.calcsize('@h'), complete=complete)
    # Only the first successful top-level rule and its continuations may print.
    # Swap identical predicates to disambiguate source ordering from rule rank.
    for first, second in [('alpha', 'beta'), ('beta', 'alpha')]:
        for matches in (True, False):
            magic = (f'0\tstring\tCSH95\t{first}\n>5\tbyte\t=7\tchild\n'
                     f'0\tstring\tCSH95\t{second}\n>5\tbyte\t=8\tforbidden\n').encode()
            yield witness('precedence-' + first + ('-child' if matches else '-no-child'),
                          magic, PREFIX + bytes([7 if matches else 8]),
                          first.encode() + (b' child' if matches else b''),
                          first_rule=first, continuation=matches)


def setup(directory, row):
    if 'magic_environment' not in row:
        return None
    sizes = dict(byte=ctypes.sizeof(ctypes.c_byte), short=ctypes.sizeof(ctypes.c_short))
    if sizes != dict(byte=struct.calcsize('@b'), short=struct.calcsize('@h')):
        raise OSError('Python packing does not match host C integer widths')
    for name, data in row['files'].items():
        if (directory / name).read_bytes() != data:
            raise OSError('authored magic fixture readback mismatch: ' + name)
    return dict(phase='armed', byteorder=sys.byteorder, c_bytes=sizes,
                sample_hex=row['files']['sample'].hex(), **row['magic_environment'])
