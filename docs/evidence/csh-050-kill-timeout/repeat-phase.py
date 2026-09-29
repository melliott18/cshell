import sys, pathlib, json, time
root=pathlib.Path.cwd();sys.path.insert(0,str(root/'tests'));import smoke
cases=smoke.load_suite(root/'build/tests/kill-job-state.json')['cases']
case=next(c for c in cases if c['name']=='kill state: ungrouped/CONT/after')
case['env']={'CSH_TRACE':str(root/'build/csh050-investigation/phase.log')}
start=time.monotonic();results=[]
for i in range(int(sys.argv[1])):
 (root/'build/csh050-investigation/phase.log').write_text('')
 t=time.monotonic(); failures=smoke.run_case(root/'build/csh050-investigation/kill_phase',case,5,65536)
 results.append({'iteration':i,'seconds':time.monotonic()-t,'failures':failures})
 if failures:
  print(json.dumps(results[-1]),flush=True);break
 if (i+1)%100==0: print('completed',i+1,flush=True)
pathlib.Path(sys.argv[2]).write_text(json.dumps({'elapsed':time.monotonic()-start,'results':results},indent=2)+'\n')
