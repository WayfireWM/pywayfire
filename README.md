
Waypy serves as a python library, offering bindings specifically designed to interact with the wayfire compositor.
With waypy, effortlessly access information about windows, workspaces, and monitors within an active compositor instance. Additionally, waypy provides an event watch feature.


# Usage

```
import waypy
import os

addr = os.getenv("WAYFIRE_SOCKET")
sock = waypy.WayfireSocket(addr)
```

## Get focused window info
```
sock.get_focused_view()["info"]
```

## Get pid from focused window
```
view_id = sock.get_focused_view()["info"]["id"]
sock.get_view_pid(view_id)
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

## Move focused window to another workspace
```
view_id = sock.get_focused_view()["info"]["id"]
workspace_number = 2
sock.set_workspace(workspace_number, view_id)

```

## Get the list of all windows
```
sock.list_views()
```

## Monitor info
```
monitor_output_id = 1
sock.query_output(monitor_output_id)
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



