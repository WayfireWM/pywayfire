#!/usr/bin/python3

# A script to monitor wayfire ipc events using GLib mainloop.

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib
import wayfire

class MyWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(400, 300)
        self.set_title("Wayfire Event Monitor")

        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_size_request(400, 300)
        self.label = Gtk.Label()
        self.label.set_valign(Gtk.Align.START)
        self.scrolled_window.set_child(self.label)
        self.set_child(self.scrolled_window)

        self.label_text = ""

        self.wf_socket = wayfire.WayfireSocket()
        self.wf_socket.watch()
        GLib.io_add_watch(self.wf_socket.client.fileno(), GLib.IO_IN, self.on_wf_event)

    def on_wf_event(self, source, condition):
       if condition & GLib.IO_IN:
           self.label_text += str(self.wf_socket.read_next_event()) + '\n'
           self.label.set_label(self.label_text)
           vadjustment = self.scrolled_window.get_vadjustment()
           vadjustment.set_value(vadjustment.get_upper() - vadjustment.get_page_size())
       return True

def on_activate(app):
    win = MyWindow(application=app)
    win.present()

if __name__ == "__main__":
    app = Gtk.Application(application_id="GLib.wayfire.event.monitor")
    app.connect("activate", on_activate)
    app.run(None)
