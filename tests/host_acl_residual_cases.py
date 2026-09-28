"""CSH-063 Linux ACL precedence and creation-mode witnesses.

Expectations follow acl(5)'s access algorithm and default-ACL creation rules.
Each predicate has an independent open/write/execute witness; no utility oracle.
"""
import shlex

SOURCE = 'https://man7.org/linux/man-pages/man5/acl.5.html'


def cases(paths, helper, unequal=False):
    for permission, perms in (('r', 'r--'), ('w', '-w-'), ('x', '--x')):
        # label, owner, owning group, supplementary groups, ACL, allowed
        scenarios = [
            ('owner-precedence', 10002, 0, True,
             f'u::---,u:10002:{perms},g::---,g:10003:{perms},m::{perms},o::{perms}', False),
            ('owner-outside-mask', 10002, 0, False,
             f'u::{perms},u:10001:{perms},g::---,m::---,o::---', True),
            ('owning-group', 0, 10002, False,
             f'u::---,u:10001:---,g::{perms},m::{perms},o::---', True),
            ('owning-group-no-fallback', 0, 10002, False,
             f'u::---,u:10001:---,g::---,m::{perms},o::{perms}', False),
            ('owning-and-named-group', 0, 10002, True,
             f'u::---,g::---,g:10003:{perms},m::{perms},o::---', True),
            ('named-group-no-fallback', 0, 0, True,
             f'u::---,g::---,g:10003:---,m::{perms},o::{perms}', False),
            ('other-outside-mask', 0, 0, False,
             f'u::---,u:10001:{perms},g::---,m::---,o::{perms}', True),
        ]
        for inherited in (False, True):
            for label, owner, group, groups, entries, allowed in scenarios:
                spec = dict(subject='residual', permission=permission, inherited=inherited,
                            masked=False, acl_entries=entries, owner=owner, group=group,
                            helper=shlex.split(helper)[0])
                yield from witnesses(paths, helper, unequal, label, groups, allowed, spec)
        # A default ACL does not override the creation mode's group bits.
        # Both granting and denying creations retain the named entry itself.
        for allowed in (False, True):
            mode = 0o777 if allowed else 0o700
            spec = dict(subject='residual', permission=permission, inherited=True,
                        masked=False, acl_entries=f'u::---,u:10002:{perms},g::---,m::{perms},o::---',
                        create_mode=mode, helper=shlex.split(helper)[0])
            yield from witnesses(paths, helper, unequal, f'creation-mode-{mode:o}', False, allowed, spec)


def witnesses(paths, helper, unequal, label, groups, allowed, spec):
    effective, real = 10002, 10001 if unequal else 10002
    identity = 'identity-groups' if groups else 'identity'
    prefix = f'{helper} {identity} {real} {effective} '
    output = (f'uid={real} euid={effective} gid={real} egid={effective} groups=' +
              ('2:10003:10004\n' if groups else '0\n')).encode()
    permission = spec['permission']
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
        yield dict(name=f'U-037 ACL residual {label} {permission} inherited={spec["inherited"]} unequal={unequal} {utility}',
                   script=prefix + command + '\n', stdout=out, files=files,
                   stderr='nonempty' if utility == 'operation' and not allowed else b'',
                   status=0 if allowed else (2 if utility == 'operation' and permission == 'x' else 1),
                   controlled_fixture=spec, source=SOURCE)
