#!/usr/bin/python3

# Simple script to set the opacity of a view while it's being moved.

from wayfire import WayfireSocket
import sys

socket = WayfireSocket()
socket.watch()

try:
    alpha = float(sys.argv[1])
except ValueError:
    alpha = 0.75

app_viewid = 0
app_name = ""
app_alpha = 1.0
while True:
    try:
        msg = socket.read_next_event()
        if not (
            msg["event"] == "plugin-activation-state-changed"
            and msg["plugin"] == "move"
        ):
            continue

        if msg["state"]:
            if app_viewid == 0:
                for view in socket.list_views():
                    if view.get("activated", False) and view.get("mapped", False):
                        app_viewid = view["id"]
                        app_name = view["app-id"]
                        app_alpha = socket.get_view_alpha(app_viewid)["alpha"]
                        socket.set_view_alpha(app_viewid, alpha)
                        break

        elif app_viewid > 0:
            socket.set_view_alpha(app_viewid, app_alpha)
            app_viewid = 0

    except KeyboardInterrupt:
        exit(0)
