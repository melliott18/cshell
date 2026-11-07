/* CSH-057: an inherited Mach crash receiver can hold a fatal child in exit. */
#include "crash_notification.h"
#include <stdio.h>

#ifdef __APPLE__
#include <errno.h>
#include <mach/ndr.h>
#include <signal.h>
#include <stddef.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

struct saved_ports {
    exception_mask_t masks[EXC_TYPES_COUNT];
    mach_msg_type_number_t count;
    exception_handler_t ports[EXC_TYPES_COUNT];
    exception_behavior_t behaviors[EXC_TYPES_COUNT];
    thread_state_flavor_t flavors[EXC_TYPES_COUNT];
};

/* EXCEPTION_DEFAULT uses exception_raise, whose two codes are 32-bit values. */
struct crash_request {
    mach_msg_header_t header;
    mach_msg_body_t body;
    mach_msg_port_descriptor_t thread;
    mach_msg_port_descriptor_t task;
    NDR_record_t ndr;
    exception_type_t exception;
    mach_msg_type_number_t code_count;
    integer_t code[2];
};

union request_buffer {
    struct crash_request request;
    unsigned char bytes[4096];
};

static double now(void)
{
    struct timespec current;
    if (clock_gettime(CLOCK_MONOTONIC, &current) < 0) return -1;
    return (double)current.tv_sec + (double)current.tv_nsec / 1000000000.0;
}

static void pause_poll(void)
{
    struct timespec delay = {0, 1000000};
    nanosleep(&delay, NULL);
}

static int restore_ports(struct saved_ports *saved)
{
    int failed = csh_test_clear_crash_notification() != 0;
    mach_msg_type_number_t i;
    for (i = 0; i < saved->count; ++i) {
        if (task_set_exception_ports(mach_task_self(), saved->masks[i],
                saved->ports[i], saved->behaviors[i], saved->flavors[i]) != KERN_SUCCESS)
            failed = 1;
        if (saved->ports[i] != MACH_PORT_NULL)
            mach_port_deallocate(mach_task_self(), saved->ports[i]);
    }
    saved->count = 0;
    return failed ? -1 : 0;
}

static int reply_crash(union request_buffer *message)
{
    struct {
        mach_msg_header_t header;
        NDR_record_t ndr;
        kern_return_t result;
    } reply;
    kern_return_t rc;
    memset(&reply, 0, sizeof(reply));
    reply.header.msgh_bits = MACH_MSGH_BITS(MACH_MSG_TYPE_MOVE_SEND_ONCE, 0);
    reply.header.msgh_size = sizeof(reply);
    reply.header.msgh_remote_port = message->request.header.msgh_remote_port;
    reply.header.msgh_id = message->request.header.msgh_id + 100;
    reply.ndr = NDR_record;
    reply.result = KERN_SUCCESS;
    rc = mach_msg(&reply.header, MACH_SEND_MSG | MACH_SEND_TIMEOUT,
        sizeof(reply), 0, MACH_PORT_NULL, 100, MACH_PORT_NULL);
    if (rc == MACH_MSG_SUCCESS)
        message->request.header.msgh_remote_port = MACH_PORT_NULL;
    return rc == MACH_MSG_SUCCESS ? 0 : -1;
}

static int collect(pid_t child, int *status, double deadline)
{
    for (;;) {
        pid_t result = waitpid(child, status, WNOHANG);
        if (result == child) return 0;
        if (result < 0 && errno != EINTR) return -1;
        if (now() >= deadline) { errno = ETIMEDOUT; return -1; }
        pause_poll();
    }
}

static int cleanup_child(pid_t child, int *status, double deadline)
{
    for (;;) {
        pid_t result = waitpid(child, status, WNOHANG);
        if (result == child || (result < 0 && errno == ECHILD)) return 0;
        if (result == 0) break;
        if (errno != EINTR) return -1;
        if (now() >= deadline) { errno = ETIMEDOUT; return -1; }
    }
    /* Only an exact-child wait returning zero confirms ownership. ECHILD
     * may mean an inherited SIGCHLD ignore already reaped this PID. */
    if (kill(child, SIGKILL) < 0 && errno != ESRCH) return -1;
    if (collect(child, status, deadline) == 0 || errno == ECHILD) return 0;
    return -1;
}

