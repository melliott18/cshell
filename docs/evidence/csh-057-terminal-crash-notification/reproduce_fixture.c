#define _DARWIN_C_SOURCE
#include <mach/mach.h>
#include <mach/ndr.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
static double now(void) { struct timespec t; if(clock_gettime(CLOCK_MONOTONIC,&t))abort(); return t.tv_sec+t.tv_nsec/1e9; }
static int restore(exception_mask_t *m, mach_msg_type_number_t n, exception_handler_t *p, exception_behavior_t *b, thread_state_flavor_t *f) {
 int rc=task_set_exception_ports(mach_task_self(),EXC_MASK_CRASH,MACH_PORT_NULL,EXCEPTION_DEFAULT,THREAD_STATE_NONE);
 for(mach_msg_type_number_t i=0;i<n;i++){ if(task_set_exception_ports(mach_task_self(),m[i],p[i],b[i],f[i]))rc=1; if(p[i]!=MACH_PORT_NULL)mach_port_deallocate(mach_task_self(),p[i]); } return rc;
}
static int reply(mach_msg_header_t *message) {
 struct { mach_msg_header_t h; NDR_record_t n; kern_return_t r; } out;
 memset(&out,0,sizeof(out));out.h.msgh_bits=MACH_MSGH_BITS(MACH_MSG_TYPE_MOVE_SEND_ONCE,0);out.h.msgh_size=sizeof(out);out.h.msgh_remote_port=message->msgh_remote_port;out.h.msgh_id=message->msgh_id+100;out.n=NDR_record;out.r=KERN_SUCCESS;
 kern_return_t kr=mach_msg(&out.h,MACH_SEND_MSG|MACH_SEND_TIMEOUT,sizeof(out),0,MACH_PORT_NULL,500,MACH_PORT_NULL);
 if(kr!=KERN_SUCCESS)mach_msg_destroy(&out.h);
 message->msgh_remote_port=MACH_PORT_NULL;mach_msg_destroy(message);return kr;
}
static int cleanup_child(pid_t child, int *status, int *reaped, double deadline) {
 for (;;) {
  pid_t got=waitpid(child,status,WNOHANG);
  if(got==child){*reaped=1;return 0;}
  if(got<0&&errno==ECHILD)return 0;
  if(got==0)break;
  if(errno!=EINTR||now()>=deadline)return 1;
 }
 /* Never signal a PID after an exact-child wait reports lost ownership. */
 if(kill(child,SIGKILL)<0&&errno!=ESRCH)return 1;
 while(now()<deadline){
  pid_t got=waitpid(child,status,WNOHANG);
  if(got==child){*reaped=1;return 0;}
  if(got<0&&errno==ECHILD)return 0;
  if(got<0&&errno!=EINTR)return 1;
  struct timespec tick={0,10000000};nanosleep(&tick,NULL);
 }
 return 1;
}
int main(int argc,char **argv) {
 if(argc<3)return 2; int expected=atoi(argv[1]);
 exception_mask_t masks[EXC_TYPES_COUNT];mach_msg_type_number_t count=EXC_TYPES_COUNT;exception_handler_t ports[EXC_TYPES_COUNT];exception_behavior_t behaviors[EXC_TYPES_COUNT];thread_state_flavor_t flavors[EXC_TYPES_COUNT];
 if(task_get_exception_ports(mach_task_self(),EXC_MASK_CRASH,masks,&count,ports,behaviors,flavors))return 2;
 mach_port_t port=MACH_PORT_NULL;
 if(mach_port_allocate(mach_task_self(),MACH_PORT_RIGHT_RECEIVE,&port)||mach_port_insert_right(mach_task_self(),port,port,MACH_MSG_TYPE_MAKE_SEND)||task_set_exception_ports(mach_task_self(),EXC_MASK_CRASH,port,EXCEPTION_DEFAULT,THREAD_STATE_NONE))return 2;
 struct sigaction original_child_action, child_action={0};
 child_action.sa_handler=SIG_DFL;sigemptyset(&child_action.sa_mask);
 if(sigaction(SIGCHLD,&child_action,&original_child_action)<0){restore(masks,count,ports,behaviors,flavors);mach_port_mod_refs(mach_task_self(),port,MACH_PORT_RIGHT_RECEIVE,-1);mach_port_deallocate(mach_task_self(),port);return 2;}
 pid_t child=fork();if(child==0){execv(argv[2],argv+2);_exit(127);}
 int failed=restore(masks,count,ports,behaviors,flavors);if(child<0){mach_port_mod_refs(mach_task_self(),port,MACH_PORT_RIGHT_RECEIVE,-1); mach_port_deallocate(mach_task_self(),port);sigaction(SIGCHLD,&original_child_action,NULL);return 2;}
 union {mach_msg_header_t h;unsigned char bytes[4096];} message;
 int held=0,notifications=0,status=0,reaped=0;double started=now(),held_at=0;
 while(now()-started<25) {
  if(!held){kern_return_t kr=mach_msg(&message.h,MACH_RCV_MSG|MACH_RCV_TIMEOUT,0,sizeof(message),port,10,MACH_PORT_NULL);if(kr==KERN_SUCCESS){held=1;held_at=now();++notifications;printf("notification id=%d at=%.6f\n",message.h.msgh_id,held_at-started);fflush(stdout);}else if(kr!=MACH_RCV_TIMED_OUT){failed=1;break;}}
  if(held&&now()-held_at>=6){int kr=reply(&message.h);printf("reply status=%d at=%.6f\n",kr,now()-started);fflush(stdout);held=0;if(kr)failed=1;}
  pid_t got=waitpid(child,&status,WNOHANG);if(got==child){reaped=1;break;}if(got<0&&errno!=EINTR){failed=1;break;}
  struct timespec tick={0,10000000};nanosleep(&tick,NULL);
 }
 if(held&&reply(&message.h))failed=1;
 mach_port_mod_refs(mach_task_self(),port,MACH_PORT_RIGHT_RECEIVE,-1); mach_port_deallocate(mach_task_self(),port);
 if(!reaped){cleanup_child(child,&status,&reaped,now()+1);failed=1;}
 if(sigaction(SIGCHLD,&original_child_action,NULL)<0)failed=1;
 printf("notifications=%d launcher_status=%d elapsed=%.6f reaped=%d\n",notifications,WIFEXITED(status)?WEXITSTATUS(status):-1,now()-started,reaped);
 return failed||!reaped||notifications!=expected||!WIFEXITED(status)||WEXITSTATUS(status)!=(expected?1:0);
}
