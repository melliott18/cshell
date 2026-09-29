import sys, pathlib, json, time
root=pathlib.Path.cwd();sys.path.insert(0,str(root/'tests'));import smoke
case={'name':'minimal stop continuation','args':[sys.argv[3]],'stdin':'','expect':{'status':0,'stdout':'passed\n','stderr':''}}
start=time.monotonic();results=[]
for i in range(int(sys.argv[1])):
 t=time.monotonic(); failures=smoke.run_case(root/'build/csh050-investigation/stop_minimal',case,5,65536)
 results.append({'iteration':i,'seconds':time.monotonic()-t,'failures':failures})
 if failures:
  print(json.dumps(results[-1]),flush=True);break
 if (i+1)%100==0: print('completed',i+1,flush=True)
pathlib.Path(sys.argv[2]).write_text(json.dumps({'elapsed':time.monotonic()-start,'results':results},indent=2)+'\n')
