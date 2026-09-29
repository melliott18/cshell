#!/usr/bin/env python3
"""Private exec wrapper: record the actual child identity before invoking a provider."""
import json
import os
import errno
import subprocess
from pathlib import Path
import sys


def identity():
    result = dict(uid=os.getuid(), euid=os.geteuid(), gid=os.getgid(),
                  egid=os.getegid(), groups=os.getgroups())
    if sys.platform.startswith('linux'):
        result['resuid'] = os.getresuid()
        result['resgid'] = os.getresgid()
        result['capabilities'] = {line.split(':')[0]: line.split(':')[1].strip()
                                  for line in Path('/proc/self/status').read_text().splitlines()
                                  if line.startswith('Cap')}
    try:
        result['login'] = os.getlogin()
    except OSError as error:
        result['login_error'] = error.errno
    return result


def main():
    if sys.argv[1] == '--session-observe':
        mask = os.umask(0)
        os.umask(mask)
        observed = identity()
        observed.update(cwd=os.getcwd(), umask=mask, exported=os.environ.get('CSH_071_EXPORTED'))
        Path('session.json').write_text(json.dumps(observed))
        print('new-shell')
        return
    spec = json.loads(Path(sys.argv[1]).read_text())
    if spec.get('credentials'):
        real, effective = spec['credentials']
        os.setgroups([])
        os.setresgid(real, effective, effective)
        os.setresuid(real, effective, effective)
    observed = identity()
    if spec.get('access'):
        permission = spec['access']['permission']
        try:
            if permission == 'x':
                completed = subprocess.run(['./access'], capture_output=True, timeout=1)
                observed['access'] = dict(allowed=completed.returncode == 0,
                                         status=completed.returncode,
                                         stdout=completed.stdout.hex(), stderr=completed.stderr.hex())
            else:
                fd = os.open('access', os.O_RDONLY if permission == 'r' else os.O_WRONLY | os.O_APPEND)
                try:
                    if permission == 'r':
                        observed['access'] = dict(allowed=True, data=os.read(fd, 4096).hex())
                    else:
                        count = os.write(fd, b'written\n')
                        observed['access'] = dict(allowed=True, count=count)
                finally:
                    os.close(fd)
        except OSError as error:
            if error.errno not in (errno.EACCES, errno.EPERM):
                raise
            observed['access'] = dict(allowed=False, errno=error.errno)
    Path('identity.json').write_text(json.dumps(observed))
    os.umask(spec['umask'])
    os.execv(spec['executable'], spec['argv'])


if __name__ == '__main__':
    main()
