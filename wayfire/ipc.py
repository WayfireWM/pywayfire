import socket
import json as js
import os
from subprocess import call
from itertools import cycle
import dbus
import configparser
from itertools import filterfalse
import time
from random import randint, choice, random
import threading


def get_msg_template(method: str, methods=None):
    plugin = None
    # just in case there is a unknow situation where the method has no plugin
    if "/" in method:
        plugin = method.split("/")[0]
    if methods:
        if method not in methods:
            if plugin is not None:
                print(
                    "To utilize this feature, please ensure that the '{0}' Wayfire plugin is enabled.".format(
                        plugin
                    )
                )
                print("Once enabled, reload the Wayfire module to apply the changes.")
            else:
                print(
                    "No plugin found in the given method, cannot utilize this feature"
                )
            return None
    # Create generic message template
    message = {}
    message["method"] = method
    message["data"] = {}
    return message


def geometry_to_json(x: int, y: int, w: int, h: int):
    geometry = {}
    geometry["x"] = x
    geometry["y"] = y
    geometry["width"] = w
    geometry["height"] = h
    return geometry


class WayfireSocket:
    def __init__(self, socket_name):
        self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        # if socket_name is empity, we need a workaround to set it
        # that happens when the compositor has no views in the workspace
        # so WAYFIRE_SOCKET env is not set
        if socket_name is None:
            # the last item is the most recent socket file
            socket_list = sorted(
                [
                    os.path.join("/tmp", i)
                    for i in os.listdir("/tmp")
                    if "wayfire-wayland" in i
                ]
            )
            for sock in socket_list:
                try:
                    self.client.connect(sock)
                    break
                except Exception as e:
                    print(e)
        else:
            self.client.connect(socket_name)
        # initialize it once for performance in some cases
        self.methods = self.list_methods()

    def read_exact(self, n):
        response = bytes()
        while n > 0:
            read_this_time = self.client.recv(n)
            if not read_this_time:
                raise Exception("Failed to read anything from the socket!")
            n -= len(read_this_time)
            response += read_this_time

        return response

    def read_message(self):
        rlen = int.from_bytes(self.read_exact(4), byteorder="little")
        response_message = self.read_exact(rlen)
        response = js.loads(response_message)
        if "error" in response:
            raise Exception(response["error"])
        return response

    def list_methods(self):
        query = get_msg_template("list-methods")
        response = self.send_json(query)
        data = js.dumps(response["methods"], indent=4)
        data = data.replace("'", '"')
        data_list = js.loads(data)
        return data_list

    def xdg_open(self, path):
        call("xdg-open {0}".format(path).split())

    def send_json(self, msg):
        data = js.dumps(msg).encode("utf8")
        header = len(data).to_bytes(4, byteorder="little")
        self.client.send(header)
        self.client.send(data)
        return self.read_message()

    # this is not a socket IPC thing, but since the compositor developer won't implement
    # dpms for ipc, this tool just works fine
    # this was not intended to be here, but anyways, lets use it
    def dpms(self, state, output_name=None):
        if state == "off" and output_name is None:
            outputs = [output["name"] for output in self.list_outputs()]
            for output in outputs:
                call("wlopm --off {}".format(output).split())
        if state == "on" and output_name is None:
            outputs = [output["name"] for output in self.list_outputs()]
            for output in outputs:
                call("wlopm --on {}".format(output).split())
        if state == "on":
            call("wlopm --on {}".format(output_name).split())
        if state == "off":
            call("wlopm --off {}".format(output_name).split())
        if state == "toggle":
            call("wlopm --toggle {}".format(output_name).split())

    def get_tiling_layout(self):
        method = "simple-tile/get-layout"
        msg = get_msg_template(method, self.methods)
        if msg is None:
            return
        output = self.get_focused_output()
        wset = output["wset-index"]
        x = output["workspace"]["x"]
        y = output["workspace"]["y"]
        msg["data"]["wset-index"] = wset
        msg["data"]["workspace"] = {}
        msg["data"]["workspace"]["x"] = x
        msg["data"]["workspace"]["y"] = y
        return self.send_json(msg)["layout"]

    def set_tiling_layout(self, layout):
        msg = get_msg_template("simple-tile/set-layout", self.methods)
        if msg is None:
            return
        output = self.get_focused_output()
        wset = output["wset-index"]
        x = output["workspace"]["x"]
        y = output["workspace"]["y"]
        msg["data"]["wset-index"] = wset
        msg["data"]["workspace"] = {}
        msg["data"]["workspace"]["x"] = x
        msg["data"]["workspace"]["y"] = y
        msg["data"]["layout"] = layout
        return self.send_json(msg)

    def set_focused_view_to_workspace_without_views(self):
        view_id = self.get_focused_view_id()
        empity_workspace = self.get_workspaces_without_views()
        if empity_workspace:
            empity_workspace = empity_workspace[0]
            empity_workspace = {"x": empity_workspace[0], "y": empity_workspace[1]}
        else:
            return
        self.set_workspace(empity_workspace, view_id)

    def tile_list_views(self, layout):
        if "view-id" in layout:
            return [
                (
                    layout["view-id"],
                    layout["geometry"]["width"],
                    layout["geometry"]["height"],
                )
            ]

        split = "horizontal-split" if "horizontal-split" in layout else "vertical-split"
        list = []
        for child in layout[split]:
            list += self.tile_list_views(child)
        return list

    def close(self):
        self.client.close()

    def response_handler(self, response, result, loop):
        if response == 0:
            print(f'screenshot of all outputs: {result.get("uri")}')
            loop.stop()
        else:
            print("fail")

    def screenshot_all_outputs(self):
        bus = dbus.SessionBus()
        desktop = bus.get_object(
            "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop"
        )
        desktop.Screenshot(
            "Screenshot",
            {"handle_token": "my_token"},
            dbus_interface="org.freedesktop.portal.Screenshot",
        )
        # lets wait save the file before try opening it
        time.sleep(1)
        self.xdg_open("/tmp/out.png")

    def screenshot_focused_monitor(self):
        output = self.get_focused_output()
        name = output["name"]
        output_file = "/tmp/output-{0}.png".format(name)
        call(["grim", "-o", name, output_file])
        self.xdg_open(output_file)

    def screenshot(self, id, filename):
        capture = get_msg_template("view-shot/capture", self.methods)
        if capture is None:
            return
        capture["data"]["view-id"] = id
        capture["data"]["file"] = filename
        self.send_json(capture)

    def move_cursor(self, x: int, y: int):
        message = get_msg_template("stipc/move_cursor", self.methods)
        if message is None:
            return
        message["data"]["x"] = x
        message["data"]["y"] = y
        return self.send_json(message)

    def click_button(self, btn_with_mod: str, mode: str):
        """
        btn_with_mod can be S-BTN_LEFT/BTN_RIGHT/etc. or just BTN_LEFT/...
        If S-BTN..., then the super modifier will be pressed as well.
        mode is full, press or release
        """
        message = get_msg_template("stipc/feed_button", self.methods)
        message["method"] = "stipc/feed_button"
        message["data"]["mode"] = mode
        message["data"]["combo"] = btn_with_mod
        return self.send_json(message)

    def watch(self):
        method = "window-rules/events/watch"
        message = get_msg_template(method, self.methods)
        if message is None:
            return
        return self.send_json(message)

    def query_output(self, output_id: int):
        message = get_msg_template("window-rules/output-info", self.methods)
        if message is None:
            return
        message["data"]["id"] = output_id
        return self.send_json(message)

    def list_outputs(self):
        message = get_msg_template("window-rules/list-outputs", self.methods)
        if message is None:
            return
        return self.send_json(message)

    def list_wsets(self):
        message = get_msg_template("window-rules/list-wsets", self.methods)
        if message is None:
            return
        return self.send_json(message)

    def wset_info(self, id):
        message = get_msg_template("window-rules/wset-info", self.methods)
        if not message:
            return
        message["data"]["id"] = id
        if message is None:
            return
        return self.send_json(message)

    def ping(self):
        message = get_msg_template("stipc/ping")
        response = self.send_json(message)
        return ("result", "ok") in response.items()

    def set_key_state(self, key: str, state: bool):
        message = get_msg_template("stipc/feed_key", self.methods)
        if message is None:
            return
        message["data"]["key"] = key
        message["data"]["state"] = state
        return self.send_json(message)

    def run(self, cmd):
        message = get_msg_template("stipc/run", self.methods)
        if message is None:
            return
        message["data"]["cmd"] = cmd
        return self.send_json(message)

    def press_key(self, key: str):
        if key[:2] == "S-":
            self.set_key_state("KEY_LEFTMETA", True)
            self.set_key_state(key[2:], True)
            self.set_key_state(key[2:], False)
            self.set_key_state("KEY_LEFTMETA", False)
        elif key[:2] == "C-":
            self.set_key_state("KEY_LEFTCTRL", True)
            self.set_key_state(key[2:], True)
            self.set_key_state(key[2:], False)
            self.set_key_state("KEY_LEFTCTRL", False)
        else:
            self.set_key_state(key, True)
            self.set_key_state(key, False)

    def toggle_showdesktop(self):
        message = get_msg_template("wm-actions/toggle_showdesktop", self.methods)
        if message is None:
            return
        return self.send_json(message)

    def set_sticky(self, view_id, state):
        message = get_msg_template("wm-actions/set-sticky")
        if message is None:
            return
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def send_to_back(self, view_id, state):
        message = get_msg_template("wm-actions/send-to-back")
        if message is None:
            return
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def set_minimized(self, view_id, state):
        message = get_msg_template("wm-actions/set-minimized")
        if message is None:
            return
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def scale_toggle(self):
        message = get_msg_template("scale/toggle")
        if message is None:
            return
        self.send_json(message)
        return True

    def cube_activate(self):
        message = get_msg_template("cube/activate")
        if message is None:
            return
        self.send_json(message)
        return True

    def cube_rotate_left(self):
        message = get_msg_template("cube/rotate_left")
        if message is None:
            return
        self.send_json(message)
        return True

    def cube_rotate_right(self):
        message = get_msg_template("cube/rorate_right")
        if message is None:
            return
        self.send_json(message)
        return True

    def scale_leave(self):
        # only works in the fork
        message = get_msg_template("scale/leave")
        if message is None:
            return
        self.send_json(message)
        return True

    def list_outputs_ids(self):
        outputs = self.list_outputs()
        if outputs:
            return [i["id"] for i in outputs]

    def sum_geometry_resolution(self):
        outputs = sock.list_outputs()
        total_width = 0
        total_height = 0
        for output in outputs:
            total_width += output["geometry"]["width"]
            total_height += output["geometry"]["height"]
        return total_width, total_height

    def list_views(self):
        list_views = self.send_json(get_msg_template("window-rules/list-views"))
        if list_views is None:
            return
        clean_list = []
        for view in list_views:
            if view["role"] == "desktop-environment":
                continue
            if view["mapped"] is False:
                continue
            if view["pid"] == -1:
                continue

            clean_list.append(view)
        return clean_list

    def focused_output_views(self):
        list_views = self.list_views()
        if not list_views:
            return
        focused_output = self.get_focused_output()
        if not focused_output:
            return
        output_views = [
            view for view in list_views if view["output-id"] == focused_output["id"]
        ]
        return output_views

    def list_pids(self):
        list_views = self.list_views()
        if not list_views:
            return
        list_pids = []
        for view in list_views:
            list_pids.append(view["pid"])
        return list_pids

    def list_ids(self):
        list_views = self.list_views()
        if not list_views:
            return
        list_ids = []
        for view in list_views:
            list_ids.append(view["id"])
        return list_ids

    def configure_view(self, view_id: int, x: int, y: int, w: int, h: int):
        message = get_msg_template("window-rules/configure-view")
        if message is None:
            return
        message["data"]["id"] = view_id
        message["data"]["geometry"] = geometry_to_json(x, y, w, h)
        return self.send_json(message)

    def assign_slot(self, view_id: int, slot: str):
        message = get_msg_template("grid/" + slot)
        message["data"]["view_id"] = view_id
        return self.send_json(message)

    def get_view_workspace(self, view_id):
        wviews = self.get_workspaces_with_views()
        ws = None
        if wviews:
            ws = [i for i in wviews if view_id == i["view-id"]]
        if ws:
            ws = ws[0]
            return {"x": ws["x"], "y": ws["y"]}
        return None

    def set_focus(self, view_id: int):
        message = get_msg_template("window-rules/focus-view")
        if message is None:
            return
        message["data"]["id"] = view_id
        return self.send_json(message)

    def go_workspace_set_focus(self, view_id):
        focused_output = self.get_focused_output_id()
        view_output_id = self.get_view_output_id(view_id)
        # needed to change the workspace if not the focused output
        if focused_output != view_output_id:
            self.set_focus(view_id)
        workspace = self.get_view_workspace(view_id)
        if workspace:
            self.set_workspace(workspace)
        self.set_focus(view_id)

    def get_focused_view(self):
        message = get_msg_template("window-rules/get-focused-view")
        if message is None:
            return
        return self.send_json(message)["info"]

    def get_focused_view_info(self):
        id = self.get_focused_view_id()
        return [i for i in self.list_views() if i["id"] == id][0]

    def get_focused_view_pid(self):
        view = self.get_focused_view()
        if view is not None:
            view_id = self.get_focused_view()
            if view_id is not None:
                view_id = view_id["id"]
                return self.get_view_pid(view_id)

    def is_focused_view_fullscreen(self):
        focused_view = self.get_focused_view()
        if focused_view is not None:
            return focused_view.get("fullscreen")
        return None

    def get_focused_view_role(self):
        focused_view_info = self.get_focused_view_info()
        if focused_view_info is not None:
            return focused_view_info.get("role")
        return None

    def get_focused_view_bbox(self):
        focused_view = self.get_focused_view()
        if focused_view is not None:
            return focused_view.get("bbox")
        return None

    def get_focused_view_layer(self):
        focused_view = self.get_focused_view()
        if focused_view is not None:
            return focused_view.get("layer")
        return None

    def get_focused_view_id(self):
        focused_view = self.get_focused_view()
        if focused_view is not None:
            return focused_view.get("id")
        return None

    def get_focused_view_output(self):
        focused_view = self.get_focused_view()
        if focused_view is not None:
            return focused_view.get("output-id")
        return None

    def get_focused_view_title(self):
        # the issue here is that if you get focused data directly
        # sometimes it will get stuff from different roles like desktop-environment
        # list-view will just filter all those stuff
        view_id = self.get_focused_view()
        if view_id:
            view_id = view_id["id"]
        else:
            return ""
        list_view = self.list_views()
        title = [view["title"] for view in list_view if view_id == view["id"]]
        if title:
            return title[0]
        else:
            return ""

    def get_focused_view_type(self):
        return self.get_focused_view()["type"]

    def get_focused_view_app_id(self):
        return self.get_focused_view()["app-id"]

    def get_focused_output(self):
        message = get_msg_template("window-rules/get-focused-output")
        if message is None:
            return
        return self.send_json(message)["info"]

    def coordinates_to_number(self, rows, cols, coordinates):
        row, col = coordinates
        if 0 <= row < rows and 0 <= col < cols:
            return row * cols + col + 1
        else:
            return None

    def get_active_workspace_number(self):
        focused_output = self.get_focused_output()
        x = focused_output["workspace"]["x"]
        y = focused_output["workspace"]["y"]
        return self.get_workspace_number(x, y)

    def get_workspace_number(self, x, y):
        workspaces_coordinates = self.total_workspaces()
        coordinates_to_find = [
            i for i in workspaces_coordinates.values() if [y, x] == i
        ][0]
        total_workspaces = len(self.total_workspaces())
        rows = int(total_workspaces**0.5)
        cols = (total_workspaces + rows - 1) // rows
        workspace_number = self.coordinates_to_number(rows, cols, coordinates_to_find)
        return workspace_number

    def get_active_workspace_info(self):
        focused_output = self.get_focused_output()
        if focused_output is not None:
            return focused_output.get("workspace")
        return None

    def get_focused_output_name(self):
        focused_output = self.get_focused_output()
        if focused_output is not None:
            return focused_output.get("name")
        return None

    def get_focused_output_id(self):
        focused_output = self.get_focused_output()
        if focused_output is not None:
            return focused_output.get("id")
        return None

    def get_focused_output_geometry(self):
        focused_output = self.get_focused_output()
        if focused_output is not None:
            return focused_output.get("geometry")
        return None

    def get_focused_output_workarea(self):
        focused_output = self.get_focused_output()
        if focused_output is not None:
            return focused_output.get("workarea")
        return None

    def set_view_always_on_top(self, view_id: int, always_on_top: bool):
        message = get_msg_template("wm-actions/set-always-on-top")
        if message is None:
            return
        message["data"]["view_id"] = view_id
        message["data"]["state"] = always_on_top
        return self.send_json(message)

    def set_view_alpha(self, view_id: int, alpha: float):
        message = get_msg_template("wf/alpha/set-view-alpha")
        if message is None:
            return
        message["data"] = {}
        message["data"]["view-id"] = view_id
        message["data"]["alpha"] = alpha
        return self.send_json(message)

    def get_view_alpha(self, view_id: int):
        message = get_msg_template("wf/alpha/get-view-alpha")
        if message is None:
            return
        message["data"]["view-id"] = view_id
        return self.send_json(message)

    def set_view_shader(self, view_id: int, shader: str):
        message = get_msg_template("wf/filters/set-view-shader")
        if message is None:
            return
        message["data"] = {}
        message["data"]["view-id"] = view_id
        message["data"]["shader-path"] = shader
        return self.send_json(message)

    def unset_view_shader(self, view_id: int):
        message = get_msg_template("wf/filters/unset-view-shader")
        if message is None:
            return
        message["data"] = {}
        message["data"]["view-id"] = view_id
        return self.send_json(message)

    def list_input_devices(self):
        message = get_msg_template("input/list-devices")
        if message is None:
            return
        return self.send_json(message)

    def get_view_pid(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            pid = view["pid"]
            return pid

    def get_view(self, view_id):
        message = get_msg_template("window-rules/view-info")
        if message is None:
            return
        message["data"]["id"] = view_id
        return self.send_json(message)["info"]

    def click_and_drag(
        self, button, start_x, start_y, end_x, end_y, release=True, steps=10
    ):
        dx = end_x - start_x
        dy = end_y - start_y

        self.move_cursor(start_x, start_y)
        self.click_button(button, "press")
        for i in range(steps + 1):
            self.move_cursor(start_x + dx * i // steps, start_y + dy * i // steps)
        if release:
            self.click_button(button, "release")

    def go_next_workspace(self):
        workspaces = list(self.total_workspaces().values())
        active_workspace = self.get_focused_output()["workspace"]

        # Find the index of the current active workspace
        current_index = workspaces.index([active_workspace["y"], active_workspace["x"]])

        # Calculate the index of the next workspace
        next_index = (current_index + 1) % len(workspaces)

        # Get the next workspace
        next_workspace_coords = workspaces[next_index]

        # Find the identifier of the next workspace
        next_workspace_id = None
        for key, value in self.total_workspaces().items():
            if value == next_workspace_coords:
                next_workspace_id = key
                break

        # Set the next workspace
        if next_workspace_id:
            self.set_workspace(
                {"y": next_workspace_coords[0], "x": next_workspace_coords[1]}
            )

    def iterate_dicts(self, dicts):
        index = 0
        length = len(dicts)
        while True:
            yield dicts[index]
            index = (index + 1) % length

    def get_next_workspace(self, workspaces, active_workspace):
        # Find the index of the active workspace in the list
        active_index = None

        # Remove the "view-id" key from each workspace
        for workspace in workspaces:
            workspace.pop("view-id", None)

        # Create a set to store unique workspace dictionaries
        unique_workspaces = []

        # Filter out duplicates while maintaining the order
        for workspace in workspaces:
            if workspace not in unique_workspaces:
                unique_workspaces.append(workspace)

        # Sort the list based on the 'x' and 'y' keys
        unique_workspaces.sort(key=lambda d: (d["x"], d["y"]))

        for i, workspace in enumerate(unique_workspaces):
            if workspace == active_workspace:
                active_index = i
                break

        if active_index is None:
            first_workspace = self.get_workspaces_with_views()
            if first_workspace:
                first_workspace = first_workspace[0]
            self.set_workspace(first_workspace)
            return

        # Calculate the index of the next workspace cyclically
        next_index = (active_index + 1) % len(unique_workspaces)

        # Return the next workspace
        return unique_workspaces[next_index]

    def go_next_workspace_with_views(self):
        workspaces = self.get_workspaces_with_views()
        active_workspace = self.get_focused_output()["workspace"]
        active_workspace = {"x": active_workspace["x"], "y": active_workspace["y"]}
        next_ws = self.get_next_workspace(workspaces, active_workspace)
        if next_ws:
            self.set_workspace(next_ws)
        else:
            return

    def go_previous_workspace(self):
        previous = 1
        current_workspace = self.get_active_workspace_number()
        if current_workspace == 1:
            previous = 9
        else:
            if current_workspace is not None:
                previous = current_workspace - 1

        self.set_workspace(previous)
        return True

    def close_view(self, view_id):
        message = get_msg_template("window-rules/close-view")
        if message is None:
            return
        message["data"]["id"] = view_id
        return self.send_json(message)

    def close_focused_view(self):
        view_id = self.get_focused_view()["id"]
        self.close_view(view_id)

    def get_view_info(self, view_id):
        info = [i for i in self.list_views() if i["id"] == view_id]
        if info:
            return info[0]
        else:
            return

    def get_view_output_id(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            return view.get("output-id")
        return None

    def is_view_fullscreen(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            return view.get("fullscreen")
        return None

    def is_view_focusable(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            return view.get("focusable")
        return None

    def get_view_geometry(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            return view.get("geometry")
        return None

    def is_view_minimized(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            return view.get("minimized")
        return None

    def is_view_maximized(self, view_id):
        tiled_edges = self.get_view_tiled_edges(view_id)
        if tiled_edges is not None:
            return tiled_edges == 15
        return False

    def is_view_size_greater_than_half_workarea(self, view_id):
        output_id = self.get_view_output_id(view_id)
        output = self.query_output(output_id)
        workarea = output["workarea"]
        wa_w = workarea["width"]
        wa_h = workarea["height"]
        view = self.get_view(view_id)
        vw = view["geometry"]["width"]
        vh = view["geometry"]["height"]
        if vw > (wa_w / 2) and vh > (wa_h / 2):
            return True
        else:
            return False

    def get_view_tiled_edges(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            return view.get("tiled-edges")
        return None

    def get_view_title(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            return view.get("title")
        return None

    def get_view_type(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            return view.get("type")
        return None

    def get_view_app_id(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            return view.get("app-id")
        return None

    def get_view_role(self, view_id):
        view_info = self.get_view_info(view_id)
        if view_info is not None:
            return view_info.get("role")
        return None

    def get_view_bbox(self, view_id):
        view_info = self.get_view_info(view_id)
        if view_info is not None:
            return view_info.get("bbox")
        return None

    def get_view_layer(self, view_id):
        view_layer_content = self.get_view_layer(view_id)
        if view_layer_content:
            return view_layer_content.get("layer")
        return None

    def maximize_focused(self):
        view = self.get_focused_view()
        self.assign_slot(view["id"], "slot_c")

    def fullscreen_focused(self):
        view = self.get_focused_view()
        self.set_fullscreen(view["id"])

    def set_fullscreen(self, view_id):
        message = get_msg_template("wm-actions/set-fullscreen")
        if message is None:
            return
        message["data"]["view_id"] = view_id
        message["data"]["state"] = True
        self.send_json(message)

    def toggle_expo(self):
        message = get_msg_template("expo/toggle")
        if message is None:
            return
        self.send_json(message)

    def find_device_id(self, name_or_id_or_type):
        devices = self.list_input_devices()
        for dev in devices:
            if (
                dev["name"] == name_or_id_or_type
                or str(dev["id"]) == name_or_id_or_type
                or dev["type"] == name_or_id_or_type
            ):
                return dev["id"]
        return None

    def disable_input_device(self, args):
        device_id = self.find_device_id(args)
        msg = self.configure_input_device(device_id, False)
        return msg

    def enable_input_device(self, args):
        device_id = self.find_device_id(args)
        msg = self.configure_input_device(device_id, True)
        return msg

    def reload_plugins(self):
        filename = os.path.expanduser(os.path.join("~", ".config", "wayfire.ini"))

        config = configparser.ConfigParser()
        config.read(filename)

        # Comment out the 'plugins' line
        config["core"]["plugins"] = "# " + config["core"]["plugins"]

        # Save the modified configuration back to the file
        with open(filename, "w") as configfile:
            config.write(configfile)

        # Uncomment the 'plugins' line
        config["core"]["plugins"] = (
            config["core"]["plugins"][2:]
            if config["core"]["plugins"].startswith("# ")
            else config["core"]["plugins"]
        )

        # Save the modified configuration back to the file
        with open(filename, "w") as configfile:
            config.write(configfile)

    def reload_plugin(self, plugin_name):
        filename = os.path.expanduser(os.path.join("~", ".config", "wayfire.ini"))
        config = configparser.ConfigParser()
        config.read(filename)
        if plugin_name in config["core"]["plugins"]:
            plugins_list = config["core"]["plugins"].split()
            plugins_list.remove(plugin_name)
            config["core"]["plugins"] = " ".join(plugins_list)
            with open(filename, "w") as configfile:
                config.write(configfile)
            plugins_list.append(plugin_name)
            config["core"]["plugins"] = " ".join(plugins_list)
            with open(filename, "w") as configfile:
                config.write(configfile)

    def maximize(self, view_id):
        self.assign_slot(view_id, "slot_c")

    def maximize_all_views_from_active_workspace(self):
        for view_id in self.get_views_from_active_workspace():
            if not self.is_view_fullscreen(view_id):
                self.maximize(view_id)

    def total_workspaces(self):
        winfo = self.get_active_workspace_info()
        if not winfo:
            return
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
        return workspaces

    def view_visible_on_workspace(self, view, ws_x, ws_y, monitor):
        workspace_start_x = ws_x * monitor["width"]
        workspace_start_y = ws_y * monitor["height"]
        workspace_end_x = workspace_start_x + monitor["width"]
        workspace_end_y = workspace_start_y + monitor["height"]

        # Test intersection of two rectangles
        return not (
            view["x"] >= workspace_end_x
            or view["y"] > workspace_end_y
            or view["x"] + view["width"] <= workspace_start_x
            or view["y"] + view["height"] <= workspace_start_y
        )

    def get_workspaces_with_views(self):
        focused_output = self.get_focused_output()
        monitor = focused_output["geometry"]
        ws_with_views = []
        views = self.focused_output_views()
        if views:
            for ws_x in range(focused_output["workspace"]["grid_width"]):
                for ws_y in range(focused_output["workspace"]["grid_height"]):
                    for view in views:
                        if self.view_visible_on_workspace(
                            view["geometry"],
                            ws_x - focused_output["workspace"]["x"],
                            ws_y - focused_output["workspace"]["y"],
                            monitor,
                        ):
                            ws_with_views.append(
                                {"x": ws_x, "y": ws_y, "view-id": view["id"]}
                            )
            return ws_with_views
        return None

    def get_workspaces_without_views(self):
        workspace_with_views = self.get_workspaces_with_views()
        if not workspace_with_views:
            return
        workspace_with_views = [[i["x"], i["y"]] for i in workspace_with_views]
        total_workspaces = self.total_workspaces()
        if not total_workspaces:
            return
        all_workspaces = list(total_workspaces.values())
        return list(filterfalse(lambda x: x in workspace_with_views, all_workspaces))

    def get_workspace_coordinates(self, view_info):
        focused_output = self.get_focused_output()
        monitor = focused_output["geometry"]
        views = [view_info]
        for ws_x in range(focused_output["workspace"]["grid_width"]):
            for ws_y in range(focused_output["workspace"]["grid_height"]):
                for view in views:
                    if self.view_visible_on_workspace(
                        view["geometry"],
                        ws_x - focused_output["workspace"]["x"],
                        ws_y - focused_output["workspace"]["y"],
                        monitor,
                    ):
                        return {"x": ws_x, "y": ws_y}

    def get_views_from_active_workspace(self):
        aw = self.get_active_workspace_info()
        workspace_with_views = self.get_workspaces_with_views()
        if workspace_with_views is None or aw is None:
            return []

        return [
            i["view-id"]
            for i in workspace_with_views
            if i["x"] == aw["x"] and i["y"] == aw["y"]
        ]

    def set_view_top_left(self, view_id):
        self.assign_slot(view_id, "slot_tl")

    def set_view_top_right(self, view_id):
        self.assign_slot(view_id, "slot_tr")

    def set_view_bottom_left(self, view_id):
        self.assign_slot(view_id, "slot_bl")

    def set_view_right(self, view_id):
        self.assign_slot(view_id, "slot_r")

    def set_view_left(self, view_id):
        self.assign_slot(view_id, "slot_l")

    def set_view_bottom(self, view_id):
        self.assign_slot(view_id, "slot_b")

    def set_view_top(self, view_id):
        self.assign_slot(view_id, "slot_t")

    def set_view_center(self, view_id):
        self.assign_slot(view_id, "slot_c")

    def set_view_bottom_right(self, view_id):
        self.assign_slot(view_id, "slot_br")

    def resize_view(self, view_id, width, height, position, switch=False):
        output_id = self.get_view_output_id(view_id)
        if not output_id:
            return
        view = self.get_view(view_id)
        output = self.query_output(output_id)
        output_width = output["geometry"]["width"]
        output_height = output["geometry"]["height"]
        workarea = output["workarea"]
        wa_x = workarea["x"]
        wa_y = workarea["y"]
        wa_w = workarea["width"]
        wa_h = workarea["height"]
        vx = view["geometry"]["x"]
        vy = view["geometry"]["y"]
        vw = view["geometry"]["width"]
        vh = view["geometry"]["height"]
        # don't resize if the view is taking the whole x or y workarea
        if vw == output_width - wa_x and switch is False:
            # if view covers whole workarea width disallow for left and right
            if position == "left" or position == "right":
                return
        if vh == output_height - wa_y and switch is False:
            # if view covers whole workarea height disallow for up and down
            if position == "up" or position == "down":
                return

        if position == "left":
            # size limit for resize views
            if width < 500 or width > (wa_w - 500):
                return
            vx = wa_x

        if position == "right":
            # size limit for resize views
            if width < 500 or width > (wa_w - 500):
                return
            vx = (output_width - wa_x) - width

        if position == "up":
            # size limit for resize views
            if height < 200 or height > (wa_h - 200):
                return
            vy = wa_y

        if position == "down":
            # size limit for resize views
            if height < 200 or height > (wa_h - 200):
                return
            vy = output_height - height

        self.configure_view(
            view_id,
            vx,
            vy,
            width,
            height,
        )

    def resize_views_left(self):
        views = self.get_views_from_active_workspace()
        views = [view for view in self.list_views() if view["id"] in views]
        step_size = 40
        for view in views:
            x = view["geometry"]["x"]
            width = view["geometry"]["width"]
            height = view["geometry"]["height"]
            view_id = view["id"]
            if x < 100:
                width = width - step_size
                self.resize_view(view_id, width, height, "left")
            else:
                width = width + step_size
                self.resize_view(view_id, width, height, "right")

    def resize_views_right(self):
        views = self.get_views_from_active_workspace()
        views = [view for view in self.list_views() if view["id"] in views]
        step_size = 40
        for view in views:
            x = view["geometry"]["x"]
            width = view["geometry"]["width"]
            height = view["geometry"]["height"]
            view_id = view["id"]
            if x < 100:
                width = width + step_size
                self.resize_view(view_id, width, height, "left")
            else:
                width = width - step_size
                self.resize_view(view_id, width, height, "right")

    def resize_views_up(self):
        views = self.get_views_from_active_workspace()
        views = [view for view in self.list_views() if view["id"] in views]
        step_size = 40
        for view in views:
            y = view["geometry"]["y"]
            width = view["geometry"]["width"]
            height = view["geometry"]["height"]
            view_id = view["id"]
            # top
            if y < 100:
                height = height - step_size
                self.resize_view(view_id, width, height, "up")
            # bottom
            else:
                height = height + step_size
                self.resize_view(view_id, width, height, "down")

    def resize_views_down(self):
        views = self.get_views_from_active_workspace()
        views = [view for view in self.list_views() if view["id"] in views]
        step_size = 40
        for view in views:
            y = view["geometry"]["y"]
            width = view["geometry"]["width"]
            height = view["geometry"]["height"]
            view_id = view["id"]
            # top
            if y < 100:
                height = height + step_size
                self.resize_view(view_id, width, height, "up")
            # bottom
            else:
                height = height - step_size
                self.resize_view(view_id, width, height, "down")

    def switch_views_side(self):
        views = self.get_views_from_active_workspace()
        views = [view for view in self.list_views() if view["id"] in views]
        for view in views:
            x = view["geometry"]["x"]
            width = view["geometry"]["width"]
            height = view["geometry"]["height"]
            view_id = view["id"]
            if x < 100:
                self.resize_view(view_id, width, height, "right", switch=True)
            else:
                self.resize_view(view_id, width, height, "left", switch=True)

    def tilling_view_position(self, position, view_id):
        if position == "top-right":
            self.set_view_top_right(view_id)
        if position == "top-left":
            self.set_view_top_left(view_id)
        if position == "bottom-right":
            self.set_view_bottom_right(view_id)
        if position == "bottom-left":
            self.set_view_bottom_left(view_id)
        if position == "left":
            self.set_view_left(view_id)
        if position == "right":
            self.set_view_right(view_id)

    def tilling(self):
        # layout
        aw = self.get_views_from_active_workspace()
        if not aw:
            return None

        index = len(aw) - 1
        if len(aw) == 1:
            self.maximize_focused()
            return

        index = len(aw) - 1
        if len(aw) == 2:
            for pos in ["left", "right"]:
                self.tilling_view_position(pos, aw[index])
                if index >= 0:
                    index -= 1
                if index <= -1:
                    break
            return

        index = len(aw) - 1
        if len(aw) == 3:
            for pos in ["left", "top-right", "bottom-right"]:
                self.tilling_view_position(pos, aw[index])
                if index >= 0:
                    index -= 1
                if index <= -1:
                    break
            return

        index = len(aw) - 1
        positions = ["top-left", "top-right", "bottom-right", "bottom-left"]
        positions_cycle = cycle(positions)
        while True:
            # just in case there is a bug that it countinues bellow -1
            if index <= -1:
                break
            position = next(positions_cycle)
            self.tilling_view_position(position, aw[index])
            if index >= 0:
                index -= 1

    def tilling_toggle(self):
        aw = self.get_views_from_active_workspace()
        # no views in the active workspace, no toggle
        if not aw:
            return
        view_id = self.get_focused_view()["id"]
        if self.is_view_maximized(view_id) and not self.is_view_fullscreen(view_id):
            self.tilling()
        else:
            self.maximize_all_views_from_active_workspace()

    def set_workspace(self, workspace, view_id=None, output_id=None):
        x, y = workspace["x"], workspace["y"]
        focused_output = self.get_focused_output()
        if output_id is None:
            output_id = focused_output["id"]
        message = get_msg_template("vswitch/set-workspace", self.methods)
        if message is None:
            return
        message["data"]["x"] = x
        message["data"]["y"] = y
        message["data"]["output-id"] = output_id
        if view_id is not None:
            message["data"]["view-id"] = view_id
        self.send_json(message)
        return True

    def configure_input_device(self, id, enabled: bool):
        message = get_msg_template("input/configure-device")
        if message is None:
            return
        message["data"]["id"] = id
        message["data"]["enabled"] = enabled
        return self.send_json(message)

    def test_random_set_view_position(self, view_id):
        actions = [
            self.set_view_top_left,
            self.set_view_top_right,
            self.set_view_bottom_left,
            self.set_view_right,
            self.set_view_left,
            self.set_view_bottom,
            self.set_view_top,
            self.set_view_center,
            self.set_view_bottom_right,
        ]
        choice(actions)(view_id)

    def test_random_change_view_state(self, view_id):
        actions = [
            lambda: self.maximize(view_id),
            lambda: self.set_fullscreen(view_id),
            lambda: self.set_minimized(view_id, True),
            lambda: self.set_minimized(view_id, False),
            lambda: self.set_sticky(view_id, choice([True, False])),
            lambda: self.send_to_back(view_id, choice([True, False])),
            lambda: self.set_view_alpha(view_id, random() * 1.0),
        ]
        choice(actions)()

    def test_random_list_info(self, view_id):
        actions = [
            self.list_outputs,
            self.list_wsets,
            lambda: self.wset_info(view_id),
            lambda: self.get_view(view_id),
            lambda: self.get_view_info(view_id),
            lambda: self.get_view_alpha(view_id),
            self.list_input_devices,
            self.get_workspaces_with_views,
            self.get_workspaces_without_views,
            self.get_views_from_active_workspace,
        ]
        choice(actions)()

    def test_set_view_position(self, view_id):
        self.set_view_top_left(view_id)
        self.set_view_top_right(view_id)
        self.set_view_bottom_left(view_id)
        self.set_view_right(view_id)
        self.set_view_left(view_id)
        self.set_view_bottom(view_id)
        self.set_view_top(view_id)
        self.set_view_center(view_id)
        self.set_view_bottom_right(view_id)
        self.set_focus(view_id)

    def test_change_view_state(self, view_id):
        self.maximize(view_id)
        self.set_fullscreen(view_id)
        self.set_minimized(view_id, True)
        self.set_minimized(view_id, False)
        self.set_sticky(view_id, choice([True, False]))
        self.send_to_back(view_id, choice([True, False]))
        self.set_view_alpha(view_id, random() * 1.0)
        self.set_focus(view_id)

    def test_move_cursor_and_click(self):
        self.move_cursor(randint(100, 10000), randint(100, 10000))
        self.click_button("BTN_LEFT", "press")
        self.click_button("BTN_LEFT", "press")

    def test_list_info(self, view_id):
        self.list_outputs()
        self.list_wsets()
        self.wset_info(view_id)
        self.get_view(view_id)
        self.get_view_info(view_id)
        self.get_view_alpha(view_id)
        self.list_input_devices()
        self.get_workspaces_with_views()
        self.get_workspaces_without_views()
        self.get_views_from_active_workspace()
        self.set_focus(view_id)

    def test_cube_plugin(self):
        self.cube_activate()
        self.cube_rotate_left()
        self.cube_rotate_right()
        self.click_button("BTN_LEFT", "full")

    def test_plugins(self):
        functions = [
            (self.scale_toggle, ()),
            (self.toggle_expo, ()),
            (self.toggle_showdesktop, ()),
            (self.test_cube_plugin, ()),
            # (self.reload_plugins, ()),
        ]
        random_function, args = choice(functions)
        random_function(*args)

    def test_turn_off_on_outputs(self):
        self.dpms("off")
        time.sleep(10)
        self.dpms("on")

    def test_wayfire(self, number_of_views_to_open, max_tries=1, speed=0):
        from wayfire.tests.gtk4_window import spam_new_views, open_new_view

        list_views = self.list_views()
        view_id = None
        if list_views:
            view_id = choice([i["id"] for i in list_views])
        workspaces = self.total_workspaces()
        sumgeo = self.sum_geometry_resolution()
        if workspaces:
            workspaces = workspaces.values()
            workspaces = [{"x": x, "y": y} for x, y in workspaces]

        functions = [
            (self.go_next_workspace_with_views, ()),
            (self.set_focused_view_to_workspace_without_views, ()),
            # (self.test_move_cursor_and_click, ()),
            (self.test_random_set_view_position, (view_id,)),
            (self.test_random_change_view_state, (view_id,)),
            (self.test_random_list_info, (view_id,)),
            (self.test_set_view_position, (view_id)),
            (self.test_list_info, (view_id)),
            (self.test_change_view_state, (view_id)),
            (self.test_plugins, ()),
            (self.set_focus, (view_id,)),
            (
                self.click_and_drag,
                (
                    "S-BTN_LEFT",
                    randint(1, sumgeo[0]),
                    randint(1, sumgeo[1]),
                    randint(1, sumgeo[0]),
                    randint(1, sumgeo[1]),
                    True,
                ),
            ),
            (
                # self.click_button,
                # (
                #    choice(["BTN_RIGHT", "BTN_LEFT"]),
                #    "press",
                # ),
            ),
            (
                self.configure_view,
                (
                    view_id,
                    randint(1, sumgeo[0]),
                    randint(0, sumgeo[1]),
                    randint(1, sumgeo[0]),
                    randint(1, sumgeo[1]),
                ),
            ),
            (
                self.set_workspace,
                (choice(workspaces), view_id, choice(self.list_outputs_ids())),
            ),
        ]

        iterations = 0
        dpms_allowed = 0
        # lets keep those views open for some time
        for i in range(number_of_views_to_open):
            thread = threading.Thread(target=open_new_view, args=(1000000000))
            thread.start()

        # now spam views
        thread = threading.Thread(target=spam_new_views)
        thread.start()

        results_file = "/tmp/test-wayfire.py"
        if os.path.exists(results_file):
            with open(results_file, "w"):
                pass
        # Write the necessary imports at the beginning of the file
        with open(results_file, "a") as file:
            file.write("import socket\n")
            file.write("import json as js\n")
            file.write("import os\n")
            file.write("from subprocess import call\n")
            file.write("from itertools import cycle\n")
            file.write("from sys import argv\n")
            file.write("import dbus\n")
            file.write("import configparser\n")
            file.write("from itertools import filterfalse\n")
            file.write("import time\n")
            file.write("from random import randint, choice, random\n")
            file.write("import threading\n")
            file.write("\n")

        while iterations < max_tries:
            if speed != 0:
                random_time = speed / randint(1, speed)
                time.sleep(random_time / 1000)
            try:
                # only run dpms two times
                if dpms_allowed > max_tries / 2:
                    thread_outputs = threading.Thread(
                        target=self.test_turn_off_on_outputs
                    )
                    thread_outputs.start()
                    dpms_allowed = 0
                dpms_allowed += 1
                random_function, args = choice(functions)

                # Write the function call with "sock." prefix to the file
                with open(results_file, "a") as file:
                    file.write(
                        f"sock.{random_function.__name__}({', '.join(map(repr, args))})\n"
                    )

                result = random_function(*args)
                iterations += 1
                print(result)
            except Exception as e:
                print(e)


addr = os.getenv("WAYFIRE_SOCKET")
sock = WayfireSocket(addr)
