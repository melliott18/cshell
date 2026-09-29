"""Strict, bounded review probes; failures are retained, never expected passes.

Usage: python3 probe-contracts.py /absolute/source /absolute/output.json
The source must already have its public cshell built. Uses its unchanged runner.
"""
import datetime,hashlib,json,sys,tempfile
from pathlib import Path
source=Path(sys.argv[1]).resolve()
sys.path.insert(0,str(source/'tests'))
import smoke
binary=source/'cshell'
records=[]

def probe(name,script,mode,expected,interactive=False):
    with tempfile.TemporaryDirectory(prefix='csh012-contract-') as tmp:
        directory=Path(tmp)
        args=['-i'] if interactive else []
        stdin=''
        if mode=='string':args+=['-c',script]
        elif mode=='file':
            (directory/'input').write_text(script);args+=['input']
        else:stdin=script
        case=dict(args=args,stdin=stdin)
        status,output,failures=smoke.capture(binary,case,directory,5,65536)
        success=(not failures and status==expected['status'] and bytes(output['stdout']).decode()==expected['stdout'] and
                 (bool(output['stderr']) if expected.get('diagnostic') else not output['stderr']))
        records.append(dict(name=name,mode=mode,case=case,expected=expected,
                            status=status,stdout=bytes(output['stdout']).decode(errors='backslashreplace'),
                            stderr=bytes(output['stderr']).decode(errors='backslashreplace'),
                            harness_failures=failures,verdict='PASS' if success else 'FAIL'))

for mode in ('string','file','stdin'):
    probe('interactive main syntax recovery',"printf 'before\\n'\n)\nprintf 'after\\n'\nexit 7\n",mode,
          dict(status=7,stdout='before\nafter\n',diagnostic=True),True)
    probe('noninteractive syntax error exits',"printf 'before\\n'\n)\nprintf 'after\\n'\n",mode,
          dict(status=2,stdout='before\n',diagnostic=True))
    for depth in (127,128,129):
        probe('valid nested braces '+str(depth),'{ '*depth+"printf 'nested\\n'; "+'}; '*depth+'\n',mode,
              dict(status=0,stdout='nested\n'))
    probe('heredoc delimiter at source end','cat <<END\nbody\nEND',mode,
          dict(status=0,stdout='body\n'))
    probe('noninteractive eval syntax error exits',"eval ')'\nprintf 'after\\n'\n",mode,
          dict(status=2,stdout='',diagnostic=True))
    probe('interactive eval syntax recovery',"eval ')'\nprintf 'after\\n'\nexit 7\n",mode,
          dict(status=7,stdout='after\n',diagnostic=True),True)
with tempfile.TemporaryDirectory(prefix='csh012-contract-pty-') as tmp:
    diagnostic='cshell: stdin: 1:1: expected command\n'
    case=dict(args=['-i'],transport='pty',steps=[
        {'expect':'$ '},{'send':')\n'},{'expect':diagnostic+'$ '},
        {'send':"printf 'after\\n'\n"},{'expect':'after\n$ '},
        {'send':'exit 7\n'}])
    status,output,failures=smoke.capture(binary,case,Path(tmp),5,65536)
    actual={k:bytes(v).decode(errors='backslashreplace') for k,v in output.items()}
    expected=dict(status=7,output='$ '+diagnostic+'$ after\n$ ')
    success=not failures and status==7 and actual.get('output')==expected['output']
    records.append(dict(name='interactive main syntax recovery',mode='pty',case=case,
                        expected=expected,status=status,output=actual,
                        harness_failures=failures,verdict='PASS' if success else 'FAIL'))
report=dict(source_revision='c8c1c91372e6e77cf2e7032765cd3c068fa1906d',
            recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            runner_sha256=hashlib.sha256((source/'tests/smoke.py').read_bytes()).hexdigest(),
            cases=records)
Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({v:sum(c['verdict']==v for c in records) for v in ('PASS','FAIL')}))
raise SystemExit(any(c['verdict']=='FAIL' for c in records))
