"""CSH-102: literal byte oracles for string magic and offset spellings.

The encoded magic values and decoded bytes are authored independently. No
provider output or escape decoder supplies the expected match. Only one private
magic database and a bounded C-locale byte repertoire are qualified.
"""
from host_filesystem_cases import case

PREFIX = b'CSH102'
# Issue 8 file EXTENDED DESCRIPTION: required escapes, including longest
# one/two/three-digit octal sequences. A following non-octal byte terminates
# short sequences; a fourth octal digit remains a literal character.
VALUES = [
    ('plain', b'needle', b'needle'),
    ('space', br'left\ right', b'left right'),
    ('backslash', br'left\\right', b'left\\right'),
    ('alert', br'A\aB', b'A\x07B'),
    ('backspace', br'A\bB', b'A\x08B'),
    ('formfeed', br'A\fB', b'A\x0cB'),
    ('newline', br'A\nB', b'A\x0aB'),
    ('return', br'A\rB', b'A\x0dB'),
    ('tab', br'A\tB', b'A\x09B'),
    ('vertical-tab', br'A\vB', b'A\x0bB'),
    ('octal-one', br'A\7Z', b'A\x07Z'),
    ('octal-two', br'A\12Z', b'A\x0aZ'),
    ('octal-three', br'A\1012', b'AA2'),
    ('octal-nul', br'A\000B', b'A\x00B'),
    ('octal-high', br'A\377B', b'A\xffB'),
]
OFFSETS = [('decimal', b'16'), ('octal', b'020'), ('hex', b'0x10'), ('hex-upper', b'0X10')]


def cases():
    for name, spelling, decoded in VALUES:
        # A successful top-level rule fixes the entire output even when the
        # continuation fails; no unspecified default classification is used.
        for boundary, tail, matches in [
            ('exact', decoded, True),
            ('trailing', decoded + b'ignored', True),
            ('mismatch', decoded[:-1] + bytes([decoded[-1] ^ 1]), False),
            ('truncated', decoded[:-1], False),
            ('at-eof', b'', False),
        ]:
            magic = b'0\tstring\tCSH102\tfixture\n>16\tstring\t' + spelling + b'\tmatched\n'
            yield witness(name + '-' + boundary, magic, PREFIX + b'.' * 10 + tail,
                          matches, spelling, decoded, 16, boundary)
    for name, spelling in OFFSETS:
        for boundary, sample, matches in [
            ('exact', PREFIX + b'.' * 10 + b'AB', True),
            ('before', PREFIX + b'.' * 9 + b'AB.', False),
            ('after', PREFIX + b'.' * 11 + b'AB', False),
            ('past-eof', PREFIX, False),
        ]:
            magic = b'0\tstring\tCSH102\tfixture\n>' + spelling + b'\tstring\tAB\tmatched\n'
            yield witness('offset-' + name + '-' + boundary, magic, sample,
                          matches, b'AB', b'AB', 16, boundary)


def witness(name, magic, sample, matches, spelling, decoded, offset, boundary):
    files = dict(magic=magic, sample=sample)
    return case('file', 'magic-strings-' + name, ['-m', 'magic', 'sample'],
                ticket='CSH-102', files=files,
                out=b'sample: fixture' + (b' matched' if matches else b'') + b'\n',
                effects={key: dict(type='file', content=data) for key, data in files.items()},
                magic_environment=dict(encoded_hex=spelling.hex(), decoded_hex=decoded.hex(),
                                       offset=offset, boundary=boundary, matches=matches))
