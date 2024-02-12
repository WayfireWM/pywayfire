import socket
import json as js


def get_msg_template(method: str):
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

    def send_json(self, msg):
        data = js.dumps(msg).encode("utf8")
        header = len(data).to_bytes(4, byteorder="little")
        self.client.send(header)
        self.client.send(data)
        return self.read_message()

    def close(self):
        self.client.close()

    def watch(self):
        message = get_msg_template("window-rules/events/watch")
        return self.send_json(message)

    def query_output(self, output_id: int):
        message = get_msg_template("window-rules/output-info")
        message["data"]["id"] = output_id
        return self.send_json(message)

    def list_views(self):
        return self.send_json(get_msg_template("window-rules/list-views"))

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

    def get_focused_view(self):
        message = get_msg_template("window-rules/get-focused-view")
        return self.send_json(message)["info"]

    def get_focused_view_info(self):
        id = self.get_focused_view_id()
        return [i for i in self.list_views() if i["id"] == id][0]

    def get_focused_view_pid(self):
        view_id = self.get_focused_view()["id"]
        return self.get_view_pid(view_id)

    def is_focused_view_fullscreen(self):
        return self.get_focused_view()["fullscreen"]

    def get_focused_view_role(self):
        return self.get_focused_view_info()["role"]

    def get_focused_view_tiled(self):
        return self.get_focused_view()["tiled"]

    def get_focused_view_bbox(self):
        return self.get_focused_view()["bbox"]

    def get_focused_view_layer(self):
        return self.get_focused_view()["layer"]

    def get_focused_view_id(self):
        return self.get_focused_view()["id"]

    def get_focused_view_output(self):
        return self.get_focused_view()["output"]

    def get_focused_view_title(self):
        return self.get_focused_view()["title"]

    def get_focused_view_type(self):
        return self.get_focused_view()["type"]

    def get_focused_view_app_id(self):
        return self.get_focused_view()["app-id"]

    def get_focused_output(self):
        focused_view = self.get_focused_view()
        output_id = focused_view["info"]["output"]
        return self.query_output(output_id)

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
        workspaces_coordinates = self.total_workspaces()
        coordinates_to_find = [
            i for i in workspaces_coordinates.values() if [y, x] == i
        ][0]
        total_workspaces = 9
        rows = int(total_workspaces**0.5)
        cols = (total_workspaces + rows - 1) // rows
        workspace_number = self.coordinates_to_number(rows, cols, coordinates_to_find)
        return workspace_number

    def get_active_workspace_info(self):
        return self.get_focused_output()["workspace"]

    def get_focused_output_name(self):
        return self.get_focused_output()["name"]

    def get_focused_output_id(self):
        return self.get_focused_output()["id"]

    def get_focused_output_geometry(self):
        return self.get_focused_output()["geometry"]

    def get_focused_output_workarea(self):
        return self.get_focused_output()["workarea"]

    def set_always_on_top(self, view_id: int, always_on_top: bool):
        message = get_msg_template("wm-actions/set-always-on-top")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = always_on_top
        return self.send_json(message)

    def set_view_alpha(self, view_id: int, alpha: float):
        message = get_msg_template("wf/alpha/set-view-alpha")
        message["data"] = {}
        message["data"]["view-id"] = view_id
        message["data"]["alpha"] = alpha
        return self.send_json(message)

    def list_input_devices(self):
        message = get_msg_template("input/list-devices")
        return self.send_json(message)

    def get_view_pid(self, view_id):
        message = get_msg_template("window-rules/get-view-pid")
        message["data"]["id"] = view_id
        return self.send_json(message)

    def get_view(self, view_id):
        message = get_msg_template("window-rules/view-info")
        message["data"]["id"] = view_id
        return self.send_json(message)["info"]

    def get_view_info(self, view_id):
        info = [i for i in self.list_views() if i["id"] == view_id]
        if info:
            return info[0]
        else:
            return

    def get_view_output(self, view_id):
        return self.get_view(view_id)["output"]

    def is_view_fullscreen(self, view_id):
        return self.get_view(view_id)["fullscreen"]

    def is_view_focusable(self, view_id):
        return self.get_view(view_id)["focusable"]

    def get_view_geometry(self, view_id):
        return self.get_view(view_id)["geometry"]

    def is_view_minimized(self, view_id):
        return self.get_view(view_id)["minimized"]

    def get_view_tiled_edges(self, view_id):
        return self.get_view(view_id)["tiled_edges"]

    def get_view_title(self, view_id):
        return self.get_view(view_id)["title"]

    def get_view_type(self, view_id):
        return self.get_view(view_id)["type"]

    def get_view_app_id(self, view_id):
        return self.get_view(view_id)["app-id"]

    def get_view_role(self, view_id):
        return self.get_view_info(view_id)["role"]

    def get_view_bbox(self, view_id):
        return self.get_view_info(view_id)["bbox"]

    def get_view_layer(self, view_id):
        return self.get_view_info(view_id)["layer"]

    def total_workspaces(self):
        winfo = self.get_active_workspace_info()
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

    def set_workspace(self, workspace_number, view_id=None):
        workspaces_coordinates = self.total_workspaces()
        y, x = workspaces_coordinates[workspace_number]
        focused_view = self.get_focused_view()
        output_id = focused_view["info"]["output"]
        message = get_msg_template("vswitch/set-workspace")
        message["data"]["x"] = x
        message["data"]["y"] = y
        message["data"]["output-id"] = output_id
        if view_id is not None:
            message["data"]["view-id"] = view_id
        self.send_json(message)

    def configure_input_device(self, id, enabled: bool):
        message = get_msg_template("input/configure-device")
        message["data"]["id"] = id
        message["data"]["enabled"] = enabled
        return self.send_json(message)
