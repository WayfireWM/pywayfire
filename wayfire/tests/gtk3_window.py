from random import randint
import threading

try:
    import gi

    try:
        gi.require_version("Gtk", "3.0")
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


class TestWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title=generate_complex_chars(10))
        self.connect("destroy", Gtk.main_quit)
        self.label = Gtk.Label(label=generate_complex_chars(10))
        self.add(self.label)
        self.show_all()

    def open_new_view(self, timeout):
        GLib.timeout_add(timeout, self.close_window)

    def close_window(self):
        self.destroy()
        return False


def open_new_view(timeout):
    window = TestWindow()
    window.open_new_view(timeout)
    Gtk.main()


def spam_new_views():
    while True:
        timeout = randint(100, 1000)
        open_new_view(timeout)
