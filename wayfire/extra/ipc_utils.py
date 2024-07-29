from itertools import filterfalse

from wayfire.ipc import WayfireSocket

class WayfireUtils:
    def __init__(self, socket: WayfireSocket):
        self.socket = socket

    def find_view_middle_cursor_position(self, view_geometry, monitor_geometry):
        # Calculate the middle position of the view
        view_middle_x = view_geometry["x"] + view_geometry["width"] // 2
        view_middle_y = view_geometry["y"] + view_geometry["height"] // 2

        # Calculate the offset from the monitor's top-left corner
        cursor_x = monitor_geometry["x"] + view_middle_x
        cursor_y = monitor_geometry["y"] + view_middle_y

        return cursor_x, cursor_y

    def set_focused_view_to_workspace_without_views(self):
        view_id = self.get_focused_view_id()
        empity_workspace = self.get_workspaces_without_views()
        if empity_workspace:
            empity_workspace = empity_workspace[0]
            empity_workspace = {"x": empity_workspace[0], "y": empity_workspace[1]}
        else:
            return
        self.socket.set_workspace(empity_workspace, view_id)

    def tile_list_views(self, layout):
        if "view-id" in layout:
            return [
                (
                    layout["view-id"],
                    layout["geometry"]["width"],
                    layout["geometry"]["height"],
                )
            ]

        split = "horizontal-split" if "horizontal-split" in layout else "vertical-split"
        list = []
        for child in layout[split]:
            list += self.tile_list_views(child)
        return list

    def response_handler(self, response, result, loop):
        if response == 0:
            print(f'screenshot of all outputs: {result.get("uri")}')
            loop.stop()
        else:
            print("fail")

    def focused_output_views(self):
        list_views = self.socket.list_views()
        if not list_views:
            return
        focused_output = self.socket.get_focused_output()
        if not focused_output:
            return
        output_views = [
            view for view in list_views if view["output-id"] == focused_output["id"]
        ]
        return output_views

    def list_pids(self):
        list_views = self.socket.list_views()
        if not list_views:
            return
        list_pids = []
        for view in list_views:
            list_pids.append(view["pid"])
        return list_pids

    def list_ids(self):
        list_views = self.socket.list_views()
        if not list_views:
            return []
        list_ids = []
        for view in list_views:
            list_ids.append(view["id"])
        return list_ids

    def list_outputs_ids(self):
        outputs = self.socket.list_outputs()
        if outputs:
            return [i["id"] for i in outputs]
        return []

    def list_outputs_names(self):
        outputs = self.socket.list_outputs()
        if outputs:
            return [i["name"] for i in outputs]

    def sum_geometry_resolution(self):
        outputs = self.socket.list_outputs()
        total_width = 0
        total_height = 0
        for output in outputs:
            total_width += output["geometry"]["width"]
            total_height += output["geometry"]["height"]
        return total_width, total_height

    def get_active_workspace(self):
        data = self.get_active_workspace_info()
        if data:
            x = data["x"]
            y = data["y"]
            return {"x": x, "y": y}

    def get_view_workspace(self, view_id):
        wviews = self.get_workspaces_with_views()
        ws = None
        if wviews:
            ws = [i for i in wviews if view_id == i["view-id"]]
        if ws:
            ws = ws[0]
            return {"x": ws["x"], "y": ws["y"]}
        return None

    def go_workspace_set_focus(self, view_id):
        workspace = self.get_view_workspace(view_id)
        active_workspace = self.get_active_workspace()
        if workspace:
            if active_workspace != workspace:
                self.socket.set_workspace(workspace)
        self.socket.set_focus(view_id)

    def get_focused_view_info(self):
        id = self.get_focused_view_id()
        return [i for i in self.socket.list_views() if i["id"] == id][0]

    def get_focused_view_pid(self):
        view = self.socket.get_focused_view()
        if view is not None:
            view_id = self.socket.get_focused_view()
            if view_id is not None:
                view_id = view_id["id"]
                return self.get_view_pid(view_id)

    def has_ouput_fullscreen_view(self, output_id):
        # any fullscreen doesn't matter from what workspace
        list_views = self.socket.list_views()
        if not list_views:
            return
        if any(
            True
            for i in list_views
            if i["fullscreen"] is True and i["output-id"] == output_id
        ):
            return True

    def is_focused_view_fullscreen(self):
        focused_view = self.socket.get_focused_view()
        if focused_view is not None:
            return focused_view.get("fullscreen")
        return None

    def get_focused_view_role(self):
        focused_view_info = self.get_focused_view_info()
        if focused_view_info is not None:
            return focused_view_info.get("role")
        return None

    def get_focused_view_bbox(self):
        focused_view = self.socket.get_focused_view()
        if focused_view is not None:
            return focused_view.get("bbox")
        return None

    def get_focused_view_layer(self):
        focused_view = self.socket.get_focused_view()
        if focused_view is not None:
            return focused_view.get("layer")
        return None

    def get_focused_view_id(self):
        focused_view = self.socket.get_focused_view()
        if focused_view is not None:
            return focused_view.get("id")
        return None

    def get_focused_view_output(self):
        focused_view = self.socket.get_focused_view()
        if focused_view is not None:
            return focused_view.get("output-id")
        return None

    def get_focused_view_title(self):
        # the issue here is that if you get focused data directly
        # sometimes it will get stuff from different roles like desktop-environment
        # list-view will just filter all those stuff
        view_id = self.socket.get_focused_view()
        if view_id:
            view_id = view_id["id"]
        else:
            return ""
        list_view = self.socket.list_views()
        title = [view["title"] for view in list_view if view_id == view["id"]]
        if title:
            return title[0]
        else:
            return ""

    def get_focused_view_type(self):
        return self.socket.get_focused_view()["type"]

    def get_focused_view_app_id(self):
        return self.socket.get_focused_view()["app-id"]

    def coordinates_to_number(self, rows, cols, coordinates):
        row, col = coordinates
        if 0 <= row < rows and 0 <= col < cols:
            return row * cols + col + 1
        else:
            return None

    def get_active_workspace_number(self):
        focused_output = self.socket.get_focused_output()
        x = focused_output["workspace"]["x"]
        y = focused_output["workspace"]["y"]
        return self.get_workspace_number(x, y)

    def get_workspace_number(self, x, y):
        workspaces_coordinates = self.total_workspaces()
        if not workspaces_coordinates:
            return

        coordinates_to_find = [
            i for i in workspaces_coordinates.values() if [y, x] == i
        ][0]
        total_workspaces = len(workspaces_coordinates)
        rows = int(total_workspaces**0.5)
        cols = (total_workspaces + rows - 1) // rows
        workspace_number = self.coordinates_to_number(rows, cols, coordinates_to_find)
        return workspace_number

    def get_active_workspace_info(self):
        focused_output = self.socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("workspace")
        return None

    def get_focused_output_name(self):
        focused_output = self.socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("name")
        return None

    def get_focused_output_id(self):
        focused_output = self.socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("id")
        return None

    def get_output_id_by_name(self, output_name):
        for output in self.socket.list_outputs():
            if output["name"] == output_name:
                return output["id"]

    def get_output_name_by_id(self, output_id):
        for output in self.socket.list_outputs():
            if output["id"] == output_id:
                return output["name"]

    def get_focused_output_geometry(self):
        focused_output = self.socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("geometry")
        return None

    def get_focused_output_workarea(self):
        focused_output = self.socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("workarea")
        return None

    def get_view_pid(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            pid = view["pid"]
            return pid

    def go_next_workspace(self):
        all_workspaces = self.total_workspaces()
        if not all_workspaces:
            return

        workspaces = list(all_workspaces.values())
        active_workspace = self.socket.get_focused_output()["workspace"]

        # Find the index of the current active workspace
        current_index = workspaces.index([active_workspace["y"], active_workspace["x"]])

        # Calculate the index of the next workspace
        next_index = (current_index + 1) % len(workspaces)

        # Get the next workspace
        next_workspace_coords = workspaces[next_index]

        # Find the identifier of the next workspace
        next_workspace_id = None
        for key, value in all_workspaces.items():
            if value == next_workspace_coords:
                next_workspace_id = key
                break

        # Set the next workspace
        if next_workspace_id:
            self.socket.set_workspace(
                {"y": next_workspace_coords[0], "x": next_workspace_coords[1]}
            )

    def iterate_dicts(self, dicts):
        index = 0
        length = len(dicts)
        while True:
            yield dicts[index]
            index = (index + 1) % length

    def get_next_workspace(self, workspaces, active_workspace):
        # Find the index of the active workspace in the list
        active_index = None

        # Remove the "view-id" key from each workspace
        for workspace in workspaces:
            workspace.pop("view-id", None)

        # Create a set to store unique workspace dictionaries
        unique_workspaces = []

        # Filter out duplicates while maintaining the order
        for workspace in workspaces:
            if workspace not in unique_workspaces:
                unique_workspaces.append(workspace)

        # Sort the list based on the 'x' and 'y' keys
        unique_workspaces.sort(key=lambda d: (d["x"], d["y"]))

        for i, workspace in enumerate(unique_workspaces):
            if workspace == active_workspace:
                active_index = i
                break

        if active_index is None:
            first_workspace = self.get_workspaces_with_views()
            if first_workspace:
                first_workspace = first_workspace[0]
            self.socket.set_workspace(first_workspace)
            return

        # Calculate the index of the next workspace cyclically
        next_index = (active_index + 1) % len(unique_workspaces)

        # Return the next workspace
        return unique_workspaces[next_index]

    def go_next_workspace_with_views(self):
        workspaces = self.get_workspaces_with_views()
        active_workspace = self.socket.get_focused_output()["workspace"]
        active_workspace = {"x": active_workspace["x"], "y": active_workspace["y"]}
        next_ws = self.get_next_workspace(workspaces, active_workspace)
        if next_ws:
            self.socket.set_workspace(next_ws)
        else:
            return

    def go_previous_workspace(self):
        previous = 1
        current_workspace = self.get_active_workspace_number()
        if current_workspace == 1:
            previous = 9
        else:
            if current_workspace is not None:
                previous = current_workspace - 1

        self.socket.set_workspace(previous)
        return True

    def focus_next_view_from_active_workspace(self):
        views = self.get_views_from_active_workspace()
        if views:
            self.go_workspace_set_focus(views[0])

    def get_workspace_from_view(self, view_id):
        ws_with_views = self.get_workspaces_with_views()
        if ws_with_views:
            for ws in ws_with_views:
                if ws["view-id"] == view_id:
                    return {"x": ws["x"], "y": ws["y"]}

    def has_workspace_views(self, ws):
        ws_with_views = self.get_workspaces_with_views()
        if ws_with_views:
            for wwv in ws_with_views:
                del wwv["view-id"]
                if wwv == ws:
                    return True
        return False

    def get_workspaces_with_views(self):
        focused_output = self.socket.get_focused_output()
        monitor = focused_output["geometry"]
        ws_with_views = []
        views = self.focused_output_views()
        if views:
            for ws_x in range(focused_output["workspace"]["grid_width"]):
                for ws_y in range(focused_output["workspace"]["grid_height"]):
                    for view in views:
                        if self.view_visible_on_workspace(
                            view["geometry"],
                            ws_x - focused_output["workspace"]["x"],
                            ws_y - focused_output["workspace"]["y"],
                            monitor,
                        ):
                            ws_with_views.append(
                                {"x": ws_x, "y": ws_y, "view-id": view["id"]}
                            )
            return ws_with_views
        return None

    def get_workspaces_without_views(self):
        workspace_with_views = self.get_workspaces_with_views()
        if not workspace_with_views:
            return
        workspace_with_views = [[i["x"], i["y"]] for i in workspace_with_views]
        total_workspaces = self.total_workspaces()
        if not total_workspaces:
            return
        all_workspaces = list(total_workspaces.values())
        return list(filterfalse(lambda x: x in workspace_with_views, all_workspaces))

    def get_workspace_coordinates(self, view_info):
        focused_output = self.socket.get_focused_output()
        monitor = focused_output["geometry"]
        views = [view_info]
        for ws_x in range(focused_output["workspace"]["grid_width"]):
            for ws_y in range(focused_output["workspace"]["grid_height"]):
                for view in views:
                    if self.view_visible_on_workspace(
                        view["geometry"],
                        ws_x - focused_output["workspace"]["x"],
                        ws_y - focused_output["workspace"]["y"],
                        monitor,
                    ):
                        return {"x": ws_x, "y": ws_y}

    def get_views_from_active_workspace(self):
        aw = self.get_active_workspace_info()
        workspace_with_views = self.get_workspaces_with_views()
        if workspace_with_views is None or aw is None:
            return []

        return [
            i["view-id"]
            for i in workspace_with_views
            if i["x"] == aw["x"] and i["y"] == aw["y"]
        ]

    def close_focused_view(self):
        view_id = self.socket.get_focused_view()["id"]
        self.socket.close_view(view_id)

    def get_view_info(self, view_id):
        info = [i for i in self.socket.list_views() if i["id"] == view_id]
        if info:
            return info[0]
        else:
            return

    def get_view_output_id(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("output-id")
        return None

    def get_view_output_name(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("output-name")
        return None

    def is_view_fullscreen(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("fullscreen")
        return None

    def is_view_focusable(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("focusable")
        return None

    def get_view_geometry(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("geometry")
        return None

    def is_view_minimized(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("minimized")
        return None

    def is_view_maximized(self, view_id):
        tiled_edges = self.get_view_tiled_edges(view_id)
        if tiled_edges is not None:
            return tiled_edges == 15
        return False

    def get_view_tiled_edges(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("tiled-edges")
        return None

    def get_view_title(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("title")
        return None

    def get_view_type(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("type")
        return None

    def get_view_app_id(self, view_id):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("app-id")
        return None

    def get_view_role(self, view_id):
        view_info = self.get_view_info(view_id)
        if view_info is not None:
            return view_info.get("role")
        return None

    def get_view_bbox(self, view_id):
        view_info = self.get_view_info(view_id)
        if view_info is not None:
            return view_info.get("bbox")
        return None

    def get_view_layer(self, view_id):
        view_layer_content = self.get_view_layer(view_id)
        if view_layer_content:
            return view_layer_content.get("layer")
        return None

    def maximize_focused(self):
        view = self.socket.get_focused_view()
        self.socket.assign_slot(view["id"], "slot_c")

    def fullscreen_focused(self):
        view = self.socket.get_focused_view()
        self.socket.set_view_fullscreen(view["id"])

    def find_view_by_pid(self, pid):
        lviews = self.socket.list_views()
        if not lviews:
            return
        view = [view for view in lviews if view["pid"] == pid]
        if view:
            return view[0]

    def find_device_id(self, name_or_id_or_type):
        devices = self.socket.list_input_devices()
        for dev in devices:
            if (
                dev["name"] == name_or_id_or_type
                or str(dev["id"]) == name_or_id_or_type
                or dev["type"] == name_or_id_or_type
            ):
                return dev["id"]
        return None

    def disable_input_device(self, args):
        device_id = self.find_device_id(args)
        msg = self.socket.configure_input_device(device_id, False)
        return msg

    def enable_input_device(self, args):
        device_id = self.find_device_id(args)
        msg = self.socket.configure_input_device(device_id, True)
        return msg

    def maximize(self, view_id):
        self.socket.assign_slot(view_id, "slot_c")

    def maximize_all_views_from_active_workspace(self):
        for view_id in self.get_views_from_active_workspace():
            if not self.is_view_fullscreen(view_id):
                self.maximize(view_id)

    def total_workspaces(self):
        winfo = self.get_active_workspace_info()
        if not winfo:
            return {}
        total_workspaces = winfo["grid_height"] * winfo["grid_width"]

        # Calculate the number of rows and columns based on the total number of workspaces
        rows = int(total_workspaces**0.5)
        cols = (total_workspaces + rows - 1) // rows

        # Initialize the dictionary to store workspace numbers and their coordinates
        workspaces = {}

        # Loop through each row and column to assign workspace numbers and coordinates
        for row in range(rows):
            for col in range(cols):
                workspace_num = row * cols + col + 1
                if workspace_num <= total_workspaces:
                    workspaces[workspace_num] = [row, col]
        return workspaces

    def view_visible_on_workspace(self, view, ws_x, ws_y, monitor):
        workspace_start_x = ws_x * monitor["width"]
        workspace_start_y = ws_y * monitor["height"]
        workspace_end_x = workspace_start_x + monitor["width"]
        workspace_end_y = workspace_start_y + monitor["height"]

        # Test intersection of two rectangles
        return not (
            view["x"] >= workspace_end_x
            or view["y"] > workspace_end_y
            or view["x"] + view["width"] <= workspace_start_x
            or view["y"] + view["height"] <= workspace_start_y
        )

    def set_view_top_left(self, view_id):
        self.socket.assign_slot(view_id, "slot_tl")

    def set_view_top_right(self, view_id):
        self.socket.assign_slot(view_id, "slot_tr")

    def set_view_bottom_left(self, view_id):
        self.socket.assign_slot(view_id, "slot_bl")

    def set_view_right(self, view_id):
        self.socket.assign_slot(view_id, "slot_r")

    def set_view_left(self, view_id):
        self.socket.assign_slot(view_id, "slot_l")

    def set_view_bottom(self, view_id):
        self.socket.assign_slot(view_id, "slot_b")

    def set_view_top(self, view_id):
        self.socket.assign_slot(view_id, "slot_t")

    def set_view_center(self, view_id):
        self.socket.assign_slot(view_id, "slot_c")

    def set_view_bottom_right(self, view_id):
        self.socket.assign_slot(view_id, "slot_br")

    def get_current_tiling_layout(self):
        output = self.socket.get_focused_output()
        wset = output["wset-index"]
        x = output["workspace"]["x"]
        y = output["workspace"]["y"]
        return self.socket.get_tiling_layout(wset, x, y)

    def set_current_tiling_layout(self, layout):
        output = self.socket.get_focused_output()
        wset = output["wset-index"]
        x = output["workspace"]["x"]
        y = output["workspace"]["y"]
        return self.socket.set_tiling_layout(wset, x, y, layout)

    def toggle_minimize_from_app_id(self, app_id):
        list_views = self.socket.list_views()
        if not list_views:
            return
        ids = [i["id"] for i in list_views if i["app-id"] == app_id]
        for id in ids:
            if self.is_view_minimized(id):
                self.socket.set_view_minimized(id, False)
            else:
                self.socket.set_view_minimized(id, True)

