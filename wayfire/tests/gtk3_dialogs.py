import gi
import threading
import random

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


def close_dialog(dialog):
    dialog.response(Gtk.ResponseType.CLOSE)


def open_dialog_and_close(dialog_title, dialog_message):
    dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.NONE,
        text=dialog_title,
    )
    dialog.format_secondary_text(dialog_message)
    dialog.set_default_size(300, 100)

    timeout = random.uniform(0.01, 1.0)
    t = threading.Timer(timeout, close_dialog, args=[dialog])
    t.start()

    dialog.run()
    dialog.destroy()


def spam_new_dialogs():
    while True:
        open_dialog_and_close("Title", "Hello, I am here to produce more crashes yet")
