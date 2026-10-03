"""CSH-060 controlled environments; no selected utility generates an oracle."""
import os
import shlex
import stat
import subprocess
from host_acl_cases import cases as acl_cases, setup as setup_acl, verify_acl_metadata


def cases(paths, helper, printf_faults, locales, controlled, unequal_acl=False):
    def case(name, script, out=b'', status=0, err=b'', **kw):
        return dict(name=name, script=script + '\n', stdout=out, status=status,
                    stderr=err, **kw)

    # Authored decimal/base/sign/padding expectations, not differential output.
    formats = [('%d', '-12', '-12'), ('%i', '012', '10'), ('%u', '12', '12'),
               ('%o', '10', '12'), ('%x', '31', '1f'), ('%X', '31', '1F'),
               ('%+06d', '12', '+00012'), ('% 6d', '12', '    12'),
               ('%-6d', '-12', '-12   '), ('%06d', '-12', '-00012'),
               ('%6.4d', '12', '  0012'), ('%06.4d', '12', '  0012'),
               ('%#o', '10', '012'), ('%#x', '31', '0x1f'),
               ('%#X', '31', '0X1F'), ('%.0d', '0', ''),
               ('%#.0o', '0', '0'), ('%5.0u', '0', '     '),
               ('%5c', 'xyz', '    x'), ('%-5s', 'xy', 'xy   '),
               ('%5.2s', 'xyz', '   xy'), ('%-5.2s', 'xyz', 'xy   '),
               ('%.2f', '1.5', '1.50'), ('%+.1e', '1.5', '+1.5e+00'),
               ('%.1E', '1.5', '1.5E+00'), ('%.3g', '1.5', '1.5'),
               ('%#.3G', '1.5', '1.50')]
    for fmt, operand, expected in formats:
        yield case('U-035 format matrix ' + fmt,
                   'printf ' + shlex.quote('[' + fmt + ']') + ' ' + shlex.quote(operand),
                   ('[' + expected + ']').encode())
    for fmt in ('%', '%Q', '%2147483648b', '%.2147483648b'):
        yield case('U-035 format failure ' + fmt, 'printf ' + shlex.quote(fmt) + ' x',
                   status='nonzero', err='nonempty')
    if printf_faults:
        for kind, fmt in [('strdup', '%b'), ('realloc', '%d')]:
            for fail in (False, True):
                yield case('U-035 allocation ' + kind + (' failure' if fail else ' control'),
                           shlex.quote(str(printf_faults)) + ' ' + shlex.quote(fmt) + ' 12',
                           b'' if fail else b'12', 1 if fail else 0,
                           'nonempty' if fail else b'',
                           env={'CSH_PRINTF_FAIL': kind if fail else ''})
    if locales.get('german'):
        yield case('U-035 German numeric', "printf '%.2f' 1,5", b'1,50',
                   env={'LC_ALL': locales['german']})
    if locales.get('gb18030'):
        env = {'LC_ALL': locales['gb18030']}
        # Both two-byte and four-byte characters; Python's codec defines data.
        payload = '中\U00010000'.encode('gb18030')
        yield case('U-035 GB18030 byte operands', "printf '%b' '" + ''.join(
            '\\0%03o' % n for n in payload) + "'", payload, env=env)
        yield case('U-040 sed GB18030 characters', "sed 's/./x/g' encoded", b'xx\n',
                   env=env, input_files={'encoded': payload + b'\n'})
    for utility in ('echo', 'env', 'true', 'false'):
        for shape in ('single', 'aggregate'):
            yield case('U-040 exec E2BIG ' + utility + ' ' + shape,
                       helper + ' exec-size ' + shape + ' ' + shlex.quote(paths[utility]),
                       b'E2BIG\n', exec_boundary={'shape': shape,
                           'system_query': 'child ARG_MAX', 'allocation_cap_bytes': 16 * 1024 * 1024 + 65537,
                           'environment': ['LC_ALL=C'], 'expect_errno': 'E2BIG',
                           'claim': 'oversized exec rejected before utility entry; not an exact threshold'})
    for command in ('cat long', "sed -n p long"):
        yield case('U-040 file limit ' + command, helper + ' small-file ' + command + ' >limited',
                   status='nonzero', err='nonempty', files={'limited': b'x' * 1024},
                   resource_override={'RLIMIT_FSIZE': [1024, 1024], 'SIGXFSZ': 'ignored'})
    for answer in ('n', 'y'):
        yield case('U-040 rm prompt ' + answer,
                   "rm -i remove <<'ANSWER'\n" + answer + '\nANSWER', err='nonempty',
                   files={'remove': b'' if answer == 'n' else None})
    if locales.get('utf8'):
        yield case('U-040 find UTF-8 question mark', "find names -name '?' -type f", 'names/é\n'.encode(),
                   env={'LC_ALL': locales['utf8']}, input_files={'names/é': b'', 'names/aa': b''})
    if controlled:
        yield from acl_cases(paths, helper, unequal_acl)
        for kind in ('owner', 'group', 'acl'):
            identities = ((10001, 10001), (10002, 10002)) if kind == 'acl' and not unequal_acl else (
                (10002, 10001), (10001, 10002))
            for real, effective in identities:
                prefix = f'uid={real} euid={effective} gid={real} egid={effective} groups=0\n'.encode()
                if kind == 'acl':
                    # Independently witness an actual open/read of the authored
                    # private bytes under the same credentials as the predicate.
                    allowed = effective == 10001
                    yield case(f'U-037 ACL read control real={real} effective={effective}',
                               f'{helper} identity {real} {effective} ' + shlex.quote(paths['cat']) +
                               ' controlled', prefix + (b'private\n' if allowed else b''),
                               0 if allowed else 1, b'' if allowed else 'nonempty', controlled_fixture=kind)
                for utility in ('test', '['):
                    suffix = ' ]' if utility == '[' else ''
                    yield case(f'U-037 {kind} {utility} real={real} effective={effective}',
                               f'{helper} identity {real} {effective} ' + shlex.quote(paths[utility]) +
                               ' -r controlled' + suffix, prefix, 0 if effective == 10001 else 1,
                               controlled_fixture=kind)
        yield case('U-040 chmod cross-user denial',
                   helper + ' identity 10002 10002 ' + shlex.quote(paths['chmod']) + ' 600 controlled',
                   b'uid=10002 euid=10002 gid=10002 egid=10002 groups=0\n',
                   status=1, err='nonempty', controlled_fixture='owner')
        for utility in ('test', '['):
            suffix = ' ]' if utility == '[' else ''
            for kind, predicate in (('block', 'b'), ('character', 'c')):
                yield case(f'U-037 private {kind} namespace {utility}',
                           shlex.quote(paths[utility]) + ' -' + predicate + ' controlled' + suffix,
                           controlled_fixture=kind)


