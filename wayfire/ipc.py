import socket
import json as js
import os
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

    def close(self):
        self.client.close()

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

    def run_cmd(self, cmd):
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

    def set_focus(self, view_id: int):
        message = get_msg_template("window-rules/focus-view")
        if message is None:
            return
        message["data"]["id"] = view_id
        return self.send_json(message)

    def get_focused_view(self):
        message = get_msg_template("window-rules/get-focused-view")
        if message is None:
            return
        return self.send_json(message)["info"]

    def get_focused_output(self):
        message = get_msg_template("window-rules/get-focused-output")
        if message is None:
            return None
        message = self.send_json(message)
        if "info" in message:
            return message["info"]
        else:
            return message

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

    def close_view(self, view_id):
        message = get_msg_template("window-rules/close-view")
        if message is None:
            return
        message["data"]["id"] = view_id
        return self.send_json(message)

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

    def configure_input_device(self, id, enabled: bool):
        message = get_msg_template("input/configure-device")
        if message is None:
            return
        message["data"]["id"] = id
        message["data"]["enabled"] = enabled
        return self.send_json(message)


addr = os.getenv("WAYFIRE_SOCKET")
sock = WayfireSocket(addr)
