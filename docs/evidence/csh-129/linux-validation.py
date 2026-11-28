import json, os, shutil, subprocess, time
from pathlib import Path
os.chdir('/work')
root=Path('build/csh129-validation');root.mkdir(parents=True,exist_ok=True)
for name in ('host_language_helper.py','ed_signal_order_probe.py','test_host_languages.py'):
    shutil.copyfile('/source/tests/'+name, 'tests/'+name)
shutil.copyfile('/source/build/tests/csh129-original-helper.py','tests/csh129-original-helper.py')
commands=[
 ['make','-j4','cshell','host-profile','build/tests/host_ed_faults'],
 ['python3','tests/ed_signal_order_probe.py','--helper','tests/csh129-original-helper.py','--ed','build/host-ed','--record',str(root/'ordered-original.json')],
 ['python3','tests/ed_signal_order_probe.py','--ed','build/host-ed','--record',str(root/'ordered-fixed.json')],
 ['python3','tests/host_languages.py','./cshell','--path','/work/build/host-profile/bin:'+os.defpath,'--case','ed/signal-int','--record',str(root/'signal-int.json')],
 ['make','test-host-languages','test-host-profile'],
 ['make','test-harness'],
]
records=[]
for i, command in enumerate(commands):
    start=time.monotonic()
    with (root/f'command-{i}.log').open('w') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    records.append(dict(argv=command,status=result.returncode,seconds=time.monotonic()-start))
    (root/'commands.json').write_text(json.dumps(dict(uid=os.getuid(),commands=records),indent=2)+'\n')
    print(i, result.returncode,flush=True)
for name in ('host-languages-results.json','host-languages-profile-results.json','host-profile-results.json','host-filesystem-profile.json','host-text-results.json'):
    path=Path('build/tests')/name
    if path.exists():shutil.copyfile(path,root/name)
