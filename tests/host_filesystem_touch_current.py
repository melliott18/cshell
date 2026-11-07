"""CSH-113: touch creation and current time, with independent clock bounds.

A one-second floor permits filesystem timestamp truncation; this is a bounded
seconds-resolution witness, not nanosecond accuracy or clock-step qualification.
"""
import os
import stat
import time

from host_filesystem_cases import case
from host_filesystem_reference import BASELINE, REFERENCE, SELECTIONS
from host_filesystem_touch_permissions import CONTENT, TARGET

SECOND = 1000000000


def cases():
    for boundary in ('existing', 'create', 'no-create', 'fixed-create', 'reference-create'):
        for mask, mode in ((0o027, 0o640), (0o077, 0o600), (0o777, 0o000)):
            for selection, flags in SELECTIONS:
                files = {'first': CONTENT, 'last': CONTENT, 'reference': CONTENT}
                if boundary == 'existing':
                    files['target'] = CONTENT
                extra = (['-c'] if boundary == 'no-create' else
                         ['-t', '200109090146.40'] if boundary == 'fixed-create' else
                         ['-r', 'reference'] if boundary == 'reference-create' else [])
                effects = {name: dict(type='file', content=value, mode=0o640)
                           for name, value in files.items()}
                if boundary != 'existing':
                    effects['target'] = (dict(type='absent') if boundary == 'no-create' else
                                         dict(type='file', mode=mode, size=0, nlink=1))
                yield case('touch', f'current-{boundary}-{mask:03o}-{selection}',
                           [*flags, *extra, 'first', 'target', 'last'], ticket='CSH-113',
                           files=files, effects=effects,
                           touch_current=dict(boundary=boundary, mask=mask, created_mode=mode,
                                              access=flags != ['-m'], modify=flags != ['-a']))


def snapshot(path):
    info = path.lstat()
    return dict(device=info.st_dev, inode=info.st_ino, mode=info.st_mode,
                nlink=info.st_nlink, size=info.st_size,
                atime_ns=info.st_atime_ns, mtime_ns=info.st_mtime_ns)


def setup(directory, row):
    if 'touch_current' not in row:
        return None
    if os.getuid() != os.geteuid() or os.geteuid() == 0:
        raise OSError('touch current-time witnesses require one unprivileged identity')
    before, probes = {}, []
    for name in row['files']:
        path = directory / name
        if path.read_bytes() != CONTENT:
            raise OSError('touch current fixture content mismatch')
        path.chmod(0o640)
        stamps = REFERENCE if name == 'reference' else BASELINE
        for requested in ((TARGET, TARGET), stamps):
            os.utime(path, ns=requested)
            info = snapshot(path)
            actual = (info['atime_ns'], info['mtime_ns'])
            if actual != requested:
                raise OSError('filesystem cannot represent authored touch timestamps')
            probes.append(dict(path=name, requested_ns=requested, observed_ns=actual))
        before[name] = snapshot(path)
    return dict(before=before, probes=probes, uid=os.getuid(), euid=os.geteuid())


def clock():
    return dict(realtime_ns=time.time_ns(), monotonic_ns=time.monotonic_ns())


def marker_matches(marker, spec, provider):
    return marker == dict(phase='exec', provider=provider, uid=os.getuid(), euid=os.geteuid(),
                          requested_mask=spec['mask'], observed_mask=spec['mask'],
                          probe_mode=spec['created_mode'])


def verify(directory, row, environment, start, end):
    if environment is None:
        return [], None
    spec = row['touch_current']
    elapsed = end['realtime_ns'] - start['realtime_ns']
    monotonic = end['monotonic_ns'] - start['monotonic_ns']
    errors = []
    if elapsed < 0 or monotonic < 0 or abs(elapsed - monotonic) > SECOND:
        errors.append('touch clock interval moved or is invalid')
    lower, upper = start['realtime_ns'] // SECOND * SECOND, end['realtime_ns']
    names = list(environment['before'])
    if spec['boundary'] not in ('existing', 'no-create'):
        names.append('target')
    # Snapshot before generic effects read file content and change access times.
    after = {}
    for name in names:
        try:
            after[name] = snapshot(directory / name)
        except OSError as error:
            errors.append('touch current missing/unreadable object: ' + name + ': ' + str(error))
    for name, info in after.items():
        before = environment['before'].get(name)
        if before:
            if any(info[key] != before[key] for key in ('device', 'inode', 'mode', 'nlink', 'size')):
                errors.append('touch current identity mismatch: ' + name)
        elif not stat.S_ISREG(info['mode']):
            errors.append('touch creation type mismatch: ' + name)
        for field, selected in (('atime_ns', spec['access']), ('mtime_ns', spec['modify'])):
            index = 0 if field == 'atime_ns' else 1
            expected = None
            if name == 'reference' or (before and not selected):
                expected = before[field]
            elif selected and spec['boundary'] == 'fixed-create':
                expected = TARGET
            elif selected and spec['boundary'] == 'reference-create':
                expected = REFERENCE[index]
            if expected is not None:
                valid = info[field] == expected
            else:
                # Unselected fields of a newly created file retain creation time.
                valid = lower <= info[field] <= upper
            if not valid:
                errors.append('touch current timestamp mismatch: ' + name + '/' + field)
    return errors, dict(start=start, end=end, lower_ns=lower, upper_ns=upper, objects=after)
