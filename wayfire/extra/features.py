import os
from configparser import ConfigParser
import requests
import json as js
from wayfire.core.template import get_msg_template
from wayfire.extra.ipc_utils import WayfireUtils
import psutil
import time
import subprocess
import os
import dbus
import pkg_resources
from itertools import cycle

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


class ExtraFeatures(WayfireUtils):
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

        config = ConfigParser()
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
        self.run_cmd(
            "{0} wayfire -c {1} -d &>{2}".format(asan_options, wayfire_ini, logfile)
        )["pid"]
        time.sleep(1)
        wayland_display = extract_socket_name(logfile)
        if cmd is not None:
            self.run_cmd("WAYLAND_DISPLAY={0} {1}".format(wayland_display, cmd))
        os.environ["WAYLAND_DISPLAY"] = wayland_display # type: ignore
        self.socket_name = "/tmp/wayfire-{}.socket".format(wayland_display)
        print(self.socket_name)
        print(os.path.exists(self.socket_name))
        self.connect_client(self.socket_name)
        return wayland_display

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
        subprocess.call(["grim", "-o", name, output_file])
        self.xdg_open(output_file)

    def screenshot(self, id, filename):
        capture = get_msg_template("view-shot/capture")
        if capture is None:
            return
        capture["data"]["view-id"] = id
        capture["data"]["file"] = filename
        self.send_json(capture)

    def dpms_status(self):
        status = subprocess.check_output(["wlopm"]).decode().strip().split("\n")
        dpms_status = {}
        for line in status:
            line = line.split()
            dpms_status[line[0]] = line[1]
        return dpms_status

    def dpms(self, state, output_name=None):
        if state == "off" and output_name is None:
            outputs = [output["name"] for output in self.list_outputs()]
            for output in outputs:
                subprocess.call("wlopm --off {}".format(output).split())
        if state == "on" and output_name is None:
            outputs = [output["name"] for output in self.list_outputs()]
            for output in outputs:
                subprocess.call("wlopm --on {}".format(output).split())
        if state == "on":
            subprocess.call("wlopm --on {}".format(output_name).split())
        if state == "off":
            subprocess.call("wlopm --off {}".format(output_name).split())
        if state == "toggle":
            subprocess.call("wlopm --toggle {}".format(output_name).split())

    def xdg_open(self, path):
        subprocess.call("xdg-open {0}".format(path).split())

    def is_view_size_greater_than_half_workarea(self, view_id):
        output_id = self.get_view_output_id(view_id)
        assert output_id
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

    def toggle_minimize_from_app_id(self, app_id):
        list_views = self.list_views()
        if not list_views:
            return
        ids = [i["id"] for i in list_views if i["app-id"] == app_id]
        for id in ids:
            if self.is_view_minimized(id):
                self.set_minimized(id, False)
            else:
                self.set_minimized(id, True)
