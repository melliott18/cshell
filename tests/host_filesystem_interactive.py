"""CSH-086 owned-PTY overwrite decisions with independent byte/effect oracles."""
import os
import re

from host_filesystem_cases import case

SOURCE = b'new source bytes\n'
DESTINATION = b'original destination\n'


def cases():
    for utility in ('cp', 'mv'):
        # cp -f does not cancel -i; mv uses the last of -f and -i.
        options = [('interactive', ['-i']), ('force-then-interactive', ['-f', '-i'])]
        if utility == 'cp':
            options.append(('interactive-then-force', ['-i', '-f']))
        for name, args in options:
            for response in ('y', 'n'):
                accepted = response == 'y'
                yield case(utility, 'prompt-' + name + '-' + response,
                           args + ['source', 'target'], ticket='CSH-086',
                           files={'source': SOURCE, 'target': DESTINATION},
                           effects={'source': {'type': 'absent'} if utility == 'mv' and accepted else {'content': SOURCE},
                                    'target': {'content': SOURCE if accepted else DESTINATION}},
                           overwrite_prompt=True, response=response,
                           modes=('pty-direct', 'pty-string', 'pty-file'))
    yield case('mv', 'prompt-last-force', ['-i', '-f', 'source', 'target'], ticket='CSH-086',
               files={'source': SOURCE, 'target': DESTINATION}, overwrite_prompt=True,
               response=None, modes=('pty-direct', 'pty-string', 'pty-file'),
               effects={'source': {'type': 'absent'}, 'target': {'content': SOURCE}})

    # A declined first operand must not hide a later real copy error.
    for response in ('y', 'n'):
        yield case('cp', 'prompt-then-missing-' + response,
                   ['-i', 'source', 'missing', 'destination'], ticket='CSH-086',
                   files={'source': SOURCE, 'destination/source': DESTINATION},
                   overwrite_prompt=True, prompt_target='destination/source',
                   terminal_diagnostic=True, response=response, status='nonzero',
                   modes=('pty-direct', 'pty-string', 'pty-file'),
                   effects={'source': {'content': SOURCE},
                            'destination/source': {'content': SOURCE if response == 'y' else DESTINATION},
                            'destination/missing': {'type': 'absent'}})


def prompt_outputs(row, provider):
    """Exact known C-locale wording; POSIX leaves wording unspecified.

    Both vendor spellings are allowed independently of the platform because the
    selected Darwin profile may use GNU. Output, status and effects are never
    rewritten. The output channel is proved separately by the exec helper.
    """
    if row['response'] is None:
        return (b'',)
    prefix = os.fsencode(provider)
    target = os.fsencode(row.get('prompt_target', 'target'))
    apple = b'overwrite ' + target + b'? (y/n [n]) ' + (b'not overwritten\n' if row['response'] == 'n' else b'')
    return (apple, prefix + b": overwrite '" + target + b"'? ")


def steps(row):
    if row['response'] is None:
        return []
    return [{'expect': row.get('prompt_target', 'target')}, {'send': row['response'] + '\n'}]


def output_matches(row, provider, output):
    for prompt in prompt_outputs(row, provider):
        if row.get('terminal_diagnostic'):
            # Wording is unspecified; require a distinct diagnostic naming the
            # authored missing operand after the complete expected prompt.
            if output.startswith(prompt) and re.fullmatch(rb"[^\n]*missing[^\n]*\n", output[len(prompt):]):
                return True
        elif output == prompt:
            return True
    return False
