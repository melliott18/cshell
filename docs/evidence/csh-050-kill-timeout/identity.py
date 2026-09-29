import datetime,hashlib,json,pathlib,platform,subprocess,sys
root=pathlib.Path.cwd()
def command(args):
 p=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);return {'status':p.returncode,'output':p.stdout.strip()}
files=[root/'Makefile',root/'Dockerfile']
for dirname in ['src','include','tests']:
 files.extend(p for p in (root/dirname).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
result={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':'d1ca90b','variant':sys.argv[1],'source_manifest':manifest,'source_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),'uname':platform.uname()._asdict(),'python':sys.version,'compiler':command(['cc','--version']),'normal_flags':'-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2','sanitizer_flags':'-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer; link -fsanitize=address,undefined','cppflags':'-D_POSIX_C_SOURCE=200809L -Iinclude','binaries':{}}
for name in ['cshell','build/tests/kill_job_state','build/tests/jobs_lifecycle','build/tests/execute_faults','build/csh050-investigation/kill_phase','build/csh050-investigation/kill_trace','build/csh050-investigation/kill_sample','build/csh050-investigation/kill_alarm','build/csh050-investigation/old-kill','build/csh050-investigation/stop_minimal']:
 p=root/name
 if p.exists():result['binaries'][name]=hashlib.sha256(p.read_bytes()).hexdigest()
if sys.platform=='darwin':result['os_version']=command(['sw_vers'])
else:result['libc']=command(['getconf','GNU_LIBC_VERSION'])
print(json.dumps(result,indent=2))
