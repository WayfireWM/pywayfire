The [Wayfire] compositor provides access to its functionalities via Inter-Process Communication (IPC). This repository contains the source code for the python client bindings, as well as hosts many examples of how to use the IPC.

## Quickstart

### Installation
```
pip install wayfire
```

OR

```
git clone https://github.com/WayfireWM/pywayfire
cd pywayfire
python3 -m pip install .
```

### Usage examples

Basic usage is simple, import the `wayfire.ipc` module, create a socket (it will auto-detect the compositor by using the `WAYFIRE_SOCKET` environment variable) and call its functions:

```py
from wayfire import WayfireSocket

socket = WayfireSocket()
print(socket.list_views())
```

Many examples can be found in the `scripts` directory.
