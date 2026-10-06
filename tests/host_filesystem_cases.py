"""CSH-072 independently authored, bounded filesystem contract witnesses.

The setup and effect oracles use Python/POSIX APIs, never the selected utility.
Every ordinary case runs through cshell's three input modes and direct exec.
"""
import os
from pathlib import Path
import stat

UTILITIES = tuple('basename dirname cp dd df du file find ln ls mkdir mkfifo mv '
                  'pathchk pax pwd readlink realpath rm rmdir touch'.split())
BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'
DATA = bytes(range(256)) * 4


def case(utility, name, args, out=b'', status=0, err=b'', **kw):
    return dict(id=utility + '/' + name, utility=utility, args=args,
                stdout=out, stderr=err, status=status,
                source=BASE + utility + '.html', **kw)


def cases():
    for operand, expected in [('a/b///', b'b\n'), ('/', b'/\n'),
                              ('plain', b'plain\n'), ('a//b', b'b\n')]:
        yield case('basename', 'path-' + str(len(operand)) + '-' + expected.hex(), [operand], expected)
    yield case('basename', 'suffix', ['a/report.txt', '.txt'], b'report\n')
    yield case('basename', 'entire-suffix', ['foo', 'foo'], b'foo\n')
    yield case('basename', 'nonmatching-suffix', ['a/foo', '.txt'], b'foo\n')
    for i, (operand, expected) in enumerate([('a/b///', b'a\n'), ('/', b'/\n'),
                                            ('plain', b'.\n'), ('a//b', b'a\n')]):
        yield case('dirname', str(i), [operand], expected)
    yield case('cp', 'bytes', ['data', 'copy'], effects={'copy': {'content': DATA}})
    yield case('cp', 'preserve', ['-p', 'data', 'copy'], effects={'copy': {'content': DATA, 'mode': 0o640, 'mtime': 1000000000}})
    yield case('cp', 'recursive-physical', ['-R', '-P', 'tree', 'copy'], effects={'copy/leaf': {'content': b'leaf\n'}, 'copy/link': {'link': '../data'}})
    yield case('cp', 'symlink-follow', ['link', 'copy'], effects={'copy': {'content': DATA}})
    yield case('cp', 'same-file', ['data', 'data'], status='nonzero', err='nonempty', effects={'data': {'content': DATA}})
    yield case('dd', 'copy', ['if=data', 'of=copy', 'bs=256', 'count=2'], err='dd-statistics', effects={'copy': {'content': DATA[:512]}})
    yield case('dd', 'skip', ['if=data', 'of=copy', 'bs=128', 'skip=1', 'count=1'], err='dd-statistics', effects={'copy': {'content': DATA[128:256]}})
    yield case('dd', 'swab', ['if=ascii', 'of=copy', 'conv=swab', 'bs=4'], err='dd-statistics', effects={'copy': {'content': b'badcfehg'}})
    yield case('dd', 'file-size-fault', ['if=data', 'of=copy', 'bs=256'], status='nonzero', err='nonempty', fault=True, effects={'copy': {'size': 512}})
    yield case('df', 'portable-k', ['-P', '-k', 'data'], out='df-portable')
    yield case('du', 'file-k', ['-k', 'data'], out='du-blocks')
    yield case('file', 'empty', ['empty'], out='file-empty')
    yield case('file', 'directory', ['tree'], out='file-directory')
    yield case('find', 'regular', ['tree', '-type', 'f'], b'tree/leaf\n')
    yield case('find', 'link', ['tree', '-type', 'l'], b'tree/link\n')
    yield case('find', 'prune', ['tree', '-prune', '-print'], b'tree\n')
    yield case('find', 'depth', ['tree', '-depth', '-name', 'tree', '-print'], b'tree\n')
    yield case('find', 'deep-utf8', ['deep', '-name', '?', '-type', 'f'], out='deep-leaf', setup='deep', utf8=True)
    yield case('ln', 'hard', ['data', 'newlink'], effects={'newlink': {'same_inode': 'data', 'content': DATA}})
    yield case('ln', 'symbolic', ['-s', 'absent', 'newlink'], effects={'newlink': {'link': 'absent'}})
    yield case('ln', 'replace', ['-f', 'data', 'ascii'], effects={'ascii': {'same_inode': 'data'}})
    yield case('ls', '512-c-order', ['-1', 'many'], out=b''.join(f'f{i:04d}\n'.encode() for i in range(512)), setup='many')
    yield case('ls', 'hidden', ['-A', '-1', 'hidden'], b'.dot\nvisible\n', setup='hidden')
    yield case('mkdir', 'parents', ['-p', 'new/a/b'], effects={'new/a/b': {'type': 'directory'}})
    yield case('mkdir', 'mode', ['-m', '750', 'new'], effects={'new': {'type': 'directory', 'mode': 0o750}})
    yield case('mkdir', 'existing-parents', ['-p', 'tree'], effects={'tree/leaf': {'content': b'leaf\n'}})
    yield case('mkdir', 'existing-error', ['tree'], status='nonzero', err='nonempty')
    yield case('mkfifo', 'mode', ['-m', '640', 'newfifo'], effects={'newfifo': {'type': 'fifo', 'mode': 0o640}})
    yield case('mv', 'rename', ['data', 'moved'], effects={'data': {'type': 'absent'}, 'moved': {'content': DATA, 'mode': 0o640}})
    yield case('mv', 'replace', ['data', 'ascii'], effects={'data': {'type': 'absent'}, 'ascii': {'content': DATA}})
    yield case('mv', 'symlink', ['link', 'moved'], effects={'link': {'type': 'absent'}, 'moved': {'link': 'data'}})
    yield case('pathchk', 'portable', ['-p', 'abc/DEF_09.-'])
    yield case('pathchk', 'portable-too-long', ['-p', 'x' * 15], status='nonzero', err='nonempty')
    yield case('pathchk', 'nonportable-byte', ['-p', 'a:b'], status='nonzero', err='nonempty')
    yield case('pathchk', 'name-max', ['x' * 256], status='nonzero', err='nonempty')
    yield case('pax', 'copy-tree', ['-rw', 'tree', 'destination'], effects={'destination/tree/leaf': {'content': b'leaf\n'}, 'destination/tree/link': {'link': '../data'}})
    yield case('pax', 'archive-write', ['-w', '-x', 'ustar', '-f', 'archive', 'data'], archive='write', env={'COPYFILE_DISABLE': '1'})
    yield case('pax', 'archive-read', ['-r', '-p', 'p', '-f', 'archive'], setup='archive', effects={'archived': {'content': b'archive bytes\n', 'mode': 0o640}})
    yield case('pwd', 'physical', ['-P'], out='cwd')
    yield case('pwd', 'physical-name-boundary', ['-P'], out='cwd', setup='long-cwd')
    yield case('readlink', 'link', ['link'], b'data\n')
    yield case('readlink', 'no-newline', ['-n', 'dangling'], b'absent')
    yield case('realpath', 'existing', ['tree/../link'], out='resolved-data')
    yield case('rm', 'file', ['data'], effects={'data': {'type': 'absent'}})
    yield case('rm', 'symlink', ['link'], effects={'link': {'type': 'absent'}, 'data': {'content': DATA}})
    yield case('rm', 'recursive', ['-r', 'tree'], effects={'tree': {'type': 'absent'}, 'data': {'content': DATA}})
    yield case('rm', 'force-missing', ['-f', 'absent'])
    yield case('rmdir', 'empty', ['vacant'], effects={'vacant': {'type': 'absent'}})
    yield case('rmdir', 'nonempty', ['tree'], status='nonzero', err='nonempty', effects={'tree/leaf': {'content': b'leaf\n'}})
    yield case('rmdir', 'parents', ['-p', 'new/a/b'], setup='parents', effects={'new': {'type': 'absent'}})
    yield case('touch', 'reference', ['-r', 'data', 'empty'], effects={'empty': {'content': b'', 'mtime': 1000000000, 'atime': 1000000000}})
    yield case('touch', 'no-create', ['-c', 'absent'], effects={'absent': {'type': 'absent'}})
    yield case('touch', 'timestamp', ['-t', '200109090146.40', 'empty'], effects={'empty': {'mtime': 1000000000, 'atime': 1000000000}})
    for utility in ('cp', 'dd', 'df', 'du', 'find', 'ln', 'ls', 'mv', 'pax', 'rm', 'rmdir'):
        args = {'cp': ['absent', 'copy'], 'dd': ['if=absent'], 'ln': ['absent', 'newlink'],
                'mv': ['absent', 'moved'], 'pax': ['-r', '-f', 'absent']}.get(utility, ['absent'])
        yield case(utility, 'missing', args, status='nonzero', err='nonempty')


