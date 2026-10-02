#!/usr/bin/env python3
"""Supply/verify private Linux locales or installed Darwin locales, without sudo."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
import smoke
from host_utilities import serial, sha

LOCALES = (('fr_FR.UTF-8', 'fr_FR', 'UTF-8', ','),
           ('de_DE.UTF-8', 'de_DE', 'UTF-8', ','),
           ('en_US.UTF-8', 'en_US', 'UTF-8', '.'),
           ('zh_CN.GB18030', 'zh_CN', 'GB18030', '.'),
           ('fr_FR.ISO8859-1', 'fr_FR', 'ISO-8859-1', ','))


def provision(probe, destination):
    # Restrict replacement/cleanup to this generated profile directory.
    if destination.absolute() != ROOT / 'build/host-profile/locales':
        raise ValueError('destination must be this checkout\'s build/host-profile/locales')
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = dict(platform=platform.platform(), locales=[], setup=[], failures=[],
                  strategy='private LOCPATH' if platform.system() == 'Linux' else 'installed Darwin locales',
                  localedef=shutil.which('localedef', path=os.defpath),
                  probe_sha256=sha(probe), source_hashes={})
    result['localedef_sha256'] = sha(result['localedef'])
    with tempfile.TemporaryDirectory(prefix='csh076-locales-', dir=destination.parent) as temporary:
        root = Path(temporary)
        def run(binary, args, env):
            fixture = dict(args=args, stdin=b'', env=env)
            status, output, failures = smoke.capture(Path(binary), fixture, root, 30, 65536,
                                                     file_size_limit=8 * 1024 * 1024)
            for name in ('.home', '.tmp'):
                shutil.rmtree(root / name)
            return status, {key: bytes(value) for key, value in output.items()}, failures, fixture
        try:
            for name, source, encoding, point in LOCALES:
                env = dict(PATH=os.defpath, LANG='C', LC_ALL='C')
                if platform.system() == 'Linux':
                    source_path = Path('/usr/share/i18n/locales') / source
                    map_path = Path('/usr/share/i18n/charmaps') / (encoding + '.gz')
                    for path in (source_path, map_path):
                        result['source_hashes'][str(path)] = sha(path)
                    args = ['-i', str(source_path), '-f', encoding, str(root / name)]
                    status, output, failures, fixture = run(result['localedef'], args, env)
                    result['setup'].append(serial(dict(invocation=fixture, status=status, output=output,
                                                       failures=failures)))
                    if status or output['stderr'] or failures:
                        result['failures'].append('localedef setup failed: ' + name)
                        continue
                    env['LOCPATH'] = str(root)
                status, output, failures, fixture = run(probe, ['locale', name], env)
                lines = bytes(output['stdout']).decode(errors='replace').splitlines()
                normalize = lambda text: ''.join(c for c in text.upper() if c.isalnum())
                ok = (status == 0 and not failures and not output['stderr'] and len(lines) == 2
                      and normalize(lines[0]) == normalize(encoding) and lines[1] == point)
                result['locales'].append(serial(dict(name=name, expected_codeset=encoding,
                    expected_decimal_point=point, invocation=fixture, status=status, output=output,
                    failures=failures, verified=ok)))
                if not ok:
                    result['failures'].append('locale capability failed: ' + name)
            if not result['failures'] and platform.system() == 'Linux':
                # Published generations remain valid until make clean. A consumer
                # holds the manifest's real path, never a mutable directory alias.
                generation = destination.parent / ('locales-' + uuid.uuid4().hex)
                root.rename(generation)
                alias = destination.parent / ('.locales-' + uuid.uuid4().hex)
                alias.symlink_to(generation.name, target_is_directory=True)
                if destination.exists() and not destination.is_symlink():
                    destination.rename(destination.parent / ('locales-legacy-' + uuid.uuid4().hex))
                os.replace(alias, destination)
                result['locale_path'] = str(generation)
                result['generated_sha256'] = {str(p.relative_to(generation)): sha(p)
                    for p in sorted(generation.rglob('*')) if p.is_file()}
        except (OSError, ValueError) as error:
            result['failures'].append(str(error))
    result['cleanup'] = not root.exists()
    record = destination.parent / ('.locales-' + uuid.uuid4().hex + '.json')
    record.write_text(json.dumps(result, indent=2) + '\n')
    os.replace(record, destination.parent / 'locales.json')
    for error in result['failures']:
        print('FAIL:', error, file=sys.stderr)
    print(f"Locales: {sum(row['verified'] for row in result['locales'])}/5 verified ({result['strategy']})")
    return int(bool(result['failures']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    raise SystemExit(provision(args.probe.resolve(), args.destination.absolute()))
