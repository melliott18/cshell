#!/usr/bin/env python3
"""Private container syslog sink, including kernel-attested sender credentials."""
import json
import os
from pathlib import Path
import socket
import struct
import sys

with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
    receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
    receiver.bind('/dev/log')
    os.chmod('/dev/log', 0o666)
    with Path(sys.argv[1]).open('w', buffering=1) as output:
        while True:
            payload, ancillary, flags, _ = receiver.recvmsg(65536, socket.CMSG_SPACE(12))
            record = dict(data=payload.hex(), flags=flags)
            for level, kind, credentials in ancillary:
                if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS:
                    record['pid'], record['uid'], record['gid'] = struct.unpack('3i', credentials)
            output.write(json.dumps(record) + '\n')
