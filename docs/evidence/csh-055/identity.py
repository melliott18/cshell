import datetime,hashlib,json,os,pathlib,platform,subprocess,sys
root=pathlib.Path.cwd()
def command(*args):
 try: p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 except OSError as error: return {'argv':list(args),'status':None,'output':str(error)}
 return {'argv':list(args),'status':p.returncode,'output':p.stdout.strip()}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[root/'Makefile',root/'Dockerfile']
for directory in ('src','include','tests'):
 inputs.extend(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
manifest={str(p.relative_to(root)):sha(p) for p in sorted(inputs)}
identity={'recorded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source_revision':os.environ.get('EVIDENCE_REVISION') or command('git','rev-parse','HEAD')['output'],
 'source_note':'Source digest covers Makefile, Dockerfile, src, include and tests, excluding Python caches. Subsequent evidence documentation is outside that digest.',
 'source_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest(),
 'binary':{'path':str(root/'cshell'),'realpath':str((root/'cshell').resolve()),'sha256':sha(root/'cshell')},
 'compiler':command('cc','--version'), 'platform':platform.platform(),'uname':list(platform.uname()),
 'python':sys.version,'libc':platform.libc_ver(),
 'flags':{'CPPFLAGS':'-D_POSIX_C_SOURCE=200809L -Iinclude','CFLAGS':os.environ.get('EVIDENCE_CFLAGS','-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2'),'LDFLAGS':os.environ.get('EVIDENCE_LDFLAGS',''),'LDLIBS':''},
 'generated_suites':{str(p.relative_to(root)):sha(p) for p in sorted((root/'build/tests').glob('*.json'))},
 'source_files':manifest,
 'test_executables':{str(p.relative_to(root)):sha(p) for p in sorted((root/'build/tests').iterdir()) if p.is_file() and os.access(p,os.X_OK)},
 'helpers':{str(p):sha(p) for p in [pathlib.Path('/bin/cat'),pathlib.Path('/usr/bin/cmp'),root/'build/tests/execute_helper'] if p.exists()}}
if sys.platform=='darwin':
 identity['os_build']=command('sw_vers');identity['system_library']=command('ls','-l','/usr/lib/libSystem.B.dylib')
else:
 identity['os_release']=pathlib.Path('/etc/os-release').read_text();identity['libc_build']=command('ldd','--version')
print(json.dumps(identity,indent=2))
