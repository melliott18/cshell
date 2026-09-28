"""Run inside the disposable Linux root container after building the helper."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path('tests').resolve()))
from host_environment_cases import setup_controlled
from host_platform import filesystem_identity


def command(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    return dict(argv=argv, status=result.returncode, stdout=result.stdout, stderr=result.stderr)


helper = str(Path(sys.argv[1] if len(sys.argv) > 1 else 'build/tests/host_utility_helper').resolve())
linked = command(['ldd', '/usr/bin/test'])
libc = next(Path(line.split('=>')[1].split()[0]) for line in linked['stdout'].splitlines()
            if 'libc.so' in line)
selected = {name: dict(path='/usr/bin/' + name,
    sha256=hashlib.sha256(Path('/usr/bin/' + name).read_bytes()).hexdigest(),
    linked=command(['ldd', '/usr/bin/' + name]),
    imports=command(['objdump', '-T', '/usr/bin/' + name])) for name in ('test', '[')}
record = dict(selected=selected, helper=dict(path=helper, sha256=hashlib.sha256(Path(helper).read_bytes()).hexdigest()), linked=linked, libc=dict(path=str(libc), sha256=hashlib.sha256(libc.read_bytes()).hexdigest()),
              versions=command(['dpkg-query', '-W', 'coreutils', 'libc6']),
              imports=command(['objdump', '-T', '/usr/bin/test']), cases=[])
with tempfile.TemporaryDirectory(prefix='csh-acl-diagnosis-') as temporary:
    fixture = setup_controlled(Path(temporary), 'acl')
    record['fixture'] = fixture
    record['filesystem'] = filesystem_identity(Path(temporary))
    for real, effective in ((10001, 10001), (10002, 10001), (10001, 10002)):
        record['cases'].append(command([helper, 'identity', str(real), str(effective),
                                        helper, 'acl-probe', temporary + '/controlled']))
print(json.dumps(record, indent=2))
