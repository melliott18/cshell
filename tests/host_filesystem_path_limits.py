"""CSH-090 total pathname bytes, independent of component-name length.

Use repeated ./ components in a private directory: no deep tree, mounts,
capacity consumption, credentials, libc injection or kernel limit changes.
PATH_MAX includes the terminating NUL; the portable minimum is 256 bytes.
"""
import errno
import os

from host_filesystem_cases import case


def cases():
    for portable in (False, True):
        profile = 'portable' if portable else 'filesystem'
        for delta in (-1, 0, 1):
            yield case('pathchk', 'path-limit-' + profile + {-1: '-below', 0: '-at', 1: '-above'}[delta],
                       [], ticket='CSH-090', path_limit=True, portable=portable, deltas=[delta],
                       status=0 if delta < 0 else 'nonzero',
                       err='path-limit-diagnostics')
        # Require a diagnostic for both invalid operands, even after a valid
        # nonexistent operand. Never derive expected diagnostics from a utility.
        yield case('pathchk', 'path-limit-' + profile + '-continuation', [],
                   ticket='CSH-090', path_limit=True, portable=portable, deltas=[0, -1, 1],
                   missing_middle=True, status='nonzero', err='path-limit-diagnostics')


def operand(length, missing=False):
    leaf = ('m' if missing else 'a') * (1 if length % 2 else 2)
    return './' * ((length - len(leaf)) // 2) + leaf


def setup(directory, row):
    if not row.get('path_limit'):
        return None
    path_max = os.pathconf(directory, 'PC_PATH_MAX')
    name_max = os.pathconf(directory, 'PC_NAME_MAX')
    if not 256 <= path_max <= 8192 or name_max < 2:
        raise OSError('finite PATH_MAX in [256,8192] and NAME_MAX >= 2 required')
    for name in ('a', 'aa'):
        (directory / name).mkdir()
    limit = 256 if row['portable'] else path_max
    measurements = []
    args = ['-p'] if row['portable'] else []
    row['diagnostic_operands'] = []
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for index, delta in enumerate(row['deltas']):
            missing = row.get('missing_middle', False) and index == 1
            spelling = operand(limit + delta, missing)
            raw = os.fsencode(spelling)
            # Do not pass the operand through pathlib: it removes ./ and would
            # silently destroy the boundary being independently measured.
            expected_errno = (errno.ENAMETOOLONG if len(raw) >= path_max else
                              errno.ENOENT if missing else 0)
            try:
                info = os.stat(spelling, dir_fd=fd)
            except OSError as error:
                observed_errno = error.errno
            else:
                observed_errno = 0
                target = os.stat('a' if len(raw) % 2 else 'aa', dir_fd=fd)
                if (info.st_dev, info.st_ino) != (target.st_dev, target.st_ino):
                    raise OSError('pathname probe reached a different inode')
            if observed_errno != expected_errno:
                raise OSError('pathname boundary probe returned unexpected errno: ' + str(observed_errno))
            args.append(spelling)
            measurements.append(dict(operand=spelling, bytes=len(raw), bytes_with_nul=len(raw) + 1,
                                     errno=observed_errno, missing=missing))
            if delta >= 0:
                row['diagnostic_operands'].append(spelling)
    finally:
        os.close(fd)
    row['path_byte_limit'] = limit
    row['args'] = args
    row['effects'] = {'a': {'type': 'directory'}, 'aa': {'type': 'directory'},
                      'm': {'type': 'absent'}, 'mm': {'type': 'absent'}}
    return dict(phase='armed', path_max=path_max, name_max=name_max, selected_limit=limit,
                max_component_bytes=2, measurements=measurements,
                probe='pathconf and unnormalized stat operand relative to private directory fd',
                scope='total pathname bytes only; no tree depth, allocation or filesystem exhaustion')


def diagnostics_match(row, output):
    operands = [os.fsencode(name) for name in row['diagnostic_operands']]
    lines = output.splitlines()
    # Wording is unspecified. These C-locale provider dialects must name the
    # complete operand AND identify the length error; an unrelated error cannot
    # qualify the boundary. Separate lines reject missing/duplicate diagnostics.
    return (output.endswith(b'\n') if operands else output == b'') and (
        len(lines) == len(operands)
        and all(name in line and (b'too long' in line.lower() or
                f"limit {row['path_byte_limit'] - 1} exceeded by length {len(name)}".encode() in line)
                for name, line in zip(operands, lines)))
