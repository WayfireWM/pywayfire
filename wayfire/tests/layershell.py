import gi
import random
import threading
import time

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")

from gi.repository import Gtk, Gdk, GtkLayerShell


class DockBar(Gtk.Window):
    def __init__(self):
        super().__init__()

        GtkLayerShell.init_for_window(self)

        self.set_title("Dock Bar")
        self.set_default_size(1080, 1080)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_decorated(False)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(box)

        label = Gtk.Label(label="Hello World! " * 100)
        box.pack_start(label, True, True, 0)

        self.connect("destroy", Gtk.main_quit)


def spam_new_layers():
    layers = list(range(1, 4))
    layer_mapping = {
        1: GtkLayerShell.Layer.TOP,
        2: GtkLayerShell.Layer.OVERLAY,
        3: GtkLayerShell.Layer.BACKGROUND,
    }
    while True:
        layer = random.choice(layers)
        time_interval = random.uniform(0.2, 1.0)
        dock_bar = DockBar()
        try:
            GtkLayerShell.set_layer(
                dock_bar, layer_mapping.get(layer, GtkLayerShell.Layer.TOP)
            )
            GtkLayerShell.auto_exclusive_zone_enable(dock_bar)
            dock_bar.show_all()
        except Exception as e:
            print("An error occurred:", e)
        time.sleep(time_interval)
