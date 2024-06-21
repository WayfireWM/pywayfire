import socket
import json as js
import os
from wayfire.core.template import get_msg_template, geometry_to_json


class WayfireSocket:
    def __init__(self, socket_name, allow_manual_search=False):
        if socket_name is None:
            socket_name = os.getenv("WAYFIRE_SOCKET")

        self.socket_name = None

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

        # initialize it once for performance in some cases

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

    def query_output(self, output_id: int):
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

    def watch(self):
        method = "window-rules/events/watch"
        message = get_msg_template(method)
        return self.send_json(message)

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
        message["data"]["id"] = view_id
        message["data"]["geometry"] = geometry_to_json(x, y, w, h)
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
