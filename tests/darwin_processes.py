"""Read Darwin process metadata without spawning a system-wide ps command.

ABI: Apple's libproc.h and sys/proc_info.h (PROC_PIDT_SHORTBSDINFO).
Only owned-session members are queried for status; no process is signalled here.
"""
import ctypes
import errno
from functools import lru_cache
import os
import time

PROC_ALL_PIDS = 1
PROC_PIDT_SHORTBSDINFO = 13
SZOMB = 5
MAX_SNAPSHOT_BYTES = 1024 * 1024


class ShortBSDInfo(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in ('pid', 'ppid', 'pgid', 'status')] + [
        ('comm', ctypes.c_char * 16)] + [
        (name, ctypes.c_uint32) for name in
        ('flags', 'uid', 'gid', 'ruid', 'rgid', 'svuid', 'svgid', 'reserved')]


@lru_cache(maxsize=1)
def library():
    lib = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
    lib.proc_listpids.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int]
    lib.proc_listpids.restype = ctypes.c_int
    lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                                ctypes.c_void_p, ctypes.c_int]
    lib.proc_pidinfo.restype = ctypes.c_int
    return lib


def check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('process snapshot exceeded cleanup deadline')


def process_ids(deadline):
    check_deadline(deadline)
    lib = library()
    ctypes.set_errno(0)
    needed = lib.proc_listpids(PROC_ALL_PIDS, 0, None, 0)
    check_deadline(deadline)
    if needed <= 0:
        raise OSError(ctypes.get_errno() or errno.EIO, 'proc_listpids sizing failed')
    size = max(4096, needed + 4096)
    while size <= MAX_SNAPSHOT_BYTES:
        check_deadline(deadline)
        buffer = (ctypes.c_int * ((size + 3) // 4))()
        size = ctypes.sizeof(buffer)
        ctypes.set_errno(0)
        count = lib.proc_listpids(PROC_ALL_PIDS, 0, buffer, size)
        check_deadline(deadline)
        if count <= 0 or count > size or count % ctypes.sizeof(ctypes.c_int):
            raise OSError(ctypes.get_errno() or errno.EIO, 'invalid proc_listpids snapshot')
        if count < size:
            return [pid for pid in buffer[:count // ctypes.sizeof(ctypes.c_int)] if pid > 0]
        # A full buffer may be truncated by processes created since sizing.
        # Never treat an incomplete enumeration as proof that cleanup finished.
        size *= 2
    raise OSError(errno.EOVERFLOW, 'process snapshot exceeds 1 MiB')


def process_info(pid, deadline):
    check_deadline(deadline)
    info = ShortBSDInfo()
    ctypes.set_errno(0)
    count = library().proc_pidinfo(pid, PROC_PIDT_SHORTBSDINFO, 0,
                                   ctypes.byref(info), ctypes.sizeof(info))
    error = ctypes.get_errno()
    check_deadline(deadline)
    if count == 0 and error == errno.ESRCH:
        return None
    if count != ctypes.sizeof(info) or info.pid != pid:
        raise OSError(error or errno.EIO, f'invalid proc_pidinfo for PID {pid}')
    return info


def session_members(session, deadline):
    members = []
    for pid in process_ids(deadline):
        check_deadline(deadline)
        try:
            if os.getsid(pid) != session:
                continue
            info = process_info(pid, deadline)
            # Revalidate session membership after reading the record. A process
            # may exit, change session, or be replaced between kernel queries.
            if info is not None and info.status != SZOMB and os.getsid(pid) == session:
                members.append((pid, info.pgid))
        except ProcessLookupError:
            continue
    check_deadline(deadline)
    return members
