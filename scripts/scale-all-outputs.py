#!/usr/bin/python3

# The scale plugin only operates on one output (monitor). This script triggers
# scale_toggle_al() on all outputs.
#
# Example configuration, binding hotkey in wayfire.ini:
#
# [command]
# ...
# binding_scaleall = <shift> <super> KEY_P
# command_scaleall = python3 scale-all-outputs.py
# ...
#

from wayfire import WayfireSocket

socket = WayfireSocket()

views_array = []  # array of views we used to get outputs
processed_outputs = set()  # set of outputs we processed
views = socket.list_views()  # array of views
outputs = socket.list_outputs()  # array of outputs

for view in views:
    output_id = view.get("output-id")
    if (
        output_id not in processed_outputs
        and view.get("mapped", False)
        and view.get("type") == "toplevel"
    ):
        # focus this view to scale it's output
        socket.set_focus(view["id"])
        socket.scale_toggle_all()
        views_array.append(view["id"])
        processed_outputs.add(output_id)

        # Stop when we processed all available outputs
        if len(processed_outputs) == len(outputs):
            break

# Toggle scaling again when a view takes focus
focused_view_id = 0
socket.watch()
while True:
    msg = socket.read_message()
    if msg["event"] == "view-focused" and msg["view"] != None:
        focused_view_id = msg["view"]["id"]
        print(f"Focused: {focused_view_id}")

    if msg["event"] == "plugin-activation-state-changed" and msg["plugin"] == "scale":
        for view_id in views_array:
            if focused_view_id == view_id:
                continue

            print(f"Unsetting {view_id}")
            socket.set_focus(view_id)
            socket.scale_toggle_all()
        break

socket.set_focus(focused_view_id)
socket.close()
