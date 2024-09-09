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
        """
        Move the cursor to a specified position.

        This method sets the cursor's position to the given coordinates (x, y).

        Args:
            x (int): The x-coordinate to move the cursor to.
            y (int): The y-coordinate to move the cursor to.

        """
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
        Simulate a button click with optional modifier keys.

        The button can be specified with or without a super modifier, and the click 
        action can be configured as a full click, press, or release.

        Args:
            btn_with_mod (str): The button to be clicked, optionally including a 
                                modifier key (e.g., "S-BTN_LEFT" for super + left 
                                button, or "BTN_RIGHT" for just the right button).
            mode (str): The mode of the button action, which can be "full" for a 
                        complete click, "press" for pressing the button, or "release" 
                        for releasing the button.

        Example:
            click_button("S-BTN_LEFT", "full")
            # Simulates a full click with the super modifier + left button.
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
        """
        Simulate pressing a combination of keys with optional modifiers.

        This method simulates the pressing of a key or key combination, including 
        any specified modifier keys (Alt, Shift, Ctrl, Meta). It handles key 
        press and release actions, and optionally waits between actions based on 
        the provided timeout.

        Args:
            keys (str): A string representing the keys to be pressed, with modifiers 
                        separated by hyphens (e.g., "A-S-C-W" for Alt+Shift+Ctrl+Meta+W).
            timeout (int, optional): The time in milliseconds to wait between key 
                                     press and release actions. Defaults to 0.

        Example:
            press_key("A-KEY_TAB") <- simulates pressing Alt + Tab
            press_key("C-KEY_C")  <- Simulates pressing Ctrl + C
            press_key("A-S-KEY_TAB", 500)  <- Simulates pressing Alt + Shift + Tab with a 500ms delay

        Returns:
            None: This method performs actions without returning a value.
        """
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
        """
        Simulate a click-and-drag action of the mouse cursor.

        This method moves the cursor to a starting position, simulates pressing a mouse 
        button, drags the cursor to an ending position in specified steps, and optionally 
        releases the mouse button.

        Args:
            button (str): The mouse button to be used for the click-and-drag action (e.g., "BTN_LEFT").
            start_x (int): The x-coordinate of the starting position.
            start_y (int): The y-coordinate of the starting position.
            end_x (int): The x-coordinate of the ending position.
            end_y (int): The y-coordinate of the ending position.
            release (bool, optional): Whether to release the mouse button after dragging. Defaults to True.
            steps (int, optional): The number of steps to divide the drag motion into. Defaults to 10.

        Example:
            click_and_drag("BTN_LEFT", 100, 200, 300, 400, release=True, steps=20)
            # Simulates a left mouse button click-and-drag from (100, 200) to (300, 400) with 20 steps.

        Returns:
            None: This method performs actions without returning a value.
        """
        dx = end_x - start_x
        dy = end_y - start_y

        self.move_cursor(start_x, start_y)
        self.click_button(button, "press")
        for i in range(steps + 1):
            self.move_cursor(start_x + dx * i // steps, start_y + dy * i // steps)
        if release:
            self.click_button(button, "release")
