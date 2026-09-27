"""CSH-059 bounded witnesses; expected bytes are constructed independently."""
import shlex


def cases(paths, utf8_locale):
    def case(name, script, out=b'', status=0, err=b'', **kw):
        return dict(name=name, script=script + '\n', stdout=out, status=status,
                    stderr=err, **kw)

    octets = bytes(range(256))
    yield case('U-035 b all bytes', "printf '%b' '" + ''.join(
        '\\0%03o' % n for n in range(256)) + "'", octets)
    yield case('U-035 format all bytes', "printf '" + ''.join(
        '\\%03o' % n for n in range(256)) + "'", octets)
    for fmt, expected in [('%b', b'a\0bZ'), ('%.3b', b'a\0b'),
                          ('%5.3b', b'  a\0b'), ('%-5.3b', b'a\0b  '),
                          ('%5.0b', b'     '), ('%.b', b'')]:
        yield case('U-035 binary precision ' + fmt,
                   "printf '[" + fmt + "]' 'a\\000bZ'", b'[' + expected + b']')
    yield case('U-035 binary numbered reuse',
               "printf '%2$b:%1$s|' one 'a\\000b' two 'c\\000d'",
               b'a\0b:one|c\0d:two|')
    yield case('U-035 binary stop', "printf '%b:after' 'a\\000b\\cignored' unused", b'a\0b')
    # Retain the vendored implementation's star-width extension separately.
    yield case('U-035 binary star extension', "printf '[%*.*b]' -5 3 'a\\000bZ'", b'[a\0b  ]')
    yield case('U-035 bounded format', "printf '" + 'x' * 8192 + "%s' end", b'x' * 8192 + b'end')
    yield case('U-035 bounded conversions', "printf '" + '%s' * 256 + "' " + 'x ' * 256, b'x' * 256)
    yield case('U-035 bounded b allocation', "printf '%b' '" + 'x' * 8192 + "'", b'x' * 8192)
    yield case('U-035 bounded b width', "printf '%8192b' x", b' ' * 8191 + b'x')
    yield case('U-036 bounded single argument', "echo '" + 'x' * 8192 + "'", b'x' * 8192 + b'\n')
    yield case('U-036 bounded argument count', 'echo ' + 'word ' * 256, b' '.join([b'word'] * 256) + b'\n')
    if utf8_locale:
        env = {'LC_ALL': utf8_locale}
        yield case('U-035 UTF-8 byte precision', "printf '[%.1s][%.1b]' é é", b'[\xc3][\xc3]', env=env)
        yield case('U-036 UTF-8 operands', 'echo é 中', 'é 中\n'.encode(), env=env)
        yield case('U-040 sed UTF-8 character', "sed 's/^.$/match/' unicode", b'match\nmatch\n',
                   env=env, input_files={'unicode': 'é\n中\n'.encode()})
        yield case('U-040 ls UTF-8 filenames', 'ls -1 unicode-tree', 'é\n'.encode(),
                   env=env, input_files={'unicode-tree/é': b''})
    # These are finite successful sizes, never claimed utility maxima.
    payload = b'x' * 32768 + b'\n'
    yield case('U-040 sed bounded hold space', "sed -n 'h;g;p' payload >bytes",
               input_files={'payload': payload}, files={'bytes': payload})
    payload = bytes(range(256)) * 256
    yield case('U-040 cat bounded file', 'cat payload >bytes',
               input_files={'payload': payload}, files={'bytes': payload})
    yield case('U-040 head large count short input', 'head -n 2147483647 data', b'one\ntwo\n')
    yield case('U-040 cmp different silent', 'cmp -s first second', status=1)
    yield case('U-040 cmp EOF', 'cmp empty data', status=1, err='nonempty', input_files={'empty': b''})
    yield case('U-040 cmp bounded offset', 'cmp -s left right', status=1,
               input_files={'left': b'x' * 65536 + b'a', 'right': b'x' * 65536 + b'b'})
    yield case('U-040 ed bounded edit buffer', "ed -s edit-buffer <<'END'\n1,$p\nq\nEND",
               b'line\n' * 1024, requires='ed', input_files={'edit-buffer': b'line\n' * 1024})
    tree = '/'.join(['deep'] + ['d'] * 32 + ['leaf'])
    yield case('U-040 find bounded depth', 'find deep -type f', (tree + '\n').encode(),
               input_files={tree: b''})
    yield case('U-040 rm bounded depth', 'rm -r deep && test ! -e deep', input_files={tree: b''})
    names = ['entry%03d' % n for n in range(256)]
    yield case('U-040 ls bounded directory', 'ls -1 entries', ('\n'.join(names) + '\n').encode(),
               input_files={'entries/' + name: b'' for name in names})
    # Force the inventoried external pwd, avoiding the PATH-associated builtin.
    if paths['pwd']:
        yield case('U-040 pwd deleted cwd', 'mkdir gone && cd gone && rmdir ../gone && ' +
                   shlex.quote(paths['pwd']) + ' -P', status='nonzero', err='nonempty')
