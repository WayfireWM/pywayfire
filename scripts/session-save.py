#!/usr/bin/python3

#
# Copyright (c) 2025 - Scott Moreau <oreaus@gmail.com>
#
# Restart previously running gtk clients after wayfire restarts
#
# This script relies on gtk-launch to 'launch' .desktop files
# and gets this information from the application's identifier,
# which means it asserts that the app-id must be the same as
# its .desktop file name. If this is not the case, the app will
# not launch without mapping the app-id string to the .desktop
# file that launches it manually.
#
# Usage: Autostart with autostart plugin.
# ~/.config/wayfire.ini:
# [autostart]
# a1 = sh -c 'sleep 1; python3 scripts/session-save.py'
#

import os
import pickle
import subprocess
from wayfire import WayfireSocket

save_file = os.getenv("HOME") + "/.config/wayfire.pickle"

sock = WayfireSocket()
sock.watch()

class geometry:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def set_geometry(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

class window(object):
    def __init__(self, app_id, geometry):
        self.app_id = app_id
        self.geometry = geometry

    def set_geometry(self, geometry):
        self.geometry = geometry

window_list = []

try:
    try:
        with open(save_file, 'x') as file:
            pass
    except:
        pass
    with open(save_file, "rb") as file:
        window_list = pickle.load(file)

    for w in window_list:
        subprocess.run(["gtk-launch", w.app_id])
except:
    print("Failed to pickle")
    pass

def serialize_to_file():
    with open(save_file, "wb") as file:
        pickle.dump(window_list, file)

while True:
    try:
        msg = sock.read_next_event()
        if "event" in msg:
            if "view" in msg:
                if msg["view"] is None:
                    continue
                elif msg["view"]["app-id"] == "":
                    continue
                elif msg["event"] == "view-unmapped":
                    for w in window_list:
                        if msg["view"]["app-id"] == w.app_id:
                            window_list.remove(w)
                            break
                    serialize_to_file()
                elif msg["event"] == "view-mapped":
                    found = False
                    for w in window_list:
                        if w.app_id == msg["view"]["app-id"]:
                            sock.configure_view(msg["view"]["id"], w.geometry.x, w.geometry.y, w.geometry.w, w.geometry.h)
                            sock.set_focus(msg["view"]["id"])
                            found = True
                            break
                    if not found:
                        g = geometry(msg["view"]["geometry"]["x"], msg["view"]["geometry"]["y"], msg["view"]["geometry"]["width"], msg["view"]["geometry"]["height"])
                        window_list.append(window(msg["view"]["app-id"], geometry(g.x, g.y, g.w, g.h)))
                        serialize_to_file()
                elif msg["event"] == "view-geometry-changed":
                    if msg["view"]["type"] == "toplevel" and msg["view"]["mapped"]:
                        for w in window_list:
                            if w.app_id == msg["view"]["app-id"]:
                                g = geometry(msg["view"]["geometry"]["x"], msg["view"]["geometry"]["y"], msg["view"]["geometry"]["width"], msg["view"]["geometry"]["height"])
                                w.set_geometry(geometry(g.x, g.y, g.w, g.h))
                                serialize_to_file()
                                break
    except KeyboardInterrupt:
        exit(0)
