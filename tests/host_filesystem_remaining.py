"""CSH-080 bounded ordinary contracts; no privileged or capacity claims.

Expected bytes and effects are authored from the utility clauses, never obtained
by running a reference utility. Existing CSH-072 cases remain mandatory.
"""
import os

from host_filesystem_cases import case, DATA


def cases():
    def witness(utility, name, args, **kw):
        return case(utility, 'remaining-' + name, args, ticket='CSH-080', **kw)

    # Both selected providers choose the permitted empty basename and collapse //.
    yield witness('basename', 'empty-policy', [''], out=b'\n')
    yield witness('basename', 'double-slash-policy', ['//'], out=b'/\n')
    yield witness('basename', 'utf8-suffix', ['répertoire/été.txt', '.txt'], out='été\n'.encode(), utf8=True)
    yield witness('basename', 'utf8-entire-suffix', ['été', 'été'], out='été\n'.encode(), utf8=True)
    for i, (operand, expected) in enumerate([('', '.'), ('//', '/'), ('///a////b///', '///a'),
                                            ('a////b///', 'a'), ('a////', '.'), ('a//b//c', 'a//b')]):
        yield witness('dirname', 'slash-' + str(i), [operand], out=(expected + '\n').encode())
    yield witness('dirname', 'utf8', ['répertoire/été'], out='répertoire\n'.encode(), utf8=True)

    # Exact dd full/partial record counts and byte totals, plus independent files.
    conversions = [
        ('block', b'a\nbc\n', ['ibs=5', 'obs=8', 'cbs=4', 'conv=block'], b'a   bc  ', (1, 0, 1, 0)),
        ('unblock', b'a   bc  ', ['ibs=8', 'obs=5', 'cbs=4', 'conv=unblock'], b'a\nbc\n', (1, 0, 1, 0)),
        ('ucase', b'aBz!\n', ['bs=5', 'conv=ucase'], b'ABZ!\n', (1, 0, 1, 0)),
        ('lcase', b'aBz!\n', ['bs=5', 'conv=lcase'], b'abz!\n', (1, 0, 1, 0)),
        ('sync', b'abc', ['ibs=4', 'obs=4', 'conv=sync'], b'abc\0', (0, 1, 1, 0)),
        ('block-sync', b'a\n', ['ibs=4', 'obs=4', 'cbs=4', 'conv=block,sync'], b'a       ', (0, 1, 2, 0)),
        ('swab-odd', b'abcde', ['bs=5', 'conv=swab'], b'badce', (1, 0, 1, 0)),
        ('seek-notrunc', b'XY', ['bs=2', 'seek=1', 'conv=notrunc'], b'abXYefgh', (1, 0, 1, 0)),
        ('seek-truncate', b'XY', ['bs=2', 'seek=1'], b'abXY', (1, 0, 1, 0)),
        ('skip-count', b'abcdefgh', ['bs=2', 'skip=1', 'count=2'], b'cdef', (2, 0, 2, 0)),
    ]
    for name, data, operands, expected, counts in conversions:
        yield witness('dd', name, ['if=input', 'of=copy', *operands],
                      files={'input': data, 'copy': b'abcdefgh'}, err='dd-records',
                      dd_records=counts, dd_bytes=2 if name.startswith('seek-') else len(expected),
                      effects={'copy': {'content': expected}})

    yield witness('cp', 'continue-missing', ['absent', 'data', 'destination'], status='nonzero', err='nonempty',
                  effects={'destination/data': {'content': DATA}})
    yield witness('ln', 'continue-missing', ['absent', 'data', 'destination'], status='nonzero', err='nonempty',
                  effects={'destination/data': {'same_inode': 'data'}})
    yield witness('mv', 'continue-missing', ['absent', 'data', 'destination'], status='nonzero', err='nonempty',
                  effects={'destination/data': {'content': DATA}, 'data': {'type': 'absent'}})
    yield witness('mv', 'empty-directory-replace', ['vacant', 'destination'],
                  directory_modes={'vacant': 0o750, 'destination/vacant': 0o700},
                  effects={'vacant': {'type': 'absent'}, 'destination/vacant': {'type': 'directory', 'mode': 0o750}})
    yield witness('mkdir', 'parent-final-mode', ['-p', '-m', 'u=rwx,g=rx,o=rx', 'new/a'],
                  effects={'new': {'mode': 0o700}, 'new/a': {'mode': 0o755}})
    yield witness('mkdir', 'parent-file-continue', ['-p', 'data/child', 'new'], status='nonzero', err='nonempty',
                  effects={'data': {'content': DATA}, 'new': {'type': 'directory'}})
    yield witness('mkdir', 'existing-mode-preserved', ['-p', '-m', '777', 'tree'],
                  effects={'tree': {'type': 'directory', 'mode': 0o700}})
    yield witness('mkfifo', 'existing-continue', ['data', 'newfifo'], status='nonzero', err='nonempty',
                  effects={'data': {'content': DATA}, 'newfifo': {'type': 'fifo', 'mode': 0o600}})
    yield witness('mkfifo', 'symbolic-sequence', ['-m', 'u=rw,g=u,o=g,o-w', 'newfifo'],
                  effects={'newfifo': {'type': 'fifo', 'mode': 0o664}})
    yield witness('rm', 'missing-continue', ['absent', 'data'], status='nonzero', err='nonempty',
                  effects={'data': {'type': 'absent'}})
    yield witness('rmdir', 'nonempty-continue', ['tree', 'vacant'], status='nonzero', err='nonempty',
                  effects={'tree/leaf': {'content': b'leaf\n'}, 'vacant': {'type': 'absent'}})
    yield witness('rmdir', 'symlink-rejected', ['dirlink'], status='nonzero', err='nonempty',
                  effects={'dirlink': {'link': 'tree/sub'}, 'tree/sub': {'type': 'directory'}})
    yield witness('touch', 'missing-prefix-continue', ['absent/child', 'created'], status='nonzero', err='nonempty',
                  effects={'created': {'content': b''}, 'absent': {'type': 'absent'}})
    yield witness('touch', 'follow-symlink', ['-t', '200109090146.40', 'link'],
                  effects={'link': {'link': 'data'}, 'data': {'mtime': 1000000000, 'atime': 1000000000}})
    for name, stamp in [('utc', '2001-09-09T01:46:40Z'), ('local', '2001-09-09 01:46:40')]:
        yield witness('touch', 'date-' + name, ['-d', stamp, 'empty'],
                      effects={'empty': {'mtime': 1000000000, 'atime': 1000000000}})

    for flags in (['-P'], ['-p', '-P'], ['-P', '-p']):
        suffix = ''.join(x[1:] for x in flags)
        yield witness('pathchk', suffix + '-valid', [*flags, 'abc/DEF_09.-'])
        for name, operand in [('empty', ''), ('dash', 'a/-b')]:
            yield witness('pathchk', suffix + '-' + name, [*flags, operand], status='nonzero', err='nonempty')

    yield witness('find', 'size-bytes', ['data', '-size', '1024c', '-print'], out=b'data\n')
    yield witness('find', 'size-rounded-blocks', ['ascii', '-size', '1', '-print'], out=b'ascii\n')
    yield witness('find', 'perm-exact', ['data', '-perm', '0640', '-print'], out=b'data\n')
    yield witness('find', 'perm-all', ['data', '-perm', '-0600', '-print'], out=b'data\n')
    yield witness('find', 'negation', ['data', '!', '-type', 'd', '-print'], out=b'data\n')
    yield witness('find', 'grouping', ['data', '(', '-type', 'd', '-o', '-name', 'data', ')', '-print'], out=b'data\n')
    yield witness('find', 'exec-batch', ['data', 'ascii', '-exec', 'printf', '<%s>\n', '{}', '+'], out=b'<data>\n<ascii>\n')
    yield witness('ls', 'reverse-c', ['-1', '-r', 'ascii', 'data'], out=b'data\nascii\n')
    yield witness('ls', 'all-reverse-c', ['-1', '-A', '-r', 'hidden'], setup='hidden', out=b'visible\n.dot\n')
    yield witness('ls', 'size-sort', ['-1', '-S', 'ascii', 'data'], out=b'data\nascii\n')
    yield witness('ls', 'time-sort', ['-1', '-t', 'data', 'empty'], out=b'empty\ndata\n',
                  times={'empty': 1000000100})
    for flags, physical in ((['-L', '-P'], True), (['-P', '-L'], False)):
        yield witness('pwd', 'last-' + flags[-1][1:], flags, out='cwd' if physical else 'logical-cwd', logical_cwd=True)
    yield witness('readlink', 'utf8-bytes', ['unicode-link'], out='répertoire/été\n'.encode(),
                  links={'unicode-link': 'répertoire/été'}, utf8=True)


def setup(directory, row):
    for name, mode in row.get('directory_modes', {}).items():
        (directory / name).mkdir(parents=True, exist_ok=True)
        (directory / name).chmod(mode)
    if row.get('absolute_link'):
        (directory / 'absolute-link').symlink_to(str(directory.resolve() / 'absent'))
    for name, data in row.get('files', {}).items():
        (directory / name).write_bytes(data)
    for name, target in row.get('links', {}).items():
        (directory / name).symlink_to(target)
    for name, stamp in row.get('times', {}).items():
        os.utime(directory / name, (stamp, stamp))
    if row.get('logical_cwd'):
        (directory / 'logical').symlink_to('tree')
        return directory / 'tree'
    return None
