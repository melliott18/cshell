#ifndef CSH_TEST_CRASH_NOTIFICATION_H
#define CSH_TEST_CRASH_NOTIFICATION_H

#ifdef __APPLE__
#include <mach/mach.h>
#endif

/* An intentionally fatal test signal must not wait for an inherited task
 * exception receiver. This changes neither the POSIX signal disposition nor
 * the wait status, and does not disable host crash/corpse reporting. The
 * terminal fault fixture calls this only in children about to receive its
 * deliberate SIGQUIT. */
static inline int csh_test_clear_crash_notification(void)
{
#ifdef __APPLE__
    return (int)task_set_exception_ports(mach_task_self(), EXC_MASK_CRASH,
        MACH_PORT_NULL, EXCEPTION_DEFAULT, THREAD_STATE_NONE);
#else
    return 0;
#endif
}

#endif
