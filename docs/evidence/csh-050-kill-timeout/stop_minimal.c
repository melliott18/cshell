#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
static void event(int sig) { (void)sig; }
static void byte(int fd) { char c; ssize_t n; do { n=read(fd,&c,1); } while(n<0 && errno==EINTR); assert(n==1); }
int main(int argc,char **argv) {
 int gate[2],release[2],status;pid_t children[2];struct sigaction action={0};
 assert(argc==2);alarm(4);action.sa_handler=event;sigemptyset(&action.sa_mask);assert(sigaction(SIGCHLD,&action,0)==0);
 assert(pipe(gate)==0 && pipe(release)==0);
 for(int i=0;i<2;++i){
  children[i]=fork();assert(children[i]>=0);
  if(!children[i]){close(gate[1]);close(release[1]);byte(gate[0]);
   if(strcmp(argv[1],"parent")) assert((!strcmp(argv[1],"raise")?raise(SIGSTOP):kill(getpid(),SIGSTOP))==0);
   byte(release[0]);_exit(23+i);
  }
 }
 assert(write(gate[1],"xx",2)==2);close(gate[0]);close(gate[1]);
 if(!strcmp(argv[1],"parent"))for(int i=0;i<2;++i)assert(kill(children[i],SIGSTOP)==0);
 for(int i=0;i<2;++i){siginfo_t info;int rc;do{rc=waitid(P_PID,children[i],&info,WSTOPPED|WNOWAIT);}while(rc<0&&errno==EINTR);assert(rc==0&&info.si_code==CLD_STOPPED);}
 for(int i=0;i<2;++i){assert(waitpid(children[i],&status,WUNTRACED)==children[i]&&WIFSTOPPED(status));}
 for(int i=0;i<2;++i)assert(kill(children[i],SIGCONT)==0);
 assert(write(release[1],"xx",2)==2);close(release[0]);close(release[1]);
 for(int i=0;i<2;++i){pid_t p;do{p=waitpid(children[i],&status,0);}while(p<0&&errno==EINTR);assert(p==children[i]&&WIFEXITED(status)&&WEXITSTATUS(status)==23+i);}
 assert(waitpid(-1,&status,WNOHANG)==-1&&errno==ECHILD);puts("passed");
}
