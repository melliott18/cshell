import ctypes,os,sys,unittest,threading,time
from pathlib import Path
sys.path.insert(0,'tests')
import test_host_filesystem as test
assert ctypes.CDLL(None,use_errno=True).prctl(36,1,0,0,0)==0
original=os.kill
reaping=set()
threads=[]
def reap_later(pid):
    time.sleep(0.1)
    child,status=os.waitpid(pid,0)
    print("DELAYED_REAP",child,status,flush=True)
def kill(pid,signum):
    result=original(pid,signum)
    if signum==0:
        try:
            print('VISIBLE_AFTER_CLEANUP',Path('/proc/'+str(pid)+'/stat').read_text(),flush=True)
            if pid not in reaping:
                reaping.add(pid)
                thread=threading.Thread(target=reap_later,args=(pid,))
                threads.append(thread)
                thread.start()
        except FileNotFoundError:pass
    return result
os.kill=kill
result=unittest.TextTestRunner(verbosity=2).run(test.FilesystemHarnessTests('test_metadata_timeout_cleans_process_and_fixture_in_every_mode'))
for thread in threads: thread.join(2)
assert result.wasSuccessful()
while True:
    try:
        pid,status=os.waitpid(-1,os.WNOHANG)
        if not pid:break
        print('REAPED_OWNED_CHILD',pid,status,flush=True)
    except ChildProcessError:break
