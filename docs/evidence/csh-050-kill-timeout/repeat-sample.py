import sys, pathlib, json, time
root=pathlib.Path.cwd();sys.path.insert(0,str(root/'tests'));import smoke
cases=smoke.load_suite(root/'build/tests/kill-job-state.json')['cases']
case=next(c for c in cases if c['name']=='kill state: ungrouped/CONT/after')
case['env']={'CSH_TRACE':str(root/'build/csh050-investigation/sample-pids.log')}
import selectors,subprocess
select=selectors.DefaultSelector.select
sampled=False
def observe(self,timeout=None):
 global sampled
 result=select(self,timeout)
 if not sampled and time.monotonic()-t>.3:
  sampled=True
  pids=(root/'build/csh050-investigation/sample-pids.log').read_text().splitlines()[0].split()
  ps=subprocess.run(['/bin/ps','-o','pid,ppid,pgid,stat,wchan,command','-p',','.join(pids)],capture_output=True,text=True)
  (root/'build/csh050-investigation/stalled-ps.txt').write_text(ps.stdout+ps.stderr)
  samplers=[]
  for index,pid in enumerate(pids):
   samplers.append(subprocess.Popen(['/usr/bin/sample',pid,'1','1','-file',str(root/f'build/csh050-investigation/sample-{index}.txt')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
  for process in samplers:process.wait(timeout=2)
 return result
selectors.DefaultSelector.select=observe
start=time.monotonic();results=[]
for i in range(int(sys.argv[1])):
 (root/'build/csh050-investigation/sample-pids.log').write_text('')
 sampled=False
 t=time.monotonic(); failures=smoke.run_case(root/'build/csh050-investigation/kill_sample',case,5,65536)
 results.append({'iteration':i,'seconds':time.monotonic()-t,'failures':failures})
 if failures:
  print(json.dumps(results[-1]),flush=True);break
 if (i+1)%100==0: print('completed',i+1,flush=True)
pathlib.Path(sys.argv[2]).write_text(json.dumps({'elapsed':time.monotonic()-start,'results':results},indent=2)+'\n')
