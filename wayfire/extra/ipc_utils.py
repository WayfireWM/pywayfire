from itertools import filterfalse
from typing import Any, List, Optional, Tuple
from wayfire import WayfireSocket
from wayfire.extra.stipc import Stipc


class WayfireUtils:
    def __init__(self, socket: WayfireSocket):
        self._socket = socket
        self._stipc = Stipc(socket)

    def _find_view_middle_cursor_position(self, view_geometry: dict, monitor_geometry: dict):
        """
        Calculate the cursor position at the middle of a view.

        This method computes the position of the cursor at the center of a view, 
        taking into account the view's geometry and the monitor's geometry. It returns 
        the coordinates of the cursor relative to the monitor's top-left corner.

        Args:
            view_geometry (dict): A dictionary representing the view with keys 
                                  "x", "y", "width", and "height" for its position 
                                  and dimensions.
            monitor_geometry (dict): A dictionary representing the monitor with keys 
                                     "x" and "y" for its position and dimensions.

        Returns:
            tuple: A tuple (cursor_x, cursor_y) representing the cursor position at 
                   the middle of the view, relative to the monitor's top-left corner.
        """
        # Calculate the middle position of the view
        view_middle_x = view_geometry["x"] + view_geometry["width"] // 2
        view_middle_y = view_geometry["y"] + view_geometry["height"] // 2

        # Calculate the offset from the monitor's top-left corner
        cursor_x = monitor_geometry["x"] + view_middle_x
        cursor_y = monitor_geometry["y"] + view_middle_y

        return cursor_x, cursor_y

    def center_cursor_on_view(self, view_id: int) -> None:
        """
        Centers the cursor on the specified view by calculating the middle position
        of the view on its associated output.

        Args:
            view_id (int): The ID of the view to center the cursor on.
        """
        output_id = self.get_view_output_id(view_id)
        if output_id is None:
            return

        view_geometry = self.get_view_geometry(view_id)
        if view_geometry is None:
            return

        output_geometry = self.get_output_geometry(output_id)
        if output_geometry is None:
            return

        # Calculate the middle cursor position based on view and output geometries
        cursor_x, cursor_y = self._find_view_middle_cursor_position(view_geometry, output_geometry)

        # Move the cursor to the calculated position
        self._stipc.move_cursor(cursor_x, cursor_y)

    def move_view_to_empty_workspace(self, view_id: int) -> None:
        """
        Moves a top-level view to an empty workspace.

        This method performs the following steps:
        - Verifies that the view with the given ID is a top-level view.
        - Identifies an empty workspace that currently does not have any views.
        - Moves the specified view to the identified empty workspace.

        Args:
            view_id (int): The ID of the view to be moved.

        Raises:
            AssertionError: If the view is not top-level or if no empty workspace is available.
        """
        top_level_mapped_view = self.get_view_role(view_id) == "toplevel"
        assert top_level_mapped_view, f"Unable to move view with ID {view_id}: view not found or not top-level."

        empty_workspace = self.get_workspaces_without_views()
        assert empty_workspace, "No empty workspace available."

        empty_workspace = empty_workspace[0]
        self._socket.set_workspace(empty_workspace[0], empty_workspace[1], view_id)

    def get_focused_output_views(self):
        return [
            view for view in self._socket.list_views()
            if view["output-id"] == self.get_focused_output_id()
        ]

    def list_pids(self):
        return [view["pid"] for view in self._socket.list_views() if view["pid"] != -1]

    def list_ids(self):
        return [view["id"] for view in self._socket.list_views()]

    def list_outputs_ids(self):
        return [i["id"] for i in self._socket.list_outputs()]

    def list_outputs_names(self):
        return [i["name"] for i in self._socket.list_outputs()]

    def _get_plugins(self) -> List[str]:
        """
        Fetches the current list of plugins from the socket and parses it into a list.

        :return: A list of plugin names.
        """
        plugins_value = self._socket.get_option_value("core/plugins")["value"]
        return plugins_value.split()

    def _set_plugins(self, plugins: List[str]) -> None:
        """
        Updates the list of plugins by converting the list to a space-separated string 
        and setting it via the socket.

        :param plugins: A list of plugin names to be set.
        """
        plugins_value = " ".join(plugins)
        self._socket.set_option_values({"core/plugins": plugins_value})

    def set_plugin(self, plugin_name: str, enabled: Optional[bool] = True) -> None:
        """
        Enables or disables a plugin based on the 'enabled' flag.

        :param plugin_name: The name of the plugin to set.
        :param enabled: If True, enables the plugin. If False, disables it. Defaults to True.
        """
        plugins = self._get_plugins()

        if enabled:
            if plugin_name not in plugins:
                plugins.append(plugin_name)
        else:
            plugins = [plugin for plugin in plugins if plugin_name not in plugin]

        self._set_plugins(plugins)

    def is_plugin_enabled(self, plugin_name: str) -> bool:
        """
        Checks whether a plugin is enabled.

        :param plugin_name: The name of the plugin to check.
        :return: True if the plugin is enabled, False otherwise.
        """
        plugins = self._get_plugins()
        return plugin_name in plugins

    def _sum_geometry_resolution(self):
        """
        Calculate the total width and height of all connected outputs.

        This method retrieves the list of connected monitors (outputs),
        sums their geometrical widths and heights, and returns the total width and 
        height as a tuple.

        Returns:
            tuple: A tuple containing two integers:
                - total_width (int): The sum of the widths of all connected outputs.
                - total_height (int): The sum of the heights of all connected outputs.
        """
        outputs = self._socket.list_outputs()
        total_width = 0
        total_height = 0
        for output in outputs:
            total_width += output["geometry"]["width"]
            total_height += output["geometry"]["height"]
        return total_width, total_height

    def get_active_workspace(self):
        """
        Retrieve the coordinates of the active workspace.

        This method calls `get_active_workspace_info()` to obtain information 
        about the currently active workspace. If the workspace information is 
        available, it extracts the `x` and `y` coordinates and returns them as 
        a dictionary.

        Returns:
            dict: A dictionary with two keys:
                - "x" (int): The column index of the active workspace.
                - "y" (int): The row index of the active workspace.
        """
        data = self.get_active_workspace_info()
        if data:
            x = data["x"]
            y = data["y"]
            return {"x": x, "y": y}

    def go_workspace_set_focus(self, view_id: int) -> None:
        """
        Moves the focus to the workspace containing the specified view and sets the focus to the view.

        This method performs the following steps:
        - Determines the workspace associated with the given view ID.
        - Retrieves the currently active workspace.
        - If the view's workspace is different from the active workspace, it switches to the view's workspace.
        - Sets the focus to the specified view.

        Args:
            view_id (int): The ID of the view to which the focus should be set.

        Notes:
            The function assumes that the `view_id` is valid and that the workspace retrieval methods return appropriate values.
        """
        workspace = self.get_workspace_from_view(view_id)
        active_workspace = self.get_active_workspace()
        if workspace and active_workspace:
            workspace_x, workspace_y = active_workspace.values()
            if active_workspace != workspace:
                self._socket.set_workspace(workspace_x, workspace_y)
        self._socket.set_focus(view_id)

    def has_ouput_fullscreen_view(self, output_id):
        """
        Check if there is any fullscreen view on the specified output.

        This method retrieves the list of views and checks
        if any view is currently fullscreen on the specified output. It does not
        consider the workspace of the view; it only checks the fullscreen status
        and output ID.

        Args:
            output_id (str): The ID of the output to check for fullscreen views.

        Returns:
            bool: True if there is at least one fullscreen view on the specified 
                  output, otherwise False.
        """
        list_views = self._socket.list_views()
        if not list_views:
            return
        if any(
            True
            for i in list_views
            if i["fullscreen"] is True and i["output-id"] == output_id
        ):
            return True

    def list_filtered_views(self):
        """
        List all filtered views based on specific criteria.

        This method retrieves all views and filters them based on the following criteria:
        - The view's role must be "toplevel".
        - The view's application ID must not be "nil".
        - The view's process ID (PID) must not be -1.

        Returns:
            list: A list of dictionaries, where each dictionary represents a view 
                  that meets the criteria. Each view contains details such as role, 
                  application ID, and PID.
        """
        views = self._socket.list_views()
        filtered_views = [
            view for view in views
            if view["role"] == "toplevel"
            and view["app-id"] != "nil"
            and view["pid"] != -1
        ]
        return filtered_views

    def get_active_workspace_number(self):
        """
        Retrieve the number of the currently active workspace.

        This method gets the current workspace information, including its `x` and `y` 
        coordinates, and uses these coordinates to determine the workspace number 
        by calling `get_workspace_number`.

        Returns:
            int: The number of the currently active workspace. Returns None if 
                  workspace information is not available.
        """
        workspace = self.get_active_workspace_info()
        if workspace:
            return self.get_workspace_number(workspace["x"], workspace["y"])

    def get_workspace_number(self, workspace_x: int, workspace_y: int):
        """
        Retrieve the workspace number corresponding to the given coordinates.

        This method compares the provided `workspace_x` and `workspace_y` coordinates 
        with a list of all available workspace coordinates. It returns the workspace 
        number if a match is found.

        Args:
            workspace_x (int): The x-coordinate of the workspace.
            workspace_y (int): The y-coordinate of the workspace.

        Returns:
            int: The number of the workspace that matches the given coordinates. 
                  Returns None if no matching workspace is found.
        """
        workspaces_coordinates = self._total_workspaces()
        if not workspaces_coordinates:
            return None
        for workspace_number, coords in workspaces_coordinates.items():
            if coords == [workspace_x, workspace_y]:
                return workspace_number
        return None

    def get_active_workspace_info(self):
        """
        Retrieve information about the currently active workspace.

        This method obtains the focused output from the Wayfire socket and returns 
        the workspace information associated with it. If no focused output is found, 
        it returns None.

        Returns:
            dict or None: A dictionary containing information about the active workspace, 
                          if available. The dictionary typically includes workspace 
                          coordinates or other relevant details. Returns None if no 
                          focused output is found.
        """
        focused_output = self._socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get("workspace")
        return None

    def get_output_id_by_name(self, output_name: str):
        """
        Retrieve the ID of an output by its name.

        This method iterates through the list of outputs and returns the ID of the 
        output that matches the given `output_name`. If no matching output is found, 
        it returns None.

        Args:
            output_name (str): The name of the output to find.

        Returns:
            str or None: The ID of the output with the specified name, or None if no 
                         matching output is found.
        """
        for output in self._socket.list_outputs():
            if output["name"] == output_name:
                return output["id"]

    def get_output_name_by_id(self, output_id: int):
        """
        Retrieve the name of an output by its ID.

        This method iterates through the list of outputs and returns the name of the 
        output that matches the given `output_id`. If no matching output is found, 
        it returns None.

        Args:
            output_id (int): The ID of the output to find.

        Returns:
            str or None: The name of the output with the specified ID, or None if no 
                         matching output is found.
        """
        for output in self._socket.list_outputs():
            if output["id"] == output_id:
                return output["name"]

    def get_output(self, output_id: int, key: str):
        output = self._socket.get_output(output_id)
        if output is not None:
            return output.get(key)
        return None

    def get_output_id(self, output_id: int):
        return self.get_output(output_id, "id")

    def get_output_name(self, output_id: int):
        return self.get_output(output_id, "name")

    def get_output_geometry(self, output_id: int):
        return self.get_output(output_id, "geometry")

    def get_output_workarea(self, output_id: int):
        return self.get_output(output_id, "workarea")

    def get_output_workspace(self, output_id: int):
        return self.get_output(output_id, "workspace")

    def get_output_wset_index(self, output_id: int):
        return self.get_output(output_id, "wset-index")

    def get_focused_output(self, key: str):
        focused_output = self._socket.get_focused_output()
        if focused_output is not None:
            return focused_output.get(key)
        return None

    def get_focused_output_id(self):
        return self.get_focused_output("id")

    def get_focused_output_name(self):
        return self.get_focused_output("name")

    def get_focused_output_geometry(self):
        return self.get_focused_output("geometry")

    def get_focused_output_workarea(self):
        return self.get_focused_output("workarea")

    def get_focused_output_workspace(self):
        return self.get_focused_output("workspace")

    def get_focused_output_wset_index(self):
        return self.get_focused_output("wset-index")

    def get_focused_view(self, key: str):
        focused_view = self._socket.get_focused_view()
        if focused_view is not None:
            return focused_view.get(key)
        return None

    def get_focused_view_id(self):
        return self.get_focused_view("id")

    def get_focused_view_title(self):
        return self.get_focused_view("title")

    def get_focused_view_geometry(self):
        return self.get_focused_view("geometry")

    def get_focused_view_base_geometry(self):
        return self.get_focused_view("base-geometry")

    def get_focused_view_bbox(self):
        return self.get_focused_view("bbox")

    def get_focused_view_max_size(self):
        return self.get_focused_view("max-size")

    def get_focused_view_min_size(self):
        return self.get_focused_view("min-size")

    def get_focused_view_layer(self):
        return self.get_focused_view("layer")

    def get_focused_view_output_id(self):
        return self.get_focused_view("output-id")

    def get_focused_view_output_name(self):
        return self.get_focused_view("output-name")

    def get_focused_view_pid(self):
        return self.get_focused_view("pid")

    def get_focused_view_role(self):
        return self.get_focused_view("role")

    def get_focused_view_sticky(self):
        return self.get_focused_view("sticky")

    def get_focused_view_tiled_edges(self):
        return self.get_focused_view("tiled-edges")

    def get_focused_view_wset_index(self):
        return self.get_focused_view("wset-index")

    def get_view(self, view_id: int, key: str):
        view = self._socket.get_view(view_id)

        if view is not None:
            return view.get(key, None)
        return None

    def get_view_activated(self, view_id: int):
        return self.get_view(view_id, "activated")

    def get_view_app_id(self, view_id: int):
        return self.get_view(view_id, "app-id")

    def get_view_base_geometry(self, view_id: int):
        return self.get_view(view_id, "base-geometry")

    def get_view_bbox(self, view_id: int):
        return self.get_view(view_id, "bbox")

    def get_view_focusable(self, view_id: int):
        return self.get_view(view_id, "focusable")

    def get_view_fullscreen(self, view_id: int):
        return self.get_view(view_id, "fullscreen")

    def get_view_geometry(self, view_id: int):
        return self.get_view(view_id, "geometry")

    def get_view_id(self, view_id: int):
        return self.get_view(view_id, "id")

    def get_view_last_focus_timestamp(self, view_id: int):
        return self.get_view(view_id, "last-focus-timestamp")

    def get_view_layer(self, view_id: int):
        return self.get_view(view_id, "layer")

    def get_view_mapped(self, view_id: int):
        return self.get_view(view_id, "mapped")

    def get_view_max_size(self, view_id: int):
        return self.get_view(view_id, "max-size")

    def get_view_min_size(self, view_id: int):
        return self.get_view(view_id, "min-size")

    def get_view_minimized(self, view_id: int):
        return self.get_view(view_id, "minimized")

    def get_view_output_id(self, view_id: int):
        return self.get_view(view_id, "output-id")

    def get_view_output_name(self, view_id: int):
        return self.get_view(view_id, "output-name")

    def get_view_parent(self, view_id: int):
        return self.get_view(view_id, "parent")

    def get_view_pid(self, view_id: int):
        return self.get_view(view_id, "pid")

    def get_view_role(self, view_id: int):
        return self.get_view(view_id, "role")

    def get_view_sticky(self, view_id: int):
        return self.get_view(view_id, "sticky")

    def get_view_tiled_edges(self, view_id: int):
        return self.get_view(view_id, "tiled-edges")

    def get_view_title(self, view_id: int):
        return self.get_view(view_id, "title")

    def get_view_type(self, view_id: int):
        return self.get_view(view_id, "type")

    def get_view_wset_index(self, view_id: int):
        return self.get_view(view_id, "wset-index")

    def _get_adjacent_workspace(self, workspace_x: int, workspace_y: int, direction: str) -> Optional[Tuple[int, int]]:
        """
        Retrieves the coordinates of an adjacent workspace based on the specified direction.

        This function finds the workspace coordinates adjacent to the given `workspace_x` and `workspace_y`
        based on the provided `direction`. The function handles three directions:
        - "current": Returns the current workspace coordinates.
        - "previous": Returns the coordinates of the previous workspace in the sorted list.
        - "next": Returns the coordinates of the next workspace in the sorted list.

        The list of unique workspaces is sorted by row (y) and then column (x) to determine adjacency.

        Parameters:
        - workspace_x (int): The x-coordinate of the current workspace.
        - workspace_y (int): The y-coordinate of the current workspace.
        - direction (str): The direction to move. Should be one of 'current', 'previous', or 'next'.

        Returns:
        - Optional[Tuple[int, int]]: The coordinates of the adjacent workspace as a tuple (x, y),
          or `None` if the direction is invalid or if no adjacent workspace is found.

        Raises:
        - ValueError: If an invalid direction is specified.
        """
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

        if direction == "current":
            return unique_workspaces[active_index]
        elif direction == "previous":
            adjacent_index = (active_index - 1) % len(unique_workspaces)
        elif direction == "next":
            # Calculate the index of the next workspace cyclically
            adjacent_index = (active_index + 1) % len(unique_workspaces)
        else:
            raise ValueError("Invalid direction specified. Use 'current', 'previous', or 'next'.")

        return unique_workspaces[adjacent_index]

    def _get_previous_workspace(self, workspace_x: int, workspace_y: int) -> Optional[Tuple[int, int]]:
        return self._get_adjacent_workspace(workspace_x, workspace_y, "previous")

    def _get_next_workspace(self, workspace_x: int, workspace_y: int) -> Optional[Tuple[int, int]]:
        return self._get_adjacent_workspace(workspace_x, workspace_y, "next")

    def _get_next_workspace_with_views(self, current_x: int, current_y: int):
        return self.get_workspaces_with_views(current_x, current_y, "next")

    def _get_previous_workspace_with_views(self, current_x: int, current_y: int):
        return self.get_workspaces_with_views(current_x, current_y, "previous")

    def _go_workspace(self, direction: str, with_views: bool = False):
        """
        Navigate to the previous, next, or next workspace with views based on the given direction.
 
        :param direction: 'previous' to go to the previous workspace, 'next' to go to the next workspace.
        :param with_views: If True, go to the next workspace with views instead of any workspace.
        """
        workspace = self.get_focused_output_workspace()
        if workspace:
            current_x = workspace['x']
            current_y = workspace['y']

            if with_views:
                if direction == 'next':
                    target_workspace_coords = self._get_next_workspace_with_views(current_x, current_y)
                elif direction == 'previous':
                    target_workspace_coords = self._get_previous_workspace_with_views(current_x, current_y)
                else:
                    print("Invalid direction for workspaces with views. Use 'next' or 'previous'.")
                    return
            else:
                if direction == 'previous':
                    target_workspace_coords = self._get_previous_workspace(current_x, current_y)
                elif direction == 'next':
                    target_workspace_coords = self._get_next_workspace(current_x, current_y)
                else:
                    print("Invalid direction. Use 'previous' or 'next'.")
                    return
 
            if target_workspace_coords is None:
                return

            workspace_x, workspace_y = target_workspace_coords
            self._socket.set_workspace(workspace_x, workspace_y)

    def go_previous_workspace(self):
        self._go_workspace("previous")

    def go_next_workspace(self):
        self._go_workspace("next")

    def go_next_workspace_with_views(self):
        self._go_workspace("next", with_views=True)

    def go_previous_workspace_with_views(self):
        self._go_workspace("previous", with_views=True)

    def get_workspace_from_view(self, view_id):
        """
        Retrieve the workspace coordinates associated with a specific view.

        This method checks a list of workspaces that have views and returns the coordinates 
        (x and y) of the workspace that contains the view with the given `view_id`. If no 
        matching workspace is found, it returns None.

        Args:
            view_id: The ID of the view whose workspace coordinates are to be retrieved.

        Returns:
            dict or None: A dictionary with keys "x" and "y" representing the coordinates 
                          of the workspace containing the view. Returns None if no matching 
                          workspace is found.
        """
        ws_with_views = self.get_workspaces_with_views()
        if ws_with_views:
            for ws in ws_with_views:
                if ws["view-id"] == view_id:
                    return {"x": ws["x"], "y": ws["y"]}

    def has_workspace_views(self, workspace_x, workspace_y):
        """
        Check if a workspace has any views.

        This method checks if there are any views associated with a workspace specified 
        by `workspace_x` and `workspace_y` coordinates. It iterates through a list of 
        workspaces with views, and if it finds a match, it returns True. If no matching 
        workspace is found, it returns False.

        Args:
            workspace_x (int): The x-coordinate of the workspace to check.
            workspace_y (int): The y-coordinate of the workspace to check.

        Returns:
            bool: True if the specified workspace has views, otherwise False.
        """
        ws_with_views_list = self.get_workspaces_with_views()
        if ws_with_views_list:
            for workspace_with_views in ws_with_views_list:
                del workspace_with_views["view-id"]
                x, y = workspace_with_views.values()
                if [x, y] == [workspace_x, workspace_y]:
                    return True
        return False

    def get_workspaces_with_views(self, current_x = None, current_y = None, direction = None):
        """
        Retrieves workspaces with views.

        If `current_x`, `current_y`, and `direction` are provided, the function will return the next or previous
        workspace with views relative to the given coordinates. If no arguments are provided, it returns all
        workspaces with views.

        Parameters:
        - current_x (int, optional): The x-coordinate of the current workspace.
        - current_y (int, optional): The y-coordinate of the current workspace.
        - direction (str, optional): The direction to move ('next' or 'previous').

        Returns:
        - dict: The next or previous workspace with views based on the provided direction, or a list of all
                workspaces with views if no direction is specified.
        """

        monitor = self.get_focused_output_geometry()
        workspace = self.get_focused_output_workspace()
        ws_with_views = []
        views = self.get_focused_output_views()

        if views and workspace and monitor:
            grid_width = workspace["grid_width"]
            grid_height = workspace["grid_height"]
            current_ws_x = workspace["x"]
            current_ws_y = workspace["y"]

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

        if current_x is None or current_y is None or direction is None:
            return ws_with_views

        # Extract unique workspaces with views
        unique_workspaces = { (ws['x'], ws['y']) for ws in ws_with_views }

        # Ensure that unique_workspaces are sorted to maintain a consistent order
        sorted_workspaces = sorted(unique_workspaces, key=lambda d: (d[1], d[0]))  # Sort by y, then x

        # Find the index of the current workspace in the sorted list of workspaces with views
        current_ws_index = next((i for i, (x, y) in enumerate(sorted_workspaces)
                                if x == current_x and y == current_y), None)
        if current_ws_index is None:
            return None

        # Calculate the index of the target workspace cyclically
        if direction == 'next':
            target_index = (current_ws_index + 1) % len(sorted_workspaces)
        elif direction == 'previous':
            target_index = (current_ws_index - 1) % len(sorted_workspaces)
        else:
            print("Invalid direction. Use 'next' or 'previous'.")
            return None

        return sorted_workspaces[target_index]

    def get_workspaces_without_views(self):
        """
        Retrieve a list of workspaces that do not have any views.

        This method compares the list of workspaces with views to the total list of 
        workspaces and returns a list of workspaces that do not have any associated 
        views. The result is a list of workspace coordinates that are not present in 
        the list of workspaces with views.

        Returns:
            list: A list of workspace coordinates (each as a list of [x, y]) for workspaces 
                  that do not have any views. Returns an empty list if all workspaces have 
                  views or if no workspaces are available.
        """
        workspace_with_views = self.get_workspaces_with_views()
        if not workspace_with_views:
            return
        workspace_with_views = [[i["x"], i["y"]] for i in workspace_with_views]
        total_workspaces = self._total_workspaces()
        if not total_workspaces:
            return
        all_workspaces = list(total_workspaces.values())
        return list(filterfalse(lambda x: x in workspace_with_views, all_workspaces))

    def get_views_from_active_workspace(self):
        """
        Retrieve the IDs of views associated with the currently active workspace.

        This method first obtains the information about the active workspace and the list 
        of workspaces with views. It then returns a list of view IDs that belong to the 
        active workspace. If there are no workspaces with views or the active workspace 
        information is not available, it returns an empty list.

        Returns:
            list: A list of view IDs for views that are in the active workspace. Returns 
                  an empty list if no views are found or if the active workspace information 
                  is not available.
        """
        active_workspace = self.get_active_workspace_info()
        workspace_with_views = self.get_workspaces_with_views()
 
        if not workspace_with_views or not active_workspace:
            return []

        return [
            view["view-id"]
            for view in workspace_with_views
            if view["x"] == active_workspace["x"] and view["y"] == active_workspace["y"]
        ]
 
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
        """
        Find the ID of an input device based on its name, ID, or type.

        This method searches through the list of input devices to find one that matches 
        the provided `name_or_id_or_type`. It checks the device's name, ID, and type 
        against the given value. If a matching device is found, it returns the device's ID. 
        If no matching device is found, it raises an AssertionError.

        Args:
            name_or_id_or_type (str): The name, ID, or type of the device to find.

        Returns:
            str: The ID of the device that matches the given name, ID, or type.

        Raises:
            AssertionError: If no device with the given name, ID, or type is found.
        """
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
        """
        Disable an input device based on provided arguments.

        This method uses the provided arguments to find the corresponding device ID 
        and then disables the input device by calling the appropriate configuration 
        method. If the device is not found, it raises an AssertionError.

        Args:
            args (str): The name, ID, or type of the device to be disabled.

        Returns:
            The result of the device configuration operation.

        Raises:
            AssertionError: If the device cannot be found using the provided arguments.
        """

        device_id = self.find_device_id(args)
        assert device_id is not None, f"Device with arguments {args} not found."
        msg = self._socket.configure_input_device(device_id, False)
        return msg

    def enable_input_device(self, args):
        """
        Enable an input device based on provided arguments.

        This method uses the provided arguments to find the corresponding device ID 
        and then enables the input device by calling the appropriate configuration 
        method. If the device is not found, it raises an AssertionError.

        Args:
            args (str): The name, ID, or type of the device to be enabled.

        Returns:
            The result of the device configuration operation.

        Raises:
            AssertionError: If the device cannot be found using the provided arguments.
        """
        device_id = self.find_device_id(args)
        assert device_id is not None, f"Device with arguments {args} not found."
        msg = self._socket.configure_input_device(device_id, True)
        return msg

    def set_view_maximized(self, view_id: int):
        self._socket.assign_slot(view_id, "slot_c")

    def _total_workspaces(self):
        """
        Get a dictionary of all workspaces with their coordinates.

        This method calculates the total number of workspaces based on the active 
        workspace's grid dimensions (height and width). It then creates a dictionary 
        where each key is a workspace number and each value is a list of coordinates 
        [column, row] corresponding to that workspace.

        Returns:
            dict: A dictionary mapping workspace numbers to their coordinates 
                  [column, row]. The keys are workspace numbers, and the values 
                  are lists containing the column and row indices of the workspaces.
        """
        winfo = self.get_active_workspace_info()
        if not winfo:
            return {}

        total_workspaces = winfo["grid_height"] * winfo["grid_width"]
        workspaces = {}

        # Loop through each row and column to assign workspace numbers and coordinates
        for row in range(winfo["grid_height"]):
            for col in range(winfo["grid_width"]):
                workspace_num = row * winfo["grid_width"] + col + 1
                if workspace_num <= total_workspaces:
                    workspaces[workspace_num] = [col, row]
        return workspaces

    def _calculate_intersection_area(self, view: dict, ws_x: int, ws_y: int, monitor: dict):
        """
        Calculate the intersection area between a view and a workspace.

        This method computes the area of intersection between a given view and a 
        workspace based on their respective rectangles. It calculates the intersection 
        by determining the overlapping coordinates and then computes the area.

        Args:
            view (dict): A dictionary representing the view with keys "x", "y", 
                         "width", and "height" for its position and dimensions.
            ws_x (int): The x-coordinate of the workspace in grid units.
            ws_y (int): The y-coordinate of the workspace in grid units.
            monitor (dict): A dictionary representing the monitor with keys "width" 
                            and "height" for its dimensions.

        Returns:
            int: The area of the intersection between the view and the workspace. 
                 Returns 0 if there is no overlap.
        """
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
            wset = self.get_output_wset_index(output_id)
            if view_id and wset:
                self._socket.send_view_to_wset(view_id, wset)

    def get_tile_list_views(self, layout):
        """
        Retrieve a list of views and their dimensions from a tiling layout.

        This method extracts information about views from the given tiling layout. 
        If the layout contains a single view, it returns a list with that view's ID 
        and dimensions. If the layout contains split sections, it recursively gathers 
        information from child layouts.

        Args:
            layout (dict): A dictionary representing the tiling layout. It may contain 
                           view details or split sections ("horizontal-split" or 
                           "vertical-split") with further child layouts.

        Returns:
            list: A list of tuples, each containing a view ID and its dimensions 
                  (width, height). If the layout contains split sections, the method 
                  recursively processes and combines views from all child layouts.
        """
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

    def get_current_tiling_layout(self):
        """
        Retrieve the current tiling layout of the focused workspace.

        This method obtains the index of the focused workspace set and the coordinates 
        of the focused workspace. It then queries the Wayfire socket for the tiling 
        layout of the workspace.

        Returns:
            The current tiling layout of the focused workspace. The format of the 
            returned layout depends on the Wayfire socket's implementation. If the 
            workspace set index or workspace coordinates are not available, it returns None.
        """
        wset = self.get_focused_view_wset_index()
        ws = self.get_focused_output_workspace()
        if wset and ws:
            return self._socket.get_tiling_layout(wset, ws["x"], ws["y"])

    def set_current_tiling_layout(self, layout):
        """
        Set the tiling layout for the currently focused workspace.

        This method updates the tiling layout of the focused workspace based on 
        the provided `layout`. It retrieves the index of the focused workspace set 
        and the coordinates of the focused workspace, and then applies the new 
        layout via the Wayfire socket.

        Args:
            layout: The new tiling layout to be applied. The format of `layout` 
                    depends on the Wayfire socket's implementation.

        Returns:
            The result of the layout configuration operation. The exact return value 
            depends on the Wayfire socket's implementation.
        """
        wset = self.get_focused_view_wset_index()
        ws = self.get_focused_output_workspace()
        if wset and ws:
            return self._socket.set_tiling_layout(wset, ws["x"], ws["y"], layout)