static int scenario(int isolated)
{
    struct saved_ports saved = {0};
    union request_buffer message;
    mach_port_t server = MACH_PORT_NULL;
    struct sigaction original_action, action = {0};
    struct sigaction original_child_action, child_action = {0};
    sigset_t blocked, original_mask, child_mask;
    pid_t child = -1, observed;
    int gate[2] = {-1, -1}, status = 0, failed = 0;
    int ports_installed = 0, mask_saved = 0, action_saved = 0;
    int child_action_saved = 0;
    int request_received = 0, child_collected = 0;
    double deadline = now() + 4.0;
    kern_return_t rc;

#define REQUIRE(condition) do { \
    if (!(condition)) { \
        fprintf(stderr, "%s crash notification: line %d: %s\n", \
            isolated ? "isolated" : "held", __LINE__, #condition); \
        failed = 1; goto cleanup; \
    } \
} while (0)

    REQUIRE(deadline > 4.0);
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGQUIT);
    REQUIRE(sigprocmask(SIG_BLOCK, &blocked, &original_mask) == 0);
    mask_saved = 1;
    child_mask = original_mask;
    sigdelset(&child_mask, SIGQUIT);
    action.sa_handler = SIG_DFL;
    sigemptyset(&action.sa_mask);
    REQUIRE(sigaction(SIGQUIT, &action, &original_action) == 0);
    action_saved = 1;
    /* A default SIGCHLD with no SA_NOCLDWAIT preserves ownership until our
     * exact wait reaps the child, including between a poll and cleanup kill. */
    child_action.sa_handler = SIG_DFL;
    sigemptyset(&child_action.sa_mask);
    REQUIRE(sigaction(SIGCHLD, &child_action, &original_child_action) == 0);
    child_action_saved = 1;
    REQUIRE(pipe(gate) == 0);
    saved.count = EXC_TYPES_COUNT;
    REQUIRE(task_get_exception_ports(mach_task_self(), EXC_MASK_CRASH,
        saved.masks, &saved.count, saved.ports, saved.behaviors,
        saved.flavors) == KERN_SUCCESS);
    REQUIRE(mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE,
        &server) == KERN_SUCCESS);
    REQUIRE(mach_port_insert_right(mach_task_self(), server, server,
        MACH_MSG_TYPE_MAKE_SEND) == KERN_SUCCESS);
    REQUIRE(task_set_exception_ports(mach_task_self(), EXC_MASK_CRASH,
        server, EXCEPTION_DEFAULT, THREAD_STATE_NONE) == KERN_SUCCESS);
    ports_installed = 1;
    child = fork();
    if (child == 0) {
        char byte;
        ssize_t count;
        close(gate[1]);
        if (isolated && csh_test_clear_crash_notification() != 0) _exit(70);
        do { count = read(gate[0], &byte, 1); } while (count < 0 && errno == EINTR);
        if (count != 0) _exit(71);
        close(gate[0]);
        if (sigprocmask(SIG_SETMASK, &child_mask, NULL) < 0) _exit(72);
        _exit(73); /* The parent made SIGQUIT pending before opening the gate. */
    }
    /* The receiver belongs only to our child; restore the test driver now. */
    rc = (kern_return_t)restore_ports(&saved);
    ports_installed = 0;
    REQUIRE(rc == 0 && child > 0);
    close(gate[0]); gate[0] = -1;
    REQUIRE(setpgid(child, child) == 0);
    REQUIRE(kill(child, SIGQUIT) == 0);
    close(gate[1]); gate[1] = -1;
    REQUIRE(sigprocmask(SIG_SETMASK, &original_mask, NULL) == 0);
    mask_saved = 0;

    if (isolated) {
        /* A notification is a failure even if it could be answered promptly.
         * Poll both the receiver and the exact child against one deadline. */
        for (;;) {
            rc = mach_msg(&message.request.header, MACH_RCV_MSG | MACH_RCV_TIMEOUT,
                0, sizeof(message), server, 10, MACH_PORT_NULL);
            if (rc == MACH_MSG_SUCCESS) request_received = 1;
            REQUIRE(rc == MACH_RCV_TIMED_OUT);
            observed = waitpid(child, &status, WNOHANG);
            REQUIRE(observed >= 0 || errno == EINTR);
            if (observed == child) { child_collected = 1; break; }
            REQUIRE(now() < deadline);
        }
    } else {
        rc = mach_msg(&message.request.header, MACH_RCV_MSG | MACH_RCV_TIMEOUT,
            0, sizeof(message), server, 1000, MACH_PORT_NULL);
        if (rc == MACH_MSG_SUCCESS) request_received = 1;
        REQUIRE(request_received);
        REQUIRE(message.request.header.msgh_size >= sizeof(struct crash_request));
        REQUIRE(message.request.exception == EXC_CRASH && message.request.code_count == 2);
        REQUIRE(((unsigned)message.request.code[0] >> 24) == SIGQUIT);
        observed = waitpid(child, &status, WNOHANG);
        if (observed == child) child_collected = 1;
        REQUIRE(observed == 0);
        REQUIRE(kill(child, SIGKILL) == 0);
        /* The kernel cannot complete this exit while the exception reply is
         * withheld. An exact SIGKILL does not remove that dependency. */
        double held_until = now() + 0.1;
        do {
            observed = waitpid(child, &status, WNOHANG);
            if (observed == child) child_collected = 1;
            REQUIRE(observed == 0);
            pause_poll();
        } while (now() < held_until);
        REQUIRE(reply_crash(&message) == 0);
        mach_msg_destroy(&message.request.header);
        request_received = 0;
        REQUIRE(collect(child, &status, deadline) == 0);
        child_collected = 1;
    }
    REQUIRE(WIFSIGNALED(status) && WTERMSIG(status) == SIGQUIT);

