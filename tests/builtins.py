"""State builtin observations through the replacement literal executor."""
import os
import pathlib
import subprocess
import tempfile
import sys
binary = str(pathlib.Path(sys.argv[1]).resolve())
def run(script, out='', status=0, error=False, env=None):
    p = subprocess.run([binary, script], text=True, capture_output=True,
                       env={'PATH': '/bin:/usr/bin', **(env or {})})
    assert (p.returncode, p.stdout, bool(p.stderr)) == (status, out, error), (script, p.returncode, p.stdout, p.stderr)
with tempfile.TemporaryDirectory() as tmp:
    tmp = str(pathlib.Path(tmp).resolve())
    os.chdir(tmp)
    run('export Z="a\'b"\nexport EMPTY=\nexport UNSET\nexport -p\n',
        "export EMPTY=''\nexport PATH='/bin:/usr/bin'\nexport UNSET\nexport Z='a'\\''b'\n")
    run('readonly Z="a b"\nreadonly UNSET\nreadonly -p\n', "readonly UNSET\nreadonly Z='a b'\n")
    run('export X=value\nunset X\nset\n', "PATH='/bin:/usr/bin'\n")
    run('export X=value > listing\npwd\n', tmp+'\n')
    assert pathlib.Path('listing').read_text() == ''
    run('pwd > listing\n:\n')
    assert pathlib.Path('listing').read_text() == tmp+'\n'
    run('pwd 1>&-\n', status=1, error=True)
    run('set -x\n', status=1, error=True)
    run('unset -f name\n', status=1, error=True)
    run('cd\n', status=1, error=True)
    pathlib.Path('real/child').mkdir(parents=True)
    pathlib.Path('link').symlink_to('real/child', target_is_directory=True)
    run('cd link\npwd -L\npwd -P\ncd ..\npwd\n', tmp+'/link\n'+tmp+'/real/child\n'+tmp+'\n')
    run('cd -P link\ncd ..\npwd\n', tmp+'/real\n')
    run('cd link\ncd -\npwd\n', tmp+'\n'+tmp+'\n')
    run('cd child\npwd\n', (tmp+'/real/child\n')*2, env={'CDPATH': tmp+'/real'})
    run('cd missing/..\n', status=1, error=True)
    pathlib.Path('file').write_text('')
    run('cd file/..\n', status=1, error=True)
    run('readonly PWD\ncd real\npwd\n', tmp+'\n', error=True)
    run('pwd -L\n', tmp+'\n', env={'PWD': '/wrong'})
    run('cd -Pe real\npwd\n', tmp+'/real\n')
    run('cd -- real\npwd\n', tmp+'/real\n')
    run("cd ''\n", status=1, error=True)
    run('readonly X=fixed\nexport X=bad 2> errors\npwd\n', tmp+'\n')
    assert pathlib.Path('errors').read_text() == 'cshell: export: readonly variable\n'
    run(': -- ignored\n')
    run('cd -Z\n', status=1, error=True)
    run('cd real child\n', status=1, error=True)
print('state builtin behavior checks passed (24 cases)')
