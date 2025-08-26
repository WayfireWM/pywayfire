#!/usr/bin/python3

# A script to monitor wayfire ipc events using GLib mainloop.

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib
import signal
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
        click_gesture = Gtk.GestureClick()
        click_gesture.set_button(Gdk.BUTTON_PRIMARY)
        click_gesture.connect("released", self.on_click_released)
        click_gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.scrolled_window.set_child(self.label)
        self.overlay_label = Gtk.Label(label="Text copied to clipboard")
        self.overlay_label.set_halign(Gtk.Align.CENTER)
        self.overlay_label.set_valign(Gtk.Align.CENTER)
        self.overlay = Gtk.Overlay()
        self.overlay.add_controller(click_gesture)
        self.overlay.set_child(self.scrolled_window)
        self.set_child(self.overlay)
        vadjustment = self.scrolled_window.get_vadjustment()
        vadjustment.connect("changed", self.on_vadjustment_changed)
        self.clipboard = Gdk.Display.get_default().get_clipboard()

        self.wf_socket = wayfire.WayfireSocket()
        self.wf_socket.watch()
        GLib.io_add_watch(self.wf_socket.client.fileno(), GLib.IO_IN, self.on_wf_event)

        self.line_number = 1
        self.last_vadjustment = 0
        self.toast_timeout = None

        self.connect("close-request", self.on_window_close)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.on_sigint)

    def on_window_close(self, window):
        self.get_application().quit()

    def on_sigint(self):
        self.get_application().quit()

    def on_toast_timeout(self):
        self.overlay.remove_overlay(self.overlay_label)
        self.toast_timeout = None
        return False

    def on_click_released(self, gesture, n_press, x, y):
        bounds = self.label.get_selection_bounds()
        selected_text = self.label.get_text()[bounds.start:bounds.end]
        if self.clipboard and selected_text:
            self.clipboard.set_content(Gdk.ContentProvider.new_for_value(selected_text))
            self.overlay.add_overlay(self.overlay_label)
            if self.toast_timeout:
                GLib.source_remove(self.toast_timeout)
            self.toast_timeout = GLib.timeout_add(2000, self.on_toast_timeout)

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
