import json,os,subprocess,sys,time
from pathlib import Path
label=sys.argv[1]
root=Path.cwd(); destination=root/'build/csh091-validation';destination.mkdir(parents=True,exist_ok=True)
commands=[['make','test-host-inventory','test-host-profile','test-host-filesystem-allocation','test-host-filesystem-provider-audit','test-host-filesystem-residual','test-host-filesystem-isolated','test-host-filesystem-interactive','test-host-filesystem-decisions','test-host-filesystem-metadata','test-host-filesystem-recursive','test-host-filesystem-path-limits','test-host-filesystem-cwd'],['make','test-host-filesystem-audit'],[sys.executable,'tests/host_filesystem.py','./cshell','--extended-only','--provider-audit','--record','build/tests/host-filesystem-stock-provider-audit.json']]
records=[]
for index,command in enumerate(commands):
 start=time.time();log=destination/f'{label}-{index}.log'
 with log.open('wb') as output:
  result=subprocess.run(command,stdout=output,stderr=subprocess.STDOUT)
 row=dict(argv=command,exit_status=result.returncode,elapsed_seconds=time.time()-start,log=log.name)
 records.append(row);(destination/f'{label}-commands.json').write_text(json.dumps(records,indent=2)+'\n')
 print(json.dumps(row),flush=True)