def setup_controlled(directory, kind, device_fixtures=None):
    """Root-only disposable Linux fixtures. Devices are created/stat'ed, never opened."""
    if isinstance(kind, dict):
        return setup_acl(directory, kind)
    directory.chmod(0o755)
    target = directory / 'controlled'
    if kind in ('block', 'character'):
        mode = stat.S_IFBLK if kind == 'block' else stat.S_IFCHR
        if device_fixtures is None:
            os.mknod(target, mode | 0o600, os.makedev(7, 255) if kind == 'block' else os.makedev(1, 3))
        else:
            source = (device_fixtures / kind).absolute()
            witness = source.lstat()
            if stat.S_IFMT(witness.st_mode) != mode:
                raise OSError('supplied device witness has wrong type: ' + str(source))
            # A parent namespace may supply private nodes when this namespace
            # cannot mknod. These predicates only stat the target; never open it.
            target.symlink_to(source)
    else:
        target.write_bytes(b'private\n')
        if kind == 'owner':
            os.chown(target, 10001, 10002)
            target.chmod(0o400)
        elif kind == 'group':
            os.chown(target, 0, 10001)
            target.chmod(0o040)
        elif kind == 'acl':
            target.chmod(0)
            subprocess.run(['setfacl', '-m', 'u:10001:r--,m::r--', str(target)],
                           check=True, capture_output=True, timeout=5)
        else:
            raise ValueError('unknown controlled fixture: ' + kind)
    observed = target.stat()
    result = dict(kind=kind, uid=observed.st_uid, gid=observed.st_gid,
                  mode=oct(observed.st_mode), rdev=observed.st_rdev)
    if kind in ('block', 'character') and device_fixtures is not None:
        if (observed.st_dev, observed.st_ino) != (witness.st_dev, witness.st_ino):
            raise OSError('supplied device witness changed during setup')
        result['supplied_device'] = dict(path=str(source), device=witness.st_dev,
                                         inode=witness.st_ino, stat_only=True)
    if kind == 'acl':
        result['acl'] = subprocess.check_output(['getfacl', '-cpn', str(target)], timeout=5).decode()
        verify_acl_metadata(dict(acl_entries='u::---,u:10001:r--,g::---,m::r--,o::---',
                                 inherited=False), result['acl'], observed)
    return result
