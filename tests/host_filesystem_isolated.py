"""CSH-085 private graph, magic and timestamp environments.

No mounts, privileged identities, shared files, or volume-capacity changes.
The accounting oracle uses an explicitly authored graph and pre-exec lstat
measurements, not another du implementation or a traversal copied from du.
"""
import os
import re
import struct

from host_filesystem_cases import case

BASE_NS = 900000000125000000
STAMP_NS = 1000000000002000000


def cases():
    def witness(utility, name, args, **kw):
        return case(utility, 'isolated-' + name, args, ticket='CSH-085', **kw)

    for name, options, operand, hard in [
        ('recursive-512', [], 'account', False),
        ('all-k', ['-a', '-k'], 'account', False),
        ('summary-hardlinks', ['-s', '-k'], 'account', True),
        ('operand-H', ['-H', '-k'], 'account-link', False),
        ('nested-L', ['-L', '-k'], 'account', False),
        ('last-H', ['-L', '-H', '-k'], 'account-link', False),
        ('last-L', ['-H', '-L', '-k'], 'account-link', False),
    ]:
        yield witness('du', name, options + [operand], out='isolated-du',
                      accounting=dict(options=options, operand=operand, hardlink=hard))

    # Every rule has a matching and nonmatching sample. A continuation fallback
    # supplies an exact independent message for the negative comparison as well.
    for name, kind, comparison, good, bad in [
        ('equal', 'byte', '=7', b'\x07', b'\x08'),
        ('less', 'byte', '<7', b'\x06', b'\x07'),
        ('greater', 'byte', '>7', b'\x08', b'\x07'),
        ('mask-hex', 'byte&0x0f', '=7', b'\x17', b'\x18'),
        ('mask-octal', 'byte&017', '=7', b'\x17', b'\x18'),
        ('bits-set', 'byte', '&3', b'\x07', b'\x06'),
        ('bits-missing', 'byte', '^3', b'\x06', b'\x07'),
        ('native-short', 'short', '=513', struct.pack('@h', 513), struct.pack('@h', 514)),
    ]:
        for matches, sample in [(True, good), (False, bad)]:
            magic = ('0 string CSH85 fixture\n>5 ' + kind + ' ' + comparison + ' matched\n').encode()
            yield witness('file', 'numeric-' + name + ('-yes' if matches else '-no'),
                          ['-m', 'magic', 'sample'], files={'magic': magic, 'sample': b'CSH85' + sample + b'\0'},
                          out=b'sample: fixture' + (b' matched' if matches else b'') + b'\n')

    for name, date, options, env in [
        ('fraction-period-utc', '2001-09-09T01:46:40.002Z', [], {}),
        ('fraction-comma-utc', '2001-09-09T01:46:40,002Z', [], {}),
        ('fraction-space-local', '2001-09-09 02:46:40.002', [], {'TZ': 'XXX-1'}),
        ('fraction-access-only', '2001-09-09T01:46:40.002Z', ['-a'], {}),
        ('fraction-modify-only', '2001-09-09T01:46:40.002Z', ['-m'], {}),
    ]:
        expected = dict(atime_ns=BASE_NS if '-m' in options else STAMP_NS,
                        mtime_ns=BASE_NS if '-a' in options else STAMP_NS)
        yield witness('touch', name, options + ['-d', date, 'empty'], env=env,
                      timestamp_environment=True, effects={'empty': dict(type='file', size=0, **expected)})


def measurements(directory, names):
    result = {}
    for name in names:
        info = (directory / name).lstat()
        if info.st_blocks < 0:
            raise OSError('negative allocation measurement')
        result[name] = dict(device=info.st_dev, inode=info.st_ino, blocks=info.st_blocks,
                            size=info.st_size, mode=info.st_mode, nlink=info.st_nlink)
    return result


def setup(directory, row):
    if row.get('timestamp_environment'):
        for stamp in (STAMP_NS, BASE_NS):
            os.utime(directory / 'empty', ns=(stamp, stamp))
            info = (directory / 'empty').stat()
            if (info.st_atime_ns, info.st_mtime_ns) != (stamp, stamp):
                raise OSError('filesystem cannot represent the authored subsecond timestamp')
        return dict(kind='timestamp', phase='armed', baseline_ns=BASE_NS, target_ns=STAMP_NS,
                    probe='utime(ns) followed by stat on the private target')
    if not row.get('accounting'):
        return None
    spec = row['accounting']
    (directory / 'account/sub').mkdir(parents=True)
    (directory / 'outside').mkdir()
    for name, size in [('account/top', 1537), ('account/sub/leaf', 8193), ('outside/extra', 4097)]:
        (directory / name).write_bytes(bytes((i % 251 for i in range(size))))
    (directory / 'account/symbol').symlink_to('../outside')
    (directory / 'account-link').symlink_to('account')
    names = ['account', 'account/sub', 'account/top', 'account/sub/leaf',
             'account/symbol', 'outside', 'outside/extra', 'account-link']
    if spec['hardlink']:
        os.link(directory / 'account/sub/leaf', directory / 'account/sub/twin')
        names.append('account/sub/twin')
    observed = measurements(directory, names)
    if len({v['device'] for v in observed.values()}) != 1:
        raise OSError('accounting fixture unexpectedly crosses devices')
    if spec['hardlink']:
        a, b = (observed[n] for n in ('account/sub/leaf', 'account/sub/twin'))
        if (a['device'], a['inode'], a['nlink']) != (b['device'], b['inode'], 2):
            raise OSError('hard-link identity was not established')
    blocks = {n: v['blocks'] for n, v in observed.items()}
    options, operand = spec['options'], spec['operand']
    follow_all = next((o == '-L' for o in reversed(options) if o in ('-H', '-L')), False)
    sub = blocks['account/sub'] + blocks['account/sub/leaf']
    symbol = blocks['outside'] + blocks['outside/extra'] if follow_all else blocks['account/symbol']
    expected = {operand: blocks['account'] + sub + blocks['account/top'] + symbol}
    if '-s' not in options:
        expected[operand + '/sub'] = sub
        if follow_all:
            expected[operand + '/symbol'] = symbol
        if '-a' in options:
            expected.update({operand + '/top': blocks['account/top'],
                             operand + '/sub/leaf': blocks['account/sub/leaf'],
                             operand + '/symbol': symbol})
    divisor = 2 if '-k' in options else 1
    expected = {name: (count + divisor - 1) // divisor for name, count in expected.items()}
    return dict(kind='accounting', phase='armed', unit_bytes=512 * divisor,
                measurements=observed, expected=expected,
                scope='allocated blocks for an authored private graph; no shared-extent or capacity claim')


def accounting_matches(environment, output):
    actual = {}
    for line in output.splitlines():
        match = re.fullmatch(rb'(\d+)[ \t]+([^\r\n]+)', line)
        if not match:
            return False
        name = os.fsdecode(match[2])
        if name in actual:
            return False
        actual[name] = int(match[1])
    return actual == environment['expected'] and output.endswith(b'\n')


def verify(directory, environment):
    if environment and environment['kind'] == 'accounting':
        observed = measurements(directory, environment['measurements'])
        if observed != environment['measurements']:
            return ['accounting fixture changed during execution']
    return []
