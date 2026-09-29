"""Focused ACL, effective-credential and ownership witnesses for CSH-071."""
import os
from pathlib import Path
import pwd
import re
import subprocess

from host_permission_cases import case


def cases(darwin_acls=False, controlled=False, darwin_credentials=False):
    # Equal credentials on ordinary hosts; independent UID/GID/supplementary
    # choices in a disposable Linux root environment.
    if controlled:
        for real, effective in ((10001, 10002), (10002, 10001)):
            for args, value in ((['-u'], effective), (['-ur'], real),
                                (['-g'], 10004), (['-gr'], 10003)):
                yield case('id', f'credentials-{real}-{effective}-{args[0]}', args,
                           out=f'{value}\n'.encode(), credentials=[real, effective],
                           gids=[10003, 10004], supplementary=[10005, 10006], modes=('direct',))
            yield case('id', f'credentials-groups-{real}-{effective}', ['-G'], groups=True,
                       credentials=[real, effective], gids=[10003, 10004],
                       supplementary=[10005, 10006], modes=('direct',))
        for utility in ('chmod', 'chown', 'chgrp'):
            operand = {'chmod': '600', 'chown': '10002', 'chgrp': '10002'}[utility]
            yield case(utility, 'non-owner-preservation', [operand, 'subject'],
                       credentials=[10002, 10002], initial_owner=[10001, 10001],
                       status='nonzero', err='nonempty',
                       metadata={'subject': {'uid': 10001, 'gid': 10001, 'mode': 0o644}})

    if os.geteuid() != 0:
        uid, gid = os.geteuid(), os.getegid()
        groups = sorted(set(os.getgroups()) - {gid})
        for utility, operand in (('chown', str(uid)), ('chgrp', str(gid))):
            yield case(utility, 'unprivileged-setid-clear', [operand, 'subject'],
                       initial=0o6755, metadata={'subject': {'uid': uid, 'gid': gid, 'mode': 0o755}})
        if groups:
            target = groups[0]
            yield case('chgrp', 'supplementary-group-change', [str(target), 'subject'],
                       metadata={'subject': {'uid': uid, 'gid': target, 'mode': 0o644}},
                       ctime_update=True)
        yield case('chmod', 'ctime-update', ['600', 'subject'],
                   metadata={'subject': {'mode': 0o600}}, ctime_update=True)

    if not darwin_acls:
        return
    user = pwd.getpwnam(os.environ['SUDO_USER']) if darwin_credentials else pwd.getpwuid(os.geteuid())
    alternate = pwd.getpwnam('daemon') if darwin_credentials else user
    helper = str(Path(__file__).resolve().parent.parent / 'build/tests/host_utility_helper')
    for permission in ('r', 'w', 'x'):
        for inherited in (False, True):
            for actions in ([], ['allow'], ['deny'], ['deny', 'allow'], ['allow', 'deny']):
                allowed = bool(actions) and actions[0] == 'allow'
                # The second identity makes real and effective IDs disagree in
                # both directions while retaining the same file/ACL principal.
                credentials = ([None] if not darwin_credentials else
                               [[alternate.pw_uid, user.pw_uid], [user.pw_uid, alternate.pw_uid]])
                for pair in credentials:
                    effective_matches = pair is None or pair[1] == user.pw_uid
                    expected = allowed and effective_matches
                    # Deny fixtures have mode 0777 to prove the ACL takes precedence;
                    # grants use mode 000 to prove access came from the ACL.
                    # Unequal-ID unrelated subjects use mode 000 for a true denial.
                    mode = 0 if allowed or darwin_credentials or not actions else 0o777
                    if permission == 'x' and mode == 0:
                        # Darwin exec requires some execute mode bit even when
                        # the ACL grants execute. Group X is unavailable to the
                        # owner (owner precedence), or to either dropped subject
                        # of root-owned fixtures. The empty-ACL control proves it.
                        mode = 0o454
                    for utility in ('test', '['):
                        for negate in (False, True):
                            label = f'ACL-{permission}-{inherited}-{"-".join(actions)}-{pair}-{negate}'
                            yield case(utility, label, (['!'] if negate else []) + ['-' + permission, 'access'],
                                       status=0 if expected != negate else 1,
                                       access=dict(permission=permission, allowed=expected, binary=permission == 'x'),
                                       acl=dict(user=user.pw_name, actions=actions, inherited=inherited, mode=mode, helper=helper),
                                       credentials=pair, **({'gids': [pwd.getpwuid(i).pw_gid for i in pair]} if pair else {}), modes=('direct',) if pair else ('direct', 'string', 'file', 'stdin'))


def setup_acl(root, spec, permission):
    """Set and verify private Darwin ACL entries; report ignored setup as failure."""
    parent = root / 'acl-parent'
    parent.mkdir(mode=0o755)
    target = parent / 'access'
    rights = {'r': {'read'}, 'w': {'write', 'append'}, 'x': {'execute'}}[permission]

    def install(path, inherited):
        for index, action in enumerate(spec['actions']):
            permissions = sorted(rights | ({'file_inherit', 'only_inherit'} if inherited else set()))
            subprocess.run(['/bin/chmod', '+a#', str(index),
                            f'user:{spec["user"]} {action} ' + ','.join(permissions), str(path)],
                           check=True, capture_output=True, timeout=5)

    if spec['inherited']:
        install(parent, True)
    data = Path(spec['helper']).read_bytes() if permission == 'x' else b'private\n'
    # Write through the creation descriptor even when the inherited ACL denies
    # later opens. Do not chmod after inheritance: that would change the fixture.
    old = os.umask(0)
    try:
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, spec['mode'])
    finally:
        os.umask(old)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
    if not spec['inherited']:
        install(target, False)
    (root / 'access').unlink()
    (root / 'access').symlink_to('acl-parent/access')
    output = subprocess.check_output(['/bin/ls', '-lde', str(target)], text=True, timeout=5)
    entries = []
    for line in output.splitlines()[1:]:
        match = re.fullmatch(r'\s*(\d+): user:(\S+) (inherited )?(allow|deny) (.*)', line)
        if not match:
            raise OSError('malformed ACL metadata: ' + output)
        entries.append(dict(index=int(match[1]), user=match[2], inherited=bool(match[3]),
                            action=match[4], rights=set(match[5].split(','))))
    expected = [dict(index=i, user=spec['user'], inherited=spec['inherited'], action=a, rights=rights)
                for i, a in enumerate(spec['actions'])]
    if entries != expected or (target.stat().st_mode & 0o777) != spec['mode']:
        raise OSError('ACL fixture differs from authored metadata: ' + output)
    return output


def clear_acls(root):
    # Clear only our owned fixture ACLs so failed/denied cases can be removed.
    for name in ('acl-parent/access', 'acl-parent'):
        path = root / name
        if path.exists():
            subprocess.run(['/bin/chmod', '-N', str(path)], check=True, capture_output=True, timeout=5)
