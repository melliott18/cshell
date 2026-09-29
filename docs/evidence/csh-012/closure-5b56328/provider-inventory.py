"""Read-only executable inventory; presence/hashes never establish semantics."""
import datetime,hashlib,json,os,platform,shutil,subprocess,sys
from pathlib import Path
names=[x['utility'] for x in json.loads((Path(__file__).parent/'utility-sources.json').read_text())['pages']]+['[']
standard=os.confstr('CS_PATH');profile=sys.argv[1] if len(sys.argv)>1 else None
paths={'standard':standard}
if profile:paths['qualified']=profile+os.pathsep+standard
report={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'platform':platform.platform(),'uname':list(platform.uname()),'libc':platform.libc_ver(),'uid':os.getuid(),'gid':os.getgid(),'paths':paths,'utilities':{},'commands':[]}
for name in names:
 report['utilities'][name]={}
 for label,path in paths.items():
  found=shutil.which(name,path=path)
  item={'path':found}
  if found:
   p=Path(found);item.update(realpath=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
  report['utilities'][name][label]=item
commands=[['uname','-a'],['getconf','PATH'],['cc','--version']]
if sys.platform=='linux':commands += [['cat','/etc/os-release'],['dpkg-query','-W','coreutils','dash','bash','findutils','diffutils','sed','ed','procps','libc6','gcc','locales','busybox','acl']]
else:commands += [['sw_vers'],['/usr/bin/otool','-L','/usr/bin/true']]
for cmd in commands:
 p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
 report['commands'].append({'argv':cmd,'status':p.returncode,'output':p.stdout})
print(json.dumps(report,indent=2))
