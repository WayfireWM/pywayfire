import socket
import json as js
import requests
import os
from subprocess import call, Popen, check_output, run, PIPE
from itertools import cycle
import dbus
import configparser
from configparser import ConfigParser
from itertools import filterfalse
import time
from random import randint, choice, random, sample
import threading
import psutil
import pkg_resources

from ctypes import CDLL

CDLL("libgtk4-layer-shell.so")


def check_geometry(x: int, y: int, width: int, height: int, obj) -> bool:
    if (
        obj["x"] == x
        and obj["y"] == y
        and obj["width"] == width
        and obj["height"] == height
    ):
        return True
    return False


def extract_socket_name(file_path):
    with open(file_path, "r") as file:
        for line in file:
            if "Using socket name" in line:
                parts = line.split()
                return parts[-1].strip()


def find_wayland_display(pid):
    try:
        process = psutil.Process(pid)
        for fd in process.open_files():
            if "wayland-" in fd.path:
                display = fd.path.split("-")[-1]
                if "." in display:
                    display = display.split(".")[0]
                return f"wayland-{display}"
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    return None


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

    def dpms_status(self):
        status = check_output(["wlopm"]).decode().strip().split("\n")
        dpms_status = {}
        for line in status:
            line = line.split()
            dpms_status[line[0]] = line[1]
        return dpms_status

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

    def toggle_minimize_from_app_id(self, app_id):
        list_views = sock.list_views()
        if not list_views:
            return
        ids = [i["id"] for i in list_views if i["app-id"] == app_id]
        for id in ids:
            if sock.is_view_minimized(id):
                sock.set_minimized(id, False)
            else:
                sock.set_minimized(id, True)

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

    def get_wayfire_ini_path(self):
        wayfire_ini_path = os.getenv("WAYFIRE_CONFIG_FILE")
        if wayfire_ini_path:
            return wayfire_ini_path
        else:
            print("Error: WAYFIRE_CONFIG_FILE environment variable is not set.")
            return None

    def enable_plugin(self, plugin_name):
        wayfire_ini_path = self.get_wayfire_ini_path()
        if not wayfire_ini_path:
            return

        config = ConfigParser()
        config.read(wayfire_ini_path)

        if "core" not in config:
            config["core"] = {}

        plugins = config["core"].get("plugins", "").split()

        if plugin_name in plugins:
            print(f"Plugin '{plugin_name}' is already enabled in wayfire.ini.")
            return

        plugins.append(plugin_name)
        config["core"]["plugins"] = " ".join(plugins)

        with open(wayfire_ini_path, "w") as configfile:
            config.write(configfile)

        print(f"Plugin '{plugin_name}' enabled successfully in wayfire.ini.")

    def disable_plugin(self, plugin_name):
        wayfire_ini_path = self.get_wayfire_ini_path()
        if not wayfire_ini_path:
            return

        config = ConfigParser()
        config.read(wayfire_ini_path)

        if "core" not in config:
            print("Error: 'core' section not found in wayfire.ini.")
            return

        plugins = config["core"].get("plugins", "").split()

        if plugin_name not in plugins:
            print(f"Plugin '{plugin_name}' is not enabled in wayfire.ini.")
            return

        plugins.remove(plugin_name)
        config["core"]["plugins"] = " ".join(plugins)

        with open(wayfire_ini_path, "w") as configfile:
            config.write(configfile)

        print(f"Plugin '{plugin_name}' disabled successfully in wayfire.ini.")

    def list_plugins(self):
        official_url = "https://github.com/WayfireWM/wayfire/tree/master/metadata"
        extra_url = (
            "https://github.com/WayfireWM/wayfire-plugins-extra/tree/master/metadata"
        )

        official_response = requests.get(official_url)
        extra_response = requests.get(extra_url)

        if official_response.status_code != 200 or extra_response.status_code != 200:
            print("Failed to fetch content from one or both repositories.")
            return {}

        official_html_content = official_response.text
        extra_html_content = extra_response.text

        official_start_index = official_html_content.find(
            '<script type="application/json" data-target="react-app.embeddedData">'
        )
        extra_start_index = extra_html_content.find(
            '<script type="application/json" data-target="react-app.embeddedData">'
        )

        official_end_index = official_html_content.find(
            "</script>", official_start_index
        )
        extra_end_index = extra_html_content.find("</script>", extra_start_index)

        official_json_data = official_html_content[
            official_start_index
            + len(
                '<script type="application/json" data-target="react-app.embeddedData">'
            ) : official_end_index
        ]
        extra_json_data = extra_html_content[
            extra_start_index
            + len(
                '<script type="application/json" data-target="react-app.embeddedData">'
            ) : extra_end_index
        ]

        official_data = js.loads(official_json_data)
        extra_data = js.loads(extra_json_data)

        official_plugin_names = [
            item["name"][:-4]
            for item in official_data["payload"]["tree"]["items"]
            if item["contentType"] == "file" and item["name"].endswith(".xml")
        ]
        extra_plugin_names = [
            item["name"][:-4]
            for item in extra_data["payload"]["tree"]["items"]
            if item["contentType"] == "file" and item["name"].endswith(".xml")
        ]

        return {
            "official-plugins": official_plugin_names,
            "extra-plugins": extra_plugin_names,
        }

    def list_enabled_plugins(self):
        wayfire_ini_path = self.get_wayfire_ini_path()
        if not wayfire_ini_path:
            return []

        config = ConfigParser()
        config.read(wayfire_ini_path)

        if "core" not in config:
            print("Error: 'core' section not found in wayfire.ini.")
            return []

        plugins = config["core"].get("plugins", "").split()
        return plugins

    def reload_plugins(self):
        filename = self.get_wayfire_ini_path()
        if not filename:
            return

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
        self.disable_plugin(plugin_name)
        self.enable_plugin(plugin_name)

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

    def get_config_location_from_log(self, file_path):
        with open(file_path, "r") as file:
            for line in file:
                if "Using config file:" in line:
                    parts = line.split()
                    return parts[-1].strip()

    def start_nested_wayfire(self, wayfire_ini=None, cmd=None):
        if wayfire_ini is None:
            module_dir = pkg_resources.resource_filename(__name__, "")
            wayfire_ini = os.path.join(module_dir, "tests/wayfire.ini")
            print("Using config: {}".format(wayfire_ini))
        logfile = "/tmp/wayfire-nested.log"
        asan_options = "ASAN_OPTIONS=new_delete_type_mismatch=0:detect_leaks=0:detect_odr_violation=0"
        sock.run(
            "{0} wayfire -c {1} -d &>{2}".format(asan_options, wayfire_ini, logfile)
        )["pid"]
        time.sleep(1)
        wayland_display = extract_socket_name(logfile)
        if cmd is not None:
            sock.run("WAYLAND_DISPLAY={0} {1}".format(wayland_display, cmd))
        os.environ["WAYLAND_DISPLAY"] = wayland_display
        self.socket_name = "/tmp/wayfire-{}.socket".format(wayland_display)
        print(self.socket_name)
        print(os.path.exists(self.socket_name))
        self.connect_client(self.socket_name)
        return wayland_display

    def test_random_press_key_with_modifiers(self, num_combinations=1):
        """
        Randomly generates key combinations and calls press_key function.

        Args:
            sock: Instance of the class containing the press_key method.
            num_combinations (int): Number of random key combinations to generate.

        Returns:
            None
        """
        keys = [
            "KEY_CANCEL",
            "KEY_HELP",
            "KEY_BACK_SPACE",
            "KEY_TAB",
            "KEY_CLEAR",
            "KEY_ENTER",
            "KEY_SHIFT",
            "KEY_CONTROL",
            "KEY_ALT",
            "KEY_PAUSE",
            "KEY_CAPS_LOCK",
            "KEY_ESCAPE",
            "KEY_SPACE",
            "KEY_PAGE_UP",
            "KEY_PAGE_DOWN",
            "KEY_END",
            "KEY_HOME",
            "KEY_ARROW_LEFT",
            "KEY_ARROW_UP",
            "KEY_ARROW_RIGHT",
            "KEY_ARROW_DOWN",
            "KEY_PRINT_SCREEN",
            "KEY_INSERT",
            "KEY_DELETE",
            "KEY_0",
            "KEY_1",
            "KEY_2",
            "KEY_3",
            "KEY_4",
            "KEY_5",
            "KEY_6",
            "KEY_7",
            "KEY_8",
            "KEY_9",
            "KEY_SEMICOLON",
            "KEY_EQUALS",
            "KEY_A",
            "KEY_B",
            "KEY_C",
            "KEY_D",
            "KEY_E",
            "KEY_F",
            "KEY_G",
            "KEY_H",
            "KEY_I",
            "KEY_J",
            "KEY_K",
            "KEY_L",
            "KEY_M",
            "KEY_N",
            "KEY_O",
            "KEY_P",
            "KEY_Q",
            "KEY_R",
            "KEY_S",
            "KEY_T",
            "KEY_U",
            "KEY_V",
            "KEY_W",
            "KEY_X",
            "KEY_Y",
            "KEY_Z",
            "KEY_LEFT_WINDOW_KEY",
            "KEY_RIGHT_WINDOW_KEY",
            "KEY_SELECT_KEY",
            "KEY_NUMPAD_0",
            "KEY_NUMPAD_1",
            "KEY_NUMPAD_2",
            "KEY_NUMPAD_3",
            "KEY_NUMPAD_4",
            "KEY_NUMPAD_5",
            "KEY_NUMPAD_6",
            "KEY_NUMPAD_7",
            "KEY_NUMPAD_8",
            "KEY_NUMPAD_9",
            "KEY_MULTIPLY",
            "KEY_ADD",
            "KEY_SEPARATOR",
            "KEY_SUBTRACT",
            "KEY_DECIMAL_POINT",
            "KEY_DIVIDE",
            "KEY_F1",
            "KEY_F2",
            "KEY_F3",
            "KEY_F4",
            "KEY_F5",
            "KEY_F6",
            "KEY_F7",
            "KEY_F8",
            "KEY_F9",
            "KEY_F10",
            "KEY_F11",
            "KEY_F12",
            "KEY_NUM_LOCK",
            "KEY_SCROLL_LOCK",
            "KEY_COMMA",
            "KEY_PERIOD",
            "KEY_SLASH",
            "KEY_BACK_QUOTE",
            "KEY_OPEN_BRACKET",
            "KEY_BACK_SLASH",
            "KEY_CLOSE_BRACKET",
            "KEY_QUOTE",
            "KEY_META",
        ]

        modifiers = ["A-", "S-", "C-"]

        for _ in range(num_combinations):
            modifier = choice(modifiers)
            main_key = choice(keys)
            key_combination = modifier + main_key
            try:
                self.press_key(key_combination)
            except:
                continue

    def test_random_set_view_position(self, view_id):
        if view_id is None:
            view_id = self.test_random_view_id()
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
        if view_id is None:
            view_id = self.test_random_view_id()
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
        if view_id is None:
            view_id = self.test_random_view_id()
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
        if view_id is None:
            view_id = self.test_random_view_id()
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

    def test_random_view_id(self):
        ids = self.list_ids()
        if ids:
            return choice(ids)

    def test_change_view_state(self, view_id):
        if view_id is None:
            view_id = self.test_random_view_id()
        actions = [
            lambda: self.maximize(view_id),
            lambda: self.set_fullscreen(view_id),
            lambda: self.set_minimized(view_id, choice([True, False])),
            lambda: self.set_sticky(view_id, choice([True, False])),
            lambda: self.send_to_back(view_id, choice([True, False])),
            lambda: self.set_view_alpha(view_id, random() * 1.0),
        ]
        choice(actions)()

    def test_move_cursor_and_click(self):
        sumgeo = self.sum_geometry_resolution()
        self.move_cursor(randint(100, sumgeo[0]), randint(100, sumgeo[1]))
        self.click_button("BTN_LEFT", "full")

    def test_move_cursor_and_drag_drop(self):
        sumgeo = self.sum_geometry_resolution()
        random_iterations = randint(1, 8)

        for _ in range(random_iterations):
            self.click_and_drag(
                "S-BTN_LEFT",
                randint(1, sumgeo[0]),
                randint(1, sumgeo[1]),
                randint(1, sumgeo[0]),
                randint(1, sumgeo[1]),
                True,
            )

    def test_list_info(self, view_id):
        if view_id is None:
            view_id = self.test_random_view_id()
        self.list_outputs()
        self.list_wsets()
        # self.wset_info(view_id)
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

    def test_toggle_switcher_view_plugin(self):
        for _ in range(2):
            self.press_key("A-KEY_TAB")

    def test_toggle_tile_plugin(self):
        self.press_key("W-KEY_T")

    def test_auto_rotate_plugin(self):
        keys_combinations = [
            "C-W-KEY_UP",
            "C-W-KEY_LEFT",
            "C-W-KEY_RIGHT",
            "C-W-KEY_DOWN",
        ]

        for _ in range(len(keys_combinations)):
            key_combination = choice(keys_combinations)
            self.press_key(key_combination)

    def test_invert_plugin(self):
        for _ in range(2):
            self.press_key("A-KEY_I")

    def test_magnifier_plugin(self):
        for _ in range(2):
            self.press_key("A-W-KEY_M")

    def test_focus_change_plugin(self):
        for _ in range(2):
            self.press_key("S-W-KEY_UP")
            self.press_key("S-W-KEY_DOWN")
            self.press_key("S-W-KEY_LEFT")
            self.press_key("S-W-KEY_RIGHT")

    def test_output_switcher_plugin(self):
        for _ in range(2):
            self.press_key("A-KEY_O")
            self.press_key("A-S-KEY_O")

    def test_low_priority_plugins(self, plugin=None):
        functions = {
            "invert": (self.test_invert_plugin, ()),
            "focus-change": (self.test_focus_change_plugin, ()),
            "magnifier": (self.test_magnifier_plugin, ()),
            "output-switcher": (self.test_output_switcher_plugin, ()),
        }

        if plugin is None:
            random_function, args = choice(list(functions.values()))
            random_function(*args)
        elif plugin in functions:
            random_function, args = functions[plugin]
            random_function(*args)

    def test_plugins(self, plugin=None):
        functions = {
            "expo": (self.toggle_expo, ()),
            "scale": (self.scale_toggle, ()),
            "showdesktop": (self.toggle_showdesktop, ()),
            "cube": (self.test_cube_plugin, ()),
            "switcherview": (self.test_toggle_switcher_view_plugin, ()),
            "autorotate": (self.test_auto_rotate_plugin, ()),
            "invert": (self.test_invert_plugin, ()),
            "tile": (self.test_toggle_tile_plugin, ()),
        }

        if plugin is None:
            random_function, args = choice(list(functions.values()))
            random_function(*args)
        elif plugin in functions:
            random_function, args = functions[plugin]
            random_function(*args)

    def test_output(self):
        current_outputs = self.list_outputs_ids()
        if randint(1, 99) != 4:
            return
        self.create_wayland_output()
        for output_id in self.list_outputs_ids():
            if output_id in current_outputs:
                continue
            else:
                name = self.query_output(output_id)["name"]
                self.destroy_wayland_output(name)

    def test_turn_off_on_outputs(self):
        self.dpms("off")
        time.sleep(10)
        self.dpms("on")

    def test_is_terminal_available(self, terminal):
        try:
            Popen(["which", terminal], stdout=PIPE, stderr=PIPE)
            return True
        except FileNotFoundError:
            return False

    def test_choose_terminal(self):
        terminals = [
            "xterm",
            "alacritty",
            "kitty",
            "rxvt",
            "rxvt-unicode",
            "lxterminal",
            "eterm",
            "roxterm",
            "mlterm",
            "sakura",
            "aterm",
            "xfce4-terminal",
            "mlterm",
            "stterm",
            "konsole",
            "gnome-terminal",
            "mate-terminal",
            "terminology",
            "terminator",
            "tilda",
            "tilix",
            "alacritty",
            "foot",
            "cool-retro-term",
            "deepin-terminal",
            "rxvt-unicode-256color",
            "pantheon-terminal",
        ]
        for terminal in terminals:
            if self.test_is_terminal_available(terminal):
                run(["killall", "-9", terminal])
                return terminal
        return None

    def test_spam_terminals(self, number_of_views_to_open, wayland_display=None):
        chosen_terminal = self.test_choose_terminal()
        if chosen_terminal:
            for _ in range(number_of_views_to_open):
                if wayland_display is None:
                    sock.run(chosen_terminal)
                else:
                    command = "export WAYLAND_DISPLAY={0} ; {1}".format(
                        wayland_display, chosen_terminal
                    )
                    Popen(command, shell=True)

    def test_spam_go_workspace_set_focus(self):
        list_ids = self.list_ids()
        num_items = randint(1, len(list_ids))
        random_views = sample(list_ids, num_items)
        for view_id in random_views:
            self.go_workspace_set_focus(view_id)

    def test_set_function_priority(self, functions):
        priority = []
        for _ in range(randint(1, 4)):
            priority.append(choice(functions))
        return priority

    def random_delay_next_tx(self):
        random_run = randint(1, 8)
        if random_run > 4:
            for _ in range(1, randint(2, 100)):
                self.delay_next_tx()

    def test_random_views(self, view_id):
        functions = [
            lambda: self.test_random_set_view_position(view_id),
            lambda: self.test_random_change_view_state(view_id),
            lambda: self.test_set_view_position(view_id),
            lambda: self.test_change_view_state(view_id),
        ]

        choice(functions)()

    def test_wayfire(
        self, number_of_views_to_open, max_tries=1, speed=0, plugin=None, display=None
    ):
        from wayfire.tests.gtk3_window import spam_new_views
        from wayfire.tests.gtk3_dialogs import spam_new_dialogs
        from wayfire.tests.layershell import spam_new_layers

        # Retrieve necessary data
        view_id = self.test_random_view_id()
        workspaces = (
            [{"x": x, "y": y} for x, y in self.total_workspaces().values()]
            if self.total_workspaces()
            else []
        )
        sumgeo = self.sum_geometry_resolution()

        # Define functions to be executed
        functions = [
            (self.go_workspace_set_focus, (view_id)),
            (self.test_move_cursor_and_click, ()),
            (self.test_plugins, (plugin,)),
            (self.test_low_priority_plugins, (plugin,)),
            (self.test_move_cursor_and_drag_drop, ()),
            (self.test_output, ()),
            (self.test_random_views, (view_id)),
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

        self.test_spam_terminals(number_of_views_to_open, wayland_display=display)

        # Start spamming views
        thread = threading.Thread(target=spam_new_views)
        thread.start()

        thread = threading.Thread(target=spam_new_dialogs)
        thread.start()

        # spam_new_layers_thread = threading.Thread(target=spam_new_layers)
        # spam_new_layers_thread.start()

        # FIXME: Implement this to not use keybinds in the terminal with script running
        # first_view_focused = self.get_focused_view()

        # Execute functions with specified priority
        func_priority = self.test_set_function_priority(functions)
        should_execute_function_priority = 0
        should_change_function_priority = 0

        while iterations < max_tries:
            if speed != 0:
                random_time = speed / randint(1, speed)
                time.sleep(random_time / 1000)

            try:
                # Repeat certain functions every N iterations
                if should_execute_function_priority > 20:
                    for func, args in func_priority:
                        for _ in range(4):
                            result = func(*args)
                            print(result)
                    should_execute_function_priority = 0

                should_execute_function_priority += 1

                if should_change_function_priority > 40:
                    func_priority = self.test_set_function_priority(functions)
                    should_execute_function_priority = 0

                should_change_function_priority += 1

                random_function, args = choice(functions)

                result = random_function(*args)
                iterations += 1
                print(result)
                self.random_delay_next_tx()
                if iterations + 1 == max_tries:
                    # lets close the focused output in the last iteration
                    # so it close while still there is actions going on
                    try:
                        output_id = self.get_focused_output_id()
                        name = self.query_output(output_id)["name"]
                        self.destroy_wayland_output(name)
                    except Exception as e:
                        print(e)

            except Exception as e:
                func_priority = self.test_set_function_priority(functions)
                print(e)


addr = os.getenv("WAYFIRE_SOCKET")
sock = WayfireSocket(addr)
