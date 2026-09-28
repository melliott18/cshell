"""CSH-061 private Linux ACL witnesses with independent I/O controls."""
import os
from pathlib import Path
import shlex
import subprocess


def cases(paths, helper):
    for inherited in (False, True):
        for subject in ('user', 'group'):
            for permission in ('r', 'w', 'x'):
                for access in ('grant', 'unrelated', 'masked'):
                    allowed = access == 'grant'
                    uid = 10002 if subject == 'group' or access == 'unrelated' else 10001
                    groups = subject == 'group' and access != 'unrelated'
                    identity = 'identity-group' if groups else 'identity'
                    prefix = f'{helper} {identity} {uid} {uid} '
                    output = (f'uid={uid} euid={uid} gid={uid} egid={uid} groups=' +
                              ('1:10003\n' if groups else '0\n')).encode()
                    fixture = dict(subject=subject, permission=permission,
                                   inherited=inherited, masked=access == 'masked',
                                   helper=shlex.split(helper)[0])
                    name = f'U-037 ACL {subject} {permission} {access} inherited={inherited}'
                    for utility in ('test', '[', 'operation'):
                        command = (shlex.quote(paths[utility]) + f' -{permission} controlled' +
                                   (' ]' if utility == '[' else '')) if utility != 'operation' else {
                            'r': shlex.quote(paths['cat']) + ' controlled',
                            'w': helper + ' acl-write controlled',
                            'x': './controlled acl-executed',
                        }[permission]
                        out = output + (dict(r=b'private\n', w=b'', x=b'executed\n')[permission]
                                        if utility == 'operation' and allowed else b'')
                        files = ({'controlled': b'private\n' + (b'written\n' if allowed else b'')}
                                 if utility == 'operation' and permission == 'w' else {})
                        yield dict(name=name + ' ' + utility, script=prefix + command + '\n',
                                   stdout=out, stderr='nonempty' if utility == 'operation' and not allowed else b'',
                                   status=0 if allowed else (2 if utility == 'operation' and permission == 'x' else 1),
                                   controlled_fixture=fixture, files=files)


def setup(directory, spec):
    """Inherit defaults at creation; never reapply an access ACL to the child."""
    directory.chmod(0o755)
    parent = directory / 'acl-parent'
    parent.mkdir(mode=0o755)
    target = parent / 'child'
    perms = {'r': 'r--', 'w': '-w-', 'x': '--x'}[spec['permission']]
    subject = 'u:10001' if spec['subject'] == 'user' else 'g:10003'
    entries = 'u::---,g::---,o::---,' + subject + ':' + perms + ',m::' + (
        '---' if spec['masked'] else perms)
    def acl(path, default=False):
        subprocess.run(['setfacl', '-m', ','.join(('d:' if default else '') + entry
                        for entry in entries.split(',')), str(path)],
                       check=True, capture_output=True, timeout=5)
    if spec['inherited']:
        acl(parent, True)
    # Explicit creation mode allows all inherited permissions; umask cannot
    # mask a default ACL. No chmod after creation, which would change its mask.
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o777)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(Path(spec['helper']).read_bytes() if spec['permission'] == 'x' else b'private\n')
    if not spec['inherited']:
        acl(target)
    (directory / 'controlled').symlink_to('acl-parent/child')
    observed = target.stat()
    def record(path):
        return subprocess.check_output(['getfacl', '-cpn', str(path)], timeout=5).decode()
    return dict(kind=spec, uid=observed.st_uid, gid=observed.st_gid,
                mode=oct(observed.st_mode), rdev=observed.st_rdev,
                acl=record(target), parent_acl=record(parent))
