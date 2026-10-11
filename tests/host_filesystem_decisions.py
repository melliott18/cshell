"""CSH-087 bounded operand sequences and recursive terminal decisions.

Effects come from authored bytes and one-child graphs, never provider output.
One-child recursion avoids assuming a filesystem traversal order. Each response
waits for its target and question mark; all stderr bytes are checked afterward.
"""
import os
import re

from host_filesystem_cases import case

MODES = ('pty-direct', 'pty-string', 'pty-file')
FIRST, SECOND = b'first new bytes\n', b'second new bytes\n'
OLD_FIRST, OLD_SECOND = b'first old bytes\n', b'second old bytes\n'


def event(action, target, response):
    return dict(action=action, target=target, response=response)


def witness(utility, name, args, prompts, **kw):
    return case(utility, 'decisions-' + name, args, ticket='CSH-087',
                overwrite_prompt=True, prompt_sequence=prompts, response=None,
                modes=MODES, **kw)


def cases():
    for utility in ('cp', 'mv'):
        for responses in ('yy', 'yn', 'ny', 'nn'):
            effects = {}
            for name, source, old, response in zip(
                    ('first', 'second'), (FIRST, SECOND), (OLD_FIRST, OLD_SECOND), responses):
                effects[name] = ({'type': 'absent'} if utility == 'mv' and response == 'y'
                                 else {'content': source})
                effects['destination/' + name] = {'content': source if response == 'y' else old}
            yield witness(utility, 'multiple-' + responses,
                          ['-i', 'first', 'second', 'destination'],
                          [event('overwrite', 'destination/' + name, response)
                           for name, response in zip(('first', 'second'), responses)],
                          files={'first': FIRST, 'second': SECOND,
                                 'destination/first': OLD_FIRST, 'destination/second': OLD_SECOND},
                          effects=effects)
        # A real error between prompts must neither hide errors nor stop later
        # operands. The diagnostic is required at its exact transcript position.
        for response in ('y', 'n'):
            prompts = [event('overwrite', 'destination/first', response),
                       event('diagnostic', 'missing', None),
                       event('overwrite', 'destination/second', 'y')]
            yield witness(utility, 'missing-between-' + response,
                          ['-i', 'first', 'missing', 'second', 'destination'], prompts,
                          status='nonzero',
                          files={'first': FIRST, 'second': SECOND,
                                 'destination/first': OLD_FIRST, 'destination/second': OLD_SECOND},
                          effects={'first': {'type': 'absent'} if utility == 'mv' and response == 'y' else {'content': FIRST},
                                   'second': {'type': 'absent'} if utility == 'mv' else {'content': SECOND},
                                   'destination/first': {'content': FIRST if response == 'y' else OLD_FIRST},
                                   'destination/second': {'content': SECOND},
                                   'destination/missing': {'type': 'absent'}})

    for response in ('y', 'n'):
        yield witness('cp', 'recursive-' + response,
                      ['-R', '-P', '-i', 'branch', 'destination'],
                      [event('overwrite', 'destination/branch/sub/leaf', response)],
                      directory_modes={'branch/sub': 0o700, 'destination/branch/sub': 0o700},
                      files={'branch/sub/leaf': FIRST, 'destination/branch/sub/leaf': OLD_FIRST},
                      effects={'branch/sub/leaf': {'content': FIRST},
                               'destination/branch/sub/leaf': {'content': FIRST if response == 'y' else OLD_FIRST}})

    # Nonempty directories require a descent decision. A negative answer must
    # preserve the subtree and continue with the following operand.
    yield witness('rm', 'decline-descent-continue', ['-R', '-i', 'branch', 'second'],
                  [event('descend', 'branch', 'n'), event('file', 'second', 'y')],
                  directory_modes={'branch': 0o700}, files={'branch/leaf': FIRST, 'second': SECOND},
                  effects={'branch/leaf': {'content': FIRST}, 'second': {'type': 'absent'}})
    for final in ('y', 'n'):
        yield witness('rm', 'recursive-final-' + final, ['-R', '-i', 'branch'],
                      [event('descend', 'branch', 'y'), event('file', 'branch/leaf', 'y'),
                       event('directory', 'branch', final)],
                      directory_modes={'branch': 0o700}, files={'branch/leaf': FIRST},
                      effects={'branch/leaf': {'type': 'absent'},
                               'branch': {'type': 'absent' if final == 'y' else 'directory'}})
    yield witness('rm', 'recursive-symlink', ['-R', '-i', 'branch'],
                  [event('descend', 'branch', 'y'), event('link', 'branch/link', 'y'),
                   event('directory', 'branch', 'y')],
                  directory_modes={'branch': 0o700, 'outside': 0o700},
                  files={'outside/leaf': FIRST}, links={'branch/link': '../outside'},
                  effects={'branch': {'type': 'absent'}, 'outside/leaf': {'content': FIRST}})
    for options, prompts, removed in [
        (['-f', '-i'], [event('file', 'first', 'n'), event('file', 'second', 'y')], False),
        (['-i', '-f'], [], True),
    ]:
        yield witness('rm', 'last-' + options[-1][1:], options + ['first', 'second'], prompts,
                      files={'first': FIRST, 'second': SECOND},
                      effects={'first': {'type': 'absent'} if removed else {'content': FIRST},
                               'second': {'type': 'absent'}})

    # Same-device directory replacement and rejection use ordinary direct exec
    # and all three shell input modes, independently of terminal fixtures.
    for occupied in (False, True):
        yield case('mv', 'decisions-directory-' + ('nonempty' if occupied else 'empty'),
                   ['source-dir', 'destination'], ticket='CSH-087',
                   directory_modes={'source-dir': 0o700, 'destination/source-dir': 0o700},
                   files={'source-dir/leaf': FIRST, **({'destination/source-dir/old': OLD_FIRST} if occupied else {})},
                   status='nonzero' if occupied else 0, err='nonempty' if occupied else b'',
                   effects=({'source-dir/leaf': {'content': FIRST},
                             'destination/source-dir/old': {'content': OLD_FIRST},
                             'destination/source-dir/leaf': {'type': 'absent'}} if occupied else
                            {'source-dir': {'type': 'absent'}, 'destination/source-dir/leaf': {'content': FIRST}}))


