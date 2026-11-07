import json, os, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'tests'))
import smoke
from host_permissions import run_case
from host_permission_cases import case
from host_utilities import inventory
ROOT=Path.cwd(); OUT=ROOT/'build/chgrp-triage'; search=str(ROOT/'build/host-profile/bin')+':'+os.defpath
tools=inventory(search, names=('chgrp',)); original=smoke.kill_group
failures=[]; records=[]
def capture_stall(process, deadline=None):
    if process.poll() is None:
        prefix=OUT/('stall-'+str(process.pid)); started=time.monotonic()
        observed=subprocess.run(['/bin/ps','-axo','pid=,ppid=,pgid=,stat=,wchan=,command='],capture_output=True,timeout=2)
        lines=observed.stdout.decode().splitlines(); members=[]
        for line in lines:
            fields=line.split(None,5)
            if len(fields)>2 and fields[2]==str(process.pid): members.append(line)
        prefix.with_suffix('.ps').write_text('\n'.join(members)+'\n')
        for line in members:
            pid=line.split()[0]
            try:
                subprocess.run(['/usr/bin/sample',pid,'1','1','-file',str(prefix)+'.'+pid+'.sample'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
            except subprocess.TimeoutExpired: pass
        if deadline is not None: deadline+=time.monotonic()-started
    return original(process,deadline)
smoke.kill_group=capture_stall
for repeat in range(40):
    for operand in ('staff',str(os.getegid())):
        for mode in ('direct','string','file','stdin'):
            expected=case('chgrp','triage-'+operand,[operand,'subject','data'],metadata={p:{'uid':os.geteuid(),'gid':os.getegid()} for p in ('subject','data')})
            started=time.monotonic(); result=run_case(ROOT/'cshell',tools,search,expected,mode,Path(__import__('tempfile').gettempdir()))
            result.update(repeat=repeat,elapsed=time.monotonic()-started)
            records.append(result); (OUT/'probe.json').write_text(json.dumps(records,indent=2))
            if result['verdict']!='PASS':
                failures.append(result);print('FAIL',repeat,operand,mode,result.get('actual'),flush=True)
    print('round',repeat+1,'cases',len(records),'failures',len(failures),flush=True)
    if failures: break
