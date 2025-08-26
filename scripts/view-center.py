#!/usr/bin/python3
#
# This script centers and optionally resizes the active view.
#
# Example configuration, binding 3 hotkeys in wayfire.ini:
#
# [command]
# ...
# binding_center   = <alt> <ctrl> KEY_C
# command_center   = python3 view-center.py 1.0
#
# binding_centerup = <alt> <ctrl> KEY_UP
# command_centerup = python3 view-center.py 1.25
#
# binding_centerdn = <alt> <ctrl> KEY_DOWN
# command_centerdn = python3 view-center.py 0.75
# ...

import sys
from wayfire import WayfireSocket


def center(scale):
    socket = WayfireSocket()

    active_view = None
    for view in socket.list_views():
        if view.get("activated", False) and view.get("mapped", False):
            active_view = view
            break

    if not active_view:
        print("No active view found.")
        return

    view_id = active_view["id"]
    output_id = active_view["output-id"]
    output_info = socket.get_output(output_id)
    screen_w = output_info["geometry"]["width"]
    screen_h = output_info["geometry"]["height"]
    workarea_h = output_info["workarea"]["height"]

    view_geom = active_view.get("geometry", {})
    view_w = view_geom.get("width", 0)
    view_h = view_geom.get("height", 0)

    min_scale = 0.25
    min_w = int(screen_w * min_scale)
    min_h = int(screen_h * min_scale)

    new_w = int(min(max(view_w * scale, min_w), screen_w))
    new_h = int(min(max(view_h * scale, min_h), screen_h))
    new_x = (screen_w - new_w) // 2
    new_y = (screen_h - new_h) // 2

    # max out at workarea height
    if new_y == 0 and new_h > workarea_h:
        new_y = screen_h - workarea_h
        new_h = workarea_h

    socket.configure_view(view_id, new_x, new_y, new_w, new_h)


if __name__ == "__main__":
    scale = 1.00
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print(
                "Usage: view-center.py [scale]\n"
                "\n"
                "Centers and optionally resizes the active view in Wayfire.\n"
                "\n"
                "Arguments:\n"
                "  scale    Optional. Floating point value to scale the active view size.\n"
                "           Default is 1.0. Example: 1.25 to enlarge, 0.75 to shrink.\n"
                "           Use -h or --help to show this message."
            )
            sys.exit(0)
        try:
            scale = float(sys.argv[1])
        except ValueError:
            pass

    center(scale)
