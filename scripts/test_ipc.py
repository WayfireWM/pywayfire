from wayfire import WayfireSocket
import subprocess
import time
import sys

# === Configuration ===
TERMINAL = "kitty"  # or "alacritty"
TITLE = "Simple Pywayfire Tests"

# Set up the socket and shell commands
sock = WayfireSocket()


def find_view_by_title(title: str):
    views = sock.list_views()
    for v in views:
        if v.get("title") == title and v.get("role") == "toplevel" and v.get("mapped"):
            return v
    return None


def launch_terminal():
    if TERMINAL == "kitty":
        subprocess.Popen(
            [
                "kitty",
                "--title",
                TITLE,
                "sh",
                "-c",
                "echo 'Wayfire test terminal'; sleep 1000",
            ]
        )
    elif TERMINAL == "alacritty":
        subprocess.Popen(
            [
                "alacritty",
                "--title",
                TITLE,
                "-e",
                "sh",
                "-c",
                "echo 'Wayfire test terminal'; sleep 1000",
            ]
        )
    else:
        raise ValueError(f"Unsupported terminal: {TERMINAL}")


def wait_for_view(title: str, timeout=10):
    print(f"Waiting for view with title '{title}'...")
    start = time.time()
    while True:
        view = find_view_by_title(title)
        if view:
            print(f"Found view: {view['id']} ({view['title']})")
            return view
        if time.time() - start > timeout:
            raise TimeoutError(f"Timeout waiting for view with title '{title}'")
        time.sleep(0.2)


def restore_state(view_id, original_alpha, original_sticky, original_fullscreen):
    print("[RESTORE] Restoring original state...")
    sock.set_view_alpha(view_id, original_alpha)
    sock.set_view_sticky(view_id, original_sticky)
    sock.set_view_fullscreen(view_id, original_fullscreen)
    sock.set_view_always_on_top(view_id, False)
    sock.set_view_minimized(view_id, False)
    sock.set_option_values({"core/xwayland": True})
    sock.send_view_to_back(view_id, False)

    print("[RESTORE] Done.")


def main():
    try:
        # Launch terminal
        print(f"Launching {TERMINAL} with title '{TITLE}'...")
        launch_terminal()

        view = wait_for_view(TITLE)
        view_id = view["id"]

        # Save original state
        original_alpha = view.get("alpha", 1.0)
        original_sticky = view.get("sticky", False)
        original_fullscreen = view.get("fullscreen", False)

        print(
            f"Original Alpha: {original_alpha}, Sticky: {original_sticky}, Fullscreen: {original_fullscreen}"
        )

        print("Focusing view...")
        sock.set_focus(view_id)

        print("Resizing and moving view...")
        sock.configure_view(view_id, 100, 100, 800, 600)

        print("Setting transparency...")
        sock.set_view_alpha(view_id, 0.7)

        print("Toggling sticky state...")
        sock.set_view_sticky(view_id, not original_sticky)

        print("Toggling fullscreen...")
        sock.set_view_fullscreen(view_id, not original_fullscreen)

        print("Setting always-on-top...")
        sock.set_view_always_on_top(view_id, True)

        print("Setting config options")
        sock.set_option_values({"core/xwayland": False})

        print("Setting view workspace")
        sock.set_workspace(0, 0, view_id)

        print("Setting view minimized")
        sock.set_view_minimized(view_id, True)

        print("Sending view to back")
        sock.send_view_to_back(view_id, True)

        print("Sending view to wset")
        wset_index = view["wset-index"]
        sock.send_view_to_wset(view_id, wset_index)

        print("Setting output wset")
        output_id = view["output-id"]
        sock.set_output_wset(output_id, wset_index)

        print("Using get functions")
        sock.get_focused_view()
        sock.get_cursor_position()
        focused_output_id = sock.get_focused_output()["id"]
        sock.get_view(view_id)
        sock.get_option_value("core/plugins")
        sock.get_configuration()
        sock.get_output(focused_output_id)
        layout_index = sock.get_keyboard_layout()["layout-index"]

        print("Setting keyboard layout")
        sock.set_keyboard_layout(layout_index)

        print("Using list functions")
        sock.list_views()
        sock.list_methods()
        sock.list_input_devices()
        sock.list_wsets()
        sock.list_outputs()

        print(f"Assign {TERMINAL} to the slots")
        positions = ["tl", "tr", "bl", "br", "br", "t", "b", "l", "r", "c"]
        for position in positions:
            sock.assign_slot(view_id, f"slot_{position}")

        print("Creating headless output")
        headless_output_name = sock.create_headless_output(100, 100)["output"]["name"]

        print("Destroying headless output")
        sock.destroy_headless_output(headless_output_name)

        def register_binding():
            print("Registering binding")
            return sock.register_binding(
                binding="<ctrl><super><alt> KEY_T",
                call_method="scale/toggle",  # use sock.list_methods for more info
                call_data={},
                exec_always=True,
                mode="normal",
            )

        sock.unregister_binding(register_binding()["binding-id"])
        print("Unregistering binding")

        print("Registering binding again to test clear_bindings")
        register_binding()

        print("Clearing bindings")
        sock.clear_bindings()

        # Restore original state
        restore_state(view_id, original_alpha, original_sticky, original_fullscreen)

        print(f"Closing {TERMINAL}")
        sock.close_view(view_id)

        print("Tests finished ✅")

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