def terminal_cases():
    for response in ('y', 'n'):
        yield case('rm', 'terminal-' + response, ['-i', 'data'],
                   effects={'data': {'type': 'absent'} if response == 'y' else {'content': DATA}},
                   response=response, modes=('pty-direct', 'pty-string', 'pty-file'))


def audit_cases():
    """Required new Issue-8 contracts: failures are fatal in the explicit audit."""
    yield case('readlink', 'nonlink-diagnostic', ['data'], status='nonzero', err='nonempty')
    yield case('realpath', 'missing-E', ['-E', 'absent'], out='resolved-absent')
    yield case('realpath', 'existing-e', ['-e', 'link'], out='resolved-data')
    yield case('realpath', 'missing-e-error', ['-e', 'absent'], status='nonzero', err='nonempty')
    yield case('realpath', 'missing-prefix-error', ['-E', 'absent/leaf'], status='nonzero', err='nonempty')
    yield case('realpath', 'missing-dotdot-error', ['-E', 'absent/../data'], status='nonzero', err='nonempty')
    yield case('realpath', 'missing-trailing-slash', ['-E', 'absent/'], out='resolved-absent')
    yield case('realpath', 'regular-trailing-slash-error', ['-E', 'data/'], status='nonzero', err='nonempty')
    yield case('realpath', 'regular-dotdot-error', ['-E', 'data/..'], status='nonzero', err='nonempty')
    yield case('realpath', 'regular-prefix-error', ['-E', 'data/child'], status='nonzero', err='nonempty')
    yield case('realpath', 'dangling-E', ['-E', 'dangling'], out='resolved-absent')
    yield case('realpath', 'dangling-prefix-error', ['-E', 'badlink'], status='nonzero', err='nonempty')
    yield case('realpath', 'symlink-dotdot', ['-E', 'dirlink/../absent'], out='resolved-tree/absent')
    yield case('realpath', 'last-E', ['-e', '-E', 'absent'], out='resolved-absent')
    yield case('realpath', 'last-e', ['-E', '-e', 'absent'], status='nonzero', err='nonempty')
    yield case('realpath', 'loop-error', ['-E', 'loop'], status='nonzero', err='nonempty')
    yield case('realpath', 'empty-error', ['-E', ''], status='nonzero', err='nonempty')
    yield case('readlink', 'missing-diagnostic', ['absent'], status='nonzero', err='nonempty')
    yield case('readlink', 'long-bytes', ['longlink'], b'x' * 600 + b'\n')
    yield case('readlink', 'dash-operand', ['--', '-dash'], b'data\n')
    for utility, operand in (('readlink', 'link'), ('realpath', 'data')):
        yield case(utility, 'stdout-error', [operand], status='nonzero', err='nonempty', closed_stdout=True)
        yield case(utility, 'invalid-option', ['--csh-072-invalid-option', operand], status='nonzero', err='nonempty')


