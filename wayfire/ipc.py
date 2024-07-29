import socket
import json as js
import os
from typing import Any, List
from wayfire.core.template import get_msg_template, geometry_to_json


class WayfireSocket:
    def __init__(self, socket_name: str | None=None, allow_manual_search=False):
        if socket_name is None:
            socket_name = os.getenv("WAYFIRE_SOCKET")

        self.socket_name = None
        self.pending_events = []

        if socket_name is None and allow_manual_search:
            # the last item is the most recent socket file
            socket_list = sorted(
                [
                    os.path.join("/tmp", i)
                    for i in os.listdir("/tmp")
                    if "wayfire-wayland" in i
                ]
            )

            for candidate in socket_list:
                try:
                    self.connect_client(candidate)
                    self.socket_name = candidate
                    break
                except Exception:
                    pass

        elif socket_name is not None:
            self.connect_client(socket_name)
            self.socket_name = socket_name

        if self.socket_name is None:
            raise Exception("Failed to find a suitable Wayfire socket!")

    def connect_client(self, socket_name):
        self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.client.connect(socket_name)

    def close(self):
        self.client.close()

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

    def read_next_event(self):
        if self.pending_events:
            return self.pending_events.pop(0)
        return self.read_message()

    def create_headless_output(self, width, height):
        message = get_msg_template("wayfire/create-headless-output")
        message["data"]["width"] = width
        message["data"]["height"] = height
        return self.send_json(message)

    def destroy_headless_output(self, output_name=None, output_id=None):
        assert output_name is not None or output_id is not None
        message = get_msg_template("wayfire/destroy-headless-output")
        if output_name is not None:
            message["data"]["output"] = output_name
        else:
            message["data"]["output-id"] = output_id

        return self.send_json(message)

    def get_configuration(self):
        message = get_msg_template("wayfire/configuration")
        return self.send_json(message)

    def register_binding(
        self,
        binding: str,
        *,
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
        message["data"] = sanitized_options
        return self.send_json(message)

    def list_methods(self):
        query = get_msg_template("list-methods")
        response = self.send_json(query)
        return response["methods"]

    @staticmethod
    def _wayfire_plugin_from_method(method: str) -> str:
        if method.startswith("wf/alpha"):
            return "alpha"
        if method.startswith("wf/obs"):
            return "obs (wayfire-plugins-extra)"
        if method.startswith("wf/filters"):
            return "filters (soreau/filters)"
        if method.startswith("window-rules"):
            return "ipc-rules"
        if "/" not in method:
            return "unknown"

        return method.split("/")[0]

    def send_json(self, msg):
        if 'method' not in msg:
            raise Exception("Malformed json request: missing method!")

        data = js.dumps(msg).encode("utf8")
        header = len(data).to_bytes(4, byteorder="little")
        self.client.send(header)
        self.client.send(data)

        while True:
            response = self.read_message()
            if 'event' in response:
                self.pending_events.append(response)
                continue

            if "error" in response and response["error"] == "No such method found!":
                raise Exception(f"Method {msg['method']} is not available. \
                        Please ensure that the '{self._wayfire_plugin_from_method(msg['method'])}' Wayfire plugin is enabled. \
                        Once enabled, restart Wayfire to ensure that ipc was correctly loaded.")
            return response

    def get_output(self, output_id: int):
        message = get_msg_template("window-rules/output-info")
        message["data"]["id"] = output_id
        return self.send_json(message)

    def list_outputs(self):
        message = get_msg_template("window-rules/list-outputs")
        return self.send_json(message)

    def list_wsets(self):
        message = get_msg_template("window-rules/list-wsets")
        return self.send_json(message)

    def wset_info(self, id):
        message = get_msg_template("window-rules/wset-info")
        message["data"]["id"] = id
        return self.send_json(message)

    def watch(self, events: List[str] | None = None):
        method = "window-rules/events/watch"
        message = get_msg_template(method)
        if events is not None:
            message["data"]["events"] = events
        return self.send_json(message)

    def list_views(self, filter_mapped_toplevel=False) -> List[Any]:
        views = self.send_json(get_msg_template("window-rules/list-views"))
        if views is None:
            return []
        if filter_mapped_toplevel:
            return [v for v in views if v["mapped"] is True and v["role"] != "desktop-environment" and v["pid"] != -1]
        return views

    def configure_view(self, view_id: int, x: int, y: int, w: int, h: int, output_id = None):
        message = get_msg_template("window-rules/configure-view")
        message["data"]["id"] = view_id
        message["data"]["geometry"] = geometry_to_json(x, y, w, h)
        if output_id is not None:
            message["data"]["output_id"] = output_id
        return self.send_json(message)

    def assign_slot(self, view_id: int, slot: str):
        message = get_msg_template("grid/" + slot)
        message["data"]["view_id"] = view_id
        return self.send_json(message)

    def set_focus(self, view_id: int):
        message = get_msg_template("window-rules/focus-view")
        message["data"]["id"] = view_id
        return self.send_json(message)

    def get_view(self, view_id):
        message = get_msg_template("window-rules/view-info")
        message["data"]["id"] = view_id
        return self.send_json(message)["info"]

    def configure_input_device(self, id, enabled: bool):
        message = get_msg_template("input/configure-device")
        message["data"]["id"] = id
        message["data"]["enabled"] = enabled
        return self.send_json(message)

    def close_view(self, view_id):
        message = get_msg_template("window-rules/close-view")
        message["data"]["id"] = view_id
        return self.send_json(message)

    def get_focused_view(self):
        message = get_msg_template("window-rules/get-focused-view")
        return self.send_json(message)["info"]

    def get_focused_output(self):
        message = get_msg_template("window-rules/get-focused-output")
        message = self.send_json(message)
        if "info" in message:
            return message["info"]
        else:
            return message

    def set_view_fullscreen(self, view_id):
        message = get_msg_template("wm-actions/set-fullscreen")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = True
        self.send_json(message)

    def toggle_expo(self):
        message = get_msg_template("expo/toggle")
        self.send_json(message)

    def set_workspace(self, workspace, view_id=None, output_id=None):
        x, y = workspace["x"], workspace["y"]
        focused_output = self.get_focused_output()
        if output_id is None:
            output_id = focused_output["id"]

        message = get_msg_template("vswitch/set-workspace")
        message["data"]["x"] = x
        message["data"]["y"] = y
        message["data"]["output-id"] = output_id
        if view_id is not None:
            message["data"]["view-id"] = view_id
        return self.send_json(message)

    def toggle_showdesktop(self):
        message = get_msg_template("wm-actions/toggle_showdesktop")
        return self.send_json(message)

    def set_view_sticky(self, view_id, state):
        message = get_msg_template("wm-actions/set-sticky")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def send_view_to_back(self, view_id, state):
        message = get_msg_template("wm-actions/send-to-back")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def set_view_minimized(self, view_id, state):
        message = get_msg_template("wm-actions/set-minimized")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def scale_toggle(self):
        message = get_msg_template("scale/toggle")
        self.send_json(message)
        return True

    def cube_activate(self):
        message = get_msg_template("cube/activate")
        self.send_json(message)
        return True

    def cube_rotate_left(self):
        message = get_msg_template("cube/rotate_left")
        self.send_json(message)
        return True

    def cube_rotate_right(self):
        message = get_msg_template("cube/rorate_right")
        self.send_json(message)
        return True

    def scale_leave(self):
        # only works in the fork
        message = get_msg_template("scale/leave")
        self.send_json(message)
        return True

    def set_view_always_on_top(self, view_id: int, always_on_top: bool):
        message = get_msg_template("wm-actions/set-always-on-top")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = always_on_top
        return self.send_json(message)

    def set_view_alpha(self, view_id, alpha: float):
        message = get_msg_template("wf/alpha/set-view-alpha")
        message["data"] = {}
        message["data"]["view-id"] = view_id
        message["data"]["alpha"] = alpha
        return self.send_json(message)

    def get_view_alpha(self, view_id):
        message = get_msg_template("wf/alpha/get-view-alpha")
        message["data"]["view-id"] = view_id
        return self.send_json(message)

    def list_input_devices(self):
        message = get_msg_template("input/list-devices")
        return self.send_json(message)

    def get_tiling_layout(self, wset: int, x: int, y: int):
        method = "simple-tile/get-layout"
        msg = get_msg_template(method)
        msg["data"]["wset-index"] = wset
        msg["data"]["workspace"] = {}
        msg["data"]["workspace"]["x"] = x
        msg["data"]["workspace"]["y"] = y
        return self.send_json(msg)["layout"]

    def set_tiling_layout(self, wset: int, x: int, y: int, layout):
        msg = get_msg_template("simple-tile/set-layout")
        msg["data"]["wset-index"] = wset
        msg["data"]["workspace"] = {}
        msg["data"]["workspace"]["x"] = x
        msg["data"]["workspace"]["y"] = y
        msg["data"]["layout"] = layout
        return self.send_json(msg)
