"""Bounded adjacent success/E2BIG measurements, not a universal ARG_MAX claim.

Every successful trial verifies literal bytes, status and stderr. Only echo is
exec'ed: it does not fork. All trials have wall/CPU/file bounds and are reaped.
Environment, argv layout and child stack limits are fixed within each search.
"""
import errno
import hashlib
import os
import platform
import resource
import signal
import time
import tempfile

CAP = 4 * 1024 * 1024


def threshold(executable, shape, padding, stack, timeout=5, *, disposable_darwin=False):
    # This kernel/exec configuration previously left unkillable processes.
    # Enforce the exclusion at the entry point, not only in the caller's list.
    disposable = (disposable_darwin and os.environ.get('GITHUB_ACTIONS') == 'true' and
                  os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted' and
                  os.environ.get('RUNNER_OS') == 'macOS')
    if platform.system() == 'Darwin' and stack < 8 * 1024 * 1024 and not disposable:
        return dict(verdict='UNQUALIFIED', owner='CSH-079', trials=[],
                    reason='Darwin low-stack exec requires a disposable OS with reset capability',
                    stack_soft=stack, stack_hard=stack)
    env = {'LC_ALL': 'C', 'PAD': 'e' * padding}
    trials = []

    def limits():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (CAP + 65536, CAP + 65536))
        resource.setrlimit(resource.RLIMIT_STACK, (stack, stack))

    def trial(size):
        # Single varies bytes in one operand; aggregate varies number of fixed
        # 1024-byte strings. Include NUL and pointer counts in the record.
        operands = ['x' * size] if shape == 'single' else ['x' * 1024] * size
        argv = [str(executable)] + operands
        expected = (' '.join(operands) + '\n').encode()
        detail = dict(size=size, argc=len(argv),
                      argv_bytes_with_nuls=sum(len(a.encode()) + 1 for a in argv),
                      argv_pointer_count=len(argv) + 1,
                      expected_stdout_sha256=hashlib.sha256(expected).hexdigest())
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err, tempfile.TemporaryFile() as launch_error:
            # Own the PID before exec: Popen can block on its exec-error pipe
            # before returning a PID, outside process.wait(timeout=...). This
            # matters for the retained Darwin kernel-stuck exec observation.
            pid = os.fork()
            if pid == 0:
                phase = 'setup'
                try:
                    os.setsid()
                    with open(os.devnull, 'rb') as source:
                        os.dup2(source.fileno(), 0)
                    os.dup2(out.fileno(), 1)
                    os.dup2(err.fileno(), 2)
                    limits()
                    phase = 'exec'
                    os.execve(executable, argv, env)
                except BaseException as error:
                    os.write(launch_error.fileno(),
                             (phase + ':' + str(getattr(error, 'errno', 0))).encode())
                os._exit(125)

            def reap(seconds):
                deadline = time.monotonic() + seconds
                while True:
                    waited, wait_status = os.waitpid(pid, os.WNOHANG)
                    if waited:
                        return os.waitstatus_to_exitcode(wait_status)
                    if time.monotonic() >= deadline:
                        return None
                    time.sleep(0.005)

            detail.update(pid=pid, reaped=False, pid_disappeared=False)
            status = reap(timeout)
            timed_out = status is None
            if timed_out:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                status = reap(2)
            detail.update(status=status, reaped=status is not None)
            if status is not None:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    detail['pid_disappeared'] = True
            if timed_out:
                detail['error'] = 'timeout' if status is not None else 'cleanup timeout'
                trials.append(detail)
                raise RuntimeError('echo threshold ' + detail['error'] + '; owned pid=' + str(pid))
            launch_error.seek(0)
            launch = launch_error.read(128).decode()
            if launch:
                phase, error_number = launch.split(':')
                detail.update(phase=phase, errno=int(error_number))
                trials.append(detail)
                if phase != 'exec' or int(error_number) != errno.E2BIG or not detail['pid_disappeared']:
                    raise RuntimeError('echo threshold launch failure: ' + launch)
                return False
            out.seek(0)
            err.seek(0)
            actual, diagnostic = out.read(CAP + 65537), err.read(65536)
            detail.update(status=status, errno=None, stdout_bytes=len(actual),
                          stdout_sha256=hashlib.sha256(actual).hexdigest(),
                          stderr_hex=diagnostic.hex())
            trials.append(detail)
            if not detail['pid_disappeared'] or status or actual != expected or diagnostic:
                raise RuntimeError('echo threshold output/status mismatch')
            return True

    result = dict(shape=shape, environment=env,
                  environment_bytes_with_nuls=sum(len(k) + len(v) + 2 for k, v in env.items()),
                  stack_soft=stack, stack_hard=stack, allocation_cap=CAP,
                  max_trials=30, disposable_darwin=disposable, trials=trials)
    try:
        lo, hi = 0, (CAP - 4096 if shape == 'single' else (CAP - 4096) // 1025)
        if not trial(lo):
            raise RuntimeError('empty control rejected')
        if trial(hi):
            raise RuntimeError('no rejecting bound within allocation cap; unqualified')
        while hi - lo > 1:
            middle = (lo + hi) // 2
            if trial(middle):
                lo = middle
            else:
                hi = middle
        # Repeat both adjacent endpoints; ASLR-dependent instability is failure.
        if not trial(lo) or trial(hi):
            raise RuntimeError('threshold endpoints unstable')
        result.update(verdict='PASS', largest_success=lo, smallest_e2big=hi)
    except (OSError, RuntimeError) as error:
        result.update(verdict='FAIL', error=str(error))
    return result
