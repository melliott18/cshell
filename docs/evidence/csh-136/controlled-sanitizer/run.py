#!/usr/bin/env python3
"""Replay the 24 credential predicates and fatal sanitizer controls in Docker."""
import hashlib,json,os,platform,subprocess,tempfile,pathlib
assert platform.system() == 'Linux' and os.geteuid() == 0 and pathlib.Path('/.dockerenv').exists(), 'requires disposable Linux container root'
P=pathlib.Path('/tmp/repro'); P.mkdir(mode=0o755)
flags=['-std=c99','-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer']
for name in ['before','after','helper','env']:
 source = {'after':'/repo/tools/host-profile/test.c','helper':'/repo/tests/host_utility_helper.c'}.get(name,'/input/'+name+'.c')
 subprocess.run(['gcc',*([] if name=='env' else flags),'-I/input',source,'-o',str(P/name)],check=True)
for name in ['before','after']:
 (P/(name+'-bin')).mkdir()
 for utility in ['test','[']: (P/(name+'-bin')/utility).symlink_to(P/name)
env={'PATH':'/usr/bin:/bin','ASAN_OPTIONS':'halt_on_error=1:detect_leaks=0','UBSAN_OPTIONS':'halt_on_error=1'}
records=[]
for provider in ['before','after']:
 for kind in ['owner','group']:
  for real,effective in [(10002,10001),(10001,10002)]:
   for utility in ['test','[']:
    for mode in ['string','file','stdin']:
     with tempfile.TemporaryDirectory(dir=P) as d:
      root=pathlib.Path(d); root.chmod(0o755)
      f=root/'controlled'; f.write_bytes(b'private\n')
      os.chown(f,10001 if kind=='owner' else 0,10002 if kind=='owner' else 10001)
      f.chmod(0o400 if kind=='owner' else 0o040)
      command=f'{P}/helper identity {real} {effective} {P}/{provider}-bin/{utility} -r controlled'+(' ]' if utility=='[' else '')+'\n'
      if mode=='string': argv=['/work/cshell','-c',command]; data=b''
      elif mode=='file':
       (root/'script').write_text(command); argv=['/work/cshell','script']; data=b''
      else: argv=['/work/cshell']; data=command.encode()
      r=subprocess.run(argv,input=data,capture_output=True,cwd=d,env=env,timeout=10)
      want=f'uid={real} euid={effective} gid={real} egid={effective} groups=0\n'.encode()
      ok=(r.returncode==(0 if effective==10001 else 1) and r.stdout==want and r.stderr==b'')
      records.append(dict(provider=provider,kind=kind,real=real,effective=effective,utility=utility,mode=mode,passed=ok,status=r.returncode,stdout=r.stdout.decode(),stderr=r.stderr.decode()))
# Establish that options survive exec while the sanitizer's Linux env source is denied.
r=subprocess.run([str(P/'helper'),'identity','10002','10001',str(P/'env')],capture_output=True,env=env,timeout=10)
# Sanity-check both diagnostic classes still terminate under the same credentials.
faults=[]
for name,body,marker in [('address','volatile char *p=malloc(4); p[8]=1; return p[8];','AddressSanitizer'),('undefined','volatile int n=2147483647; return n+1;','runtime error:')]:
 source='#define main provider_main\n#include "/repo/tools/host-profile/test.c"\n#undef main\n#include <stdlib.h>\nint main(void) {'+body+'}\n'
 (P/(name+'.c')).write_text(source)
 subprocess.run(['gcc',*flags,*(['-fno-sanitize=undefined'] if name=='address' else []),'-I/input',str(P/(name+'.c')),'-o',str(P/name)],check=True)
 result=subprocess.run([str(P/'helper'),'identity','10002','10001',str(P/name)],capture_output=True,env=env,timeout=10)
 faults.append(dict(name=name,status=result.returncode,stderr=result.stderr.decode(),passed=result.returncode!=0 and marker.encode() in result.stderr))
summary={provider:{'passed':sum(x['passed'] for x in records if x['provider']==provider),'failed':sum(not x['passed'] for x in records if x['provider']==provider)} for provider in ['before','after']}
output=dict(platform=platform.platform(),compiler=subprocess.check_output(['gcc','--version'],text=True).splitlines()[0],flags=flags,source_sha256={name:hashlib.sha256(pathlib.Path({'after':'/repo/tools/host-profile/test.c','helper':'/repo/tests/host_utility_helper.c'}.get(name,'/input/'+name+'.c')).read_bytes()).hexdigest() for name in ['before','after','helper','env']},summary=summary,cases=records,environment_probe=dict(status=r.returncode,stdout=r.stdout.decode(),stderr=r.stderr.decode()),faults=faults)
pathlib.Path('/output/results.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(summary)); print(output['environment_probe']);print([(x['name'],x['passed']) for x in faults])
assert summary['before']=={'passed':0,'failed':24},summary
assert summary['after']=={'passed':24,'failed':0},summary
assert b'ASAN_OPTIONS=halt_on_error=1:detect_leaks=0 proc_errno=13' in r.stdout
assert all(x['passed'] for x in faults)
