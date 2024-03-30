from random import randint

try:
    import gi

    try:
        gi.require_version("Gtk", "4.0")
    except ValueError:
        # Gtk is already loaded with the required version
        pass
    from gi.repository import Gtk, GLib
except ImportError:
    print(
        "GTK is not available. Please make sure the required libraries are installed."
    )


def generate_complex_chars(length=10):
    min_codepoint = 0x80
    max_codepoint = 0x10FFFF
    complex_chars = [chr(randint(min_codepoint, max_codepoint)) for _ in range(length)]
    complex_string = "".join(complex_chars)

    # Filter out characters that cannot be encoded to UTF-8
    complex_string_valid_utf8 = ""
    for char in complex_string:
        try:
            char.encode("utf-8")
            complex_string_valid_utf8 += char
        except UnicodeEncodeError:
            # Replace characters that cannot be encoded to UTF-8 with a placeholder
            complex_string_valid_utf8 += "�"  # U+FFFD REPLACEMENT CHARACTER

    return complex_string_valid_utf8


class MyWindow(Gtk.ApplicationWindow):
    def __init__(self, app, timeout):
        Gtk.Window.__init__(self, title=generate_complex_chars(), application=app)
        self.set_default_size(800, 600)

        # Set a timeout to close the window
        GLib.timeout_add(timeout, self.close_window)

    def close_window(self):
        self.destroy()
        return False  # Returning False removes the timeout


class MyApplication(Gtk.Application):
    def __init__(self, timeout):
        Gtk.Application.__init__(self)
        self.timeout = timeout

    def do_activate(self):
        win = MyWindow(self, self.timeout)
        win.present()


def open_new_view(timeout):
    app = MyApplication(timeout)
    app.run()


def spam_new_views():
    while True:
        timeout = randint(40, 4000)
        open_new_view(timeout)
