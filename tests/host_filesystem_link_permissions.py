"""CSH-111: owned ln permission boundaries, proved before provider dispatch.

ln DESCRIPTION delegates to link/symlink/unlink. The probes exercise ordinary
kernel EACCES under this fixture identity, not ACLs, injected faults or limits.
"""
import copy
import errno
import os
import stat

from host_filesystem_cases import case


def cases():
    base = {
        'sources': dict(type='directory', mode=0o700),
        'sources/first': dict(type='file', mode=0o640, content=b'first\n'),
        'sources/last': dict(type='file', mode=0o600, content=b'last\n'),
        'guard': dict(type='directory', mode=0o700),
        'guard/middle': dict(type='file', mode=0o600, content=b'middle\n'),
        'targets': dict(type='directory', mode=0o700),
        'referent': dict(type='file', mode=0o600, content=b'preserve\n'),
    }

    def witness(name, args, objects, outputs, guard, mode, *, source=False, symbolic=False):
        effects = copy.deepcopy(objects)
        effects.update(copy.deepcopy(outputs))
        for path, entry in objects.items():
            if entry['type'] != 'directory':
                effects[path]['nlink'] = 1 + sum(e.get('same_lstat') == path for e in outputs.values())
        success = source and symbolic
        return case('ln', 'link-permission-' + name, args, ticket='CSH-111',
                    link_graph=objects, link_replaced=[], effects=effects,
                    link_permission=dict(guard=guard, mode=mode, source=source, symbolic=symbolic),
                    status=0 if success else 'nonzero', err=b'' if success else 'nonempty')

    # The middle hard-link operand is inaccessible; the surrounding operands
    # still succeed. For -s the inaccessible spelling is only literal content.
    for flags in (['-L'], ['-P'], ['-s'], ['-s', '-L'], ['-s', '-P']):
        symbolic = '-s' in flags
        outputs = {}
        for source in ('sources/first', 'guard/middle', 'sources/last'):
            name = source.split('/')[-1]
            outputs['targets/' + name] = (dict(type='link', link=source, nlink=1) if symbolic else
                dict(type='absent') if name == 'middle' else
                dict(base[source], same_lstat=source, nlink=2))
        yield witness('source-' + ''.join(f[1:] for f in flags),
                      flags + ['sources/first', 'guard/middle', 'sources/last', 'targets'],
                      copy.deepcopy(base), outputs, 'guard', 0o600, source=True, symbolic=symbolic)
    # Both creation and forced unlink must fail without changing destinations.
    for mode, denial in ((0o500, 'write'), (0o600, 'search')):
        for symbolic in (False, True):
            for kind in ('absent', 'file', 'link', 'fifo'):
                objects = copy.deepcopy(base)
                existing = (dict(type='absent') if kind == 'absent' else
                            dict(type='file', mode=0o600, content=b'old\n') if kind == 'file' else
                            dict(type='link', link='../referent') if kind == 'link' else
                            dict(type='fifo', mode=0o600))
                if kind != 'absent':
                    objects['targets/first'] = existing
                yield witness(denial + '-' + ('symbolic-' if symbolic else 'hard-') + kind,
                              (['-s'] if symbolic else ['-P']) +
                              (['-f'] if kind != 'absent' else []) + ['sources/first', 'targets/first'],
                              objects, {'targets/first': existing}, 'targets', mode, symbolic=symbolic)


def denied(operation):
    try:
        operation()
    except OSError as error:
        if error.errno != errno.EACCES:
            raise
    else:
        raise OSError('link permission probe unexpectedly succeeded')


def arm(directory, row):
    spec = row.get('link_permission')
    if spec is None:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('link permission witnesses require one unprivileged identity')
    guard = directory / spec['guard']
    probe = guard / '.unlink-probe'
    destination = directory / ('targets/.link-probe' if spec['source'] else 'targets/.create-probe')
    probe.write_bytes(b'probe\n')
    probes = []
    try:
        guard.chmod(spec['mode'])
        if spec['source']:
            denied(lambda: os.link(guard / 'middle', destination))
            probes.append('link inaccessible source')
        else:
            operation = (lambda: os.symlink('sources/first', destination)) if spec['symbolic'] else (
                lambda: os.link(directory / 'sources/first', destination))
            denied(operation)
            probes.append('symlink destination' if spec['symbolic'] else 'link destination')
            denied(probe.unlink)
            probes.append('unlink existing destination')
    finally:
        restore(directory, row)
        probe.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
    guard.chmod(spec['mode'])
    return dict(phase='armed', errno=errno.EACCES, probes=probes,
                mode=stat.S_IMODE(guard.lstat().st_mode), uid=os.getuid(), euid=os.geteuid())


def restore(directory, row):
    spec = row.get('link_permission')
    if spec is None:
        return
    guard = directory / spec['guard']
    try:
        info = guard.lstat()
    except FileNotFoundError:
        return
    # Never follow an unexpectedly replaced guard symlink during teardown.
    if stat.S_ISDIR(info.st_mode):
        guard.chmod(0o700)


def verify(directory, row):
    spec = row.get('link_permission')
    if spec is None:
        return [], None
    mode = stat.S_IMODE((directory / spec['guard']).lstat().st_mode)
    restore(directory, row)
    return ([] if mode == spec['mode'] else ['link permission guard mode changed']), dict(armed_mode=mode)
