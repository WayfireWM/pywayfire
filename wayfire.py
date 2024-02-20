import socket
import json as js
import os
from subprocess import call


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
                except:
                    pass
        else:
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

    # this is not a socket IPC thing, but since the compositor developer won't implement
    # dpms for ipc, this tool just works fine
    # this was not intended to be here, but anyways, lets use it
    def dpms(self, state, output_name):
        if state == "on":
            call("wlopm --on {}".format(output_name).split())
        if state == "off":
            call("wlopm --off {}".format(output_name).split())
        if state == "toggle":
            call("wlopm --toggle {}".format(output_name).split())

    def close(self):
        self.client.close()

    def screenshot(self, id, filename):
        capture = get_msg_template("view-shot/capture")
        capture["data"]["view-id"] = id
        capture["data"]["file"] = filename
        self.send_json(capture)

    def watch(self):
        method = "window-rules/events/watch"
        message = get_msg_template(method)
        return self.send_json(message)

    def query_output(self, output_id: int):
        message = get_msg_template("window-rules/output-info")
        message["data"]["id"] = output_id
        return self.send_json(message)

    def scale_toggle(self):
        message = get_msg_template("scale/toggle")
        self.send_json(message)
        return True

    def scale_leave(self):
        # only works in the fork
        message = get_msg_template("scale/leave")
        self.send_json(message)
        return True

    def list_views(self):
        list_views = self.send_json(get_msg_template("window-rules/list-views"))
        clean_list = []
        for view in list_views:
            if view["role"] == "desktop-environment":
                continue
            if view["app-id"] == "nil":
                continue
            if view["mapped"] is False:
                continue
            if view["pid"] == -1:
                continue

            clean_list.append(view)
        return clean_list

    def focused_output_views(self):
        list_views = self.list_views()
        focused_output = self.get_focused_output()
        output_views = [
            view for view in list_views if view["output-id"] == focused_output["id"]
        ]
        return output_views

    def list_pids(self):
        list_views = self.list_views()
        list_pids = []
        for view in list_views:
            list_pids.append(view["pid"])
        return list_pids

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
        view = self.get_focused_view()
        if view is not None:
            view_id = self.get_focused_view()
            if view_id is not None:
                view_id = view_id["id"]
                return self.get_view_pid(view_id)

    def is_focused_view_fullscreen(self):
        return self.get_focused_view()["fullscreen"]

    def get_focused_view_role(self):
        return self.get_focused_view_info()["role"]

    def get_focused_view_bbox(self):
        return self.get_focused_view()["bbox"]

    def get_focused_view_layer(self):
        return self.get_focused_view()["layer"]

    def get_focused_view_id(self):
        return self.get_focused_view()["id"]

    def get_focused_view_output(self):
        return self.get_focused_view()["output-id"]

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
        focused_view = self.get_focused_view()
        output_id = focused_view["output-id"]
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
        view = self.get_view(view_id)
        if view is not None:
            pid = view["pid"]
            return pid

    def get_view(self, view_id):
        message = get_msg_template("window-rules/view-info")
        message["data"]["id"] = view_id
        return self.send_json(message)["info"]

    def go_next_workspace(self):
        next = 0
        current_workspace = self.get_active_workspace_number()
        if current_workspace == 2:
            next = 1
        else:
            next = 2

        self.set_workspace(next)
        return True

    def iterate_dicts(self, dicts):
        index = 0
        length = len(dicts)
        while True:
            yield dicts[index]
            index = (index + 1) % length

    def get_next_workspace(self, workspaces, active_workspace):
        # Find the index of the active workspace in the list
        active_index = None

        # Sort the list based on the 'x' and 'y' keys
        workspaces.sort(key=lambda d: (d["x"], d["y"]))

        for i, workspace in enumerate(workspaces):
            if workspace == active_workspace:
                active_index = i
                break

        if active_index is None:
            raise ValueError("Active workspace not found in the list of workspaces.")

        # Calculate the index of the next workspace cyclically
        next_index = (active_index + 1) % len(workspaces)

        # Return the next workspace

        return workspaces[next_index]

    def go_next_workspace_with_views(self):
        workspaces = self.get_workspaces_with_views()
        active_workspace = self.get_focused_output()["workspace"]
        active_workspace = {"x": active_workspace["x"], "y": active_workspace["y"]}
        next_ws = self.get_next_workspace(workspaces, active_workspace)
        print(next_ws)
        self.set_workspace(next_ws)

    def go_previous_workspace(self):
        previous = 1
        current_workspace = self.get_active_workspace_number()
        if current_workspace == 1:
            previous = 9
        else:
            previous = current_workspace - 1

        self.set_workspace(previous)
        return True

    def get_view_info(self, view_id):
        info = [i for i in self.list_views() if i["id"] == view_id]
        if info:
            return info[0]
        else:
            return

    def get_view_output_id(self, view_id):
        return self.get_view(view_id)["output-id"]

    def is_view_fullscreen(self, view_id):
        return self.get_view(view_id)["fullscreen"]

    def is_view_focusable(self, view_id):
        return self.get_view(view_id)["focusable"]

    def get_view_geometry(self, view_id):
        return self.get_view(view_id)["geometry"]

    def is_view_minimized(self, view_id):
        return self.get_view(view_id)["minimized"]

    def is_view_maximized(self, view_id):
        output_id = self.get_view_output_id(view_id)
        output = self.query_output(output_id)
        workarea = output["workarea"]
        width, height = output["geometry"]["width"], output["geometry"]["height"]
        view = self.get_view(view_id)
        g = view["geometry"]
        vw = round(g["width"] - workarea["x"])
        vh = round(g["height"] - workarea["y"])
        ow = round(width - workarea["x"])
        oh = round(height - workarea["y"])
        if vw == ow and vh == oh:
            return True
        else:
            return False

    def get_view_tiled_edges(self, view_id):
        return self.get_view(view_id)["tiled-edges"]

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

    def maximize_focused(self):
        view = self.get_focused_view()
        self.assign_slot(view["id"], "slot_c")

    def toggle_expo(self):
        message = get_msg_template("expo/toggle")
        self.send_json(message)

    def maximize(self, view_id):
        return self.assign_slot(view_id, "slot_c")

    def maximize_all_views_from_active_workspace(self):
        for view_id in self.get_views_from_active_workspace():
            self.maximize(view_id)

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

    def get_workspaces_with_views(self):
        focused_output = self.get_focused_output()
        ws = self.get_active_workspace_info()
        monitor = focused_output["geometry"]
        monitor_h = monitor["height"]
        monitor_w = monitor["width"]
        ws_with_views = []
        for view in self.focused_output_views():
            x = view["geometry"]["x"]
            y = view["geometry"]["y"]

            pos_x, pos_y = ws["x"], ws["y"]
            ws_rectangle_x, ws_rectangle_y = 0, 0

            view_width_fraction = 1
            # cannot divide by zero
            if x != 0:
                view_width_fraction = round(monitor_w / abs(x))

            if x == 0:
                pos_x = ws["x"]

            else:
                ws_rectangle_x = round((view_width_fraction + ws["x"]) * monitor_w)
                pos_x = sorted([ws_rectangle_x, x])
                pos_x.reverse()
                pos_x = round(pos_x[0] / pos_x[1])
                if ws["x"] < 0 and abs(ws["x"]) == monitor_w:
                    pos_x = 0
                if pos_x < monitor_w and pos_x > 2:
                    pos_x = ws["x"]
                if pos_x <= 0:
                    pos_x = abs(pos_x + ws["x"])

            view_height_fraction = 1
            # cannot divide by zero
            if y != 0:
                view_height_fraction = round(monitor_h / abs(y))

            if y == 0:
                pos_y = ws["y"]
            else:
                ws_rectangle_y = round((view_height_fraction + ws["y"]) * monitor_h)
                pos_y = sorted([ws_rectangle_y, y])
                pos_y.reverse()
                pos_y = round(pos_y[0] / pos_y[1])
                if ws["y"] < 0 and abs(ws["y"]) == monitor_h:
                    pos_x = 0
                if pos_y < monitor_h and pos_y > 2:
                    pos_y = ws["y"]
                if pos_y <= 0:
                    pos_y = abs(pos_y + ws["y"])

            # if the view is the focused window we already have the coordinates
            if self.get_focused_view()["id"] == view["id"]:
                pos_x = ws["x"]
                pos_y = ws["y"]

            if x < 0:
                pos_x = 0
            if y < 0:
                pos_y = 0
            ws_v = {"x": pos_x, "y": pos_y, "view-id": view["id"]}
            if ws_v not in ws_with_views:
                ws_with_views.append(ws_v)
        return ws_with_views

    def get_views_from_active_workspace(self):
        aw = self.get_active_workspace_info()
        return [
            i["view-id"]
            for i in self.get_workspaces_with_views()
            if i["x"] == aw["x"] and i["y"] == aw["y"]
        ]

    def set_view_top_left(self, view_id):
        output_id = self.get_view_output_id(view_id)
        output = self.query_output(output_id)
        workarea = output["workarea"]
        width, height = output["geometry"]["width"], output["geometry"]["height"]
        self.configure_view(
            view_id, workarea["x"], workarea["y"], round(width / 2), round(height / 2)
        )

    def set_view_top_right(self, view_id):
        output_id = self.get_view_output_id(view_id)
        output = self.query_output(output_id)
        workarea = output["workarea"]
        width, height = output["geometry"]["width"], output["geometry"]["height"]
        self.configure_view(
            view_id,
            round(width / 2),
            workarea["y"],
            round(width / 2),
            round(round(height / 2) - workarea["y"]),
        )

    def set_view_bottom_left(self, view_id):
        output_id = self.get_view_output_id(view_id)
        output = self.query_output(output_id)
        workarea = output["workarea"]
        width, height = output["geometry"]["width"], output["geometry"]["height"]
        self.configure_view(
            view_id,
            workarea["x"],
            round(height / 2),
            round(width / 2),
            round(round(height / 2) - workarea["y"]),
        )

    def set_view_left(self, view_id):
        output_id = self.get_view_output_id(view_id)
        output = self.query_output(output_id)
        workarea = output["workarea"]
        width, height = output["geometry"]["width"], output["geometry"]["height"]
        self.configure_view(
            view_id,
            workarea["x"],
            workarea["y"],
            round(width / 2),
            round(height - workarea["y"]),
        )

    def set_view_right(self, view_id):
        output_id = self.get_view_output_id(view_id)
        output = self.query_output(output_id)
        workarea = output["workarea"]
        width, height = output["geometry"]["width"], output["geometry"]["height"]
        self.configure_view(
            view_id,
            round(round(width / 2) - workarea["x"]),
            workarea["y"],
            round(width / 2),
            round(height - workarea["y"]),
        )

    def set_view_bottom_right(self, view_id):
        output_id = self.get_view_output_id(view_id)
        output = self.query_output(output_id)
        workarea = output["workarea"]
        width, height = output["geometry"]["width"], output["geometry"]["height"]
        self.configure_view(
            view_id,
            round(round(width / 2) - workarea["x"]),
            round(round(height / 2) - workarea["y"]),
            round(width / 2),
            round(height / 2),
        )

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
        positions = ["top-left", "top-right", "bottom-right", "bottom-left"]
        aw = self.get_views_from_active_workspace()
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
        for position in positions:
            self.tilling_view_position(position, aw[index])
            if index >= 0:
                index -= 1
            # just in case there is a bug that it countinues bellow -1
            if index <= -1:
                break

    def tilling_toggle(self):
        focused_id = self.get_focused_view()["id"]
        if self.is_view_maximized(focused_id):
            self.maximize_all_views_from_active_workspace()
            self.tilling()
        else:
            self.maximize_all_views_from_active_workspace()

    def set_workspace(self, workspace, view_id=None):
        x, y = workspace["x"], workspace["y"]
        focused_output = self.get_focused_output()
        output_id = focused_output["id"]
        message = get_msg_template("vswitch/set-workspace")
        message["data"]["x"] = x
        message["data"]["y"] = y
        message["data"]["output-id"] = output_id
        if view_id is not None:
            message["data"]["view-id"] = view_id
        self.send_json(message)
        return True

    def configure_input_device(self, id, enabled: bool):
        message = get_msg_template("input/configure-device")
        message["data"]["id"] = id
        message["data"]["enabled"] = enabled
        return self.send_json(message)