def steps(row):
    result = []
    for prompt in row['prompt_sequence']:
        if prompt['action'] == 'diagnostic':
            continue
        result += [{'expect': prompt['target']}, {'expect': '?'}, {'send': prompt['response'] + '\n'}]
    return result


def transcript_pattern(row, provider, dialect):
    """Known C-locale spellings, not a wildcard allowance for prompt contents."""
    pattern = b''
    prefix = os.fsencode(provider)
    for prompt in row['prompt_sequence']:
        action, target, response = (prompt[k] for k in ('action', 'target', 'response'))
        target = os.fsencode(target)
        if action == 'diagnostic':
            # One diagnostic line cannot absorb a repeated or unrelated prompt.
            # libc error() and vendor helpers differ in whether argv[0] is
            # shortened; both identify the same inventoried executable.
            diagnostic_prefix = b'(?:' + re.escape(os.fsencode(os.path.basename(provider))) + b'|' + re.escape(prefix) + b')'
            pattern += diagnostic_prefix + rb': [^?\n]*\b' + re.escape(target) + rb'\b[^?\n]*\n'
            continue
        if dialect == 'apple':
            if action == 'overwrite':
                text = b'overwrite ' + target + b'? (y/n [n]) '
                if response == 'n':
                    text += b'not overwritten\n'
            else:
                text = (b'examine files in directory ' if action == 'descend' else b'remove ') + target + b'? '
        else:
            text = prefix + b': ' + {
                'overwrite': b'overwrite ', 'descend': b'descend into directory ',
                'file': b'remove regular file ', 'link': b'remove symbolic link ',
                'directory': b'remove directory ',
            }[action] + b"'" + target + b"'? "
        pattern += re.escape(text)
    return pattern


def output_matches(row, provider, output):
    return any(re.fullmatch(transcript_pattern(row, provider, dialect), output) is not None
               for dialect in ('apple', 'gnu'))
