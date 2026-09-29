#!/usr/bin/env python3
"""Strict CSH-074 host language/editor subset, never a whole-page claim."""
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys
import tempfile

import smoke
from host_language_cases import UTILITIES, BASE, cases
from host_platform import filesystem_identity
from host_utilities import inventory, serial, sha, source_identity, sanitizer_diagnostic, match

MODES = ('direct', 'string', 'file', 'stdin')


def matches(expected, actual):
    if expected == 'optional-diagnostic':
        return isinstance(actual, bytes)  # ed permits warning/diagnostic wording.
    if expected == 'normal':
        return isinstance(actual, int) and actual >= 0
    if expected == 'xargs-error':
        return isinstance(actual, int) and 1 <= actual <= 125
    return match(expected, actual)


def environment(search_path, sanitizer=False):
    result = {'PATH': search_path}
    if sanitizer:
        result.update(ASAN_OPTIONS='halt_on_error=1' +
                      (':detect_leaks=0' if platform.system() == 'Linux' else ''),
                      UBSAN_OPTIONS='halt_on_error=1')
    return result


def run_case(binary, path, case, mode, root, search_path, sanitizer=False):
    with tempfile.TemporaryDirectory(prefix='csh074-', dir=root) as temporary:
        directory = Path(temporary)
        record = dict(id=case['id'], mode=mode, expected=serial(case), phase='setup')
        try:
            for name, data in case.get('input_files', {}).items():
                target=directory/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            (directory/'input').write_bytes(case['stdin'])
            fixture=dict(args=case['args'], stdin=case['stdin'], env=environment(search_path, sanitizer))
            executable=Path(path)
            if mode!='direct':
                # PATH lookup in all public input modes; direct mode independently
                # execs the selected pathname with the identical argument vector.
                script=shlex.join([case['utility']]+case['args'])+' <input\n'
                executable=binary
                if mode=='string':
                    fixture.update(args=['-c',script],stdin=b'')
                elif mode=='file':
                    (directory/'script').write_text(script)
                    fixture.update(args=['script'],stdin=b'')
                else:
                    fixture.update(args=[],stdin=script)
            record.update(phase='assertion', invocation=serial(dict(binary=str(executable),**fixture)))
            status,output,errors=smoke.capture(executable,fixture,directory,5,65536)
            actual_files={name:(directory/name).read_bytes() if (directory/name).is_file() else None
                          for name in case.get('files',{})}
            nonempty={name:(directory/name).is_file() and (directory/name).stat().st_size>0
                      for name in case.get('nonempty_files',[])}
            if sanitizer_diagnostic(output):
                errors.append('sanitizer diagnostic')
            ok=(not errors and matches(case['status'],status)
                and matches(case.get('stdout_rule',case['stdout']),bytes(output['stdout']))
                and matches(case['stderr'],bytes(output['stderr']))
                and actual_files==case.get('files',{}) and all(nonempty.values()))
            record.update(verdict='PASS' if ok else 'FAIL', actual=serial(dict(
                status=status,stdout=bytes(output['stdout']),stderr=bytes(output['stderr']),
                files=actual_files,nonempty_files=nonempty,errors=errors)))
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            record.update(verdict='FAIL',error=str(error))
    record['fixture_removed']=not directory.exists()
    if not record['fixture_removed']:
        record['verdict']='FAIL'
    return record