cleanup:
    /* Never assert/abort with a deliberately held exception. Reply first, or
     * discard the reply right and receiver, before trying to reap the child. */
    if (request_received) {
        if (reply_crash(&message) < 0) failed = 1;
        mach_msg_destroy(&message.request.header);
    }
    if (ports_installed && restore_ports(&saved) < 0) failed = 1;
    else if (saved.count != 0) {
        mach_msg_type_number_t i;
        for (i = 0; i < saved.count; ++i)
            if (saved.ports[i] != MACH_PORT_NULL)
                mach_port_deallocate(mach_task_self(), saved.ports[i]);
    }
    if (server != MACH_PORT_NULL) {
        mach_port_mod_refs(mach_task_self(), server, MACH_PORT_RIGHT_RECEIVE, -1);
        mach_port_deallocate(mach_task_self(), server);
    }
    if (gate[0] >= 0) close(gate[0]);
    if (gate[1] >= 0) close(gate[1]);
    if (child > 0 && !child_collected) {
        if (cleanup_child(child, &status, now() + 1.0) < 0) {
            fprintf(stderr, "unreaped crash notification child: %ld\n", (long)child);
            failed = 1;
        }
    }
    if (child_action_saved && sigaction(SIGCHLD, &original_child_action, NULL) < 0)
        failed = 1;
    if (action_saved && sigaction(SIGQUIT, &original_action, NULL) < 0) failed = 1;
    if (mask_saved && sigprocmask(SIG_SETMASK, &original_mask, NULL) < 0) failed = 1;
#undef REQUIRE
    return failed;
}
#endif

int main(void)
{
#ifdef __APPLE__
    struct rlimit limit = {0, 0};
    if (setrlimit(RLIMIT_CORE, &limit) < 0) return 1;
    if (scenario(0) || scenario(1)) return 1;
    puts("crash notification isolation checks passed");
#else
    puts("UNAVAILABLE: CSH-057 Mach crash notification checks require macOS");
#endif
    return 0;
}
