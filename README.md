 Welcome to the future of interaction with the Wayfire compositor. This is a Python module meticulously crafted to streamline control and enhance interaction with the Wayfire compositor through Inter-Process Communication (IPC)
 
## Quickstart

### Installation
```
pip install wayfire 

OR

git clone https://github.com/killown/waypy
cd waypy
python3 -m pip install .

```

### Usage examples

```
from wayfire.ipc import sock
```

#### Get focused window info
```
sock.get_focused_view()
```

#### Get pid from focused window
```
sock.get_focused_view_pid()
```

#### Get active workspace number
```
sock.get_active_workspace_number()
```

#### Get focused monitor info
```
sock.get_focused_output()
```

#### Go to another workspace
```
workspace_number = 2
sock.set_workspace(workspace_number)
```

#### Go to the next workspace
```
sock.go_next_workspace()
```

#### Go to the previous workspace
```
sock.go_previous_workspace()
```

#### Move focused window to another workspace
```
view_id = sock.get_focused_view()["id"]
workspace_number = 2
sock.set_workspace(workspace_number, view_id)

```

#### Get the list of all windows
```
sock.list_views()
```

#### Monitor info fom given id
```
monitor_output_id = 1
sock.query_output(monitor_output_id)
```


#### Get active workspace info
```
sock.get_active_workspace_info()
```


#### Get focused monitor info
```
sock.get_focused_output_name()
```

#### Get focused monitor id
```
sock.get_focused_output_id()
```

#### Get focused monitor resolution
```
sock.get_focused_output_geometry()
```

#### Get focused monitor workarea
```
sock.get_focused_output_workarea()
```

#### Set focus
```
view_id = 1
sock.set_focus(view_id)
```

#### List devices
```
sock.list_input_devices()
```

#### watch events
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


#### [Use the wiki for more info](https://github.com/killown/waypy/wiki)