def run_signal(binary, path, action, mode, root, search_path, sanitizer=False):
    with tempfile.TemporaryDirectory(prefix='csh074-signal-',dir=root) as temporary:
        directory=Path(temporary)
        # Always preserve the original operand, including after recovery.
        (directory/'original').write_bytes(b'')
        argv=[path,'-s','original']
        fixture=dict(args=[],stdin='',env=environment(search_path, sanitizer))
        if mode!='direct':
            script='exec ed -s original\n'
            if mode=='string':
                argv=[str(binary),'-c',script]
            else:
                # Script-file mode leaves the independent editor input pipe open.
                (directory/'script').write_text(script)
                argv=[str(binary),'script']
        helper=Path(__file__).with_name('host_language_helper.py').resolve()
        fixture['args']=[str(helper),'ed-signal',action]+argv
        record=dict(id='ed/signal-'+action,mode=mode,phase='assertion',
                    source=BASE+'ed.html',clauses=['ASYNCHRONOUS EVENTS'],
                    invocation=fixture)
        try:
            status,output,errors=smoke.capture(Path(sys.executable),fixture,directory,7,65536)
            detail=json.loads((directory/'signal.json').read_text()) if (directory/'signal.json').is_file() else None
            ok=(status==0 and bytes(output['stdout'])==b'recovered and reaped\n'
                and not output['stderr'] and not errors and detail is not None
                and (directory/'original').read_bytes()==b'')
            record.update(verdict='PASS' if ok else 'FAIL',signal=detail,actual=serial(dict(
                status=status,stdout=bytes(output['stdout']),stderr=bytes(output['stderr']),errors=errors)))
        except (OSError,ValueError,subprocess.SubprocessError) as error:
            record.update(verdict='FAIL',error=str(error))
    record['fixture_removed']=not directory.exists()
    if not record['fixture_removed']:
        record['verdict']='FAIL'
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary',type=Path)
    parser.add_argument('--path',default=os.defpath)
    parser.add_argument('--sanitizer',action='store_true')
    parser.add_argument('--record',type=Path,required=True)
    parser.add_argument('--ed-sigint',action='store_true',
                        help='Strict optional SIGINT stream reproducer; current providers fail')
    args=parser.parse_args()
    binary=args.binary.resolve()
    tools=inventory(args.path,UTILITIES)
    records=[]
    for case in cases():
        path=tools[case['utility']]['path']
        for mode in MODES:
            if path:
                record=run_case(binary,path,case,mode,None,args.path,args.sanitizer)
            else:
                record=dict(id=case['id'],mode=mode,verdict='FAIL',phase='setup',
                            error='missing required provider: '+case['utility'])
            records.append(record)
            print(record['verdict']+': '+record['id']+' ('+mode+')',flush=True)
            if record['verdict']=='FAIL':
                print(json.dumps(record.get('actual',record)),flush=True)
    if tools['ed']['path']:
        for action in ('hup','hup-home') + (('int',) if args.ed_sigint else ()):
            for mode in ('direct','string','file'):
                record=run_signal(binary,tools['ed']['path'],action,mode,None,args.path,args.sanitizer)
                records.append(record)
                print(record['verdict']+': '+record['id']+' ('+mode+')',flush=True)
                if record['verdict']=='FAIL':
                    print(json.dumps(record),flush=True)
    counts={v:sum(r['verdict']==v for r in records) for v in ('PASS','FAIL')}
    manifest=Path(__file__).with_name('host_language_contracts.json')
    result=dict(recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                argv=sys.argv,platform=platform.platform(),uname=list(platform.uname()),
                libc=platform.libc_ver(),uid=os.getuid(),gid=os.getgid(),path=args.path,
                environment={'LANG':'C','LC_ALL':'C','HOME':'private .home','TMPDIR':'private .tmp'},
                filesystem=filesystem_identity(Path(tempfile.gettempdir())),inventory=tools,
                source_identity=source_identity(),binary_sha256=sha(binary),
                contracts_sha256=sha(manifest),scope='bounded C-locale witnesses; full pages unqualified',
                limits={'case_seconds':5,'signal_seconds':7,'cleanup_seconds':1,'output_bytes':65536,
                        'child_resources':'smoke.child_limits; 1 MiB files, 64 descriptors, no core dumps'},
                extended_sigint=args.ed_sigint,sanitizer=args.sanitizer,totals=counts,cases=records)
    command=(['dpkg-query','-W','-f=${Package} ${Version}\n'] if platform.system()=='Linux'
             else ['sw_vers'])
    identity=subprocess.run(command,capture_output=True,text=True,timeout=10)
    result['package_identity']=dict(argv=command,status=identity.returncode,stdout=identity.stdout,stderr=identity.stderr)
    args.record.parent.mkdir(parents=True,exist_ok=True)
    args.record.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(counts))
    return int(bool(counts['FAIL']))


if __name__=='__main__':
    raise SystemExit(main())
