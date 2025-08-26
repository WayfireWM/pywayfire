#!/usr/bin/python3

# Simple script to set the opacity of a view while it's being moved.
#
# Example configuration, adding to autostart in wayfire.ini:
#
# [autostart]
# ...
# move-alpha = python3 move-alpha.py 0.75
# ...

import sys
from wayfire import WayfireSocket


def move_alpha(alpha: float):
    socket = WayfireSocket()

    socket.watch()
    app_viewid = 0
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
                            app_alpha = socket.get_view_alpha(app_viewid)["alpha"]
                            socket.set_view_alpha(app_viewid, alpha)
                            break

            elif app_viewid > 0:
                socket.set_view_alpha(app_viewid, app_alpha)
                app_viewid = 0

        except KeyboardInterrupt:
            exit(0)


if __name__ == "__main__":
    alpha = 0.75
    if len(sys.argv) > 1:
        if sys.argv[1] in ("-h", "--help"):
            print(
                "Usage: move-alpha.py [alpha]\n"
                "\n"
                "Set transparency while view is being moved.\n"
                "\n"
                "Arguments:\n"
                "  alpha    Optional. Floating point value for opacity, default is 0.75.\n"
                "           Use -h or --help to show this message."
            )
            sys.exit(0)
        try:
            alpha = float(sys.argv[1])
        except ValueError:
            pass

    move_alpha(alpha)
