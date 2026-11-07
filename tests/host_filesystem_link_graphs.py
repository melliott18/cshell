"""CSH-110: independently authored ln destination and continuation graphs.

ln DESCRIPTION steps 1-4 define collision handling and the link operations.
Default source-symlink policy, directory hard links, and repeated destination
names created during the invocation are deliberately not assigned an oracle.
"""
import copy
import os

from host_filesystem_cases import case


def cases():
    base = {
        'sources': dict(type='directory', mode=0o700),
        'sources/first': dict(type='file', mode=0o640, content=b'first\n'),
        'sources/middle': dict(type='file', mode=0o600, content=b'middle\n'),
        'sources/last': dict(type='file', mode=0o640, content=b'last\n'),
        'sources/sym': dict(type='link', link='first'),
        'sources/broken': dict(type='link', link='missing'),
        'sources/dirsym': dict(type='link', link='../targets'),
        'targets': dict(type='directory', mode=0o700),
        'target-alias': dict(type='link', link='targets'),
        'referent': dict(type='file', mode=0o600, content=b'untouched\n'),
    }

    def graph(name, args, outputs, *, extra=None, replaced=(), failure=False):
        objects = copy.deepcopy(base)
        objects.update(extra or {})
        effects = copy.deepcopy(objects)
        effects.update(outputs)
        # Every unchanged object retains its original inode and mode, including
        # symlink destinations' referents. Link counts are authored from outputs.
        for source, entry in objects.items():
            if entry['type'] != 'directory' and source not in replaced:
                effects[source]['nlink'] = 1 + sum(
                    effect.get('same_lstat') == source for effect in outputs.values())
        return case('ln', 'link-graph-' + name, args, ticket='CSH-110',
                    link_graph=objects, link_replaced=list(replaced), effects=effects,
                    status='nonzero' if failure else 0, err='nonempty' if failure else b'')

    def hard(source):
        result = dict(base[source], same_lstat=source)
        result['nlink'] = 2
        return result

    for destination in ('targets', 'targets/', 'target-alias'):
        for symbolic in (False, True):
            outputs = {f'targets/{name}': (dict(type='link', link='sources/' + name, nlink=1)
                                          if symbolic else hard('sources/' + name))
                       for name in ('first', 'last')}
            yield graph(('symbolic-' if symbolic else 'hard-') + destination.replace('/', '-slash'),
                        (['-s'] if symbolic else []) + ['sources/first', 'sources/last', destination], outputs)
    # Explicit -L/-P and their last-option precedence on valid/dangling sources.
    for source in ('sym', 'broken'):
        for flags in (['-P'], ['-L', '-P'], ['-L'], ['-P', '-L']):
            physical = flags[-1] == '-P'
            failure = source == 'broken' and not physical
            output = ({'type': 'absent'} if failure else
                      hard('sources/' + source) if physical else hard('sources/first'))
            yield graph(source + '-' + ''.join(f[1:] for f in flags),
                        flags + ['sources/' + source, 'target-alias'],
                        {'targets/' + source: output}, failure=failure)
    for flags in (['-P'], ['-L', '-P']):
        yield graph('directory-source-' + ''.join(f[1:] for f in flags),
                    flags + ['sources/dirsym', 'targets'], {'targets/dirsym': hard('sources/dirsym')})
    for kind, entry in (
            ('file', dict(type='file', mode=0o600, content=b'old\n')),
            ('link', dict(type='link', link='../referent')),
            ('dangling', dict(type='link', link='../absent')),
            ('fifo', dict(type='fifo', mode=0o600)),
            ('directory', dict(type='directory', mode=0o700))):
        for force in (False, True):
            replaced = force and kind != 'directory'
            outputs = {'targets/first': hard('sources/first'), 'targets/last': hard('sources/last'),
                       'targets/middle': hard('sources/middle') if replaced else entry}
            yield graph('collision-' + kind + ('-force' if force else '-preserve'),
                        (['-f'] if force else []) +
                        ['sources/first', 'sources/middle', 'sources/last', 'target-alias'],
                        outputs, extra={'targets/middle': entry},
                        replaced=['targets/middle'] if replaced else [], failure=not replaced)
    for symbolic in (False, True):
        outputs = {f'targets/{name}': (dict(type='link', link='sources/' + name, nlink=1)
                                     if symbolic else hard('sources/' + name))
                   for name in ('first', 'last')}
        yield graph('same-entry-' + ('symbolic' if symbolic else 'hard'),
                    ['-f'] + (['-s'] if symbolic else []) +
                    ['sources/first', 'targets/middle', 'sources/last', 'targets'],
                    outputs, extra={'targets/middle': dict(type='file', mode=0o600, content=b'keep\n')},
                    failure=True)
    yield graph('missing-middle', ['sources/first', 'sources/missing', 'sources/last', 'targets'],
                {'targets/first': hard('sources/first'), 'targets/missing': {'type': 'absent'},
                 'targets/last': hard('sources/last')}, failure=True)


def snapshot(path):
    info = path.lstat()
    return dict(device=info.st_dev, inode=info.st_ino, mode=info.st_mode, nlink=info.st_nlink)


def setup(directory, row):
    if 'link_graph' not in row:
        return None
    if os.geteuid() == 0:
        raise OSError('link graph witnesses require an unprivileged fixture identity')
    observed = {}
    for name, entry in row['link_graph'].items():
        path = directory / name
        if entry['type'] == 'directory':
            path.mkdir()
        elif entry['type'] == 'file':
            path.write_bytes(entry['content'])
        elif entry['type'] == 'fifo':
            os.mkfifo(path)
        else:
            path.symlink_to(entry['link'])
        if entry['type'] != 'link':
            path.chmod(entry['mode'])
        observed[name] = snapshot(path)
        if entry['type'] != 'directory' and observed[name]['nlink'] != 1:
            raise OSError('link fixture did not start with one directory entry: ' + name)
    # Independently read back every authored type, byte string, mode and link.
    from host_filesystem_cases import effect_errors
    errors, effects = effect_errors(directory, {'effects': row['link_graph']})
    if errors:
        raise OSError('link fixture readback: ' + '; '.join(errors))
    return dict(objects=observed, effects=effects, uid=os.getuid(), euid=os.geteuid(),
                scope='private owned ln graph; no injected faults or filesystem limits')


def verify(directory, row, environment):
    if environment is None:
        return [], None
    errors, observed = [], {}
    for name, before in environment['objects'].items():
        if name in row['link_replaced']:
            continue
        after = observed[name] = snapshot(directory / name)
        if any(after[key] != before[key] for key in ('device', 'inode', 'mode')):
            errors.append('link graph preserved identity/mode changed: ' + name)
    return errors, observed
