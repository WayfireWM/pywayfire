#!/usr/bin/python3
# This script listens for focused views and automatically
# moves the mouse cursor to the center of the focused view

from wayfire import WayfireSocket
from wayfire.extra.ipc_utils import WayfireUtils as Utils

sock = WayfireSocket()
utils = Utils(sock)

sock.watch(["view-focused"])
while True:
    msg = sock.read_next_event()
    view = msg["view"]
    if view is not None:
        utils.center_cursor_on_view(view["id"])
