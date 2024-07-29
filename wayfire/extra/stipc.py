import time
from wayfire.core.template import get_msg_template
from wayfire.ipc import WayfireSocket

class Stipc:
    def __init__(self, socket: WayfireSocket):
        self.socket = socket

    def layout_views(self, layout):
        views = self.socket.list_views()
        method = "stipc/layout_views"
        message = get_msg_template(method)
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
        return self.socket.send_json(message)

    def move_cursor(self, x: int, y: int):
        message = get_msg_template("stipc/move_cursor")
        message["data"]["x"] = x
        message["data"]["y"] = y
        return self.socket.send_json(message)

    def set_touch(self, id: int, x: int, y: int):
        method = "stipc/touch"
        message = get_msg_template(method)
        message["data"]["finger"] = id
        message["data"]["x"] = x
        message["data"]["y"] = y
        return self.socket.send_json(message)

    def tablet_tool_proximity(self, x, y, prox_in):
        method = "stipc/tablet/tool_proximity"
        message = get_msg_template(method)
        message["data"]["x"] = x
        message["data"]["y"] = y
        message["data"]["proximity_in"] = prox_in
        return self.socket.send_json(message)

    def tablet_tool_tip(self, x, y, state):
        method = "stipc/tablet/tool_tip"
        message = get_msg_template(method)
        message["data"]["x"] = x
        message["data"]["y"] = y
        message["data"]["state"] = state
        return self.socket.send_json(message)

    def tablet_tool_axis(self, x, y, pressure):
        method = "stipc/tablet/tool_axis"
        message = get_msg_template(method)
        message["data"]["x"] = x
        message["data"]["y"] = y
        message["data"]["pressure"] = pressure
        return self.socket.send_json(message)

    def tablet_tool_button(self, btn, state):
        method = "stipc/tablet/tool_button"
        message = get_msg_template(method)
        message["data"]["button"] = btn
        message["data"]["state"] = state
        return self.socket.send_json(message)

    def tablet_pad_button(self, btn, state):
        method = "stipc/tablet/pad_button"
        message = get_msg_template(method)
        message["data"]["button"] = btn
        message["data"]["state"] = state
        return self.socket.send_json(message)

    def release_touch(self, id: int):
        method = "stipc/touch_release"
        message = get_msg_template(method)
        message["data"]["finger"] = id
        return self.socket.send_json(message)

    def create_wayland_output(self):
        message = get_msg_template("stipc/create_wayland_output")
        self.socket.send_json(message)

    def destroy_wayland_output(self, output: str):
        method = "stipc/destroy_wayland_output"
        message = get_msg_template(method)
        message["data"]["output"] = output
        return self.socket.send_json(message)

    def delay_next_tx(self):
        method = "stipc/delay_next_tx"
        message = get_msg_template(method)
        return self.socket.send_json(message)

    def xwayland_pid(self):
        method = "stipc/get_xwayland_pid"
        message = get_msg_template(method)
        return self.socket.send_json(message)

    def xwayland_display(self):
        method = "stipc/get_xwayland_display"
        message = get_msg_template(method)
        return self.socket.send_json(message)

    def click_button(self, btn_with_mod: str, mode: str):
        """
        btn_with_mod can be S-BTN_LEFT/BTN_RIGHT/etc. or just BTN_LEFT/...
        If S-BTN..., then the super modifier will be pressed as well.
        mode is full, press or release
        """
        message = get_msg_template("stipc/feed_button")
        message["method"] = "stipc/feed_button"
        message["data"]["mode"] = mode
        message["data"]["combo"] = btn_with_mod
        return self.socket.send_json(message)

    def ping(self):
        message = get_msg_template("stipc/ping")
        response = self.socket.send_json(message)
        return ("result", "ok") in response.items()

    def set_key_state(self, key: str, state: bool):
        message = get_msg_template("stipc/feed_key")
        message["data"]["key"] = key
        message["data"]["state"] = state
        return self.socket.send_json(message)

    def run_cmd(self, cmd):
        message = get_msg_template("stipc/run")
        message["data"]["cmd"] = cmd
        return self.socket.send_json(message)

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
