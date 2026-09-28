"""CSH-050 partial signal delivery; exact host EPERM diagnostic."""
import errno
import json
import os
from pathlib import Path
import sys

cases = []
for shape in ('grouped', 'ungrouped'):
    for signal in ('CONT', 'KILL'):
        for failure in (('before', 'after', 'first') if shape == 'grouped' else
                        ('before', 'after', 'first', 'last')):
            diagnostic = ('no such job: %missing' if failure in ('before', 'after') else
                          os.strerror(errno.EPERM) + ': %1')
            cases.append(dict(name=f'kill state: {shape}/{signal}/{failure}',
                              args=[shape, signal, failure], stdin='',
                              expect=dict(status=0,
                                  stdout='partial delivery: state and final wait status passed\n',
                                  stderr='cshell: kill: ' + diagnostic + '\n')))
Path(sys.argv[1]).write_text(json.dumps(dict(version=1, name='partial job signal delivery',
                                         kind='module', cases=cases)) + '\n')
