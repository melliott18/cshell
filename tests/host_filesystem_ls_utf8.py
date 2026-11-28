"""CSH-124: UTF-8 character rendering with independently fixed C collation.

Authored valid two-, three- and four-byte printable characters and C1 controls.
No invalid encodings, arbitrary repertoires or non-C sorting are qualified.
"""
import ctypes
import json
import locale
import subprocess
import sys
import os
import stat

if __name__ != '__main__':
    from host_filesystem_cases import case
    from host_filesystem_ls_blocks import measurements
    from host_filesystem_ls_identity import output_matches

DIRECTORY = 'dir-中\n'
FIFO = 'fifo-Ω\t'
EXECUTABLE = 'exec-𐐀\r'
LINK = 'link-中\x1b'
# Same-prefix names distinguish original byte sorting from sorting replaced
# names, and preserve collisions between literal '?' and replaced characters.
FILES = {n: n.encode('utf-8') for n in
         ('same-?', 'same-\x85', 'same-\x9f', 'same-Ω', 'same-中', 'same-𐐀',
          'mixed-Ω\x85中\x9f𐐀', ' space-中 ', 'punct-Ω\'"$`*?[\\', EXECUTABLE)}
FILES[DIRECTORY + '/guard'] = b'not listed'
ENTRIES = tuple(sorted([n for n in FILES if '/' not in n] + [DIRECTORY, FIFO, LINK],
                       key=lambda n: n.encode('utf-8')))
NAMES = (*FILES, DIRECTORY, FIFO, LINK)
NONPRINT = '\n\t\r\x1b\x85\x9f'
PRINTABLE = 'Ω中𐐀? '


def probe_locale(utf8):
    """Check libc character classes in a bounded child, without changing ours."""
    if not utf8:
        raise OSError('UTF-8 locale required for ls character witnesses')
    result = subprocess.run(
        [sys.executable, '-I', '-S', str(__file__), '--probe', utf8],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5,
        env={'LC_ALL': 'C', 'PATH': os.defpath})
    if result.returncode or result.stderr:
        raise OSError('ls UTF-8 locale probe failed: ' + result.stderr.decode(errors='replace'))
    observed = json.loads(result.stdout)
    expected = {str(ord(c)): c in PRINTABLE for c in NONPRINT + PRINTABLE}
    if (observed.get('printable') != expected or observed.get('collate') != 'C'
            or observed.get('codeset', '').lower().replace('-', '') != 'utf8'):
        raise OSError('ls UTF-8 character-class prerequisites not supplied')
    return observed


def cases():
    for graph in ('directory', 'operands'):
        for quote in (False, True):
            for style in ('plain', 'F', 'p'):
                for inode in (False, True):
                    for reverse in (False, True):
                        options = ['-1', *(['-q'] if quote else []),
                                   *([] if style == 'plain' else ['-' + style]),
                                   *(['-i'] if inode else []), *(['-r'] if reverse else [])]
                        operands = (['utf8-names'] if graph == 'directory' else
                                    ['-d', *['utf8-names/' + n for n in reversed(ENTRIES)]])
                        yield case('ls', f'utf8-{graph}-{int(quote)}-{style}-{int(inode)}-{int(reverse)}',
                                   options + operands, ticket='CSH-124', out='ls-utf8', utf8=True, ctype_only=True,
                                   ls_utf8=dict(graph=graph, quote=quote, style=style,
                                                 inode=inode, reverse=reverse))


def expected_entries(before, spec):
    entries = []
    for name in sorted(ENTRIES, key=lambda n: n.encode('utf-8'), reverse=spec['reverse']):
        # Replace characters, not their constituent UTF-8 bytes.
        display = ''.join('?' if c in NONPRINT else c for c in name) if spec['quote'] else name
        if spec['graph'] == 'operands':
            display = 'utf8-names/' + display
        mode = before[name]['mode']
        if spec['style'] in ('F', 'p') and stat.S_ISDIR(mode):
            display += '/'
        elif spec['style'] == 'F':
            if stat.S_ISLNK(mode):
                display += '@'
            elif stat.S_ISFIFO(mode):
                display += '|'
            elif stat.S_ISREG(mode) and mode & 0o111:
                display += '*'
        entries.append(dict(name=display, inode=before[name]['inode'] if spec['inode'] else None))
    return entries


def setup(directory, row, utf8):
    if 'ls_utf8' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('ls name witnesses require one unprivileged identity')
    locale_probe = probe_locale(utf8)
    root = directory / 'utf8-names'
    root.mkdir()
    (root / DIRECTORY).mkdir()
    for name, content in FILES.items():
        (root / name).write_bytes(content)
        (root / name).chmod(0o700 if name == EXECUTABLE else 0o600)
    os.mkfifo(root / FIFO, 0o600)
    (root / LINK).symlink_to(DIRECTORY)
    if sorted(os.listdir(os.fsencode(root))) != sorted(n.encode('utf-8') for n in ENTRIES):
        raise OSError('authored filename bytes were not preserved')
    before = measurements(root, NAMES)
    for name, info in before.items():
        kind = (stat.S_IFDIR if name == DIRECTORY else stat.S_IFIFO if name == FIFO
                else stat.S_IFLNK if name == LINK else stat.S_IFREG)
        if stat.S_IFMT(info['mode']) != kind or info['inode'] <= 0:
            raise OSError('ls name type/inode probe failed')
        if name in FILES and stat.S_IMODE(info['mode']) != (0o700 if name == EXECUTABLE else 0o600):
            raise OSError('ls name authored mode probe failed')
    target = (root / LINK).stat()
    if (target.st_dev, target.st_ino, target.st_mode) != tuple(before[DIRECTORY][k] for k in ('device', 'inode', 'mode')):
        raise OSError('ls name symlink referent probe failed')
    return dict(before=before, entries=expected_entries(before, row['ls_utf8']),
                uid=os.getuid(), euid=os.geteuid(), locale_probe=locale_probe,
                probe='authored UTF-8 bytes and independent libc character classes with pre-exec listdir/lstat and stat referent probes')


def verify(directory, environment):
    if environment is None:
        return [], None
    root = directory / 'utf8-names'
    after = measurements(root, NAMES)
    errors = []
    if after != environment['before']:
        errors.append('ls name metadata changed')
    for name, content in FILES.items():
        if (root / name).read_bytes() != content:
            errors.append('ls name bytes changed: ' + name)
    if os.readlink(root / LINK) != DIRECTORY:
        errors.append('ls name symlink changed')
    if sorted(os.listdir(root)) != list(ENTRIES) or os.listdir(root / DIRECTORY) != ['guard']:
        errors.append('ls name directory entries changed')
    return errors, after


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--probe':
        raise SystemExit('usage: host_filesystem_ls_utf8.py --probe LOCALE')
    locale.setlocale(locale.LC_ALL, 'C')
    locale.setlocale(locale.LC_CTYPE, sys.argv[2])
    libc = ctypes.CDLL(None)
    libc.iswprint.argtypes = [ctypes.c_uint32]
    libc.iswprint.restype = ctypes.c_int
    print(json.dumps(dict(ctype=locale.setlocale(locale.LC_CTYPE),
                          collate=locale.setlocale(locale.LC_COLLATE),
                          codeset=locale.nl_langinfo(locale.CODESET),
                          printable={str(ord(c)): bool(libc.iswprint(ord(c)))
                                     for c in NONPRINT + PRINTABLE})))
