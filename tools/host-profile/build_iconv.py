"""Build a pinned GNU libiconv CLI privately; never install system libraries."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile

URL = 'https://ftp.gnu.org/pub/gnu/libiconv/libiconv-1.19.tar.gz'
SHA256 = '88dd96a8c0464eca144fc791ae60cd31cd8ee78321e67397e25fc095c4a19aa6'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(parent, cc, cppflags, cflags, ldflags):
    # Keep requested optimization/instrumentation. Upstream warnings are logged,
    # not promoted to errors by our project's policy; adapters still use -Werror.
    vendor_cflags = cflags + ' -Wno-error'
    identity = dict(url=URL, archive_sha256=SHA256, version='1.19',
        patch='diagnose discarded invalid input unless -s; preserve failure status',
        builder_sha256=sha(__file__), compiler=cc, cppflags=cppflags,
        cflags=vendor_cflags, ldflags=ldflags, platform=platform.platform())
    compiler = shutil.which(shlex.split(cc)[0])
    if compiler:
        identity['compiler_sha256'] = sha(compiler)
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    generation = parent / ('libiconv-' + key)
    parent.mkdir(parents=True, exist_ok=True)
    with (parent / '.libiconv-build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        stamp = generation / 'provider.json'
        if stamp.exists():
            record = json.loads(stamp.read_text())
            if sha(record['path']) == record['sha256']:
                return record
            raise ValueError('cached libiconv executable changed; remove its build generation')
        archive = parent / 'libiconv-1.19.tar.gz'
        if not archive.exists():
            with tempfile.NamedTemporaryFile(dir=parent, prefix='.download-') as downloaded:
                subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                    '--proto', '=https', '--proto-redir', '=https', '--max-time', '60',
                    '--max-filesize', '10485760', '--output', downloaded.name, URL],
                    check=True, timeout=65)
                if sha(downloaded.name) != SHA256:
                    raise ValueError('libiconv archive checksum mismatch')
                os.chmod(downloaded.name, 0o644)
                os.link(downloaded.name, archive)
        if sha(archive) != SHA256:
            raise ValueError('libiconv archive checksum mismatch')
        with tempfile.TemporaryDirectory(prefix='.libiconv-', dir=parent) as temporary:
            root = Path(temporary)
            # Extraction is permitted only after checking the pinned archive.
            with tarfile.open(archive, 'r:gz') as source:
                if hasattr(tarfile, 'data_filter'):
                    source.extractall(root, filter='data')
                else:
                    # Older supported Python: this exact archive was checksum-verified.
                    source.extractall(root)
            source = root / 'libiconv-1.19'
            cli = source / 'src/iconv.c'
            text = cli.read_text()
            needle = 'if (discard_unconvertible == 1) {'
            if text.count(needle) != 2:
                raise ValueError('libiconv patch context changed')
            cli.write_text(text.replace(needle, needle + '\n              if (!silent) conversion_error_EILSEQ(infilename);'))
            identity['patched_cli_sha256'] = sha(cli)
            env = dict(os.environ, LC_ALL='C', LANG='C', CC=cc, CPPFLAGS=cppflags,
                       CFLAGS=vendor_cflags, LDFLAGS=ldflags)
            # Configure subprocesses must have the selected compiler on PATH.
            env['PATH'] = os.environ.get('PATH', os.defpath)
            # A parent make CFLAGS=... override otherwise silently replaces the
            # explicitly recorded vendor flags in this independent package build.
            for variable in ('MAKEFLAGS', 'MFLAGS', 'MAKEOVERRIDES', 'MAKELEVEL'):
                env.pop(variable, None)
            log = parent / ('libiconv-' + key + '.log')
            commands = [['./configure', '--disable-shared', '--enable-static', '--disable-nls'],
                        ['make', '-j2']]
            print('Building private GNU libiconv 1.19; log: ' + str(log), flush=True)
            with log.open('w') as output:
                for command in commands:
                    try:
                        subprocess.run(command, cwd=source, env=env, stdout=output,
                                       stderr=subprocess.STDOUT, check=True, timeout=180)
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                        output.flush()
                        print(log.read_text(errors='replace')[-6000:], file=sys.stderr)
                        raise
            # --disable-shared creates a standalone executable; it does not
            # depend on the configure/build directory after publication.
            publication = root / 'publication'
            publication.mkdir()
            binary = publication / 'iconv'
            shutil.copy2(source / 'src/iconv_no_i18n', binary)
            identity.update(path=str(generation / 'iconv'), sha256=sha(binary), commands=commands,
                            license='GPL-3.0-or-later (CLI), LGPL-2.1-or-later (library)')
            for name in ('COPYING', 'COPYING.LIB'):
                shutil.copy2(source / name, publication / name)
            (publication / 'provider.json').write_text(json.dumps(identity, indent=2) + '\n')
            publication.rename(generation)
            return identity
