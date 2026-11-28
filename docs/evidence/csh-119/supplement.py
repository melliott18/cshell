import ast,subprocess,sys
from pathlib import Path
source=Path('docs/evidence/csh-119/validate.py').read_text()
tree=ast.parse(source)
targets=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='targets' for t in n.targets))
commands=[['make',*[t for t in targets if t not in ('test-host-inventory','test-host-profile')]],['python3','tests/host_filesystem.py','./cshell','--audit','--provider-audit','--path',str(Path('build/host-profile/bin').resolve())+':/usr/bin:/bin:/usr/sbin:/sbin','--record','build/tests/host-filesystem-profile.json'],['python3','tests/test_host_permissions.py']]
for i,cmd in enumerate(commands[:1]):
 with open(f'build/csh119-validation/linux-supplement-{i}.log','wb') as out:
  result=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT)
 print(i,result.returncode,flush=True)
