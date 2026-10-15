#!/usr/bin/env python3
"""Change a private cwd namespace, prove its state, and exec the actual provider."""
import errno
import json
import os
import sys

MARKER = '.cwd-environment.json'


def identity():
    info = os.stat('.')
    return dict(device=info.st_dev, inode=info.st_ino)


def main():
    action, provider, *arguments = sys.argv[1:]
    # Keep the marker outside the changed namespace, including after deletion.
    root = os.getcwd()
    marker = os.path.join(root, MARKER)
    record = dict(action=action, provider=provider, phase='setup', pid=os.getpid())
    def save():
        with open(marker, 'w') as stream:
            json.dump(record, stream)
    try:
        if action not in ('rename-leaf', 'rename-parent', 'delete-leaf', 'delete-parent'):
            raise ValueError('unknown cwd action')
        parent = os.path.join(root, 'cwd-parent')
        leaf = os.path.join(parent, 'cwd-leaf')
        os.chdir(leaf)
        record['before'] = identity()
        if action.startswith('rename'):
            os.rename(parent if action.endswith('parent') else leaf, os.path.join(root, 'cwd-renamed'))
        else:
            os.rmdir(leaf)
            if action.endswith('parent'):
                os.rmdir(parent)
        record['after'] = identity()
        if record['before'] != record['after']:
            raise RuntimeError('cwd inode changed')
        try:
            os.stat(leaf)
        except OSError as error:
            record['old_path_errno'] = error.errno
        else:
            raise RuntimeError('old pathname still resolves')
        if record['old_path_errno'] != errno.ENOENT:
            raise RuntimeError('unexpected old pathname error')
        try:
            record['getcwd'] = os.getcwd()
            record['getcwd_errno'] = 0
        except OSError as error:
            record.update(getcwd=None, getcwd_errno=error.errno)
        if action.startswith('delete'):
            if record['getcwd_errno'] != errno.ENOENT:
                raise RuntimeError('deleted cwd did not produce ENOENT')
        else:
            expected = os.path.join(root, 'cwd-renamed') + ('/cwd-leaf' if action.endswith('parent') else '')
            if record['getcwd_errno'] or record['getcwd'] != expected:
                raise RuntimeError('renamed cwd did not resolve to its authored path')
        record['phase'] = 'armed'
        save()
        try:
            os.execv(provider, [provider, *arguments])
        except OSError as error:
            record.update(phase='exec-failure', exec_errno=error.errno)
            save()
            return 125
    except (OSError, ValueError, RuntimeError) as error:
        record.update(phase='setup-failure', error=str(error))
        save()
        return 125


if __name__ == '__main__':
    raise SystemExit(main())
