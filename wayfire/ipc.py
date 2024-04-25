import socket
import json as js
import os
from itertools import filterfalse
import time


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
        self.client = None
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
                    self.connect_client(sock)
                    break
                except Exception as e:
                    print(e)
        else:
            # initialize it once for performance in some cases
            self.connect_client(socket_name)
            self.methods = self.list_methods()
            self.socket_name = socket_name

    def connect_client(self, socket_name):
        self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.client.connect(socket_name)

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

    def create_wayland_output(self):
        message = get_msg_template("stipc/create_wayland_output", self.methods)
        self.send_json(message)

    def create_headless_output(self, width, height):
        message = get_msg_template("wayfire/create-headless-output")
        message["data"]["width"] = width
        message["data"]["height"] = height
        return self.send_json(message)

    def destroy_headless_output(self, output_name=None, output_id=None):
        assert output_name is not None or output_id is not None
        message = get_msg_template("wayfire/destroy-headless-output", self.methods)
        if output_name is not None:
            message["data"]["output"] = output_name
        else:
            message["data"]["output-id"] = output_id

        return self.send_json(message)

    def register_binding(
        self,
        binding: str,
        call_method=None,
        call_data=None,
        command=None,
        mode=None,
        exec_always=False,
    ):
        message = get_msg_template("command/register-binding")
        message["data"]["binding"] = binding
        message["data"]["exec-always"] = exec_always
        if mode and mode != "press" and mode != "normal":
            message["data"]["mode"] = mode

        if call_method is not None:
            message["data"]["call-method"] = call_method
        if call_data is not None:
            message["data"]["call-data"] = call_data
        if command is not None:
            message["data"]["command"] = command

        return self.send_json(message)

    def unregister_binding(self, binding_id: int):
        message = get_msg_template("command/unregister-binding")
        message["data"]["binding-id"] = binding_id
        return self.send_json(message)

    def clear_bindings(self):
        message = get_msg_template("command/clear-bindings")
        return self.send_json(message)

    def get_option_value(self, option):
        message = get_msg_template("wayfire/get-config-option")
        message["data"]["option"] = option
        return self.send_json(message)

    def set_option_values(self, options):
        sanitized_options = {}
        for key, value in options.items():
            if "/" in key:
                sanitized_options[key] = value
            else:
                for option_name, option_value in value.items():
                    sanitized_options[key + "/" + option_name] = option_value

        message = get_msg_template("wayfire/set-config-options")
        print(js.dumps(sanitized_options, indent=4))
        message["data"] = sanitized_options
        return self.send_json(message)

    def layout_views(self, layout):
        views = self.list_views()
        method = "stipc/layout_views"
        message = get_msg_template(method, self.methods)
        msg_layout = []

        for ident in layout:
            x, y, w, h = layout[ident][:4]
            for v in views:
                if v["app-id"] == ident or v["title"] == ident or v["id"] == ident:
                    layout_for_view = {
                        "id": v["id"],
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h,
                    }
                    if len(layout[ident]) == 5:
                        layout_for_view["output"] = layout[ident][-1]
                    msg_layout.append(layout_for_view)

        message["data"]["views"] = msg_layout
        return self.send_json(message)

    def set_touch(self, id: int, x: int, y: int):
        method = "stipc/touch"
        message = get_msg_template(method, self.methods)
        message["data"]["finger"] = id
        message["data"]["x"] = x
        message["data"]["y"] = y
        return self.send_json(message)

    def tablet_tool_proximity(self, x, y, prox_in):
        method = "stipc/tablet/tool_proximity"
        message = get_msg_template(method, self.methods)
        message["data"]["x"] = x
        message["data"]["y"] = y
        message["data"]["proximity_in"] = prox_in
        return self.send_json(message)

    def tablet_tool_tip(self, x, y, state):
        method = "stipc/tablet/tool_tip"
        message = get_msg_template(method, self.methods)
        message["data"]["x"] = x
        message["data"]["y"] = y
        message["data"]["state"] = state
        return self.send_json(message)

    def tablet_tool_axis(self, x, y, pressure):
        method = "stipc/tablet/tool_axis"
        message = get_msg_template(method, self.methods)
        message["data"]["x"] = x
        message["data"]["y"] = y
        message["data"]["pressure"] = pressure
        return self.send_json(message)

    def tablet_tool_button(self, btn, state):
        method = "stipc/tablet/tool_button"
        message = get_msg_template(method, self.methods)
        message["data"]["button"] = btn
        message["data"]["state"] = state
        return self.send_json(message)

    def tablet_pad_button(self, btn, state):
        method = "stipc/tablet/pad_button"
        message = get_msg_template(method, self.methods)
        message["data"]["button"] = btn
        message["data"]["state"] = state
        return self.send_json(message)

    def release_touch(self, id: int):
        method = "stipc/touch_release"
        message = get_msg_template(method, self.methods)
        message["data"]["finger"] = id
        return self.send_json(message)

    def destroy_wayland_output(self, output: str):
        method = "stipc/destroy_wayland_output"
        message = get_msg_template(method, self.methods)
        message["data"]["output"] = output
        return self.send_json(message)

    def delay_next_tx(self):
        method = "stipc/delay_next_tx"
        message = get_msg_template(method, self.methods)
        return self.send_json(message)

    def xwayland_pid(self):
        method = "stipc/get_xwayland_pid"
        message = get_msg_template(method, self.methods)
        return self.send_json(message)

    def xwayland_display(self):
        method = "stipc/get_xwayland_display"
        message = get_msg_template(method, self.methods)
        return self.send_json(message)

    def list_methods(self):
        query = get_msg_template("list-methods")
        response = self.send_json(query)
        data = js.dumps(response["methods"], indent=4)
        data = data.replace("'", '"')
        data_list = js.loads(data)
        return data_list

    def send_json(self, msg):
        data = js.dumps(msg).encode("utf8")
        header = len(data).to_bytes(4, byteorder="little")
        self.client.send(header)
        self.client.send(data)
        return self.read_message()

    # this is not a socket IPC thing, but since the compositor developer won't implement
    # dpms for ipc, this tool just works fine
    # this was not intended to be here, but anyways, lets use it

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

    def press_key(self, keys: str, timeout=0):
        modifiers = {
            "A": "KEY_LEFTALT",
            "S": "KEY_LEFTSHIFT",
            "C": "KEY_LEFTCTRL",
            "W": "KEY_LEFTMETA",
        }
        key_combinations = keys.split("-")

        for modifier in key_combinations[:-1]:
            if modifier in modifiers:
                self.set_key_state(modifiers[modifier], True)

        if timeout >= 1:
            time.sleep(timeout / 1000)

        actual_key = key_combinations[-1]
        self.set_key_state(actual_key, True)

        if timeout >= 1:
            time.sleep(timeout / 1000)

        self.set_key_state(actual_key, False)

        for modifier in key_combinations[:-1]:
            if modifier in modifiers:
                self.set_key_state(modifiers[modifier], False)

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

    def list_outputs_names(self):
        outputs = self.list_outputs()
        if outputs:
            return [i["name"] for i in outputs]

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

    def get_active_workspace(self):
        data = self.get_active_workspace_info()
        if data:
            x = data["x"]
            y = data["y"]
            return {"x": x, "y": y}

    def go_workspace_set_focus(self, view_id):
        workspace = self.get_view_workspace(view_id)
        active_workspace = self.get_active_workspace()
        if workspace:
            if active_workspace != workspace:
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

    def has_ouput_fullscreen_view(self, output_id):
        # any fullscreen doesn't matter from what workspace
        list_views = self.list_views()
        if not list_views:
            return
        if any(
            True
            for i in list_views
            if i["fullscreen"] is True and i["output-id"] == output_id
        ):
            return True

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
            return None
        message = self.send_json(message)
        if "info" in message:
            return message["info"]
        else:
            return message

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

    def get_output_id_by_name(self, output_name):
        for output in self.list_outputs():
            if output["name"] == output_name:
                return output["id"]

    def get_output_name_by_id(self, output_id):
        for output in self.list_outputs():
            if output["id"] == output_id:
                return output["name"]

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

    def get_view_output_name(self, view_id):
        view = self.get_view(view_id)
        if view is not None:
            return view.get("output-name")
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

    def find_view_by_pid(self, pid):
        lviews = self.list_views()
        if not lviews:
            return
        view = [view for view in lviews if view["pid"] == pid]
        if view:
            return view[0]

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

    def get_workspace_from_view(self, view_id):
        ws_with_views = self.get_workspaces_with_views()
        for ws in ws_with_views:
            if ws["view-id"] == view_id:
                return {"x": ws["x"], "y": ws["y"]}

    def has_workspace_views(self, ws):
        ws_with_views = self.get_workspaces_with_views()
        for wwv in ws_with_views:
            del wwv["view-id"]
            if wwv == ws:
                return True
        return False

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
        return self.send_json(message)

    def find_view_middle_cursor_position(self, view_geometry, monitor_geometry):
        # Calculate the middle position of the view
        view_middle_x = view_geometry["x"] + view_geometry["width"] // 2
        view_middle_y = view_geometry["y"] + view_geometry["height"] // 2

        # Calculate the offset from the monitor's top-left corner
        cursor_x = monitor_geometry["x"] + view_middle_x
        cursor_y = monitor_geometry["y"] + view_middle_y

        return cursor_x, cursor_y

    def move_cursor_middle(self, view_id):
        view = self.get_view(view_id)
        output_id = view["output-id"]
        view_geometry = view["geometry"]
        output_geometry = self.query_output(output_id)["geometry"]
        cursor_x, cursor_y = self.find_view_middle_cursor_position(
            view_geometry, output_geometry
        )
        self.move_cursor(cursor_x, cursor_y)

    def focus_next_view_from_active_workspace(self):
        views = self.get_views_from_active_workspace()
        if views:
            self.go_workspace_set_focus(views[0])

    def configure_input_device(self, id, enabled: bool):
        message = get_msg_template("input/configure-device")
        if message is None:
            return
        message["data"]["id"] = id
        message["data"]["enabled"] = enabled
        return self.send_json(message)


addr = os.getenv("WAYFIRE_SOCKET")
sock = WayfireSocket(addr)
