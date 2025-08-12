#!/usr/bin/python3

# This script centers and resizes the active window

import sys
from wayfire import WayfireSocket

def resize_and_center(scale):
    socket = WayfireSocket()

    active_view = None
    for view in socket.list_views():
        if view.get('activated', False) and view.get('mapped', False):
            active_view = view
            break

    if not active_view:
        return

    view_id = active_view['id']
    output_id = active_view['output-id']
    output_info = socket.get_output(output_id)
    screen_w = output_info['geometry']['width']
    screen_h = output_info['geometry']['height']

    new_w = int(screen_w * scale)
    new_h = int(screen_h * scale)
    new_x = (screen_w - new_w) // 2
    new_y = (screen_h - new_h) // 2

    # Send configure command to resize and move the window
    socket.configure_view(view_id, new_x, new_y, new_w, new_h)

def is_float(value):
    """Check if a string can be converted to a float."""
    try:
        float(value)
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    scale = float(sys.argv[1]) if len(sys.argv) > 1 and is_float(sys.argv[1]) else 0.75
    resize_and_center(scale)
