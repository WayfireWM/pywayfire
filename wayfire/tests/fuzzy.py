from ..ipc import WayfireSocket
from ..extra.ipc_utils import WayfireUtils
from ..extra.stipc import Stipc

import subprocess
from random import choice, randint, random, sample
import threading
import time
from subprocess import Popen, PIPE, run

sock = WayfireSocket()
utils = WayfireUtils(sock)
stipc = Stipc(sock)


class Fuzzy:
    def test_random_press_key_with_modifiers(self, num_combinations=1):
        """
        Randomly generates key combinations and calls press_key function.

        Args:
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
                stipc.press_key(key_combination)
            except:
                continue

    def test_random_set_view_position(self, view_id):
        if view_id is None:
            view_id = self.test_random_view_id()
        actions = [
            utils.set_view_top_left,
            utils.set_view_top_right,
            utils.set_view_bottom_left,
            utils.set_view_right,
            utils.set_view_left,
            utils.set_view_bottom,
            utils.set_view_top,
            utils.set_view_center,
            utils.set_view_bottom_right,
        ]
        choice(actions)(view_id)

    def test_random_change_view_state(self, view_id):
        if view_id is None:
            view_id = self.test_random_view_id()
        actions = [
            lambda: utils.maximize(view_id),
            lambda: sock.set_view_fullscreen(view_id),
            lambda: sock.set_view_minimized(view_id, True),
            lambda: sock.set_view_minimized(view_id, False),
            lambda: sock.set_view_sticky(view_id, choice([True, False])),
            lambda: sock.send_view_to_back(view_id, choice([True, False])),
            lambda: sock.set_view_alpha(view_id, random() * 1.0),
        ]
        choice(actions)()

    def test_random_list_info(self, view_id):
        if view_id is None:
            view_id = self.test_random_view_id()
        actions = [
            sock.list_outputs,
            sock.list_wsets,
            lambda: sock.wset_info(view_id),
            lambda: sock.get_view(view_id),
            lambda: sock.get_view_alpha(view_id),
            sock.list_input_devices,
            utils.get_workspaces_with_views,
            utils.get_workspaces_without_views,
            utils.get_views_from_active_workspace,
        ]
        choice(actions)()

    def test_set_view_position(self, view_id):
        if view_id is None:
            view_id = self.test_random_view_id()
        assert view_id
        utils.set_view_top_left(view_id)
        utils.set_view_top_right(view_id)
        utils.set_view_bottom_left(view_id)
        utils.set_view_right(view_id)
        utils.set_view_left(view_id)
        utils.set_view_bottom(view_id)
        utils.set_view_top(view_id)
        utils.set_view_center(view_id)
        utils.set_view_bottom_right(view_id)
        sock.set_focus(view_id)

    def test_random_view_id(self):
        ids = utils.list_ids()
        if ids:
            return choice(ids)

    def test_change_view_state(self, view_id):
        if view_id is None:
            view_id = self.test_random_view_id()
        actions = [
            lambda: utils.maximize(view_id),
            lambda: sock.set_view_fullscreen(view_id),
            lambda: sock.set_view_minimized(view_id, choice([True, False])),
            lambda: sock.set_view_sticky(view_id, choice([True, False])),
            lambda: sock.send_view_to_back(view_id, choice([True, False])),
            lambda: sock.set_view_alpha(view_id, random() * 1.0),
        ]
        choice(actions)()

    def test_move_cursor_and_click(self):
        sumgeo = utils.sum_geometry_resolution()
        stipc.move_cursor(randint(100, sumgeo[0]), randint(100, sumgeo[1]))
        stipc.click_button("BTN_LEFT", "full")

    def test_move_cursor_and_drag_drop(self):
        sumgeo = utils.sum_geometry_resolution()
        random_iterations = randint(1, 8)

        for _ in range(random_iterations):
            stipc.click_and_drag(
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
        assert view_id
        sock.list_outputs()
        sock.list_wsets()
        # sock.wset_info(view_id)
        sock.get_view(view_id)
        sock.get_view_alpha(view_id)
        sock.list_input_devices()
        utils.get_workspaces_with_views()
        utils.get_workspaces_without_views()
        utils.get_views_from_active_workspace()
        sock.set_focus(view_id)

    def test_cube_plugin(self):
        sock.cube_activate()
        sock.cube_rotate_left()
        sock.cube_rotate_right()
        stipc.click_button("BTN_LEFT", "full")

    def test_toggle_switcher_view_plugin(self):
        for _ in range(2):
            stipc.press_key("A-KEY_TAB")

    def test_toggle_tile_plugin(self):
        stipc.press_key("W-KEY_T")

    def test_auto_rotate_plugin(self):
        keys_combinations = [
            "C-W-KEY_UP",
            "C-W-KEY_LEFT",
            "C-W-KEY_RIGHT",
            "C-W-KEY_DOWN",
        ]

        for _ in range(len(keys_combinations)):
            key_combination = choice(keys_combinations)
            stipc.press_key(key_combination)

    def test_invert_plugin(self):
        for _ in range(2):
            stipc.press_key("A-KEY_I")

    def test_magnifier_plugin(self):
        for _ in range(2):
            stipc.press_key("A-W-KEY_M")

    def test_focus_change_plugin(self):
        for _ in range(2):
            stipc.press_key("S-W-KEY_UP")
            stipc.press_key("S-W-KEY_DOWN")
            stipc.press_key("S-W-KEY_LEFT")
            stipc.press_key("S-W-KEY_RIGHT")

    def test_output_switcher_plugin(self):
        for _ in range(2):
            stipc.press_key("A-KEY_O")
            stipc.press_key("A-S-KEY_O")

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
            "expo": (sock.toggle_expo, ()),
            "scale": (sock.scale_toggle, ()),
            "showdesktop": (sock.toggle_showdesktop, ()),
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
        current_outputs = utils.list_outputs_ids()
        if randint(1, 99) != 4:
            return
        stipc.create_wayland_output()
        for output_id in utils.list_outputs_ids():
            if output_id in current_outputs:
                continue
            else:
                name = sock.get_output(output_id)["name"]
                stipc.destroy_wayland_output(name)

    def dpms_status(self):
        status = subprocess.check_output(["wlopm"]).decode().strip().split("\n")
        dpms_status = {}
        for line in status:
            line = line.split()
            dpms_status[line[0]] = line[1]
        return dpms_status

    def dpms(self, state, output_name=None):
        if state == "off" and output_name is None:
            outputs = [output["name"] for output in sock.list_outputs()]
            for output in outputs:
                subprocess.call("wlopm --off {}".format(output).split())
        if state == "on" and output_name is None:
            outputs = [output["name"] for output in sock.list_outputs()]
            for output in outputs:
                subprocess.call("wlopm --on {}".format(output).split())
        if state == "on":
            subprocess.call("wlopm --on {}".format(output_name).split())
        if state == "off":
            subprocess.call("wlopm --off {}".format(output_name).split())
        if state == "toggle":
            subprocess.call("wlopm --toggle {}".format(output_name).split())

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
                    stipc.run_cmd(chosen_terminal)
                else:
                    command = "export WAYLAND_DISPLAY={0} ; {1}".format(
                        wayland_display, chosen_terminal
                    )
                    Popen(command, shell=True)

    def test_spam_go_workspace_set_focus(self):
        list_ids = utils.list_ids()
        num_items = randint(1, len(list_ids))
        random_views = sample(list_ids, num_items)
        for view_id in random_views:
            utils.go_workspace_set_focus(view_id)

    def test_set_function_priority(self, functions):
        priority = []
        for _ in range(randint(1, 4)):
            priority.append(choice(functions))
        return priority

    def random_delay_next_tx(self):
        random_run = randint(1, 8)
        if random_run > 4:
            for _ in range(1, randint(2, 100)):
                stipc.delay_next_tx()

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
        from ..tests.gtk3_window import spam_new_views
        from ..tests.gtk3_dialogs import spam_new_dialogs
        #from layershell import spam_new_layers

        # Retrieve necessary data
        view_id = self.test_random_view_id()
        workspaces = (
            [{"x": x, "y": y} for x, y in utils.total_workspaces().values()]
            if utils.total_workspaces()
            else []
        )
        sumgeo = utils.sum_geometry_resolution()

        # Define functions to be executed
        functions = [
            (utils.go_workspace_set_focus, (view_id)),
            (self.test_move_cursor_and_click, ()),
            (self.test_plugins, (plugin,)),
            (self.test_low_priority_plugins, (plugin,)),
            (self.test_move_cursor_and_drag_drop, ()),
            (self.test_output, ()),
            (self.test_random_views, (view_id)),
            (
                sock.configure_view,
                (
                    view_id,
                    randint(1, sumgeo[0]),
                    randint(0, sumgeo[1]),
                    randint(1, sumgeo[0]),
                    randint(1, sumgeo[1]),
                ),
            ),
            (
                sock.set_workspace,
                (choice(workspaces), view_id, choice(utils.list_outputs_ids())),
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
                        output_id = utils.get_focused_output_id()
                        if output_id:
                            name = sock.get_output(output_id)["name"]
                            stipc.destroy_wayland_output(name)
                    except Exception as e:
                        print(e)

            except Exception as e:
                func_priority = self.test_set_function_priority(functions)
                print(e)
