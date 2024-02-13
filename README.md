Waypy serves as a python library, offering bindings specifically designed to interact with the wayfire compositor.
With waypy, effortlessly access information about windows, workspaces, and monitors within an active compositor instance. Additionally, waypy provides an event watch feature.


# WayfireSocket Methods

The following methods are part of the `WayfireSocket` class and serve various purposes in interacting with the Wayfire system.

## Methods

### `get_focused_view_title`

- **Description:** Returns the title of the currently focused view.
- **Return Type:** str

### `list_views`

- **Description:** Retrieves a list of all views currently available.
- **Return Type:** list

### `get_focused_view_output`

- **Description:** Returns the output of the currently focused view.
- **Return Type:** int

### `is_view_fullscreen`

- **Description:** Determines whether the specified view is in fullscreen mode.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** bool

### `is_view_focusable`

- **Description:** Checks if the specified view is focusable.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** bool

### `get_view_geometry`

- **Description:** Retrieves the geometry (position and size) of the specified view.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** dict

### `is_view_minimized`

- **Description:** Checks if the specified view is minimized.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** bool

### `get_view_tiled_edges`

- **Description:** Retrieves the tiled edges of the specified view.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** int

### `get_view_title`

- **Description:** Retrieves the title of the specified view.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** str

### `get_view_type`

- **Description:** Retrieves the type of the specified view.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** str

### `get_view_app_id`

- **Description:** Retrieves the application ID of the specified view.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** str

### `get_view_role`

- **Description:** Retrieves the role of the specified view.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** str

### `get_view_bbox`

- **Description:** Retrieves the bounding box of the specified view.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** dict

### `get_view_layer`

- **Description:** Retrieves the layer of the specified view.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** str

### `list_pids`

- **Description:** Retrieves a list of all process IDs (PIDs) associated with views.
- **Return Type:** list

### `get_focused_view`

- **Description:** Retrieves information about the currently focused view.
- **Return Type:** dict

### `get_focused_view_info`

- **Description:** Retrieves detailed information about the currently focused view.
- **Return Type:** dict

### `get_focused_view_pid`

- **Description:** Retrieves the process ID (PID) of the currently focused view.
- **Return Type:** int

### `is_focused_view_fullscreen`

- **Description:** Determines whether the currently focused view is in fullscreen mode.
- **Return Type:** bool

### `get_focused_view_role`

- **Description:** Retrieves the role of the currently focused view.
- **Return Type:** str

### `get_focused_view_bbox`

- **Description:** Retrieves the bounding box of the currently focused view.
- **Return Type:** dict

### `get_focused_view_layer`

- **Description:** Retrieves the layer of the currently focused view.
- **Return Type:** str

### `get_focused_view_id`

- **Description:** Retrieves the ID of the currently focused view.
- **Return Type:** int

### `get_active_workspace_info`

- **Description:** Retrieves information about the currently active workspace.
- **Return Type:** dict

### `get_focused_output_name`

- **Description:** Retrieves the name of the currently focused output.
- **Return Type:** str

### `get_focused_output_id`

- **Description:** Retrieves the ID of the currently focused output.
- **Return Type:** int

### `get_focused_view_type`

- **Description:** Retrieves the type of the currently focused view.
- **Return Type:** str

### `get_focused_view_app_id`

- **Description:** Retrieves the application ID of the currently focused view.
- **Return Type:** int

### `get_focused_output_geometry`

- **Description:** Retrieves the geometry (position and size) of the currently focused output.
- **Return Type:** dict

### `get_focused_output_workarea`

- **Description:** Retrieves the work area (usable area) of the currently focused output.
- **Return Type:** dict

### `list_input_devices`

- **Description:** Retrieves a list of all input devices.
- **Return Type:** list

### `get_view_pid`

- **Description:** Retrieves the process ID (PID) associated with the specified view.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** int

### `get_view`

- **Description:** Retrieves detailed information about the specified view.
- **Parameters:** view_id (int) - ID of the view
- **Return Type:** dict

### `total_workspaces`

- **Description:** Calculates the total number of workspaces and their coordinates.
- **Return Type:** dict

### `set_workspace`

- **Description:** Sets the workspace for a specified view.
- **Parameters:**
  - workspace_number (int) - Workspace number
  - view_id (int) - ID of the view
- **Return Type:** bool

### `scale_leave`

- **Description:** Leaves the scale mode.
- **Return Type:** bool

### `scale_toggle`

- **Description:** Toggles the scale mode.
- **Return Type:** bool

### `get_active_workspace_number`

- **Description:** Retrieves the number of the currently active workspace.
- **Return Type:** int

### `go_next_workspace`

- **Description:** Switches to the next workspace.
- **Return Type:** bool

### `go_previous_workspace`

- **Description:** Switches to the previous workspace.
- **Return Type:** bool



# install

```
git clone https://github.com/killown/waypy
cd waypy
python3 -m pip install .

```

# Usage

```
import waypy
import os

addr = os.getenv("WAYFIRE_SOCKET")
sock = waypy.WayfireSocket(addr)
```

## Get focused window info
```
sock.get_focused_view()
```

## Get pid from focused window
```
sock.get_focused_view_pid()
```

## Get active workspace number
```
sock.get_active_workspace_number()
```

## Get focused monitor info
```
sock.get_focused_output()
```

## Go to another workspace
```
workspace_number = 2
sock.set_workspace(workspace_number)
```

## Go to the next workspace
```
sock.go_next_workspace()
```

## Go to the previous workspace
```
sock.go_previous_workspace()
```

## Move focused window to another workspace
```
view_id = sock.get_focused_view()["id"]
workspace_number = 2
sock.set_workspace(workspace_number, view_id)

```

## Get the list of all windows
```
sock.list_views()
```

## Monitor info fom given id
```
monitor_output_id = 1
sock.query_output(monitor_output_id)
```


## Get active workspace info
```
sock.get_active_workspace_info()
```


## Get focused monitor info
```
sock.get_focused_output_name()
```

## Get focused monitor id
```
sock.get_focused_output_id()
```

## Get focused monitor resolution
```
sock.get_focused_output_geometry()
```

## Get focused monitor workarea
```
sock.get_focused_output_workarea()
```

## Set focus
```
view_id = 1
sock.set_focus(view_id)
```

## List devices
```
sock.list_input_devices()
```

## watch events
```
sock.watch()

while True:
    msg = sock.read_message()
    if "event" in msg:
        event = msg["event"]
        window_created = "view-mapped"
        window_closed = "view-unmapped"
        if event == window_created:
            print("window created")
        if event == window_closed:
            print("window closed")
```



