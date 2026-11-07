"""Instrument the newly linked IANA conversion code, not all GNU touch objects."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem import run_case
from host_filesystem_transition_times import cases
from host_utilities import source_identity

label = sys.argv[1]
os.chdir(ROOT)
output = ROOT / 'build/csh101-sanitizer'
output.mkdir(exist_ok=True)
cc = os.environ.get('CC', 'cc')
flags = ['-g', '-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
commands = [
    [cc, '-std=c99', *flags, '-DHAVE_TZNAME=1', '-DUSG_COMPAT=1', '-DNETBSD_INSPIRED=0',
     '-c', 'build/host-tzcode/localtime.c', '-o', str(output / 'localtime.o')],
    [cc, *flags, '-o', str(output / 'touch'), 'build/host-coreutils-build/src/touch.o',
     str(output / 'localtime.o'), 'build/host-coreutils-build/src/libver.a',
     'build/host-coreutils-build/lib/libcoreutils.a'],
]
for command in commands:
    subprocess.run(command, check=True)
provider = output / 'touch'
records = []
with tempfile.TemporaryDirectory() as root:
    for row in cases():
        for mode in ('direct', 'string', 'file', 'stdin'):
            record = run_case(ROOT / 'cshell', {'touch': {'path': str(provider)}},
                              str(output) + os.pathsep + os.defpath, row, mode, Path(root), None, sanitizer=True)
            records.append(record)
            if record['verdict'] != 'PASS':
                print(json.dumps(record), flush=True)
report = dict(scope='ASan/UBSan instrumentation of IANA localtime.c only; GNU objects and shell are regular builds',
              compiler=subprocess.check_output([cc, '--version'], text=True),
              build_commands=commands, source_identity=source_identity(),
              binary_sha256=hashlib.sha256(provider.read_bytes()).hexdigest(),
              cases=records, totals={k:sum(r['verdict']==k for r in records) for k in ('PASS','FAIL')})
(output / (label + '-sanitizer.json')).write_text(json.dumps(report, indent=2)+'\n')
print(report['totals'])
raise SystemExit(bool(report['totals']['FAIL']) or not all(r['cleanup'] for r in records))
