"""CSH-089 declined children and nested recursive rm decisions.

Issue 8 rm DESCRIPTION 2b-2e and 3 require independent descent, child and
directory-removal decisions, followed by operand continuation. Each directory
has one child, so expectations never depend on readdir order. These bounded
graphs do not supply arbitrary depth, branching, mount or non-C environments.
"""
from host_filesystem_cases import case
from host_filesystem_decisions import MODES, FIRST, SECOND, event


def witness(name, prompts, files, directories, effects, *, status=0, links=None):
    return case('rm', 'recursive-' + name, ['-R', '-i', 'branch', 'second'],
                ticket='CSH-089', overwrite_prompt=True, response=None,
                prompt_sequence=prompts + [event('file', 'second', 'y')],
                modes=MODES, status=status,
                directory_modes={name: 0o700 for name in directories},
                files={**files, 'second': SECOND}, links=links or {},
                effects={**effects, 'second': {'type': 'absent'}})


def cases():
    # Keeping a child is not itself an error. Affirmatively attempting removal
    # of its still nonempty parent is an error; later operands must still run.
    for final in ('n', 'y'):
        prompts = [event('descend', 'branch', 'y'),
                   event('file', 'branch/leaf', 'n'), event('directory', 'branch', final)]
        if final == 'y':
            prompts.append(dict(event('diagnostic', 'branch', None), exact_target=True))
        yield witness('declined-leaf-parent-' + final, prompts,
                      {'branch/leaf': FIRST}, ['branch'],
                      {'branch': {'type': 'directory'}, 'branch/leaf': {'content': FIRST}},
                      status=0 if final == 'n' else 'nonzero')

    for final in ('n', 'y'):
        prompts = [event('descend', 'branch', 'y'),
                   event('descend', 'branch/sub', 'n'), event('directory', 'branch', final)]
        if final == 'y':
            prompts.append(dict(event('diagnostic', 'branch', None), exact_target=True))
        yield witness('declined-descent-parent-' + final, prompts,
                      {'branch/sub/leaf': FIRST}, ['branch/sub'],
                      {'branch': {'type': 'directory'}, 'branch/sub': {'type': 'directory'},
                       'branch/sub/leaf': {'content': FIRST}},
                      status=0 if final == 'n' else 'nonzero')

    for child in ('n', 'y'):
        yield witness('nested-leaf-' + child + '-keep-directories',
                      [event('descend', 'branch', 'y'), event('descend', 'branch/sub', 'y'),
                       event('file', 'branch/sub/leaf', child),
                       event('directory', 'branch/sub', 'n'), event('directory', 'branch', 'n')],
                      {'branch/sub/leaf': FIRST}, ['branch/sub'],
                      {'branch': {'type': 'directory'}, 'branch/sub': {'type': 'directory'},
                       'branch/sub/leaf': {'content': FIRST} if child == 'n' else {'type': 'absent'}})

    for final in ('n', 'y'):
        yield witness('nested-remove-parent-' + final,
                      [event('descend', 'branch', 'y'), event('descend', 'branch/sub', 'y'),
                       event('file', 'branch/sub/leaf', 'y'),
                       event('directory', 'branch/sub', 'y'), event('directory', 'branch', final)],
                      {'branch/sub/leaf': FIRST}, ['branch/sub'],
                      {'branch': {'type': 'absent' if final == 'y' else 'directory'},
                       'branch/sub': {'type': 'absent'}})

    # A retained symlink must preserve its opaque link text and external target;
    # an accepted symlink must remove only that entry, even at nested depth.
    for child in ('n', 'y'):
        yield witness('nested-link-' + child,
                      [event('descend', 'branch', 'y'), event('descend', 'branch/sub', 'y'),
                       event('link', 'branch/sub/link', child),
                       event('directory', 'branch/sub', child), event('directory', 'branch', child)],
                      {'outside/leaf': FIRST}, ['branch/sub', 'outside'],
                      {'branch': {'type': 'absent' if child == 'y' else 'directory'},
                       'branch/sub': {'type': 'absent' if child == 'y' else 'directory'},
                       'branch/sub/link': {'link': '../../outside'} if child == 'n' else {'type': 'absent'},
                       'outside': {'type': 'directory'}, 'outside/leaf': {'content': FIRST}},
                      links={'branch/sub/link': '../../outside'})
