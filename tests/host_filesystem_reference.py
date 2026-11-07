"""CSH-097 touch reference timestamps through private alias graphs.

Python constructs and measures the inodes before exec. Expectations are authored
nanoseconds, never learned from touch or a reference utility. Snapshot metadata
before any content reads, including reads through another hard link.
"""
import os
from os import utime
import stat

from host_filesystem_cases import case

REFERENCE = (1000000000125000000, 1100000000250000000)
BASELINE = (900000000375000000, 950000000500000000)
FILES = {'reference': b'reference witness\n', 'target': b'target witness\n'}
LINKS = {'reference-link': 'reference', 'reference-chain': 'reference-link',
         'target-link': 'target', 'target-chain': 'target-link',
         'missing-link': 'missing-target', 'missing-chain': 'missing-link'}
SELECTIONS = [('both', []), ('access', ['-a']), ('modify', ['-m']),
              ('explicit-both', ['-a', '-m'])]


def cases():
    graphs = [(ref, operand, [])
              for ref in ('reference', 'reference-link', 'reference-chain')
              for operand in ('target-hard', 'target-chain')]
    # Missing operands precede an existing target: silent no-create must not
    # stop processing, replace dangling links, or accidentally create a referent.
    graphs.append(('reference-chain', 'target-chain', ['missing', 'missing-chain']))
    for ref, operand, missing in graphs:
        for selection, flags in SELECTIONS:
            stamps = (BASELINE[0] if flags == ['-m'] else REFERENCE[0],
                      BASELINE[1] if flags == ['-a'] else REFERENCE[1])
            yield case('touch', 'reference-' + ('no-create' if missing else ref + '-' + operand)
                       + '-' + selection,
                       [*flags, *(['-c'] if missing else []), '-r', ref, *missing, operand],
                       ticket='CSH-097', files=FILES,
                       effects={**{n: dict(type='file', content=b) for n, b in FILES.items()},
                                **{n: dict(type='link', link=p) for n, p in LINKS.items()},
                                'target-hard': dict(type='file', same_inode='target'),
                                'missing': dict(type='absent'),
                                'missing-target': dict(type='absent')},
                       reference_environment=dict(reference=ref, operand=operand,
                                                  reference_ns=REFERENCE, target_ns=stamps,
                                                  baseline_ns=BASELINE, no_create=bool(missing)))


def snapshot(directory):
    observed = {}
    for name in (*FILES, 'target-hard', *LINKS):
        info = (directory / name).lstat()
        observed[name] = dict(device=info.st_dev, inode=info.st_ino,
                              mode=info.st_mode, nlink=info.st_nlink,
                              atime_ns=info.st_atime_ns, mtime_ns=info.st_mtime_ns)
    return observed


def setup(directory, row):
    spec = row.get('reference_environment')
    if spec is None:
        return None
    for name, content in FILES.items():
        if (directory / name).read_bytes() != content:
            raise OSError('reference fixture content readback mismatch: ' + name)
    os.link(directory / 'target', directory / 'target-hard')
    for name, target in LINKS.items():
        (directory / name).symlink_to(target)
    probes = []
    # Prove both fields representable on each actual inode, then restore a
    # distinct baseline on the target. Reference fields also differ from each other.
    for name, stamps in [('reference', REFERENCE), ('target', REFERENCE), ('target', BASELINE)]:
        utime(directory / name, ns=stamps)
        info = (directory / name).stat()
        actual = (info.st_atime_ns, info.st_mtime_ns)
        if actual != stamps:
            raise OSError('filesystem cannot represent authored reference timestamps')
        probes.append(dict(path=name, requested_ns=stamps, observed_ns=actual,
                           device=info.st_dev, inode=info.st_ino))
    before = snapshot(directory)
    identity = lambda n: (before[n]['device'], before[n]['inode'])
    if identity('reference') == identity('target') or identity('target') != identity('target-hard'):
        raise OSError('reference fixture inode graph mismatch')
    for name in ('reference-link', 'reference-chain', 'target-link', 'target-chain'):
        referent = 'reference' if name.startswith('reference') else 'target'
        info = (directory / name).stat()
        if (info.st_dev, info.st_ino) != identity(referent):
            raise OSError('reference fixture symlink resolution mismatch')
    for name in ('missing', 'missing-target', 'missing-chain'):
        try:
            (directory / name).stat()
        except FileNotFoundError:
            pass
        else:
            raise OSError('reference fixture missing path resolves: ' + name)
    return dict(phase='armed', probes=probes, before=before, **spec,
                scope='bounded private alias graph; no arbitrary graphs, races or filesystem errors')


def verify(directory, environment):
    if environment is None:
        return [], None
    after = snapshot(directory)
    errors = []
    for name, info in after.items():
        before = environment['before'][name]
        # Reading a symlink can change its atime, so only regular-file access
        # timestamps are asserted. All inode identities and link texts persist.
        keys = ('device', 'inode', 'mode', 'nlink')
        if any(info[k] != before[k] for k in keys):
            errors.append('reference graph identity mismatch: ' + name)
        if stat.S_ISREG(before['mode']):
            stamps = environment['reference_ns'] if name == 'reference' else environment['target_ns']
            if (info['atime_ns'], info['mtime_ns']) != tuple(stamps):
                errors.append('reference timestamp mismatch: ' + name)
        elif info['mtime_ns'] != before['mtime_ns']:
            errors.append('reference symlink modification time mismatch: ' + name)
    return errors, after
