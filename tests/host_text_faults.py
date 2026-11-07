#!/usr/bin/env python3
"""Attested faults in selected source-built text providers, never in the shell."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

from host_text_boundaries import child_setup, collect, finish
from host_utilities import serial, source_identity


def definitions():
    for utility in ('cat','head','cmp'):
        for fault in ('read-eintr','read-eio','read-short'):
            yield utility,fault
    for fault in ('write-eintr','write-short'):
        yield 'cat',fault
    yield 'sed','realloc-enomem'


def run_case(binary,path,library,utility,fault,mode):
    selected=shutil.which(utility,path=path)
    row=dict(id=utility+'/'+fault,mode=mode,verdict='FAIL',provider=selected,
             scope='test-only interposition; no signal-delivery or arbitrary recovery claim')
    process=None
    with tempfile.TemporaryDirectory(prefix='csh-text-fault-') as temporary:
        root=Path(temporary);trace=root/'trace'
        data=b'alpha\nbeta\ngamma\n'*200
        (root/'same').write_bytes(data)
        args={'cat':[], 'head':['-n','600'], 'cmp':['-','same'], 'sed':['s/x/y/']}[utility]
        if utility=='sed':data=b'x'*131072+b'\n'
        (root/'input').write_bytes(data)
        expected=data if utility in ('cat','head') else b''
        fails=fault in ('read-eintr','read-eio','realloc-enomem')
        if fails: expected=b''
        row['expected']=dict(stdout=serial(expected),status='positive failure' if fails else 0,
                             stderr='nonempty' if fails else '',trace='fault\n')
        env=dict(PATH=path,LC_ALL='C',HOME=str(root),CSH_TEXT_FAULT=fault,CSH_TEXT_TRACE=str(trace))
        loader='DYLD_INSERT_LIBRARIES' if platform.system()=='Darwin' else 'LD_PRELOAD'
        command=[selected]+args if selected else []
        if mode=='direct':env[loader]=str(library)
        else:command=[str(binary),'-c','exec '+shlex.join(['/usr/bin/env',loader+'='+str(library)]+command)]
        try:
            if not selected:raise RuntimeError('Missing provider: '+utility)
            row['provider_sha256']=hashlib.sha256(Path(selected).read_bytes()).hexdigest()
            with (root/'input').open('rb') as source:
                process=subprocess.Popen(command,cwd=root,env=env,stdin=source,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=child_setup)
            out,err=collect(process,time.monotonic()+5)
            attestation=trace.read_bytes() if trace.exists() else b''
            row['actual']=serial(dict(status=process.returncode,stdout=out,stderr=err,trace=attestation))
            status_ok=process.returncode>0 if fails else process.returncode==0
            row['verdict']='PASS' if (status_ok and out==expected and
                (bool(err) if fails else err==b'') and attestation==b'fault\n') else 'FAIL'
        except (OSError,RuntimeError,subprocess.SubprocessError) as error:
            row['error']=str(error)
        finally:
            try:
                row['leader_reaped']=finish(process)
            except (OSError,subprocess.SubprocessError) as error:
                row['leader_reaped']=False
                row['cleanup_error']=str(error)
    row['fixture_removed']=not root.exists()
    if not row['leader_reaped'] or not row['fixture_removed']:row['verdict']='FAIL'
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary',type=Path)
    parser.add_argument('--path',required=True)
    parser.add_argument('--library',type=Path,required=True)
    parser.add_argument('--record',type=Path,required=True)
    args=parser.parse_args()
    rows=[]
    for utility,fault in definitions():
        for mode in ('direct','exec'):
            row=run_case(args.binary.resolve(),args.path,args.library.resolve(),utility,fault,mode)
            rows.append(row);print(row['verdict']+': '+row['id']+' ('+mode+')',flush=True)
            if row['verdict']=='FAIL':print(json.dumps(row),flush=True)
    totals={v.lower():sum(r['verdict']==v for r in rows) for v in ('PASS','FAIL')}
    args.record.parent.mkdir(parents=True,exist_ok=True)
    args.record.write_text(json.dumps(dict(totals=totals,cases=rows,source_identity=source_identity(),
        platform=platform.platform(),library_sha256=hashlib.sha256(args.library.read_bytes()).hexdigest(),
        fault_contract='EINTR/EIO read returns are diagnosed as errors; short reads and cat short/EINTR writes preserve exact bytes; sed growth ENOMEM is diagnosed. No universal EINTR retry requirement.',
        limits=dict(timeout_seconds=5,input_bytes_max=131073,capture_bytes=65536)),indent=2)+'\n')
    print(totals)
    return int(bool(totals['fail']))


if __name__=='__main__':raise SystemExit(main())
