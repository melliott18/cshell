"""CSH-109: bounded rmdir parent graphs and independently proved denial.

Oracles follow rmdir DESCRIPTION/OPTIONS and rmdir() errors. Only private,
owned directories are used; no mounts, ACLs, limits or races are qualified.
"""
import errno
import os
import stat

from host_filesystem_cases import case


def cases():
    def graph(name, args, directories, removed, *, files=None, links=None,
              fifos=(), failure=False, denial=None):
        objects = {path: {'type': 'directory', 'mode': 0o700} for path in directories}
        objects.update({path: {'type': 'file', 'mode': 0o600, 'content': value}
                        for path, value in (files or {}).items()})
        objects.update({path: {'type': 'link', 'link': value} for path, value in (links or {}).items()})
        objects.update({path: {'type': 'fifo', 'mode': 0o600} for path in fifos})
        effects = {path: ({'type': 'absent'} if path in removed else dict(value))
                   for path, value in objects.items()}
        if name == 'continue-missing':
            effects['obstruction'] = {'type': 'absent'}
        return case('rmdir', 'removal-' + name, args, ticket='CSH-109',
                    removal_graph=objects, removal_denial=denial, effects=effects,
                    status='nonzero' if failure else 0, err='nonempty' if failure else b'')

    for depth in (1, 2, 4):
        chain = ['chain' + '/child' * n for n in range(depth)]
        yield graph(f'parents-{depth}', ['-p', chain[-1]], chain, chain)
    for depth in (2, 4):
        chain = ['chain' + '/child' * n for n in range(depth)]
        yield graph(f'child-first-{depth}', list(reversed(chain)), chain, chain)
        siblings = [chain[-1] + '/left', chain[-1] + '/right']
        yield graph(f'siblings-before-parent-{depth}', siblings + list(reversed(chain)) + ['after'],
                    chain + siblings + ['after'], chain + siblings + ['after'])
    for kind in ('file', 'link', 'fifo'):
        extra = {'files': {'guard/keep': b'preserve\n'}} if kind == 'file' else (
            {'links': {'guard/keep': '../missing'}} if kind == 'link' else {'fifos': ('guard/keep',)})
        yield graph('nonempty-' + kind, ['-p', 'guard/child/leaf', 'after'],
                    ['guard', 'guard/child', 'guard/child/leaf', 'after'],
                    ['guard/child/leaf', 'guard/child', 'after'], failure=True, **extra)
    for denial in ('write', 'search'):
        for depth in (1, 2):
            chain = ['guard' + '/child' * n for n in range(depth + 1)]
            # Write permission is needed on the parent of the entry removed;
            # search permission is needed on every prefix component.
            removed = chain[2:] if denial == 'write' else []
            yield graph(f'{denial}-denied-{depth}', ['-p', chain[-1], 'after'],
                        chain + ['after'], removed + ['after'], failure=True, denial=denial)
    for obstruction in ('missing', 'file', 'link'):
        extra = {'files': {'obstruction': b'preserve\n'}} if obstruction == 'file' else (
            {'links': {'obstruction': 'target'}} if obstruction == 'link' else {})
        yield graph('continue-' + obstruction, ['before', 'obstruction', 'after'],
                    ['before', 'after', 'target'], ['before', 'after'], failure=True, **extra)
    yield graph('duplicate', ['-p', 'chain/child', 'chain/child', 'after'],
                ['chain', 'chain/child', 'after'], ['chain', 'chain/child', 'after'], failure=True)
    yield graph('shared-parent', ['-p', 'chain/left', 'chain/right', 'after'],
                ['chain', 'chain/left', 'chain/right', 'after'],
                ['chain', 'chain/left', 'chain/right', 'after'], failure=True)


def snapshot(path):
    info = path.lstat()
    return dict(device=info.st_dev, inode=info.st_ino, mode=info.st_mode)


def setup(directory, row):
    if 'removal_graph' not in row:
        return None
    if os.geteuid() == 0:
        raise OSError('removal witnesses require an unprivileged fixture identity')
    observed = {}
    for name, entry in row['removal_graph'].items():
        path = directory / name
        kind = entry['type']
        if kind == 'directory':
            path.mkdir()
        elif kind == 'file':
            path.write_bytes(entry['content'])
        elif kind == 'fifo':
            os.mkfifo(path)
        else:
            path.symlink_to(entry['link'])
        if kind != 'link':
            path.chmod(entry['mode'])
        observed[name] = snapshot(path)
    return dict(objects=observed, uid=os.getuid(), euid=os.geteuid(),
                scope='private owned rmdir graph')


def arm(directory, row, environment):
    denial = row.get('removal_denial')
    if not denial:
        return
    guard = directory / 'guard'
    probe = guard / '.removal-probe'
    probe.mkdir(mode=0o700)
    mode = 0o500 if denial == 'write' else 0
    guard.chmod(mode)
    try:
        probe.rmdir()
    except OSError as error:
        if error.errno != errno.EACCES:
            raise
    else:
        raise OSError('removal permission probe unexpectedly succeeded')
    finally:
        guard.chmod(0o700)
        if probe.exists():
            probe.rmdir()
    guard.chmod(mode)
    environment['denial'] = dict(phase='armed', errno=errno.EACCES, mode=stat.S_IMODE(guard.stat().st_mode),
                                probe='rmdir guard/.removal-probe', kind=denial,
                                uid=os.getuid(), euid=os.geteuid())


def restore(directory, row):
    if not row.get('removal_denial'):
        return
    guard = directory / 'guard'
    try:
        info = guard.lstat()
    except FileNotFoundError:
        return
    if stat.S_ISDIR(info.st_mode):
        guard.chmod(0o700)


def verify(directory, row, environment):
    if environment is None:
        return [], None
    errors, observed = [], {}
    if row.get('removal_denial'):
        mode = stat.S_IMODE((directory / 'guard').lstat().st_mode)
        observed['armed_mode'] = mode
        if mode != (0o500 if row['removal_denial'] == 'write' else 0):
            errors.append('removal denied directory mode changed')
        restore(directory, row)
    for name, before in environment['objects'].items():
        if row['effects'][name]['type'] == 'absent':
            continue
        observed[name] = snapshot(directory / name)
        if observed[name] != before:
            errors.append('removal preserved identity/mode changed: ' + name)
    return errors, observed
