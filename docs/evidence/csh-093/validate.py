import gzip,json,os,platform,subprocess,sys,time
from pathlib import Path
label=sys.argv[1]
output=Path('build/csh093-validation'); output.mkdir(exist_ok=True)
commands=[['make','test-host-inventory','test-host-profile','test-host-filesystem-allocation','test-host-filesystem-provider-audit','test-host-filesystem-residual','test-host-filesystem-isolated','test-host-filesystem-interactive','test-host-filesystem-decisions','test-host-filesystem-metadata','test-host-filesystem-recursive','test-host-filesystem-path-limits','test-host-filesystem-cwd','test-host-filesystem-creation','test-host-filesystem-output'],['make','test-host-filesystem-audit'],[sys.executable,'tests/host_filesystem.py','./cshell','--extended-only','--provider-audit','--record','build/tests/host-filesystem-stock-provider-audit.json']]
records=[]
for n,cmd in enumerate(commands):
 start=time.monotonic();log=output/f'{label}-command-{n}.log'
 print('Starting',label,n,flush=True)
 with log.open('wb') as stream:
  result=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT)
 records.append(dict(argv=cmd,status=result.returncode,seconds=time.monotonic()-start,log=log.name))
 (output/f'{label}-commands.json').write_text(json.dumps(records,indent=2)+'\n')
 print('Finished',label,n,result.returncode,flush=True)
for path in Path('build/tests').glob('*.json'):
 if path.name.startswith(('host-filesystem-','host-profile-')):
  (output/(label+'-'+path.name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
for name in ['build/host-profile/manifest.json','build/host-coreutils-build/configure.log','build/host-coreutils-build/build.log','build/host-pax-build/build.log']:
 path=Path(name)
 (output/(label+'-'+path.parent.name+'-'+path.name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
