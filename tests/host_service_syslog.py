#!/usr/bin/env python3
"""Private container syslog sink; preserves every datagram, including PAM logs."""
import json
import os
from pathlib import Path
import socket
import sys

with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as receiver:
    receiver.bind('/dev/log')
    os.chmod('/dev/log', 0o666)
    with Path(sys.argv[1]).open('w', buffering=1) as output:
        while True:
            output.write(json.dumps(receiver.recv(65536).hex()) + '\n')
