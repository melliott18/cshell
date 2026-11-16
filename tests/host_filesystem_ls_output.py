"""CSH-123: ls output errors on a private, independently measured graph.

The child fault helper proves EBADF/EPIPE (and Linux virtual-device ENOSPC)
then execs the exact provider. This is not filesystem capacity exhaustion.
"""
import platform

from host_filesystem_cases import case
import host_filesystem_ls_blocks as graph

# Each invocation would emit output on the nonempty graph. The two operand
# forms exercise physical/followed links without opening FIFO contents.
FORMS = (
    ('directory', ['-1', 'blocks']),
    ('operands', ['-1', '-d', 'blocks/regular', 'blocks/symbol', 'blocks/directory']),
    ('long', ['-l', 'blocks']),
    ('numeric', ['-n', 'blocks']),
    ('allocation', ['-1', '-s', '-k', 'blocks']),
    ('identity', ['-1', '-i', '-F', 'blocks']),
    ('recursive', ['-1', '-R', 'blocks']),
    ('follow', ['-1', '-L', '-i', '-d', 'blocks/symbol', 'blocks/fifo']),
)


def cases(system=None):
    actions = ['closed-output', 'broken-pipe']
    if (system or platform.system()) == 'Linux':
        actions.append('enospc')
    for name, args in FORMS:
        for action in actions:
            yield case('ls', 'output-' + name + '-' + action, args,
                       ticket='CSH-123', ls_output=True, io_action=action,
                       status='nonzero', err='nonempty')


def setup(directory, row):
    if not row.get('ls_output'):
        return None
    # Reuse the measured regular/hard-link/sparse/directory/FIFO/symlink graph;
    # output failure does not introduce a new allocation or formatting oracle.
    environment = graph.setup(directory, {'ls_blocks': dict(names=[], follow=False)})
    return {key: environment[key] for key in ('before', 'uid', 'euid', 'probe')}


def verify(directory, environment):
    return graph.verify(directory, environment)
