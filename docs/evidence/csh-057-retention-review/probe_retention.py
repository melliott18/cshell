"""Observe flushed checkpoints without changing the production case or deadline.
Usage: probe_retention.py BINARY RESULT_JSON [CASE_ENV_JSON]
"""
import json, os, pathlib, sys, tempfile, time
root=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'tests'))
import smoke
binary=pathlib.Path(sys.argv[1]).resolve()
case=smoke.load_suite(root/'tests/fixtures/job-retention.json')['cases'][0]
if len(sys.argv)>3: case['env']=json.loads(sys.argv[3])
start=time.monotonic(); events=[]; read=os.read

def observe(fd,n):
 data=read(fd,n)
 if b'retention' in data or b'CHILD_MAX' in data:
  events.append({'elapsed':time.monotonic()-start,'data':data.decode(errors='replace')})
  print(json.dumps(events[-1]),flush=True)
 return data
os.read=observe
with tempfile.TemporaryDirectory(prefix='csh057-retention-probe-') as tmp:
 status,output,failures=smoke.capture(binary,case,pathlib.Path(tmp),60,65536)
 for name,data in output.items():
  if bytes(data)!=case['expect'][name].encode(): failures.append(name+' differs')
 if status!=0: failures.append('status '+str(status))
result={'binary':str(binary),'env':case.get('env',{}),'seconds':time.monotonic()-start,'status':status,'failures':failures,'events':events,'output':{k:bytes(v).decode(errors='replace') for k,v in output.items()}}
pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('events','output')}),flush=True)
sys.exit(bool(failures))
