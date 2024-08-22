from itertools import filterfalse
from typing import Any, List, Optional
from wayfire import WayfireSocket
from wayfire.extra.stipc import Stipc

class WayfireUtils:
    def __init__(self, socket: WayfireSocket):
        self._socket = socket
        self._stipc = Stipc(socket)

    def _find_view_middle_cursor_position(self, view_geometry: dict, monitor_geometry: dict):
        # Calculate the middle position of the view
        view_middle_x = view_geometry["x"] + view_geometry["width"] // 2
        view_middle_y = view_geometry["y"] + view_geometry["height"] // 2

        # Calculate the offset from the monitor's top-left corner
        cursor_x = monitor_geometry["x"] + view_middle_x
        cursor_y = monitor_geometry["y"] + view_middle_y

        return cursor_x, cursor_y

    def center_cursor_on_view(self, view_id):
        view = self._socket.get_view(view_id)
        output_id = view["output-id"]
        view_geometry = view["geometry"]
        output_geometry = self._socket.get_output(output_id)["geometry"]
        cursor_x, cursor_y = self._find_view_middle_cursor_position(
            view_geometry, output_geometry
        )
        self._stipc.move_cursor(cursor_x, cursor_y)

    def move_view_to_empty_workspace(self, view_id: int):
        top_level_mapped_view = self._socket.get_view(view_id)["role"] == "toplevel"
        assert top_level_mapped_view, f"Unable to move view with ID {view_id}: view not found or not top-level."

        empty_workspace = self.get_workspaces_without_views()
        assert empty_workspace, "No empty workspace available."

        empty_workspace = empty_workspace[0]
        self._socket.set_workspace(empty_workspace[0], empty_workspace[1], view_id)

    def get_tile_list_views(self, layout):
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
            list += self.get_tile_list_views(child)
        return list

    def get_focused_output_views(self):
        return [
            view for view in self._socket.list_views()
            if view["output-id"] == self._socket.get_focused_output()["id"]
        ]

    def list_pids(self):
        return [view["pid"] for view in self._socket.list_views() if view["pid"] != -1]

    def list_ids(self):
        return [view["id"] for view in self._socket.list_views()]

    def list_outputs_ids(self):
        return [i["id"] for i in self._socket.list_outputs()]

    def list_outputs_names(self):
        return [i["name"] for i in self._socket.list_outputs()]

    def _sum_geometry_resolution(self):
        outputs = self._socket.list_outputs()
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
                self._socket.set_workspace(workspace_x, workspace_y)
        self._socket.set_focus(view_id)

    def get_focused_view_pid(self):
        view = self._socket.get_focused_view()
        if view is not None:
            view_id = self._socket.get_focused_view()
            if view_id is not None:
                view_id = view_id["id"]
                return self.get_view_pid(view_id)

    def has_ouput_fullscreen_view(self, output_id):
        # any fullscreen doesn't matter from what workspace
        list_views = self._socket.list_views()
        if not list_views:
            return
        if any(
            True
            for i in list_views
            if i["fullscreen"] is True and i["output-id"] == output_id
        ):
            return True

    def get_focused_view_role(self):
        focused_view_info = self._socket.get_focused_view()
        if focused_view_info is not None:
            return focused_view_info.get("role")

    def get_focused_view_bbox(self):
        focused_view = self._socket.get_focused_view()
        if focused_view is not None:
            return focused_view.get("bbox")

    def get_focused_view_layer(self):
        focused_view = self._socket.get_focused_view()
        if focused_view is not None:
            return focused_view.get("layer")

    def get_focused_view_id(self):
        focused_view = self._socket.get_focused_view()
        if focused_view is not None:
            return focused_view.get("id")

    def get_focused_view_output(self):
        focused_view = self._socket.get_focused_view()
        if focused_view is not None:
            return focused_view.get("output-id")

    def list_filtered_views(self):
        views = self._socket.list_views()
        filtered_views = [
            view for view in views
            if view["role"] == "toplevel"
            and view["app-id"] != "nil"
            and view["pid"] != -1
        ]
        return filtered_views


    def get_focused_view_title(self):
        focused_view = self._socket.get_focused_view()
        return (
            focused_view["title"]
            if focused_view and focused_view in self.list_filtered_views()
            else None
        )

    def get_focused_view_type(self):
        return self._socket.get_focused_view()["type"]

    def get_focused_view_app_id(self):
        return self._socket.get_focused_view()["app-id"]

    def get_active_workspace_number(self):
        focused_output = self._socket.get_focused_output()
        x = focused_output["workspace"]["x"]
        y = focused_output["workspace"]["y"]
        return self.get_workspace_number(x, y)

    def get_workspace_number(self, workspace_x: int, workspace_y: int):
        workspaces_coordinates = self._total_workspaces()
        if not workspaces_coordinates:
            return

        coordinates_to_find = [
            i for i in workspaces_coordinates.values() if [workspace_x, workspace_y] == i
        ]
        if not coordinates_to_find:
            return

        coordinates_to_find = coordinates_to_find[0]
        total_workspaces = len(workspaces_coordinates)
        rows = int(total_workspaces**0.5)
        cols = (total_workspaces + rows - 1) // rows

        row, col = coordinates_to_find
        if 0 <= row < rows and 0 <= col < cols:
            return row * cols + col + 1

    def get_active_workspace_info(self):
        focused_output = self._socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("workspace")
        return None

    def get_focused_output_name(self):
        focused_output = self._socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("name")
        return None

    def get_focused_output_id(self):
        focused_output = self._socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("id")
        return None

    def get_output_id_by_name(self, output_name: str):
        for output in self._socket.list_outputs():
            if output["name"] == output_name:
                return output["id"]

    def get_output_name_by_id(self, output_id: int):
        for output in self._socket.list_outputs():
            if output["id"] == output_id:
                return output["name"]

    def get_focused_output_geometry(self):
        focused_output = self._socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("geometry")
        return None

    def get_focused_output_workarea(self):
        focused_output = self._socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("workarea")
        return None

    def get_view_pid(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            pid = view["pid"]
            return pid

    def go_next_workspace(self):
        all_workspaces = self._total_workspaces()
        if not all_workspaces:
            return

        workspaces = list(all_workspaces.values())
        active_workspace = self._socket.get_focused_output()["workspace"]

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
            self._socket.set_workspace(workspace_x, workspace_y)

    def _get_previous_workspace(self, workspace_x: int, workspace_y: int):
        total_workspaces = self._total_workspaces()

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

    def _get_next_workspace(self, workspace_x: int, workspace_y: int):
        total_workspaces = self._total_workspaces()

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
        focused_output = self._socket.get_focused_output()
        current_x = focused_output['workspace']['x']
        current_y = focused_output['workspace']['y']

        ws_with_views = self.get_workspaces_with_views()

        if not ws_with_views:
            return

        # Extract unique workspaces with views
        unique_workspaces = { (ws['x'], ws['y']) for ws in ws_with_views }

        # Ensure that unique_workspaces are sorted to maintain a consistent order
        sorted_workspaces = sorted(unique_workspaces, key=lambda d: (d[1], d[0]))  # Sort by y, then x
 
        # Find the index of the current workspace in the sorted list of workspaces with views
        current_ws_index = next((i for i, (x, y) in enumerate(sorted_workspaces)
                                if x == current_x and y == current_y), None)
        if current_ws_index is None:
            return

        # Calculate the index of the next workspace cyclically
        next_index = (current_ws_index + 1) % len(sorted_workspaces)
        next_ws = sorted_workspaces[next_index]

        # Set the next workspace
        workspace_x, workspace_y = next_ws
        self._socket.set_workspace(workspace_x, workspace_y)

    def go_previous_workspace(self):
        current_workspace = self.get_active_workspace_number()
        if current_workspace is None:
            return

        current_workspace_coords = self._total_workspaces().get(current_workspace, None)
        if current_workspace_coords is None:
            return

        # Retrieve the previous workspace coordinates
        previous_workspace_coords = self._get_previous_workspace(*current_workspace_coords)
        if previous_workspace_coords is None:
            return

        # Set the previous workspace
        workspace_x, workspace_y = previous_workspace_coords
        self._socket.set_workspace(workspace_x, workspace_y)

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
        focused_output = self._socket.get_focused_output()
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
                        intersection_area = self._calculate_intersection_area(
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
        total_workspaces = self._total_workspaces()
        if not total_workspaces:
            return
        all_workspaces = list(total_workspaces.values())
        return list(filterfalse(lambda x: x in workspace_with_views, all_workspaces))

    def get_workspace_coordinates(self, view_info):
        focused_output = self._socket.get_focused_output()
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
                intersection_area = self._calculate_intersection_area(
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
 
    def get_view_output_id(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            return view.get("output-id")
        return None

    def get_view_output_name(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            return view.get("output-name")
        return None

    def is_view_fullscreen(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            return view.get("fullscreen")
        return None

    def is_view_focusable(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            return view.get("focusable")
        return None

    def get_view_geometry(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            return view.get("geometry")
        return None

    def is_view_minimized(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            return view.get("minimized")
        return None

    def is_view_maximized(self, view_id: int):
        tiled_edges = self.get_view_tiled_edges(view_id)
        if tiled_edges is not None:
            return tiled_edges == 15
        return False

    def get_view_tiled_edges(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            return view.get("tiled-edges")
        return None

    def get_view_title(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            return view.get("title")
        return None

    def get_view_type(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            return view.get("type")
        return None

    def get_view_app_id(self, view_id: int):
        view = self._socket.get_view(view_id)
        if view is not None:
            return view.get("app-id")
        return None

    def get_view_role(self, view_id: int):
        view_info = self._socket.get_view(view_id)
        if view_info is not None:
            return view_info.get("role")
        return None

    def get_view_bbox(self, view_id: int):
        view_info = self._socket.get_view(view_id)
        if view_info is not None:
            return view_info.get("bbox")
        return None

    def get_view_layer(self, view_id: int):
        view_layer_content = self.get_view_layer(view_id)
        if view_layer_content:
            return view_layer_content.get("layer")
        return None

    def find_views(self, value: Any, key: Optional[str] = None) -> Optional[List[dict]]:
        """
        Find and return a list of views from the Wayfire compositor that match a specified value.

        The function searches through the list of views obtained from the Wayfire socket. 
        It can either search for a value within a specific key in the view dictionaries 
        or search across all key-value pairs if no key is specified.

        Args:
            value: The value to search for. Can be a string, number, or other data type.
            key (Optional[str], optional): The specific key in the view dictionary to search within. 
                                           If not provided, the function will search all key-value pairs.

        Returns:
            Optional[List[dict]]: A list of views (dictionaries) where the specified value is found.
                                  Returns None if no matching views are found.

        Raises:
            TypeError: If an integer is passed as `value` without a specified `key`.

        Example:
            views = self.find_views('kitty', key='app-id')
            # This will return all views where the app-id is 'kitty'.

            views = self.find_views('IPython')
            # This will return all views where any value, including titles, matches 'IPython'.
        """

        if isinstance(value, int) and key is None:
            raise TypeError(
                "Cannot use an integer as 'value' without specifying a 'key'. "
                "Integers are only allowed with a specified 'key'."
            )

        def value_matches(val: Any, item: Any) -> bool:
            if isinstance(item, (str, list, dict, set, tuple)):
                return val in item
            return item == val

        views: List[dict] = [
            view for view in self._socket.list_views()
            if (key and key in view and value_matches(value, view[key])) or
               (not key and any(value_matches(value, v) for v in view.values()))
        ]

        return views if views else None

    def find_device_id(self, name_or_id_or_type: str):
        devices = self._socket.list_input_devices()
        for dev in devices:
            if (
                dev["name"] == name_or_id_or_type
                or str(dev["id"]) == name_or_id_or_type
                or dev["type"] == name_or_id_or_type
            ):
                return dev["id"]
        assert False, f"Device with name, ID, or type '{name_or_id_or_type}' not found."

    def disable_input_device(self, args):
        device_id = self.find_device_id(args)
        assert device_id is not None, f"Device with arguments {args} not found."
        msg = self._socket.configure_input_device(device_id, False)
        return msg

    def enable_input_device(self, args):
        device_id = self.find_device_id(args)
        assert device_id is not None, f"Device with arguments {args} not found."
        msg = self._socket.configure_input_device(device_id, True)
        return msg

    def set_view_maximized(self, view_id: int):
        self._socket.assign_slot(view_id, "slot_c")

    def _total_workspaces(self):
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

    def _calculate_intersection_area(self, view: dict, ws_x: int, ws_y: int, monitor: dict):
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
        self._socket.assign_slot(view_id, "slot_tl")

    def set_view_top_right(self, view_id: int):
        self._socket.assign_slot(view_id, "slot_tr")

    def set_view_bottom_left(self, view_id: int):
        self._socket.assign_slot(view_id, "slot_bl")

    def set_view_right(self, view_id: int):
        self._socket.assign_slot(view_id, "slot_r")

    def set_view_left(self, view_id: int):
        self._socket.assign_slot(view_id, "slot_l")

    def set_view_bottom(self, view_id: int):
        self._socket.assign_slot(view_id, "slot_b")

    def set_view_top(self, view_id: int):
        self._socket.assign_slot(view_id, "slot_t")

    def set_view_center(self, view_id: int):
        self._socket.assign_slot(view_id, "slot_c")

    def set_view_bottom_right(self, view_id: int):
        self._socket.assign_slot(view_id, "slot_br")

    def send_view_to_output(self, view_id: int, output_name: str):
        """
        Sends a view to a specified output.

        Args:
            view_id (int): The ID of the view to be sent.
            output_name (str): The name of the output to which the view will be sent.

        Returns:
            None

        Raises:
            ValueError: If the output name does not correspond to a valid output.
        """
        output_id = self.get_output_id_by_name(output_name)
        if output_id:
            wset = self._socket.get_output(output_id)["wset-index"]
            if view_id:
                self._socket.send_view_to_wset(view_id, wset)

    def get_current_tiling_layout(self):
        output = self._socket.get_focused_output()
        wset = output["wset-index"]
        x = output["workspace"]["x"]
        y = output["workspace"]["y"]
        return self._socket.get_tiling_layout(wset, x, y)

    def set_current_tiling_layout(self, layout):
        output = self._socket.get_focused_output()
        wset = output["wset-index"]
        x = output["workspace"]["x"]
        y = output["workspace"]["y"]
        return self._socket.set_tiling_layout(wset, x, y, layout)
