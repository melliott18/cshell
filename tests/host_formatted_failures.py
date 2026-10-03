"""Bounded I/O failure and allocation-site oracles for selected C providers.

Only non-forking provider processes and cshell's replacing `exec` path run here.
The parent owns and reaps one PID per case; no global process inventory is used.
This is not a supervisor for arbitrary commands or forking executables.
"""
import hashlib
import os
from pathlib import Path
import resource
import shlex
import signal
import subprocess
import tempfile


def run_owned(argv, environment, stdout, stderr, *, ignored=(), file_limit=65536, timeout=5):
    """Return strict status/cleanup evidence, including setup and timeout failures."""
    def setup():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
        for number in (signal.SIGPIPE, signal.SIGXFSZ):
            signal.signal(number, signal.SIG_IGN if number in ignored else signal.SIG_DFL)

    # The full CI profile may compile these C providers with sanitizers.
    # Suppress leak-tracer/symbolizer subprocesses to preserve this fixture's
    # single-PID contract; memory/UB detection itself remains enabled.
    environment = dict(environment, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0:symbolize=0',
                       UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=0')
    record = dict(argv=argv, environment=environment, file_limit=file_limit,
                  ignored_signals=list(ignored), timeout_seconds=timeout,
                  cleanup_seconds=2, pid=None, status=None, reaped=False, errors=[])
    try:
        process = subprocess.Popen(argv, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr, start_new_session=True,
                                   preexec_fn=setup)
    except (OSError, subprocess.SubprocessError) as error:
        record['errors'].append('setup: ' + str(error))
        return record
    record['pid'] = process.pid
    try:
        record['status'] = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        record['errors'].append('execution timeout')
    finally:
        if process.poll() is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        try:
            record['status'] = process.wait(timeout=2)
            record['reaped'] = True
        except subprocess.TimeoutExpired:
            record['errors'].append('cleanup timeout')
    return record


def invocation(shell, prefix, name, args, mode):
    return ([str(prefix / name)] + args if mode == 'direct' else
            [str(shell), '-c', 'exec ' + shlex.join([name] + args)])


def io_cases(shell, prefix):
    environment = dict(PATH=str(prefix) + ':' + os.defpath, LC_ALL='C')
    for name, writer in [('printf', 's'), ('printf', 'b'), ('printf', 'literal'), ('echo', 'literal')]:
        for mode in ('direct', 'exec'):
            for boundary in ('control', 'pipe-default', 'pipe-ignored', 'file-default', 'file-ignored'):
                payload = 'x' * (128 if boundary == 'control' else 8192)
                args = ['%' + writer, payload] if name == 'printf' and writer != 'literal' else [payload]
                command = invocation(shell, prefix, name, args, mode)
                number = signal.SIGPIPE if boundary.startswith('pipe-') else signal.SIGXFSZ
                ignored = [number] if boundary.endswith('-ignored') else []
                file_limit = 1024 if boundary.startswith('file-') else 65536
                with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostic:
                    pipe = None
                    try:
                        if boundary.startswith('pipe-'):
                            reader, pipe = os.pipe()
                            os.close(reader)  # No reader exists before exec.
                        result = run_owned(command, environment, pipe if pipe is not None else output,
                                           diagnostic, ignored=ignored, file_limit=file_limit)
                    finally:
                        if pipe is not None:
                            os.close(pipe)
                    output.seek(0)
                    diagnostic.seek(0)
                    actual_out, actual_err = output.read(65537), diagnostic.read(65537)
                expected_out = (payload.encode() + (b'\n' if name == 'echo' else b'')
                                if boundary == 'control' else b'x' * 1024 if boundary.startswith('file-') else b'')
                expected_status = 0 if boundary == 'control' else 1 if ignored else -number
                expected_err = b''
                if ignored:
                    expected_err = (b'echo: write error\n' if name == 'echo' else
                                    b'printf: write or formatting error: ' +
                                    (b'Broken pipe\n' if number == signal.SIGPIPE else b'File too large\n'))
                ok = (result['reaped'] and not result['errors'] and result['status'] == expected_status and
                      actual_out == expected_out and actual_err == expected_err)
                yield dict(name=name + ' ' + writer + ' ' + boundary, mode=mode, verdict='PASS' if ok else 'FAIL',
                           source='ASYNCHRONOUS EVENTS / STDERR / EXIT STATUS / CONSEQUENCES OF ERRORS',
                           invocation=result, expected=dict(status=expected_status,
                               stdout_bytes=len(expected_out), stdout_sha256=hashlib.sha256(expected_out).hexdigest(),
                               stderr_hex=expected_err.hex()),
                           actual=dict(status=result['status'], stdout_bytes=len(actual_out),
                               stdout_sha256=hashlib.sha256(actual_out).hexdigest(), stderr_hex=actual_err.hex()))


def allocation_cases(shell, prefix, helper):
    # argv[0] remains printf, including for the explicitly selected instrumented
    # copy; this is a private symlink and never changes the production profile.
    with tempfile.TemporaryDirectory(prefix='allocation-', dir=prefix.parent) as temporary:
        selected = Path(temporary)
        (selected / 'printf').symlink_to(helper)
        for kind, site, fmt in [('realloc', 'printf_doformat', '%d'),
                                ('realloc', 'mknum', '%d'),
                                ('strdup', 'printf_doformat', '%b')]:
            for fail in (False, True):
                for mode in ('direct', 'exec'):
                    environment = dict(PATH=str(selected) + ':' + os.defpath, LC_ALL='C',
                                       CSH_PRINTF_FAIL=kind,
                                       CSH_PRINTF_FAIL_SITE=site if fail else 'not-a-provider-site')
                    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostic:
                        result = run_owned(invocation(shell, selected, 'printf', [fmt, '12'], mode),
                                           environment, output, diagnostic)
                        output.seek(0)
                        diagnostic.seek(0)
                        actual_out, actual_err = output.read(65537), diagnostic.read(65537)
                    expected_out = b'' if fail else b'12'
                    expected_err = b'printf: Cannot allocate memory\n' if fail else b''
                    ok = (result['reaped'] and not result['errors'] and result['status'] == int(fail) and
                          actual_out == expected_out and actual_err == expected_err)
                    yield dict(name=f'printf allocation {kind} {site} ' + ('failure' if fail else 'control'),
                               mode=mode, verdict='PASS' if ok else 'FAIL', invocation=result,
                               expected=dict(status=int(fail), stdout_hex=expected_out.hex(), stderr_hex=expected_err.hex()),
                               actual=dict(status=result['status'], stdout_hex=actual_out.hex(), stderr_hex=actual_err.hex()))
