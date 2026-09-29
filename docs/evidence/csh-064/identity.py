"""Run from the repository root in each validation environment."""
import datetime
import json
import platform
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path('tests').resolve()))
from host_utilities import source_identity
from host_platform import credential_namespace


def command(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
    return dict(argv=argv, status=result.returncode, stdout=result.stdout, stderr=result.stderr)


print(json.dumps(dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_identity=source_identity(), platform=platform.platform(), uname=list(platform.uname()),
    python=sys.version, compiler=command(['cc', '--version']),
    os_release=Path('/etc/os-release').read_text() if Path('/etc/os-release').exists() else command(['sw_vers']),
    namespace=credential_namespace(),
    normal_flags='-D_POSIX_C_SOURCE=200809L -Iinclude -Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2',
    source_base='07ee1cb plus CSH-064 worktree; source inventory identifies exact inputs'), indent=2))
