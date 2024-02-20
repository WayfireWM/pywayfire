import os
import pytest
import waypy as ws
import time

# Initialize WayfireSocket
addr = os.getenv("WAYFIRE_SOCKET")
sock = ws.WayfireSocket(addr)


def test_get_focused_view_title():
    title = sock.get_focused_view_title()
    assert isinstance(title, str)


def test_list_views():
    views = sock.list_views()
    assert isinstance(views, list)


def test_get_focused_view_output():
    output = sock.get_focused_view_output()
    assert isinstance(output, int)


def test_is_view_fullscreen():
    fullscreen = sock.is_view_fullscreen(sock.get_focused_view_id())
    assert isinstance(fullscreen, bool)


def test_is_view_focusable():
    focusable = sock.is_view_focusable(sock.get_focused_view_id())
    assert isinstance(focusable, bool)


def test_get_view_geometry():
    geometry = sock.get_view_geometry(sock.get_focused_view_id())
    assert isinstance(geometry, dict)
    assert "x" in geometry
    assert "y" in geometry
    assert "width" in geometry
    assert "height" in geometry


def test_is_view_minimized():
    minimized = sock.is_view_minimized(sock.get_focused_view_id())
    assert isinstance(minimized, bool)


def test_get_view_tiled_edges():
    tiled_edges = sock.get_view_tiled_edges(sock.get_focused_view_id())
    assert isinstance(tiled_edges, int)


def test_get_view_title():
    title = sock.get_view_title(sock.get_focused_view_id())
    assert isinstance(title, str)


def test_get_view_type():
    view_type = sock.get_view_type(sock.get_focused_view_id())
    assert isinstance(view_type, str)


def test_get_view_app_id():
    app_id = sock.get_view_app_id(sock.get_focused_view_id())
    assert isinstance(app_id, str)


def test_get_view_role():
    role = sock.get_view_role(sock.get_focused_view_id())
    assert isinstance(role, str)


def test_get_view_bbox():
    bbox = sock.get_view_bbox(sock.get_focused_view_id())
    assert isinstance(bbox, dict)


def test_get_view_layer():
    layer = sock.get_view_layer(sock.get_focused_view_id())
    assert isinstance(layer, str)


def test_list_pids():
    pids = sock.list_pids()
    assert isinstance(pids, list)


def test_get_focused_view():
    focused_view = sock.get_focused_view()
    assert isinstance(focused_view, dict)


def test_get_focused_view_info():
    focused_view_info = sock.get_focused_view_info()
    assert isinstance(focused_view_info, dict)


def test_get_focused_view_pid():
    focused_view_pid = sock.get_focused_view_pid()
    assert isinstance(focused_view_pid, int)


def test_is_focused_view_fullscreen():
    is_fullscreen = sock.is_focused_view_fullscreen()
    assert isinstance(is_fullscreen, bool)


def test_get_focused_view_role():
    role = sock.get_focused_view_role()
    assert isinstance(role, str)


def test_get_focused_view_bbox():
    bbox = sock.get_focused_view_bbox()
    assert isinstance(bbox, dict)


def test_get_focused_view_layer():
    layer = sock.get_focused_view_layer()
    assert isinstance(layer, str)


def test_get_focused_view_id():
    view_id = sock.get_focused_view_id()
    assert isinstance(view_id, int)


def test_get_active_workspace_info():
    workspace_info = sock.get_active_workspace_info()
    assert isinstance(workspace_info, dict)


def test_get_focused_output_name():
    output_name = sock.get_focused_output_name()
    assert isinstance(output_name, str)


def test_get_focused_output_id():
    output_id = sock.get_focused_output_id()
    assert isinstance(output_id, int)


def test_get_focused_view_type():
    view_type = sock.get_focused_view_type()
    assert isinstance(view_type, str)


def test_get_focused_view_app_id():
    app_id = sock.get_focused_view_app_id()
    assert isinstance(app_id, str)


def test_get_focused_output_geometry():
    output_geometry = sock.get_focused_output_geometry()
    assert isinstance(output_geometry, dict)


def test_get_focused_output_workarea():
    workarea = sock.get_focused_output_workarea()
    assert isinstance(workarea, dict)


def test_list_input_devices():
    input_devices = sock.list_input_devices()
    assert isinstance(input_devices, list)


def test_get_view_pid():
    pid = sock.get_view_pid(sock.get_focused_view_id())
    assert isinstance(pid, int)


def test_get_view():
    view = sock.get_view(sock.get_focused_view_id())
    assert isinstance(view, dict)


def test_total_workspaces():
    # Assuming you have a valid instance of WayfireSocket named 'sock'
    winfo = sock.get_active_workspace_info()
    total_workspaces = winfo["grid_height"] * winfo["grid_width"]

    # Calculate the number of rows and columns based on the total number of workspaces
    rows = int(total_workspaces**0.5)
    cols = (total_workspaces + rows - 1) // rows

    # Initialize the dictionary to store workspace numbers and their coordinates
    workspaces = {}

    # Loop through each row and column to assign workspace numbers and coordinates
    for row in range(rows):
        for col in range(cols):
            workspace_num = row * cols + col + 1
            if workspace_num <= total_workspaces:
                workspaces[workspace_num] = [row, col]

    assert isinstance(total_workspaces, int)


def test_get_active_workspace_number():
    # Assuming you have a valid instance of WayfireSocket named 'sock'
    result = sock.get_active_workspace_number()
    assert isinstance(result, int)
