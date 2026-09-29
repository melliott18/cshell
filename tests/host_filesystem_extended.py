"""Traversal, links, metadata, archive and kernel I/O failure qualification.

All trees and archives are authored here, independently of the selected tools.
No real filesystem is filled; Linux ENOSPC uses its verified virtual full device.
"""
import io
import os
import platform
import stat
import tarfile

from host_filesystem_cases import case, DATA


def cases(system=None):
    system = system or platform.system()

    def witness(utility, name, args, group, **kw):
        return case(utility, name, args, group=group, extended_setup=group, **kw)

    for flag, link_type in (('-H', 'link'), ('-L', 'file')):
        effect = {'link': '../external'} if link_type == 'link' else {'content': b'outside\n'}
        yield witness('cp', 'traverse-' + flag[1:], ['-R', flag, 'entry', 'copy'], 'traversal',
                      effects={'copy/leaf': {'content': b'inside\n'}, 'copy/alias': effect})
        yield witness('find', 'traverse-' + flag[1:], [flag, 'entry', '-name', 'alias', '-type', 'l' if flag == '-H' else 'f', '-print'],
                      'traversal', out=b'entry/alias\n')
    yield witness('cp', 'traverse-P-operand', ['-R', '-P', 'entry', 'copy'], 'traversal', effects={'copy': {'link': 'walk'}})
    yield witness('find', 'physical-operand', ['entry', '-type', 'l'], 'traversal', out=b'entry\n')
    yield witness('find', 'logical-cycle', ['-L', 'cycle', '-name', 'never'], 'traversal', status='nonzero', err='nonempty', provider_audit=True)
    yield witness('find', 'expression-precedence', ['walk', '-name', 'leaf', '-o', '-name', 'alias', '-print'],
                  'traversal', out=b'walk/alias\n')
    yield witness('find', 'depth-order', ['chain', '-depth', '-print'], 'traversal', out=b'chain/a/b\nchain/a\nchain\n')
    yield witness('rm', 'cycle-physical-removal', ['-r', 'cycle'], 'traversal', effects={'cycle': {'type': 'absent'}, 'external': {'content': b'outside\n'}})
    yield witness('cp', 'recursive-fifo', ['-R', '-P', 'nodes', 'copy'], 'traversal', effects={'copy/pipe': {'type': 'fifo', 'mode': 0o600}})

    for flags, referent in ((['-L'], 'data'), (['-P'], 'link'), (['-P', '-L'], 'data'), (['-L', '-P'], 'link')):
        expected = {'same_lstat': referent, 'type': 'file' if referent == 'data' else 'link'}
        yield witness('ln', 'hard-symlink-' + ''.join(f[1:] for f in flags), flags + ['link', 'newlink'], 'links', effects={'newlink': expected})
    yield witness('ln', 'symbolic-ignores-dereference', ['-s', '-L', '-P', 'absent', 'newlink'], 'links', effects={'newlink': {'link': 'absent'}})
    yield witness('ln', 'existing-preserved', ['data', 'ascii'], 'links', status='nonzero', err='nonempty', effects={'ascii': {'content': b'abcdefgh'}, 'data': {'nlink': 2}})
    yield witness('mv', 'rename-inode', ['data', 'moved'], 'links', effects={'data': {'type': 'absent'}, 'moved': {'same_lstat': 'peer', 'nlink': 2, 'content': DATA}})
    yield witness('rm', 'unlink-one-name', ['peer'], 'links', effects={'peer': {'type': 'absent'}, 'data': {'nlink': 1, 'content': DATA}})

    yield witness('cp', 'preserve-owner-times', ['-p', 'data', 'copy'], 'metadata',
                  effects={'copy': {'mode': 0o640, 'mtime': 1000000000, 'atime': 1000000000, 'owner_of': 'data', 'content': DATA}})
    yield witness('mkdir', 'symbolic-mode', ['-m', 'u=rwx,g=rx,o=', 'new'], 'metadata', effects={'new': {'type': 'directory', 'mode': 0o750}})
    yield witness('mkdir', 'parents-umask', ['-p', 'new/a'], 'metadata', effects={'new': {'mode': 0o700}, 'new/a': {'mode': 0o700}})
    yield witness('mkfifo', 'default-umask', ['newfifo'], 'metadata', effects={'newfifo': {'type': 'fifo', 'mode': 0o600}})
    yield witness('mkfifo', 'symbolic-mode', ['-m', 'u=rw,g=r,o=', 'newfifo'], 'metadata', effects={'newfifo': {'type': 'fifo', 'mode': 0o640}})
    for flag, key, preserved in (('-a', 'atime', 'mtime'), ('-m', 'mtime', 'atime')):
        yield witness('touch', 'isolated-' + flag[1:], [flag, '-r', 'data', 'empty'], 'metadata', effects={'empty': {key: 1000000000, preserved: 1000000123, 'content': b''}})

    archived = {'bundle': {'type': 'directory', 'mode': 0o750},
                'bundle/file': {'content': b'archive payload\n', 'mode': 0o640, 'mtime': 1000000000},
                'bundle/hard': {'same_lstat': 'bundle/file', 'nlink': 2},
                'bundle/link': {'link': 'file'}, 'bundle/pipe': {'type': 'fifo', 'mode': 0o600}}
    yield witness('pax', 'ustar-types-read', ['-r', '-p', 'p', '-f', 'archive'], 'archives', archive_input='types', effects=archived)
    yield witness('pax', 'ustar-list', ['-f', 'archive'], 'archives', archive_input='types', out=b'bundle\nbundle/file\nbundle/hard\nbundle/link\nbundle/pipe\n')
    yield witness('pax', 'ustar-select', ['-r', '-p', 'p', '-f', 'archive', 'bundle/file'], 'archives', archive_input='types',
                  effects={'bundle/file': {'content': b'archive payload\n'}, 'bundle/hard': {'type': 'absent'}, 'bundle/link': {'type': 'absent'}})
    yield witness('pax', 'ustar-substitution', ['-r', '-f', 'archive', '-s', ',^bundle/,renamed/,', 'bundle/file'], 'archives', archive_input='types',
                  effects={'renamed/file': {'content': b'archive payload\n'}, 'bundle/file': {'type': 'absent'}})
    yield witness('pax', 'unmatched-pattern', ['-f', 'archive', 'absent'], 'archives', archive_input='types', status='nonzero', err='nonempty')
    yield witness('pax', 'ustar-types-write', ['-w', '-x', 'ustar', '-f', 'archive', 'bundle'], 'archives',
                  archive_output='types', env={'COPYFILE_DISABLE': '1'})
    yield witness('pax', 'ustar-append', ['-w', '-a', '-x', 'ustar', '-f', 'archive', 'data'], 'archives',
                  archive_input='single', archive_output='append', env={'COPYFILE_DISABLE': '1'})
    yield witness('pax', 'truncated-member', ['-r', '-f', 'archive'], 'archives', archive_input='truncated', status='nonzero', err='nonempty', provider_audit=True)
    yield witness('pax', 'bad-checksum', ['-r', '-f', 'archive'], 'archives', archive_input='checksum', status='nonzero', err='nonempty')

    # These are real kernel errors. The wrapper changes only inherited descriptors
    # and signal handling, and execs the exact inventoried provider.
    for utility, args in (('dd', ['if=data', 'bs=256']), ('pax', ['-w', '-x', 'ustar', 'data'])):
        yield witness(utility, 'broken-pipe', args, 'io', io_action='broken-pipe', status='nonzero', err='nonempty', provider_audit=utility == 'pax')
    yield witness('dd', 'closed-input', ['of=copy'], 'io', io_action='closed-input', status='nonzero', err='nonempty', effects={'copy': {'size': 0}})
    yield witness('dd', 'directory-read-error', ['if=tree', 'of=copy'], 'io', status='nonzero', err='nonempty', effects={'copy': {'size': 0}})
    for utility, args in (('cp', ['data', 'copy']), ('pax', ['-w', '-x', 'ustar', '-f', 'copy', 'data'])):
        yield witness(utility, 'bounded-write-error', args, 'io', fault=True, status='nonzero', err='nonempty', effects={'copy': {'max_size': 512}}, provider_audit=utility == 'pax')
    yield witness('cp', 'destination-not-directory', ['data', 'ascii/child'], 'io', status='nonzero', err='nonempty', effects={'ascii': {'content': b'abcdefgh'}})
    if system == 'Linux':
        for utility, args in (('dd', ['if=data', 'bs=256']), ('pax', ['-w', '-x', 'ustar', 'data']),
                              ('readlink', ['link']), ('realpath', ['data'])):
            yield witness(utility, 'virtual-device-enospc', args, 'io', io_action='enospc', status='nonzero', err='nonempty', provider_audit=utility == 'pax')


