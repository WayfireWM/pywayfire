import socket
import json as js
import os
from subprocess import call
from itertools import cycle
import dbus
import configparser


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
        if state == "off" and output_name == None:
            outputs = [output["name"] for output in self.list_outputs()]
            for output in outputs:
                call("wlopm --off {}".format(output).split())
        if state == "on" and output_name == None:
            outputs = [output["name"] for output in self.list_outputs()]
            for output in outputs:
                call("wlopm --on {}".format(output).split())
        if state == "on":
            call("wlopm --on {}".format(output_name).split())
        if state == "off":
            call("wlopm --off {}".format(output_name).split())
        if state == "toggle":
            call("wlopm --toggle {}".format(output_name).split())

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
        self.xdg_open("/tmp/out.png")

    def screenshot_focused_monitor(self):
        output = self.get_focused_output()
        name = output["name"]
        output_file = "/tmp/output-{0}.png".format(name)
        call(["grim", "-o", name, output_file])

    def screenshot(self, id, filename):
        capture = get_msg_template("view-shot/capture")
        capture["data"]["view-id"] = id
        capture["data"]["file"] = filename
        self.send_json(capture)

    def move_cursor(self, x: int, y: int):
        message = get_msg_template("stipc/move_cursor")
        message["data"]["x"] = x
        message["data"]["y"] = y
        return self.send_json(message)

    def click_button(self, btn_with_mod: str, mode: str):
        """
        btn_with_mod can be S-BTN_LEFT/BTN_RIGHT/etc. or just BTN_LEFT/...
        If S-BTN..., then the super modifier will be pressed as well.
        mode is full, press or release
        """
        message = get_msg_template("stipc/feed_button")
        message["data"]["mode"] = mode
        message["data"]["combo"] = btn_with_mod
        return self.send_json(message)

    def watch(self):
        method = "window-rules/events/watch"
        message = get_msg_template(method)
        return self.send_json(message)

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

    def set_key_state(self, key: str, state: bool):
        message = get_msg_template("stipc/feed_key")
        message["data"]["key"] = key
        message["data"]["state"] = state
        return self.send_json(message)

    def run(self, cmd):
        message = get_msg_template("stipc/run")
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
        message = get_msg_template("wm-actions/toggle_showdesktop")
        return self.send_json(message)

    def set_sticky(self, view_id, state):
        message = get_msg_template("wm-actions/set-sticky")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def send_to_back(self, view_id, state):
        message = get_msg_template("wm-actions/send-to-back")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def set_minimized(self, view_id, state):
        message = get_msg_template("wm-actions/set-minimized")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
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

    def set_view_always_on_top(self, view_id: int, always_on_top: bool):
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

        print(unique_workspaces)

        for i, workspace in enumerate(unique_workspaces):
            if workspace == active_workspace:
                active_index = i
                break

        if active_index is None:
            raise ValueError("Active workspace not found in the list of workspaces.")

        # Calculate the index of the next workspace cyclically
        next_index = (active_index + 1) % len(unique_workspaces)

        # Return the next workspace
        return unique_workspaces[next_index]

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

    def close_view(self, view_id):
        message = get_msg_template("window-rules/close-view")
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
        if self.get_view_tiled_edges(view_id) == 15:
            return True
        else:
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

    def fullscreen_focused(self):
        view = self.get_focused_view()
        self.set_fullscreen(view["id"])

    def set_fullscreen(self, view_id):
        message = get_msg_template("wm-actions/set-fullscreen")
        print(message)
        message["data"]["view_id"] = view_id
        message["data"]["state"] = True
        self.send_json(message)

    def toggle_expo(self):
        message = get_msg_template("expo/toggle")
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
        print(msg)

    def enable_input_device(self, args):
        device_id = self.find_device_id(args)
        msg = self.configure_input_device(device_id, True)
        print(msg)

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
        return [
            i["view-id"]
            for i in self.get_workspaces_with_views()
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
            print(position, aw[index])
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


addr = os.getenv("WAYFIRE_SOCKET")
sock = WayfireSocket(addr)
