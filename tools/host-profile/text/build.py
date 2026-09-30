#!/usr/bin/env python3
"""Build checksum-pinned text providers under build/, without host installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(destination, jobs):
    system = platform.system()
    if system not in ('Darwin', 'Linux'):
        raise ValueError('Only Darwin and Linux are supported')
    pins = json.loads((HERE/'sources.json').read_text())
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LC_ALL='C')
    compiler = shlex.split(env.get('CC', 'cc'))
    compiler_version = subprocess.check_output(compiler+['--version'],text=True,env=env)
    expected = {'head', 'cut', 'tsort', 'sed', 'ed'} | ({'tail'} if system == 'Linux' else set())
    recipe = dict(system=system, machine=platform.machine(), release=platform.release(), sources=pins,
                  build_script=sha(__file__), patch=sha(HERE/'ed-sigint.patch'),
                  compiler=compiler, compiler_version=compiler_version, environment={k:env.get(k) for k in
                  ('CFLAGS','CPPFLAGS','LDFLAGS','CC','SDKROOT','MACOSX_DEPLOYMENT_TARGET')})
    manifest_path = destination/'manifest.json'
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if (previous.get('recipe') == recipe and set(previous.get('executables', {})) == expected and all(
                (destination/'bin'/name).is_file() and
                sha(destination/'bin'/name) == row['sha256']
                for name,row in previous['executables'].items())):
            print('Verified cached text providers: '+str(destination/'bin'))
            return
    work = Path(tempfile.mkdtemp(prefix='sources-', dir=destination))
    cache = destination/'downloads'
    cache.mkdir(exist_ok=True)

    def run(argv, cwd, label):
        print(label, flush=True)
        with (work/(label+'.log')).open('wb') as log:
            subprocess.run(argv, cwd=cwd, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)

    source = {}
    for name, pin in pins.items():
        if name == 'chimerautils' and system != 'Linux':
            continue
        archive = cache/(name + ('.tar.lz' if name == 'ed' else '.tar.xz'
                                  if name in ('sed','coreutils') else '.tar.gz'))
        if not archive.exists():
            partial = archive.with_suffix(archive.suffix+'.partial')
            run(['curl','--fail','--location','--silent','--show-error',
                 '--proto','=https','--tlsv1.2',pin['url'],'-o',str(partial)], work, name+'-download')
            if sha(partial) != pin['sha256']:
                raise ValueError('Archive checksum mismatch: '+name)
            partial.replace(archive)
        if sha(archive) != pin['sha256']:
            raise ValueError('Cached archive checksum mismatch: '+name)
        run(['tar','-xf',str(archive),'-C',str(work)], work, name+'-extract')
        source[name] = work/pin['directory']

    run(['./configure','--disable-nls','--without-gmp'],source['coreutils'],'coreutils-configure')
    # The all target generates gnulib headers before compiling program targets.
    run(['make','-j'+str(jobs)],source['coreutils'],'coreutils-build')
    run(['./configure','--disable-nls'],source['sed'],'sed-configure')
    run(['make','-j'+str(jobs)],source['sed'],'sed-build')
    run(['patch','--batch','-p1','-i',str(HERE/'ed-sigint.patch')],source['ed'],'ed-patch')
    run(['./configure'],source['ed'],'ed-configure')
    run(['make','-j'+str(jobs)],source['ed'],'ed-build')
    run(['make','check'],source['ed'],'ed-check')
    products = {n:source['coreutils']/'src'/n for n in ('head','cut','tsort')}
    products.update(sed=source['sed']/'sed/sed', ed=source['ed']/'ed')
    if system == 'Linux':
        ch = source['chimerautils']
        # None of tail's used interfaces need the optional compat replacements.
        # Keep declarations for absent APIs; link only expand_number, which tail uses.
        (ch/'include/config-compat.h').write_text('/* Standalone tail build. */\n')
        tail = ch/'src.freebsd/coreutils/tail'
        run(compiler + ['-std=c99','-O2','-D_GNU_SOURCE','-D_FILE_OFFSET_BITS=64',
                        '-Dlint','-I'+str(ch/'include'),'-o',str(work/'tail')] +
            [str(tail/(n+'.c')) for n in ('tail','forward','reverse','read','misc')] +
            [str(ch/'src.freebsd/compat/expand_number.c')],ch,'tail-build')
        products['tail'] = work/'tail'
    # Publish only after every build and upstream ed check succeeded.
    bindir = destination/'bin'
    bindir.mkdir(exist_ok=True)
    executables = {}
    for name,path in products.items():
        target = bindir/name
        staging = bindir/(name+'.new')
        shutil.copy2(path, staging)
        staging.replace(target)
        executables[name] = dict(path=str(target),sha256=sha(target),source=str(path))
    manifest_path.write_text(json.dumps(dict(recipe=recipe,executables=executables,
        source_directory=str(work),compiler_version=compiler_version),indent=2)+'\n')
    print('Built text providers: '+str(bindir), flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,default=ROOT/'build/text-providers')
    parser.add_argument('--jobs',type=int,default=2)
    args=parser.parse_args()
    if not 1 <= args.jobs <= 32:
        parser.error('--jobs must be between 1 and 32')
    try:
        build(args.destination,args.jobs)
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        parser.exit(1,str(error)+'\nBuild logs and verified source archives remain in '+str(args.destination)+'\n')
