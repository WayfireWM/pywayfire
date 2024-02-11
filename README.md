# Usage

```
import wayfire_socket as ws
import os

addr = os.getenv("WAYFIRE_SOCKET")
sock = ws.WayfireSocket(addr)
```

## Go to another workspace
```
column = 0
row = 2
monitor_output = 1
sock.set_workspace(column, row, monitor_output)
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

