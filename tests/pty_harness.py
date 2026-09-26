"""Controlling-terminal adapter for smoke.py; helpers are not shell conformance."""

import errno
import fcntl
import os
from pathlib import Path
import selectors
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time


class PtyUnavailable(Exception):
    """The host cannot provide the terminal capability this case requires."""


UNAVAILABLE = {errno.ENOSYS, errno.ENODEV, errno.ENOENT, errno.ENXIO,
               errno.EPERM, errno.EACCES, errno.ENOTTY}
CONTROLS = {"C": b"\x03", "Z": b"\x1a", "D": b"\x04", "\\": b"\x1c"}
SIGNALS = {name: getattr(signal, "SIG" + name)
           for name in ("CONT", "INT", "TERM", "HUP", "KILL", "TSTP", "USR1")}


def open_terminal():
    """Allocate and configure an owned PTY, without changing the runner's tty."""
    if sys.platform not in ("linux", "darwin"):
        raise PtyUnavailable(f"controlling PTYs are supported on Linux/macOS (platform={sys.platform})")
    master = slave = None
    try:
        master, slave = os.openpty()
        attributes = termios.tcgetattr(slave)
        attributes[0] = termios.ICRNL
        attributes[1] = 0  # Exact LF output; no ONLCR translation.
        attributes[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attributes[3] = termios.ICANON | termios.ISIG  # No input echo.
        for key, slot in (("C", termios.VINTR), ("Z", termios.VSUSP),
                          ("D", termios.VEOF), ("\\", termios.VQUIT)):
            attributes[6][slot] = CONTROLS[key]
        termios.tcsetattr(slave, termios.TCSANOW, attributes)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        os.set_blocking(master, False)
        return master, slave
    except (OSError, termios.error) as error:
        for fd in (master, slave):
            if fd is not None:
                os.close(fd)
        number = error.args[0]
        if number in UNAVAILABLE:
            raise PtyUnavailable(f"PTY allocation/configuration unavailable: {error}") from error
        # termios.error is not an OSError subclass; expose one consistent
        # operational-error path to the runner's per-case diagnostics.
        raise OSError(number, f"PTY allocation/configuration failed: {error}") from error


def session_members(session, deadline):
    """Find all live members, including jobs that changed group or were orphaned.

    Linux exposes these through procfs. Darwin needs a bounded ps snapshot and
    getsid(), since its ps session column is not the numeric session ID.
    """
    if sys.platform == "linux":
        entries = []
        for path in Path("/proc").iterdir():
            if time.monotonic() >= deadline:
                raise TimeoutError("process snapshot exceeded cleanup deadline")
            if path.name.isdecimal():
                try:
                    fields = (path / "stat").read_text().rsplit(")", 1)[1].split()
                except (FileNotFoundError, ProcessLookupError):
                    continue
                if int(fields[3]) == session and fields[0] not in ("Z", "X"):
                    entries.append((int(path.name), int(fields[2])))
        return entries
    with tempfile.TemporaryFile() as snapshot:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("process snapshot exceeded cleanup deadline")
        result = subprocess.run(["/bin/ps", "-axo", "pid=,stat="], stdout=snapshot,
                                stderr=subprocess.DEVNULL, timeout=remaining,
                                check=False)
        if result.returncode:
            raise OSError(f"ps failed with status {result.returncode}")
        snapshot.seek(0)
        raw = snapshot.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise OSError("process snapshot exceeds 1 MiB")
    members = []
    for line in raw.splitlines():
        if time.monotonic() >= deadline:
            raise TimeoutError("process snapshot exceeded cleanup deadline")
        pid, state = line.split()
        if state.startswith(b"Z"):
            continue
        pid = int(pid)
        try:
            if os.getsid(pid) == session:
                members.append((pid, os.getpgid(pid)))
        except ProcessLookupError:
            pass
    return members


def cleanup_session(process, master, timeout=5.0):
    """Bound session enumeration/killing separately from the final leader reap.

    Darwin's system-wide ps can take over one second under concurrent builds.
    Give teardown the same five-second budget as a normal case, without using
    up the final reap budget when a snapshot fails or reaches its deadline.
    """
    deadline = time.monotonic() + timeout
    failures = []
    needs_fallback = True
    # Always attempt the initial and current foreground groups, even if taking
    # the process snapshot fails. No group outside the owned session is killed.
    groups = {process.pid}
    try:
        foreground = os.tcgetpgrp(master)
        if foreground > 0 and os.getsid(foreground) == process.pid:
            groups.add(foreground)
    except (OSError, ProcessLookupError):
        pass
    try:
        while True:
            members = session_members(process.pid, deadline)
            groups.update(group for _, group in members)
            # Stop jobs before the session leader, avoiding an unnecessary
            # orphan/hangup transition while other groups are being killed.
            for group in sorted(groups, key=lambda group: group == process.pid):
                kill_group(group, process.pid, deadline)
            groups.clear()
            if not members:
                break
            if time.monotonic() >= deadline:
                failures.append(f"PTY cleanup timeout after {timeout:g}s; live session members: {members[:20]}")
                break
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        needs_fallback = False
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        failures.append(f"PTY cleanup failed: {error}")
    finally:
        # Retain a fallback if enumeration or a group operation failed.
        for group in (groups | {process.pid}) if needs_fallback else ():
            try:
                os.killpg(group, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as error:
                failures.append(f"PTY cleanup could not kill group {group}: {error}")
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            failures.append("PTY cleanup could not reap leader within 1s")
    return failures


def kill_group(group, session, deadline):
    """Kill an owned group; accept Darwin EPERM only after proving it exited."""
    try:
        os.killpg(group, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError as error:
        # XNU skips zombies when delivering group signals and returns EPERM
        # when none of the group's members remain eligible. A prior successful
        # kill, or the leader's exit, alone does not prove descendants exited.
        if sys.platform != "darwin" or error.errno != errno.EPERM:
            raise
        if any(pgid == group for _, pgid in session_members(session, deadline)):
            raise


def owned_group(group, session, deadline):
    if group <= 0:
        return False
    try:
        return os.getsid(group) == session
    except ProcessLookupError:
        # A pipeline group outlives its leader. The remaining members still
        # receive terminal signals and can be stopped/continued as a group.
        return any(pgid == group for _, pgid in session_members(session, deadline))


def capture(binary, case, directory, timeout, output_limit, environment, limit_fn):
    """Return (status, {'output': bytes}, failures); every wait shares a deadline."""
    deadline = time.monotonic() + timeout
    master, slave = open_terminal()
    process = None
    setup_read = setup_write = None
    output = bytearray()
    failures = []
    unavailable = None
    try:
        setup_read, setup_write = os.pipe()

        def child_setup():
            # Popen has already called setsid(). Report capability errors over
            # a private pipe, never by confusing candidate output with a skip.
            try:
                fcntl.ioctl(0, termios.TIOCSCTTY, 0)
                os.tcsetpgrp(0, os.getpgrp())
            except OSError as error:
                kind = "unavailable" if error.errno in UNAVAILABLE else "error"
                os.write(setup_write, f"{kind}: controlling terminal: {error}".encode()[:1000])
                os._exit(125)
            try:
                limit_fn(timeout, output_limit)
            except (OSError, ValueError) as error:
                os.write(setup_write, f"error: child resource limits: {error}".encode()[:1000])
                os._exit(125)
            os.close(setup_write)

        process = subprocess.Popen(
            [str(binary)] + case.get("args", []), cwd=directory, env=environment,
            stdin=slave, stdout=slave, stderr=slave, start_new_session=True,
            pass_fds=(setup_write,), preexec_fn=child_setup,
        )
        os.close(slave)
        slave = None
        os.close(setup_write)
        setup_write = None
        setup_error = os.read(setup_read, 1001).decode("utf-8", "replace")
        os.close(setup_read)
        setup_read = None
        if setup_error.startswith("unavailable:"):
            unavailable = setup_error
        elif setup_error:
            failures.append(setup_error)
        else:
            _interact(process, master, case["steps"], output, failures,
                      deadline, timeout, output_limit)
    finally:
        try:
            if process is not None:
                failures.extend(cleanup_session(process, master))
        finally:
            for fd in (master, slave, setup_read, setup_write):
                if fd is not None:
                    os.close(fd)
    if unavailable and not failures:
        raise PtyUnavailable(unavailable)
    return process.returncode, {"output": output}, failures


def _interact(process, master, steps, output, failures, deadline, timeout, output_limit):
    index = cursor = 0
    pending = b""
    sent = 0
    eof = False
    with selectors.DefaultSelector() as selector:
        selector.register(master, selectors.EVENT_READ)
        while True:
            # Advance only actions that are ready; expect never discards bytes
            # from the final exact transcript, just advances a search cursor.
            while index < len(steps) and not pending:
                if time.monotonic() >= deadline:
                    failures.append(f"PTY timeout after {timeout:g}s waiting for step {index + 1}: {str(steps[index])[:200]}; session cleanup requested")
                    return
                action, value = next(iter(steps[index].items()))
                if action == "expect":
                    token = value.encode("utf-8")
                    position = output.find(token, cursor)
                    if position == -1:
                        break
                    cursor = position + len(token)
                elif action in ("send", "control"):
                    pending = value.encode("utf-8") if action == "send" else CONTROLS[value]
                    sent = 0
                    if pending:
                        break
                elif action == "foreground":
                    foreground = os.tcgetpgrp(master)
                    matches = foreground == process.pid if value == "leader" else foreground > 0 and foreground != process.pid
                    if not matches:
                        failures.append(f"PTY step {index + 1}: expected foreground {value}, got pgid {foreground} (leader {process.pid})")
                        return
                elif action == "signal":
                    group = os.tcgetpgrp(master)
                    if not owned_group(group, process.pid, deadline):
                        failures.append(f"PTY step {index + 1}: no owned foreground process group")
                        return
                    os.killpg(group, SIGNALS[value])
                index += 1
            if eof:
                if index < len(steps):
                    failures.append(f"PTY closed before step {index + 1}: {str(steps[index])[:200]}")
                # A candidate may close every tty descriptor and keep running.
                if index < len(steps) or process.poll() is not None:
                    return
            elif index == len(steps) and process.poll() is not None:
                # Drain queued output before cleanup (which also closes any
                # surviving descendants). Do not wait for their inherited tty.
                while _read(master, output, failures, output_limit):
                    if failures or time.monotonic() >= deadline:
                        break
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                waiting = f"step {index + 1}: {str(steps[index])[:200]}" if index < len(steps) else "process exit"
                failures.append(f"PTY timeout after {timeout:g}s waiting for {waiting}; session cleanup requested")
                return
            if not eof:
                selector.modify(master, selectors.EVENT_READ | (selectors.EVENT_WRITE if pending else 0))
            for _, events in selector.select(min(remaining, 0.05)):
                if events & selectors.EVENT_READ:
                    result = _read(master, output, failures, output_limit)
                    if result is None:
                        eof = True
                        selector.unregister(master)
                if events & selectors.EVENT_WRITE and not eof:
                    try:
                        sent += os.write(master, pending[sent:sent + 65536])
                    except BlockingIOError:
                        continue
                    if sent == len(pending):
                        pending = b""
                        index += 1
            if failures:
                return


def _read(master, output, failures, output_limit):
    """True=data, False=would block, None=PTY hangup (Linux reports EIO)."""
    try:
        chunk = os.read(master, min(65536, output_limit - len(output) + 1))
    except BlockingIOError:
        return False
    except OSError as error:
        if error.errno == errno.EIO:
            return None
        raise
    if not chunk:
        return None
    available = output_limit - len(output)
    output.extend(chunk[:available])
    if len(chunk) > available:
        failures.append(f"PTY output limit exceeded ({output_limit} bytes combined terminal output; session cleanup requested)")
    return True
