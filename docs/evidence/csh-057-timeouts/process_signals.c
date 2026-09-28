/* Darwin-only, read-only snapshot of explicitly supplied owned PIDs. */
#include <sys/types.h>
#include <sys/sysctl.h>
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv)
{
    for (int i = 1; i < argc; ++i) {
        int mib[4] = {CTL_KERN, KERN_PROC, KERN_PROC_PID, atoi(argv[i])};
        struct kinfo_proc info;
        size_t size = sizeof(info);
        if (sysctl(mib, 4, &info, &size, NULL, 0) < 0 || !size) return 1;
        printf("pid=%d ignore=%x catch=%x pending=%x mask=%x flags=%x\n",
            info.kp_proc.p_pid, info.kp_proc.p_sigignore, info.kp_proc.p_sigcatch,
            info.kp_proc.p_siglist, info.kp_proc.p_sigmask, info.kp_proc.p_flag);
    }
}
