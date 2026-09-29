"""CSH-061/062/063 private Linux ACL witnesses with independent I/O controls."""
import errno
import os
from pathlib import Path
import shlex
import subprocess


def cases(paths, helper, unequal=False):
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

    yield from combinations(paths, helper, unequal)
    from host_acl_residual_cases import cases as residual_cases
    yield from residual_cases(paths, helper, unequal)


def combinations(paths, helper, unequal=False):
    """Multiple entries, named-user precedence, and actual supplementary sets."""
    for inherited in (False, True):
        for permission, perms in (("r", "r--"), ("w", "-w-"), ("x", "--x")):
            scenarios = [
                ("second-user", 10002, False, f"u:10001:---,u:10002:{perms}", True),
                ("first-group", 10002, True, f"g:10003:{perms},g:10004:---", True),
                ("second-group", 10002, True, f"g:10003:---,g:10004:{perms}", True),
                ("user-precedence", 10001, True, f"u:10001:---,g:10003:{perms},g:10004:{perms}", False),
                ("unrelated-groups", 10002, True, f"g:10005:{perms}", False),
                ("masked-groups", 10002, True, f"g:10003:{perms},g:10004:{perms}", False),
            ]
            for label, effective, groups, entries, allowed in scenarios:
                real = (10001 if effective == 10002 else 10002) if unequal else effective
                identity = "identity-groups" if groups else "identity"
                prefix = f"{helper} {identity} {real} {effective} "
                output = (f"uid={real} euid={effective} gid={real} egid={effective} groups=" +
                          ("2:10003:10004\n" if groups else "0\n")).encode()
                fixture = dict(subject="multiple", entries=entries, permission=permission,
                               inherited=inherited, masked=label == "masked-groups",
                               helper=shlex.split(helper)[0])
                for utility in ("test", "[", "operation"):
                    command = (shlex.quote(paths[utility]) + f" -{permission} controlled" +
                               (" ]" if utility == "[" else "")) if utility != "operation" else {
                        "r": shlex.quote(paths["cat"]) + " controlled",
                        "w": helper + " acl-write controlled",
                        "x": "./controlled acl-executed",
                    }[permission]
                    out = output + (dict(r=b"private\n", w=b"", x=b"executed\n")[permission]
                                    if utility == "operation" and allowed else b"")
                    files = ({"controlled": b"private\n" + (b"written\n" if allowed else b"")}
                             if utility == "operation" and permission == "w" else {})
                    yield dict(name=f"U-037 ACL combinations {label} {permission} inherited={inherited} unequal={unequal} {utility}",
                               script=prefix + command + "\n", stdout=out, files=files,
                               stderr="nonempty" if utility == "operation" and not allowed else b"",
                               status=0 if allowed else (2 if utility == "operation" and permission == "x" else 1),
                               controlled_fixture=fixture)


def setup(directory, spec):
    """Inherit defaults at creation; never reapply an access ACL to the child."""
    directory.chmod(0o755)
    parent = directory / 'acl-parent'
    parent.mkdir(mode=0o755)
    target = parent / 'child'
    perms = {'r': 'r--', 'w': '-w-', 'x': '--x'}[spec['permission']]
    subject = 'u:10001' if spec['subject'] == 'user' else 'g:10003'
    entries = 'u::---,g::---,o::---,' + spec.get('entries', subject + ':' + perms) + ',m::' + (
        '---' if spec['masked'] else perms)
    entries = spec.get('acl_entries', entries)
    def acl(path, default=False):
        subprocess.run(['setfacl', '-m', ','.join(('d:' if default else '') + entry
                        for entry in entries.split(',')), str(path)],
                       check=True, capture_output=True, timeout=5)
    if spec['inherited']:
        acl(parent, True)
    # Default creation allows every inherited permission; CSH-063 also
    # explicitly restricts the creation mode. Never chmod the inherited child.
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, spec.get('create_mode', 0o777))
    with os.fdopen(fd, 'wb') as stream:
        stream.write(Path(spec['helper']).read_bytes() if spec['permission'] == 'x' else b'private\n')
    if 'owner' in spec or 'group' in spec:
        os.chown(target, spec.get('owner', 0), spec.get('group', 0))
    if not spec['inherited']:
        acl(target)
    (directory / 'controlled').symlink_to('acl-parent/child')
    observed = target.stat()
    def record(path):
        return subprocess.check_output(['getfacl', '-cpn', str(path)], timeout=5).decode()
    actual_acl = record(target)
    verify_acl_metadata(dict(spec, acl_entries=entries), actual_acl, observed)
    return dict(kind=spec, uid=observed.st_uid, gid=observed.st_gid,
                mode=oct(observed.st_mode), rdev=observed.st_rdev,
                acl=actual_acl, parent_acl=record(parent))


def verify_acl_metadata(spec, actual, observed):
    """Reject malformed/ignored setup before attributing results to a utility."""
    tags = {'u': 'user', 'g': 'group', 'm': 'mask', 'o': 'other'}
    expected = {}
    for entry in spec['acl_entries'].split(','):
        tag, qualifier, perms = entry.split(':')
        expected[tags[tag] + ':' + qualifier] = perms
    if spec['inherited']:
        mode = spec.get('create_mode', 0o777)
        for key, shift in (('user:', 6), ('mask:', 3), ('other:', 0)):
            expected[key] = ''.join(char if mode & (bit << shift) else '-'
                                    for char, bit in zip(expected[key], (4, 2, 1)))
    entries = {}
    for line in actual.splitlines():
        line = line.split('#', 1)[0].strip()
        if line:
            parts = line.split(':')
            if (len(parts) != 3 or parts[0] not in tags.values() or
                    len(parts[2]) != 3 or
                    any(char not in ('-', allowed) for char, allowed in zip(parts[2], 'rwx'))):
                raise OSError(errno.EINVAL, 'Malformed ACL metadata: ' + repr(actual))
            tag, qualifier, perms = parts
            if tag + ':' + qualifier in entries:
                raise OSError(errno.EINVAL, 'Duplicate ACL metadata: ' + repr(actual))
            entries[tag + ':' + qualifier] = perms
    if (entries != expected or observed.st_uid != spec.get('owner', 0) or
            observed.st_gid != spec.get('group', 0)):
        raise OSError(errno.EINVAL, 'ACL fixture mismatch: expected ' + repr(expected) +
                      ', observed ' + repr(entries) +
                      f', owner={observed.st_uid}:{observed.st_gid}')
