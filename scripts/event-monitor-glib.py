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
        self.label.set_selectable(True)
        self.scrolled_window.set_child(self.label)
        self.set_child(self.scrolled_window)
        vadjustment = self.scrolled_window.get_vadjustment()
        vadjustment.connect("changed", self.on_vadjustment_changed)

        self.wf_socket = wayfire.WayfireSocket()
        self.wf_socket.watch()
        GLib.io_add_watch(self.wf_socket.client.fileno(), GLib.IO_IN, self.on_wf_event)

        self.line_number = 1
        self.last_vadjustment = 0

    def idle_vadjustment_changed(self, vadjustment):
        vadjustment.set_value(vadjustment.get_upper())

    def on_vadjustment_changed(self, vadjustment):
        if vadjustment.get_value() == self.last_vadjustment:
            GLib.idle_add(self.idle_vadjustment_changed, vadjustment)
        self.last_vadjustment = vadjustment.get_upper() - vadjustment.get_page_size()

    def on_wf_event(self, source, condition):
       if condition & GLib.IO_IN:
           self.label.set_markup("<span font_family='monospace'>" + \
               self.label.get_text() + " " + \
               str(self.line_number).rjust(2) + ": " + \
               str(self.wf_socket.read_next_event()) + "\n</span>")
           self.line_number += 1
       return True

def on_activate(app):
    win = MyWindow(application=app)
    win.present()

if __name__ == "__main__":
    app = Gtk.Application(application_id="GLib.wayfire.event.monitor")
    app.connect("activate", on_activate)
    app.run(None)
