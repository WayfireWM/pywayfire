#!/usr/bin/python3

# A simple script to monitor wayfire ipc events.

from wayfire import WayfireSocket

sock = WayfireSocket()
sock.watch()

while True:
    try:
        msg = sock.read_next_event()
        if "event" in msg:
            print(msg["event"].ljust(25), end = ": ")
            if "view" in msg:
                if (msg["view"] is not None):
                    print(msg["view"]["app-id"], end = " - ")
                    print(msg["view"]["id"])
    except KeyboardInterrupt:
        exit(0)
