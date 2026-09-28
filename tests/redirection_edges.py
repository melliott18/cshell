#!/usr/bin/env python3
"""CSH-049 public execution of controlled redirection failures, bounded to 5s."""
import errno
import os
from pathlib import Path
import shlex
import sys

import smoke

fault, helper = (Path(p).resolve() for p in sys.argv[1:])
h = shlex.quote(str(helper))
passed = failed = 0


def run(name, script, *, stdout='', stderr='', status=0, env=None, setup=None, files=None, interactive=False):
    global passed, failed
    for mode in ('string', 'file', 'stdin'):
        # Interactive stdin prompts have separate PTY coverage. Here use -ic
        # and -i file to isolate error consequences from terminal transport.
        if interactive and mode == 'stdin': continue
        fixture = dict(name=f'redirection-edge: {name} ({mode})', env=env or {}, setup=dict(setup or {}),
                       expect=dict(stdout=stdout, stderr=stderr, status=status, files=files or {}), stdin='', args=[])
        if mode == 'string': fixture['args'] = ['-ic' if interactive else '-c', script + '\n']
        elif mode == 'file':
            fixture['setup']['script'] = script + '\n'
            fixture['args'] = ['-i', 'script'] if interactive else ['script']
        else: fixture['stdin'] = script + '\n'
        errors = smoke.run_case(fault, fixture, 5, 65536)
        print(('FAIL' if errors else 'PASS') + ': ' + fixture['name'], flush=True)
        if errors:
            failed += 1
            print(errors, flush=True)
        else: passed += 1


def file(content):
    return {'type': 'file', 'content': content}


absent = {'type': 'absent'}
# Every command category crosses every independent open failure. EXIT actions
# inspect restored descriptors even when a special builtin must terminate.
for error in ('EACCES', 'ENOSPC', 'EROFS', 'EMFILE', 'ENFILE', 'EIO'):
    for category, command in (('empty', ''), ('special', ':'), ('regular', 'read value'),
                              ('command-special', 'command :'), ('function', 'f'),
                              ('external', h + ' args forbidden')):
        for interactive in (False, True):
            fatal = category == 'special' and not interactive
            script = ('exec 7>retained; v=old; f() { : >body; }; '
                      f'trap \'{h} fd-write 7; {h} closed 8; {h} args "$?" "$v"\' EXIT; '
                      f'v=new {command} >early 7>fault-target 8>"$(touch expanded; printf later)"; '
                      f'{h} args "$?" continued')
            run(f'{error} {category} interactive={interactive}', script,
                interactive=interactive, env={'CSH_REDIRECT_FAULT': error}, status=1 if fatal else 0,
                stdout=('[0]\n[old]\n' if fatal else '[1]\n[continued]\n[0]\n[old]\n'),
                stderr='cshell: cannot apply redirection: ' + os.strerror(getattr(errno, error)) + '\n',
                setup={'early': 'old'}, files={'early': file(''), 'retained': file('fd\n'),
                                             'fault-target': absent, 'body': absent, 'expanded': absent, 'later': absent})

for op in ('<', '>', '>|', '>>', '<>', 'noclobber'):
    actual = '>' if op == 'noclobber' else op
    setup = {} if op == 'noclobber' else {'fault-target': 'body\n'}
    command = h + (' copy' if op == '<' else ' fd-write ' + ('0' if op == '<>' else '1'))
    output = 'body\n' if op == '<' else ''
    content = 'body\n' if op == '<' else 'body\nfd\n' if op == '>>' else 'fd\ny\n' if op == '<>' else 'fd\n'
    run('open EINTR ' + op, ('set -C; ' if op == 'noclobber' else '') + f'{command} {actual}fault-target',
        env={'CSH_REDIRECT_FAULT': 'EINTR'}, setup=setup, stdout=output, files={'fault-target': file(content)})

run('noclobber replacement after stat',
    f'mkfifo fault-target; set -C; {h} args forbidden >fault-target; {h} args "$?" restored',
    env={'CSH_REDIRECT_FAULT': 'replace'}, stdout='[1]\n[restored]\n',
    stderr='cshell: cannot apply redirection: ' + os.strerror(errno.EEXIST) + '\n',
    files={'fault-target': file('preserved\n')})
run('noclobber fstat error preserves diagnostic',
    # A symlink to /dev/null opens without blocking and is not a regular file.
    f'ln -s /dev/null fault-target; set -C; {h} args forbidden >fault-target; {h} args "$?" restored',
    env={'CSH_REDIRECT_FAULT': 'fstat'}, stdout='[1]\n[restored]\n',
    stderr='cshell: cannot apply redirection: ' + os.strerror(errno.EIO) + '\n')
print(f'Redirection edges: {passed} passed, {failed} failed, 0 skipped', flush=True)
sys.exit(bool(failed))
