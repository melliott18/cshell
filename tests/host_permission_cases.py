"""Clause-derived CSH-071 cases; no selected utility supplies expected results."""
import grp
import locale
import os
import pwd
from pathlib import Path
import shlex
import sys

UTILITIES = ('test', '[', 'chmod', 'chgrp', 'chown', 'id', 'logname', 'newgrp')


def case(utility, label, args, status=0, out=b'', err=b'', **kw):
    return dict(utility=utility, name=utility + '/' + label, args=args,
                status=status, stdout=out, stderr=err, **kw)


def cases(controlled=False, sessions=False, residuals=False):
    for utility in ('test', '['):
        expressions = [([], False), ([''], False), (['x'], True), (['--'], True),
                       (['!'], True), (['!', ''], True), (['!', 'x'], False),
                       (['-n', ''], False), (['-n', 'x'], True),
                       (['-z', ''], True), (['-z', 'x'], False),
                       (['!', '-n', 'x'], False), (['!', 'x', '=', 'y'], True)]
        for op, positive, negative in (
                ('=', ['x', 'x'], ['x', 'y']), ('!=', ['x', 'y'], ['x', 'x']),
                ('<', ['a', 'b'], ['b', 'a']), ('>', ['b', 'a'], ['a', 'b']),
                ('-eq', ['01', '1'], ['1', '2']), ('-ne', ['1', '2'], ['1', '1']),
                ('-lt', ['-2', '-1'], ['2', '1']), ('-le', ['2', '2'], ['2', '1']),
                ('-gt', ['2', '1'], ['1', '2']), ('-ge', ['2', '2'], ['1', '2'])):
            expressions.extend([([positive[0], op, positive[1]], True),
                                ([negative[0], op, negative[1]], False)])
        for op, positive, negative in (
                ('-d', 'tree', 'data'), ('-e', 'data', 'missing'),
                ('-f', 'data', 'tree'), ('-g', 'setgid', 'data'),
                ('-h', 'dangling', 'data'), ('-L', 'link', 'data'),
                ('-p', 'fifo', 'data'), ('-S', 'socket', 'data'),
                ('-s', 'data', 'empty'), ('-u', 'setuid', 'data'),
                ('-r', 'data', 'missing'), ('-w', 'data', 'missing'),
                ('-x', 'executable', 'missing')):
            expressions.extend([([op, positive], True), ([op, negative], False),
                                ([op, 'missing'], False)])
        expressions.extend([(['-f', 'link'], True), (['-e', 'dangling'], False),
                            (['data', '-ef', 'hardlink'], True),
                            (['data', '-ef', 'empty'], False),
                            (['missing', '-ef', 'missing'], False),
                            (['new', '-nt', 'old'], True), (['old', '-nt', 'new'], False),
                            (['old', '-ot', 'new'], True), (['new', '-ot', 'old'], False),
                            (['new', '-nt', 'missing'], True),
                            (['missing', '-ot', 'new'], True),
                            (['missing', '-nt', 'new'], False),
                            (['new', '-ot', 'missing'], False),
                            (['missing', '-nt', 'missing'], False),
                            (['-t', '0'], False), (['-t', '9'], False)])
        for index, (args, truth) in enumerate(expressions):
            yield case(utility, f'primary-{index}', args, status=0 if truth else 1)
        for args, truth in ((['a', '<', 'a'], False), (['a', '>', 'a'], False),
                            (['!', 'a', '<', 'b'], False), (['!', 'b', '>', 'a'], False),
                            (['!', 'a', '>', 'b'], True)):
            yield case(utility, 'collation-' + ' '.join(args), args, status=0 if truth else 1)
        previous = locale.setlocale(locale.LC_COLLATE)
        try:
            try:
                locale.setlocale(locale.LC_COLLATE, 'csh_067.UTF-8')
            except locale.Error:
                pass
            else:
                # Authored Czech contraction ch sorts after h; byte comparison reverses it.
                yield case(utility, 'Czech-contraction', ['ch', '>', 'h'],
                           env={'LC_ALL': 'csh_067.UTF-8'})
        finally:
            locale.setlocale(locale.LC_COLLATE, previous)
        yield case(utility, 'bad-integer', ['x', '-eq', '1'], status='error', err='nonempty')
        if utility == '[':
            yield case(utility, 'missing-bracket', ['x'], status='error', err='nonempty', closing=False)

    # Every mode permission predicate has an independent real operation under the
    # same child credentials. Root-only baseline cannot witness DAC denial.
    for permission in ('r', 'w', 'x'):
        for allowed in ((True, False) if controlled or os.geteuid() != 0 else (True,)):
            for utility in ('test', '['):
                yield case(utility, f'access-{permission}-{allowed}', ['-' + permission, 'access'],
                           status=0 if allowed else 1, access=dict(permission=permission, allowed=allowed),
                           credentials=[10002, 10002] if controlled else None)

    # Fixed numeric expectations exercise chmod's grammar, ordering and umask.
    modes = [('000', 0o644, 0), ('754', 0o600, 0o754), ('u=rw,g=r,o=', 0o777, 0o640),
             ('a+x', 0o640, 0o751), ('u-x,g+w,o-r', 0o754, 0o670),
             ('u=rwx,g=u,o=g', 0, 0o777), ('u+r-w+x', 0o200, 0o500),
             ('a=', 0o777, 0), ('u+', 0o640, 0o640), ('g-', 0o640, 0o640),
             ('a+X', 0o644, 0o644), ('a+X', 0o744, 0o755),
             ('o+s', 0o644, 0o644),
             ('u+s,g+s', 0o755, 0o6755), ('u-s,g-s', 0o6755, 0o755)]
    if residuals:
        yield case('chmod', 'original-X', ['u+x,g+X', 'subject'], initial=0o644,
                   metadata={'subject': {'mode': 0o744}})
    for index, (mode, initial, expected) in enumerate(modes):
        yield case('chmod', f'mode-{index}', [mode, 'subject'],
                   initial=initial, metadata={'subject': {'mode': expected}})
    for mask, mode, initial, expected in (
            (0o027, '+rwx', 0, 0o750), (0o027, '-rwx', 0o777, 0o027),
            (0o027, '=rwx', 0o777, 0o750), (0o777, 'a=rwx', 0, 0o777)):
        yield case('chmod', f'mask-{mask:o}-{mode}', ['--', mode, 'subject'],
                   initial=initial, umask=mask, metadata={'subject': {'mode': expected}})
    yield case('chmod', 'directory-X', ['a+X', 'tree'], tree_mode=0o600,
               metadata={'tree': {'mode': 0o711}})
    yield case('chmod', 'recursive', ['-R', 'u=rwX,go=rX', 'tree'],
               metadata={'tree': {'mode': 0o755}, 'tree/leaf': {'mode': 0o644}})
    yield case('chmod', 'multiple', ['600', 'subject', 'data'],
               metadata={'subject': {'mode': 0o600}, 'data': {'mode': 0o600}})
    yield case('chmod', 'symlink-operand', ['600', 'link'], metadata={'data': {'mode': 0o600}})
    yield case('chmod', 'missing', ['600', 'missing'], status='nonzero', err='nonempty')
    yield case('chmod', 'bad-mode', ['u+q', 'subject'], status='nonzero', err='nonempty',
               metadata={'subject': {'mode': 0o644}})

    uid, gid = os.geteuid(), os.getegid()
    user, group = pwd.getpwuid(uid).pw_name, grp.getgrgid(gid).gr_name
    for utility, operands in (('chgrp', [str(gid), group]),
                              ('chown', [str(uid), user, f'{uid}:{gid}', f'{user}:{group}'])):
        for operand in operands:
            yield case(utility, 'owner-' + operand, [operand, 'subject', 'data'],
                       metadata={p: {'uid': uid, 'gid': gid} for p in ('subject', 'data')})
        yield case(utility, 'missing', [operands[0], 'missing'], status='nonzero', err='nonempty')
    for args, value in ((['-u'], uid), (['-ur'], os.getuid()), (['-g'], gid),
                        (['-gr'], os.getgid()), (['-un'], user), (['-gn'], group),
                        (['-u', user], uid), (['-g', user], pwd.getpwnam(user).pw_gid)):
        yield case('id', ' '.join(args), args, out=f'{value}\n'.encode())
    yield case('id', 'groups', ['-G'], groups=True)
    yield case('id', 'unknown-user', ['csh_071_no_such_user_8f7c'], status='nonzero', err='nonempty')
    yield case('logname', 'getlogin', [], login=True,
               env={'LOGNAME': 'not-the-login', 'USER': 'not-the-login'})

    if controlled:
        for real, effective in ((10001, 10002), (10002, 10001)):
            for args, value in ((['-u'], effective), (['-ur'], real),
                                (['-g'], effective), (['-gr'], real)):
                yield case('id', f'controlled-{real}-{effective}-{args[0]}', args,
                           out=f'{value}\n'.encode(), credentials=[real, effective],
                           modes=('direct',))
        for utility in ('chown', 'chgrp'):
            operand = '10002:10002' if utility == 'chown' else '10002'
            changed = {'gid': 10002}
            if utility == 'chown':
                changed['uid'] = 10002
            for policy in ('H', 'L', 'P'):
                expected = {'tree': changed, 'tree/leaf': changed,
                            'outside': changed if policy in ('H', 'L') else {'uid': 0, 'gid': 0},
                            'outside/leaf': changed if policy == 'L' else {'uid': 0, 'gid': 0}}
                yield case(utility, 'traversal-' + policy, ['-R', '-' + policy, operand, 'tree'],
                           metadata=expected, traversal=True)
            for policy in ('H', 'L', 'P', 'PLH', 'HLP'):
                follows = policy[-1] != 'P'
                expected = {p: changed if follows else {'uid': 0, 'gid': 0}
                            for p in ('tree', 'tree/leaf')}
                expected['outside'] = changed if policy[-1] in ('H', 'L') else {'uid': 0, 'gid': 0}
                yield case(utility, 'operand-link-' + policy,
                           ['-R', '-' + policy, operand, 'tree-link'], metadata=expected, traversal=True)
            yield case(utility, 'symlink-only', ['-h', operand, 'link'],
                       metadata={'link': dict(changed, nofollow=True), 'data': {'uid': 0, 'gid': 0}})
        yield case('chmod', 'non-owner-denial', ['600', 'subject'], credentials=[10002, 10002],
                   status='nonzero', err='nonempty', metadata={'subject': {'mode': 0o644}},
                   modes=('direct', 'string', 'file', 'stdin'))

    # Explicit opt-in: these invoke account policy only in a disposable Linux root environment.
    if sessions:
        observe = shlex.join([sys.executable, str(Path(__file__).with_name('host_permissions_child.py').resolve()), '--session-observe'])
        shell_input = observe + '; exit 23\n'
        for args, label, gid in (([], 'default', 0), (['root'], 'named', 0),
                                 (['0'], 'numeric', 0), (['daemon'], 'changed-group', grp.getgrnam('daemon').gr_gid)):
            yield case('newgrp', label, args, out=b'new-shell\n', shell_input=shell_input, status=23,
                       session_gid=gid, env={'CSH_071_EXPORTED': 'retained'}, umask=0o027)
        yield case('newgrp', 'failed-group-still-shell', ['csh_071_no_such_group_8f7c'],
                   out=b'new-shell\n', shell_input=shell_input, status=23, err='nonempty',
                   session_gid=0, env={'CSH_071_EXPORTED': 'retained'}, umask=0o027)
