#!/usr/bin/python3
#
# This plugin moves the currently active Wayfire view to a region of the output.
#
# Example configuration, binding hotkeys in wayfire.ini to place view at:
# 1) 2/3rd of view
# 2) center of view
# 3) last 1/3rd of view
#
# [command]
# ...
# binding_viewmove1 = <shift> <super> KEY_INSERT
# command_viewmove1 = python3 view-move.py 0.00 0.65 0.00 1.00
#
# binding_viewmove2 = <shift> <super> KEY_HOME
# command_viewmove2 = python3 view-move.py 0.20 0.80 0.00 1.00
#
# binding_viewmove3 = <shift> <super> KEY_PAGEUP
# command_viewmove3 = python3 view-move.py 0.65 1.00 0.00 1.00
# ...
#

import sys
from wayfire import WayfireSocket

HELP_TEXT = """Move the currently active Wayfire view to a region of the output.

Usage: view-move.py [x0] [x1] [y0] [y1]

Arguments:
    x0: left edge as a fraction of the workarea width (default: 0)
    x1: right edge as a fraction of the workarea width (default: 0.75)
    y0: top edge as a fraction of the workarea height (default: 0)
    y1: bottom edge as a fraction of the workarea height (default: 1)

Examples:
    view-move.py 0 0.5 0 1   # Snap to left half of output
    view-move.py 0.5 1 0 1   # Snap to right half of output
"""


def snap(x0, x1, y0, y1):
    socket = WayfireSocket()

    active_view = None
    for view in socket.list_views():
        if view.get("activated", False) and view.get("mapped", False):
            active_view = view
            break

    if not active_view:
        print("No active window found.")
        return

    view_id = active_view["id"]
    output_id = active_view["output-id"]
    output_info = socket.get_output(output_id)

    screen_w = output_info["workarea"]["width"]
    screen_h = output_info["workarea"]["height"]
    min_x = output_info["geometry"]["width"] - screen_w
    min_y = output_info["geometry"]["height"] - screen_h

    new_x = int(screen_w * x0) + min_x
    new_w = int(screen_w * x1) - new_x + min_x
    new_y = int(screen_h * y0) + min_y
    new_h = int(screen_h * y1) - new_y + min_y

    socket.configure_view(view_id, new_x, new_y, new_w, new_h)


if __name__ == "__main__":
    x0 = 0
    x1 = 0.75
    y0 = 0
    y1 = 1

    if len(sys.argv) < 4:
        print(HELP_TEXT)
        sys.exit(1)

    args = []
    arg_names = ["x0", "x1", "y0", "y1"]
    for i, name in enumerate(arg_names, 1):
        try:
            val = float(sys.argv[i])
            if not (0 <= val <= 1):
                raise ValueError
        except ValueError:
            print(
                f"Invalid value for {name}: '{sys.argv[i]}'. Must be a number between 0 and 1."
            )
            sys.exit(1)
        args.append(val)
    snap(*args)