def setup(directory, row):
    import io
    import tarfile
    (directory / 'data').write_bytes(DATA)
    (directory / 'data').chmod(0o640)
    os.utime(directory / 'data', (1000000000, 1000000000))
    (directory / 'ascii').write_bytes(b'abcdefgh')
    (directory / 'empty').touch()
    (directory / 'tree').mkdir()
    (directory / 'tree').chmod(0o700)
    (directory / 'tree/leaf').write_bytes(b'leaf\n')
    (directory / 'tree/link').symlink_to('../data')
    (directory / 'link').symlink_to('data')
    (directory / 'dangling').symlink_to('absent')
    (directory / 'longlink').symlink_to('x' * 600)
    (directory / '-dash').symlink_to('data')
    (directory / 'badlink').symlink_to('absent/child')
    (directory / 'loop').symlink_to('loop')
    (directory / 'tree/sub').mkdir()
    (directory / 'dirlink').symlink_to('tree/sub')
    (directory / 'destination').mkdir()
    (directory / 'vacant').mkdir()
    kind = row.get('setup')
    cwd = directory
    if kind == 'deep':
        leaf = directory / 'deep'
        for _ in range(64):
            leaf /= 'd'
        leaf.mkdir(parents=True)
        (leaf / 'é').write_bytes(b'leaf')
    elif kind == 'many':
        (directory / 'many').mkdir()
        for i in range(512):
            (directory / 'many' / f'f{i:04d}').touch()
    elif kind == 'hidden':
        (directory / 'hidden').mkdir()
        for name in ('.dot', 'visible'):
            (directory / 'hidden' / name).touch()
    elif kind == 'parents':
        (directory / 'new/a/b').mkdir(parents=True)
    elif kind == 'long-cwd':
        limit = os.pathconf(directory, 'PC_NAME_MAX')
        if not 1 <= limit <= 255:
            raise OSError('fixture requires measured NAME_MAX in [1,255]')
        cwd = directory / ('x' * limit)
        cwd.mkdir()
    elif kind == 'archive':
        with tarfile.open(directory / 'archive', 'w', format=tarfile.USTAR_FORMAT) as archive:
            info = tarfile.TarInfo('archived')
            data = b'archive bytes\n'
            info.size, info.mode = len(data), 0o640
            archive.addfile(info, io.BytesIO(data))
    from host_filesystem_extended import setup as extended_setup
    extended_setup(directory, row)
    from host_filesystem_remaining import setup as remaining_setup
    return remaining_setup(directory, row) or cwd


