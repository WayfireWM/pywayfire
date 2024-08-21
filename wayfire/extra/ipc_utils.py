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

    def move_view_to_empty_workspace(self, view_id: int):
        top_level_mapped_view = self.socket.get_view(view_id)["role"] == "toplevel"
        assert top_level_mapped_view, f"Unable to move view with ID {view_id}: view not found or not top-level."

        empty_workspace = self.get_workspaces_without_views()
        assert empty_workspace, "No empty workspace available."

        empty_workspace = empty_workspace[0]
        self.socket.set_workspace(empty_workspace[0], empty_workspace[1], view_id)

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

    def get_focused_output_views(self):
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

    def go_workspace_set_focus(self, view_id: int):
        workspace = self.get_workspace_from_view(view_id)
        active_workspace = self.get_active_workspace()
        if workspace and active_workspace:
            workspace_x, workspace_y = active_workspace.values()
            if active_workspace != workspace:
                self.socket.set_workspace(workspace_x, workspace_y)
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

    def list_filtered_views(self):
        views = self.socket.list_views()
        filtered_views = [
            view for view in views
            if view["role"] == "toplevel"
            and view["app-id"] != "nil"
            and view["pid"] != -1
        ]
        return filtered_views

    def get_focused_view_title(self):
        view = self.socket.get_focused_view()
        if view:
            if view in self.list_filtered_views():
                return view["title"]
            else:
                return
        else:
            return
 
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

    def get_workspace_number(self, workspace_x: int, workspace_y: int):
        workspaces_coordinates = self.total_workspaces()
        if not workspaces_coordinates:
            return

        coordinates_to_find = [
            i for i in workspaces_coordinates.values() if [workspace_x, workspace_y] == i
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

    def get_output_id_by_name(self, output_name: str):
        for output in self.socket.list_outputs():
            if output["name"] == output_name:
                return output["id"]

    def get_output_name_by_id(self, output_id: int):
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

    def get_view_pid(self, view_id: int):
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
        workspace_x, workspace_y = workspaces[next_index]

        # Find the identifier of the next workspace
        next_workspace_id = None
        for key, value in all_workspaces.items():
            if value == [workspace_x, workspace_y]:
                next_workspace_id = key
                break

        # Set the next workspace
        if next_workspace_id:
            self.socket.set_workspace(workspace_x, workspace_y)

    def iterate_dicts(self, dicts: dict):
        index = 0
        length = len(dicts)
        while True:
            yield dicts[index]
            index = (index + 1) % length


    def get_previous_workspace(self, workspace_x: int, workspace_y: int):
        total_workspaces = self.total_workspaces()

        unique_workspaces = []

        # Extract and filter out duplicate workspace coordinates
        for coords in total_workspaces.values():
            if coords not in unique_workspaces:
                unique_workspaces.append(coords)

        # Sort the list based on the 'x' and 'y' values, ensuring x is the primary sort key
        unique_workspaces.sort(key=lambda d: (d[1], d[0]))  # Sort by y (row), then x (column)

        # Find the index of the active workspace in the list
        active_index = next((i for i, coords in enumerate(unique_workspaces)
                            if coords[1] == workspace_y and coords[0] == workspace_x), None)

        if active_index is None:
            first_workspace = self.get_workspaces_with_views()
            if first_workspace:
                return first_workspace[0]
            return None

        # Calculate the index of the previous workspace cyclically
        previous_index = (active_index - 1) % len(unique_workspaces)

        # Return the previous workspace's coordinates
        return unique_workspaces[previous_index]

    def get_next_workspace(self, workspace_x: int, workspace_y: int):
        total_workspaces = self.total_workspaces()

        unique_workspaces = []

        # Extract and filter out duplicate workspace coordinates
        for coords in total_workspaces.values():
            if coords not in unique_workspaces:
                unique_workspaces.append(coords)

        # Sort the list based on the 'x' and 'y' values, ensuring x is the primary sort key
        unique_workspaces.sort(key=lambda d: (d[1], d[0]))  # Sort by y (row), then x (column)

        # Find the index of the active workspace in the list
        active_index = next((i for i, coords in enumerate(unique_workspaces)
                            if coords[1] == workspace_y and coords[0] == workspace_x), None)

        if active_index is None:
            first_workspace = self.get_workspaces_with_views()
            if first_workspace:
                return first_workspace[0]
            return None

        # Calculate the index of the next workspace cyclically
        next_index = (active_index + 1) % len(unique_workspaces)

        # Return the next workspace's coordinates
        return unique_workspaces[next_index]


    def go_next_workspace_with_views(self):
        focused_output = self.socket.get_focused_output()
        current_x = focused_output['workspace']['x']
        current_y = focused_output['workspace']['y']

        ws_with_views = self.get_workspaces_with_views()

        if not ws_with_views:
            print("No workspaces with views found.")
            return

        # Extract unique workspaces with views
        unique_workspaces = { (ws['x'], ws['y']) for ws in ws_with_views }

        # Ensure that unique_workspaces are sorted to maintain a consistent order
        sorted_workspaces = sorted(unique_workspaces, key=lambda d: (d[1], d[0]))  # Sort by y, then x
 
        # Find the index of the current workspace in the sorted list of workspaces with views
        current_ws_index = next((i for i, (x, y) in enumerate(sorted_workspaces)
                                if x == current_x and y == current_y), None)
        if current_ws_index is None:
            print("Current workspace is not in the list of workspaces with views.")
            return

        # Calculate the index of the next workspace cyclically
        next_index = (current_ws_index + 1) % len(sorted_workspaces)
        next_ws = sorted_workspaces[next_index]

        # Set the next workspace
        workspace_x, workspace_y = next_ws
        print(f"Switching to workspace with views: ({workspace_x}, {workspace_y})")
        self.socket.set_workspace(workspace_x, workspace_y)



    def go_previous_workspace(self):
        current_workspace = self.get_active_workspace_number()
        if current_workspace is None:
            return

        current_workspace_coords = self.total_workspaces().get(current_workspace, None)
        if current_workspace_coords is None:
            return

        # Retrieve the previous workspace coordinates
        previous_workspace_coords = self.get_previous_workspace(*current_workspace_coords)
        if previous_workspace_coords is None:
            return

        # Set the previous workspace
        workspace_x, workspace_y = previous_workspace_coords
        self.socket.set_workspace(workspace_x, workspace_y)


    def get_workspace_from_view(self, view_id):
        ws_with_views = self.get_workspaces_with_views()
        if ws_with_views:
            for ws in ws_with_views:
                if ws["view-id"] == view_id:
                    return {"x": ws["x"], "y": ws["y"]}

    def has_workspace_views(self, workspace_x, workspace_y):
        ws_with_views_list = self.get_workspaces_with_views()
        if ws_with_views_list:
            for workspace_with_views in ws_with_views_list:
                del workspace_with_views["view-id"]
                x, y = workspace_with_views.values()
                if [x, y] == [workspace_x, workspace_y]:
                    return True
        return False

    def get_workspaces_with_views(self):
        focused_output = self.socket.get_focused_output()
        monitor = focused_output["geometry"]
        ws_with_views = []
        views = self.get_focused_output_views()

        if views:
            grid_width = focused_output["workspace"]["grid_width"]
            grid_height = focused_output["workspace"]["grid_height"]
            current_ws_x = focused_output["workspace"]["x"]
            current_ws_y = focused_output["workspace"]["y"]

            for ws_x in range(grid_width):
                for ws_y in range(grid_height):
                    for view in views:
                        if view["role"] != "toplevel" or view["app-id"] == "nil" or view["pid"] == -1:
                            continue

                        # Calculate intersection area with the current workspace
                        intersection_area = self.calculate_intersection_area(
                            view["geometry"],
                            ws_x - current_ws_x,
                            ws_y - current_ws_y,
                            monitor
                        )

                        if intersection_area > 0:  # If there's any intersection area
                            ws_with_views.append({"x": ws_x, "y": ws_y, "view-id": view["id"]})

        return ws_with_views

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
        max_intersection_area = 0
        best_workspace = None

        # Get the current workspace grid dimensions
        grid_width = focused_output["workspace"]["grid_width"]
        grid_height = focused_output["workspace"]["grid_height"]
        current_ws_x = focused_output["workspace"]["x"]
        current_ws_y = focused_output["workspace"]["y"]

        # Iterate through all possible workspaces
        for ws_x in range(grid_width):
            for ws_y in range(grid_height):
                # Calculate intersection area with the given view
                intersection_area = self.calculate_intersection_area(
                    view_info["geometry"],
                    ws_x - current_ws_x,
                    ws_y - current_ws_y,
                    monitor
                )

                # Track the workspace with the maximum intersection area
                if intersection_area > max_intersection_area:
                    max_intersection_area = intersection_area
                    best_workspace = {"x": ws_x, "y": ws_y}

        return best_workspace


    def get_views_from_active_workspace(self):
        active_workspace = self.get_active_workspace_info()
        workspace_with_views = self.get_workspaces_with_views()
 
        if not workspace_with_views or not active_workspace:
            return []

        return [
            view["view-id"]
            for view in workspace_with_views
            if view["x"] == active_workspace["x"] and view["y"] == active_workspace["y"]
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

    def get_view_output_id(self, view_id: int):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("output-id")
        return None

    def get_view_output_name(self, view_id: int):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("output-name")
        return None

    def is_view_fullscreen(self, view_id: int):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("fullscreen")
        return None

    def is_view_focusable(self, view_id: int):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("focusable")
        return None

    def get_view_geometry(self, view_id: int):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("geometry")
        return None

    def is_view_minimized(self, view_id: int):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("minimized")
        return None

    def is_view_maximized(self, view_id: int):
        tiled_edges = self.get_view_tiled_edges(view_id)
        if tiled_edges is not None:
            return tiled_edges == 15
        return False

    def get_view_tiled_edges(self, view_id: int):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("tiled-edges")
        return None

    def get_view_title(self, view_id: int):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("title")
        return None

    def get_view_type(self, view_id: int):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("type")
        return None

    def get_view_app_id(self, view_id: int):
        view = self.socket.get_view(view_id)
        if view is not None:
            return view.get("app-id")
        return None

    def get_view_role(self, view_id: int):
        view_info = self.get_view_info(view_id)
        if view_info is not None:
            return view_info.get("role")
        return None

    def get_view_bbox(self, view_id: int):
        view_info = self.get_view_info(view_id)
        if view_info is not None:
            return view_info.get("bbox")
        return None

    def get_view_layer(self, view_id: int):
        view_layer_content = self.get_view_layer(view_id)
        if view_layer_content:
            return view_layer_content.get("layer")
        return None

    def maximize_focused_view(self):
        view = self.socket.get_focused_view()
        self.socket.assign_slot(view["id"], "slot_c")

    def find_view_by_pid(self, pid: int):
        lviews = self.socket.list_views()
        if not lviews:
            return
        view = [view for view in lviews if view["pid"] == pid]
        if view:
            return view[0]

    def find_device_id(self, name_or_id_or_type: str):
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
        assert device_id is not None, f"Device with arguments {args} not found."
        msg = self.socket.configure_input_device(device_id, False)
        return msg

    def enable_input_device(self, args):
        device_id = self.find_device_id(args)
        assert device_id is not None, f"Device with arguments {args} not found."
        msg = self.socket.configure_input_device(device_id, True)
        return msg

    def set_view_maximized(self, view_id: int):
        self.socket.assign_slot(view_id, "slot_c")

    def maximize_all_views_from_active_workspace(self):
        for view_id in self.get_views_from_active_workspace():
            if not self.is_view_fullscreen(view_id):
                self.set_view_maximized(view_id)

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

    def calculate_intersection_area(self, view: dict, ws_x: int, ws_y: int, monitor: dict):
        # Calculate workspace rectangle
        workspace_start_x = ws_x * monitor["width"]
        workspace_start_y = ws_y * monitor["height"]
        workspace_end_x = workspace_start_x + monitor["width"]
        workspace_end_y = workspace_start_y + monitor["height"]

        # Calculate view rectangle
        view_start_x = view["x"]
        view_start_y = view["y"]
        view_end_x = view_start_x + view["width"]
        view_end_y = view_start_y + view["height"]

        # Calculate intersection coordinates
        inter_start_x = max(view_start_x, workspace_start_x)
        inter_start_y = max(view_start_y, workspace_start_y)
        inter_end_x = min(view_end_x, workspace_end_x)
        inter_end_y = min(view_end_y, workspace_end_y)

        # Calculate intersection area
        inter_width = max(0, inter_end_x - inter_start_x)
        inter_height = max(0, inter_end_y - inter_start_y)
        return inter_width * inter_height

    def set_view_top_left(self, view_id: int):
        self.socket.assign_slot(view_id, "slot_tl")

    def set_view_top_right(self, view_id: int):
        self.socket.assign_slot(view_id, "slot_tr")

    def set_view_bottom_left(self, view_id: int):
        self.socket.assign_slot(view_id, "slot_bl")

    def set_view_right(self, view_id: int):
        self.socket.assign_slot(view_id, "slot_r")

    def set_view_left(self, view_id: int):
        self.socket.assign_slot(view_id, "slot_l")

    def set_view_bottom(self, view_id: int):
        self.socket.assign_slot(view_id, "slot_b")

    def set_view_top(self, view_id: int):
        self.socket.assign_slot(view_id, "slot_t")

    def set_view_center(self, view_id: int):
        self.socket.assign_slot(view_id, "slot_c")

    def set_view_bottom_right(self, view_id: int):
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

