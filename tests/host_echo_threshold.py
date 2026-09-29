"""Bounded adjacent success/E2BIG measurements, not a universal ARG_MAX claim.

Every successful trial verifies literal bytes, status and stderr. Only echo is
exec'ed: it does not fork. All trials have wall/CPU/file bounds and are reaped.
Environment, argv layout and child stack limits are fixed within each search.
"""
import errno
import hashlib
import os
import resource
import signal
import subprocess
import tempfile

CAP = 4 * 1024 * 1024


def threshold(executable, shape, padding, stack, timeout=5):
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
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                process = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                                           stdout=out, stderr=err, preexec_fn=limits,
                                           start_new_session=True)
            except OSError as error:
                detail.update(errno=error.errno, status=None)
                trials.append(detail)
                if error.errno != errno.E2BIG:
                    raise
                return False
            try:
                status = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    detail.update(status=None, error='cleanup timeout', pid=process.pid, reaped=False)
                    trials.append(detail)
                    raise RuntimeError('echo threshold cleanup timeout; owned pid=' + str(process.pid))
                detail.update(status=process.returncode, error='timeout', pid=process.pid, reaped=process.poll() is not None)
                trials.append(detail)
                raise RuntimeError('echo threshold timed out')
            out.seek(0)
            err.seek(0)
            actual, diagnostic = out.read(CAP + 65537), err.read(65536)
            detail.update(status=status, errno=None, stdout_bytes=len(actual),
                          stdout_sha256=hashlib.sha256(actual).hexdigest(),
                          stderr_hex=diagnostic.hex())
            trials.append(detail)
            if status or actual != expected or diagnostic:
                raise RuntimeError('echo threshold output/status mismatch')
            return True

    result = dict(shape=shape, environment=env,
                  environment_bytes_with_nuls=sum(len(k) + len(v) + 2 for k, v in env.items()),
                  stack_soft=stack, stack_hard=stack, allocation_cap=CAP,
                  max_trials=30, trials=trials)
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
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        result.update(verdict='FAIL', error=str(error))
    return result
