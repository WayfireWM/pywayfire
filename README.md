#### Usage

```
import wayfire_socket as ws
import os

addr = os.getenv("WAYFIRE_SOCKET")
sock = ws.WayfireSocket(addr)
```

## go to another workspace
```
column = 0
row = 2
monitor_output = 1
sock.set_workspace(column, row, monitor_output)
```
## get the list of all windows
```
sock.list_views()
```
