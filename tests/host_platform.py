"""Measured filesystem context for an explicitly selected private fixture root."""
from pathlib import Path
import os
import re
import platform


def credential_namespace(proc=Path('/proc/self')):
    """Measure namespace context; numeric IDs alone do not identify credentials."""
    if platform.system() != 'Linux':
        return None
    return dict(uid_map=(proc / 'uid_map').read_text(),
                gid_map=(proc / 'gid_map').read_text(),
                setgroups=(proc / 'setgroups').read_text().strip(),
                user=os.readlink(proc / 'ns/user'),
                mount=os.readlink(proc / 'ns/mnt'))


def filesystem_identity(directory, mountinfo=None):
    directory = Path(directory).resolve()
    measured = directory.stat()
    result = dict(path=str(directory), device=measured.st_dev,
                  platform=platform.system(), mount=None)
    if mountinfo is None and platform.system() == 'Linux':
        mountinfo = Path('/proc/self/mountinfo').read_text()
    if mountinfo is not None:
        candidates = []
        for line in mountinfo.splitlines():
            before, after = line.split(' - ', 1)
            fields, filesystem = before.split(), after.split()
            point = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), fields[4])
            if directory == Path(point) or Path(point) in directory.parents:
                candidates.append((len(point), dict(mountpoint=point, type=filesystem[0],
                    source=filesystem[1], options=fields[5], device=fields[2], root=fields[3])))
        if candidates:
            result['mount'] = max(candidates, key=lambda item: item[0])[1]
    return result
