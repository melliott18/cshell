"""CSH-093 external pathname utility output errors, not disk exhaustion.

The existing child-only fault helper proves the descriptor's errno before exec.
PWD is unset: -L falls back to the unchanged physical cwd. These cases do not
qualify logical namespace changes, allocation failure or arbitrary stdio faults.
"""
import platform

from host_filesystem_cases import DATA, case


def cases(system=None):
    system = system or platform.system()
    actions = ['closed-output', 'broken-pipe']
    if system == 'Linux':
        actions.append('enospc')
    for name, args in [('physical', ['-P']), ('logical-fallback', ['-L']),
                       ('last-physical', ['-L', '-P']), ('last-logical', ['-P', '-L'])]:
        for action in actions:
            yield case('pwd', 'output-' + name + '-' + action, args,
                       ticket='CSH-093', io_action=action, status='nonzero', err='nonempty',
                       effects={'data': {'content': DATA, 'mode': 0o640},
                                'tree/leaf': {'content': b'leaf\n'}, 'link': {'link': 'data'}})
    if system == 'Linux':
        for utility in ('basename', 'dirname'):
            yield case(utility, 'output-virtual-enospc', ['a/b'], ticket='CSH-093',
                       io_action='enospc', status='nonzero', err='nonempty',
                       effects={'data': {'content': DATA, 'mode': 0o640}})