def setup(directory, row):
    group = row.get('extended_setup')
    if group == 'traversal':
        (directory / 'walk').mkdir()
        (directory / 'walk/leaf').write_bytes(b'inside\n')
        (directory / 'external').write_bytes(b'outside\n')
        (directory / 'walk/alias').symlink_to('../external')
        (directory / 'entry').symlink_to('walk')
        (directory / 'cycle').mkdir()
        (directory / 'cycle/back').symlink_to('.')
        (directory / 'chain/a/b').mkdir(parents=True)
        (directory / 'nodes').mkdir()
        os.mkfifo(directory / 'nodes/pipe', 0o640)
    elif group == 'links':
        os.link(directory / 'data', directory / 'peer')
    elif group == 'metadata':
        os.utime(directory / 'empty', (1000000123, 1000000123))
    elif group == 'io' and row.get('io_action') == 'closed-input':
        (directory / 'copy').write_bytes(b'')
    elif group == 'archives':
        if row.get('archive_output') == 'types':
            bundle = directory / 'bundle'
            bundle.mkdir(mode=0o750)
            (bundle / 'file').write_bytes(b'archive payload\n')
            (bundle / 'file').chmod(0o640)
            os.utime(bundle / 'file', (1000000000, 1000000000))
            os.link(bundle / 'file', bundle / 'hard')
            (bundle / 'link').symlink_to('file')
            os.mkfifo(bundle / 'pipe', 0o600)
        kind = row.get('archive_input')
        if kind:
            with tarfile.open(directory / 'archive', 'w', format=tarfile.USTAR_FORMAT) as archive:
                entries = [('bundle', tarfile.DIRTYPE, 0o750, '', b''),
                           ('bundle/file', tarfile.REGTYPE, 0o640, '', b'archive payload\n'),
                           ('bundle/hard', tarfile.LNKTYPE, 0o640, 'bundle/file', b''),
                           ('bundle/link', tarfile.SYMTYPE, 0o777, 'file', b''),
                           ('bundle/pipe', tarfile.FIFOTYPE, 0o600, '', b'')]
                if kind != 'types':
                    entries = [('archived', tarfile.REGTYPE, 0o640, '', b'archive payload\n')]
                for name, type_, mode, link, data in entries:
                    info = tarfile.TarInfo(name)
                    info.type, info.mode, info.linkname, info.size, info.mtime = type_, mode, link, len(data), 1000000000
                    archive.addfile(info, io.BytesIO(data))
            target = directory / 'archive'
            if kind == 'truncated':
                target.write_bytes(target.read_bytes()[:516])
            elif kind == 'checksum':
                data = bytearray(target.read_bytes())
                data[0] ^= 1
                target.write_bytes(data)


