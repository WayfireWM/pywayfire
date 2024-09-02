#!/usr/bin/python3

# A simple script to monitor wayfire ipc events.

import os
import sys
from wayfire import WayfireSocket

sock = WayfireSocket()
sock.watch()

while True:
    try:
        msg = sock.read_next_event()
        if "event" in msg:
            print(msg["event"])
    except KeyboardInterrupt:
        exit(0)