def effect_errors(directory, row):
    import tarfile
    errors, observed = [], {}
    for name, expected in row.get('effects', {}).items():
        target = directory / name
        try:
            info = target.lstat()
            actual = {'type': 'file' if stat.S_ISREG(info.st_mode) else 'directory' if stat.S_ISDIR(info.st_mode)
                      else 'link' if stat.S_ISLNK(info.st_mode) else 'fifo' if stat.S_ISFIFO(info.st_mode) else 'other',
                      'mode': stat.S_IMODE(info.st_mode), 'size': info.st_size, 'nlink': info.st_nlink,
                      'uid': info.st_uid, 'gid': info.st_gid,
                      'atime': int(info.st_atime), 'mtime': int(info.st_mtime)}
            if 'owner_of' in expected:
                other = (directory / expected['owner_of']).lstat()
                actual['owner_of'] = expected['owner_of'] if (info.st_uid, info.st_gid) == (other.st_uid, other.st_gid) else None
            if 'same_lstat' in expected:
                other = (directory / expected['same_lstat']).lstat()
                actual['same_lstat'] = expected['same_lstat'] if (info.st_dev, info.st_ino) == (other.st_dev, other.st_ino) else None
            if 'max_size' in expected:
                actual['max_size'] = expected['max_size'] if stat.S_ISREG(info.st_mode) and info.st_size <= expected['max_size'] else None
            if 'content' in expected:
                actual['content'] = target.read_bytes() if stat.S_ISREG(info.st_mode) and info.st_size <= 1048576 else None
            if 'link' in expected:
                actual['link'] = os.readlink(target) if stat.S_ISLNK(info.st_mode) else None
            if 'same_inode' in expected:
                other = (directory / expected['same_inode']).stat()
                actual['same_inode'] = expected['same_inode'] if (info.st_dev, info.st_ino) == (other.st_dev, other.st_ino) else None
        except FileNotFoundError:
            actual = {'type': 'absent'}
        observed[name] = actual
        if any(actual.get(key) != value for key, value in expected.items()):
            errors.append('effect mismatch: ' + name)
    if row.get('archive') == 'write':
        # Python's reader independently decodes the selected pax archive. Never
        # extract untrusted paths; compare only the one expected member's bytes.
        info = (directory / 'archive').lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > 1048576:
            return errors + ['archive is not a bounded regular file'], observed
        with tarfile.open(directory / 'archive', mode='r:') as archive:
            members = archive.getmembers()
            valid = len(members) == 1 and members[0].name == 'data' and members[0].isfile() and members[0].size == len(DATA)
            if not valid or archive.extractfile(members[0]).read(len(DATA) + 1) != DATA:
                errors.append('archive member/bytes mismatch')
            observed['archive'] = [m.name for m in members]
    from host_filesystem_extended import archive_errors
    archive_failures, archive_observed = archive_errors(directory, row)
    errors.extend(archive_failures)
    if archive_observed:
        observed['archive'] = archive_observed
    return errors, observed