def archive_errors(directory, row):
    """Decode without extracting; require the exact member set and link graph."""
    expected = row.get('archive_output')
    if not expected:
        return [], {}
    errors, observed = [], {}
    info = (directory / 'archive').lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 1048576:
        return ['archive is not a bounded regular file'], {}
    with tarfile.open(directory / 'archive', mode='r:') as archive:
        members = archive.getmembers()
        normalized = [m.name.rstrip('/') for m in members]
        names = set(normalized)
        wanted = {'bundle', 'bundle/file', 'bundle/hard', 'bundle/link', 'bundle/pipe'} if expected == 'types' else {'archived', 'data'}
        if names != wanted or len(names) != len(members):
            return ['archive member set mismatch'], {'members': normalized}
        by_name = dict(zip(normalized, members))
        for name, member in by_name.items():
            archive.fileobj.seek(member.offset + 257)
            if archive.fileobj.read(8) != b'ustar\x0000':
                errors.append('archive is not ustar: ' + name)
            observed[name] = dict(type=member.type.decode('ascii'), mode=member.mode, size=member.size, link=member.linkname, mtime=member.mtime)
        if expected == 'append':
            for name, data in (('archived', b'archive payload\n'), ('data', DATA)):
                member = by_name[name]
                if not member.isfile() or member.size != len(data) or archive.extractfile(member).read(len(data) + 1) != data:
                    errors.append('archive bytes mismatch: ' + name)
        else:
            a, b = by_name['bundle/file'], by_name['bundle/hard']
            # Either hard-link name may hold the bytes; traversal order is unspecified.
            pairs = [(a, b), (b, a)]
            if not any(data.isfile() and data.size == 16 and data.mode == 0o640 and data.mtime == 1000000000
                       and link.islnk() and link.linkname.rstrip('/') == data.name.rstrip('/')
                       and archive.extractfile(data).read(17) == b'archive payload\n' for data, link in pairs):
                errors.append('archive hard-link/data graph mismatch')
            if not by_name['bundle'].isdir() or by_name['bundle'].mode != 0o750:
                errors.append('archive directory metadata mismatch')
            if not by_name['bundle/link'].issym() or by_name['bundle/link'].linkname != 'file':
                errors.append('archive symbolic link mismatch')
            if not by_name['bundle/pipe'].isfifo() or by_name['bundle/pipe'].mode != 0o600:
                errors.append('archive FIFO mismatch')
    return errors, observed
