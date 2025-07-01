import socket
import json as js
import select 
import time
import os
from typing import Any, List, Optional
from wayfire.core.template import get_msg_template, geometry_to_json

class WayfireSocket:
    def __init__(self, socket_name: str | None=None, allow_manual_search=False):
        if socket_name is None:
            socket_name = os.getenv("WAYFIRE_SOCKET")

        self.socket_name = None
        self.pending_events = []
        self.timeout = 3

        if socket_name is None and allow_manual_search:
            # the last item is the most recent socket file
            socket_list = sorted(
                [
                    os.path.join("/tmp", i)
                    for i in os.listdir("/tmp")
                    if "wayfire-wayland" in i
                ]
            )

            for candidate in socket_list:
                try:
                    self.connect_client(candidate)
                    self.socket_name = candidate
                    break
                except Exception:
                    pass

        elif socket_name is not None:
            self.connect_client(socket_name)
            self.socket_name = socket_name

        if self.socket_name is None:
            raise Exception("Failed to find a suitable Wayfire socket!")

    def connect_client(self, socket_name):
        self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.client.connect(socket_name)

    def is_connected(self):
        if self.client is None:
            return False

        try:
            if self.client.fileno() < 0:
                return False
            return True
        except (socket.error, ValueError):
            return False

    def close(self):
        self.client.close()

    def read_message(self):
        rlen = int.from_bytes(self.read_exact(4), byteorder="little")
        response_message = self.read_exact(rlen)
        if not response_message:
            raise Exception("Received empty response message")
        try:
            response = js.loads(response_message.decode("utf-8"))
        except js.JSONDecodeError as e:
            raise Exception(f"JSON decoding error: {e}")

        if "error" in response and response["error"] == "No such method found!":
            raise Exception(f"Method {response['method']} is not available. \
                    Please ensure that the '{self._wayfire_plugin_from_method(response['method'])}' Wayfire plugin is enabled. \
                    Once enabled, restart Wayfire to ensure that ipc was correctly loaded.")
        elif "error" in response:
            raise Exception(response["error"])
        return response

    def send_json(self, msg):
        if 'method' not in msg:
            raise Exception("Malformed JSON request: missing method!")

        data = js.dumps(msg).encode("utf-8")
        header = len(data).to_bytes(4, byteorder="little")

        if self.is_connected():
            self.client.send(header)
            self.client.send(data)
        else:
            raise Exception("Unable to send data: The Wayfire socket instance is not connected.")

        end_time = time.time() + self.timeout
        while True:
            remaining_time = end_time - time.time()
            if remaining_time <= 0:
                raise Exception("Response timeout")

            readable, _, _ = select.select([self.client], [], [], remaining_time)
            if readable:
                try:
                    response = self.read_message()
                except Exception as e:
                    raise Exception(f"Error reading message: {e}")

                if 'event' in response:
                    self.pending_events.append(response)
                    continue

                return response
            else:
                raise Exception("Response timeout")

    def read_exact(self, n: int):
        response = bytearray()
        while n > 0:
            read_this_time = self.client.recv(n)
            if not read_this_time:
                raise Exception("Failed to read anything from the socket!")
            n -= len(read_this_time)
            response += read_this_time

        return bytes(response)

    def read_next_event(self):
        if self.pending_events:
            return self.pending_events.pop(0)
        return self.read_message()

    def create_headless_output(self, width: int, height: int):
        """
        Creates a headless output with the specified width and height.

        A headless output is a virtual display that has no physical screen associated with it.
        It is often used for running applications in an off-screen environment, such as for
        testing, automated tasks, or rendering graphics without the need for a visible display.

        Args:
            width (int): The width of the headless output in pixels.
            height (int): The height of the headless output in pixels.

        Returns:
            The response from sending the JSON message.
        """
        message = get_msg_template("wayfire/create-headless-output")
        message["data"]["width"] = width
        message["data"]["height"] = height
        return self.send_json(message)

    def destroy_headless_output(self, output_name: Optional[str]=None, output_id: Optional[int]=None):
        """
        Destroys a headless output identified by its name or ID.

        Args:
            output_name (Optional[str]): The name of the headless output to destroy.
            output_id (Optional[int]): The ID of the headless output to destroy.

        Returns:
            The response from sending the JSON message.

        Raises:
            AssertionError: If neither `output_name` nor `output_id` is provided.
        """
        assert output_name is not None or output_id is not None
        message = get_msg_template("wayfire/destroy-headless-output")
        if output_name is not None:
            message["data"]["output"] = output_name
        else:
            message["data"]["output-id"] = output_id

        return self.send_json(message)

    def get_configuration(self):
        message = get_msg_template("wayfire/configuration")
        return self.send_json(message)

    def get_keyboard_layout(self):
        message = get_msg_template("wayfire/get-keyboard-state")
        return self.send_json(message)

    def set_keyboard_layout(self, index: int):
        message = get_msg_template("wayfire/set-keyboard-state")
        message['data']['layout-index'] = index
        return self.send_json(message)

    def register_binding(

        self,
        binding: str,
        *,
        call_method: Optional[str]=None,
        call_data=None,
        command: Optional[str]=None,
        mode: Optional[str]=None,
        exec_always: bool=False,
    ):
        """
        Registers a new key or mouse binding.

        This method allows you to register a binding (e.g., a key combination or mouse action) 
        and specify the action that should be triggered when the binding is activated. You can 
        provide additional options, such as the mode in which the binding is active and whether 
        the action should always be executed.

        Args:
            binding (str): The key or mouse binding to register.
            call_method (Optional[str]): The method to call when the binding is triggered.
            call_data (Optional): The data to pass to the method when the binding is triggered.
            command (Optional[str]): A command to execute when the binding is triggered.
            mode (Optional[str]): The mode in which the binding is active. Valid values are "press" 
                or "normal". Other modes can be specified as needed.
            exec_always (bool): If set to True, the action will be executed regardless of other conditions.

        Returns:
            The response from sending the JSON message.
        """
        message = get_msg_template("command/register-binding")
        message["data"]["binding"] = binding
        message["data"]["exec-always"] = exec_always
        if mode and mode != "press" and mode != "normal":
            message["data"]["mode"] = mode

        if call_method is not None:
            message["data"]["call-method"] = call_method
        if call_data is not None:
            message["data"]["call-data"] = call_data
        if command is not None:
            message["data"]["command"] = command

        return self.send_json(message)

    def unregister_binding(self, binding_id: int):
        """
        Unregisters a previously registered binding.

        This method removes a binding identified by its unique ID. The binding will no longer 
        trigger any associated actions or commands.

        Args:
            binding_id (int): The unique ID of the binding to unregister.

        Returns:
            The response from sending the JSON message.
        """
        message = get_msg_template("command/unregister-binding")
        message["data"]["binding-id"] = binding_id
        return self.send_json(message)

    def clear_bindings(self):
        """
        Clears all registered bindings.

        This method sends a request to remove all key and mouse bindings,
        effectively resetting the binding configuration.

        Returns:
            The response from sending the JSON message.
        """
        message = get_msg_template("command/clear-bindings")
        return self.send_json(message)

    def get_option_value(self, option: str):

        """
        Retrieves the current value of a specified internal configuration option.

        This method sends a request to get the value of an internal configuration option directly 
        bypassing `wayfire.ini`.

        Args:
            option (str): The name of the internal configuration option whose value is to be retrieved.

        Returns:
            The response from sending the JSON message, which includes the current value of the 
            specified internal configuration option.
        """
        message = get_msg_template("wayfire/get-config-option")
        message["data"]["option"] = option
        return self.send_json(message)

    def set_option_values(self, options):
        """
        Sets multiple internal configuration options.

        This method sanitizes and sends a request to update internal configuration options. It 
        supports setting options both with and without hierarchical paths. If the option keys 
        do not contain a "/", they are treated as base keys and are combined with their respective 
        sub-options to form hierarchical paths.

        Args:
            options (dict): A dictionary of configuration options to be set. The dictionary can 
                            contain:
                            - Base keys with hierarchical sub-options (e.g., `key: {sub_key: value}`), 
                              which will be formatted into hierarchical paths.
                            - Hierarchical paths directly as keys (e.g., `key/sub_key: value`).

        Returns:
            The response from sending the JSON message, which confirms the update of the configuration 
            options.
        """
        sanitized_options = {}
        for key, value in options.items():
            if "/" in key:
                sanitized_options[key] = value
            else:
                for option_name, option_value in value.items():
                    sanitized_options[key + "/" + option_name] = option_value

        message = get_msg_template("wayfire/set-config-options")
        message["data"] = sanitized_options
        return self.send_json(message)

    def list_methods(self):
        """
        Retrieves a list of available methods supported by the API.

        This method sends a request to get a list of all methods that the API supports. It provides information
        about the operations that can be performed via the API.

        Returns:
            list: A list of method names supported by the API. Each method name is represented as a string.
        """
        query = get_msg_template("list-methods")
        response = self.send_json(query)
        return response["methods"]

    @staticmethod
    def _wayfire_plugin_from_method(method: str) -> str:
        if method.startswith("wf/alpha"):
            return "alpha"
        if method.startswith("wf/obs"):
            return "obs (wayfire-plugins-extra)"
        if method.startswith("wf/filters"):
            return "filters (soreau/filters)"
        if method.startswith("window-rules"):
            return "ipc-rules"
        if method.startswith("wayfire"):
            return "ipc-rules"
        if "/" not in method:
            return "unknown"

        return method.split("/")[0]

    def get_output(self, output_id: int):
        """
        Retrieves information about a specific output.

        This method sends a request to get details about an output identified by its unique ID.

        Args:
            output_id (int): The unique ID of the output whose information is to be retrieved.

        Returns:
            The response from sending the JSON message, which includes information about the specified 
            output.
        """
        message = get_msg_template("window-rules/output-info")
        message["data"]["id"] = output_id
        return self.send_json(message)

    def list_outputs(self):
        """
        Retrieves a list of all available outputs.

        This method sends a request to get information about all outputs, returning a list of outputs
        that are currently available.

        Returns:
            The response from sending the JSON message, which includes a list of all available outputs.
        """
        message = get_msg_template("window-rules/list-outputs")
        return self.send_json(message)

    def list_wsets(self):
        """
        Retrieves a list of all available workspace sets.

        This method sends a request to get information about all workspace sets that are currently
        available.

        Returns:
            The response from sending the JSON message, which includes a list of all available workspace sets.
        """
        message = get_msg_template("window-rules/list-wsets")
        return self.send_json(message)

    def wset_info(self, id: int):
        """
        Retrieves information about a specific workspace set.

        This method sends a request to get detailed information about a workspace set identified 
        by its unique ID.

        Args:
            id (int): The unique ID of the workspace set whose information is to be retrieved.

        Returns:
            The response from sending the JSON message, which includes detailed information about 
            the specified workspace set.
        """
        message = get_msg_template("window-rules/wset-info")
        message["data"]["id"] = id
        return self.send_json(message)

    def send_view_to_wset(self, view_id: int, wset_index: int):
        """
        Moves a view to a specified workspace set.

        This method sends a request to move a view, identified by its unique ID, to a specific workspace
        set identified by its index.

        Args:
            view_id (int): The unique ID of the view to be moved.
            wset_index (int): The index of the workspace set to which the view should be moved.

        Returns:
            The response from sending the JSON message, which confirms the action of moving the view to 
            the specified workspace set.
        """
        message = get_msg_template("wsets/send-view-to-wset")
        message["data"]["view-id"] = view_id
        message["data"]["wset-index"] = wset_index
        return self.send_json(message)

    def set_output_wset(self, output_id: int, wset_index: int):
        """
        Assigns an output to a specific workspace set.

        This method sends a request to associate an output, identified by its unique ID, with a 
        particular workspace set specified by its index.

        Args:
            output_id (int): The unique ID of the output to be assigned.
            wset_index (int): The index of the workspace set to which the output should be assigned.

        Returns:
            The response from sending the JSON message, which confirms the assignment of the output 
            to the specified workspace set.
        """
        message = get_msg_template("wsets/set-output-wset")
        message["data"]["output-id"] = output_id
        message["data"]["wset-index"] = wset_index
        return self.send_json(message)

    def watch(self, events: List[str] | None = None):
        """
        Subscribes to specific events or all events for monitoring.

        This method sends a request to start watching for specified events. If no events are provided,
        it will subscribe to all available events. 

        Args:
            events (List[str] | None): A list of event names to watch. If `None`, subscribes to all events.

        Returns:
            The response from sending the JSON message, which confirms the subscription to the specified
            events.
        """
        method = "window-rules/events/watch"
        message = get_msg_template(method)
        if events is not None:
            message["data"]["events"] = events
        return self.send_json(message)

    def list_views(self, filter_mapped_toplevel=False) -> List[Any]:
        """
        Retrieves a list of all views, optionally filtering for mapped toplevel views.

        This method sends a request to get information about all views. If `filter_mapped_toplevel` is
        set to `True`, it filters the results to include only views that are mapped, not part of the 
        desktop environment, and have a valid process ID.

        Args:
            filter_mapped_toplevel (bool): Whether to filter the list to include only mapped toplevel views. 
                                           Defaults to `False`.

        Returns:
            List[Any]: A list of views. If `filter_mapped_toplevel` is `True`, the list contains only views 
                       that are mapped and meet the filtering criteria. Otherwise, it returns all views.
        """
        views = self.send_json(get_msg_template("window-rules/list-views"))
        if views is None:
            return []
        if filter_mapped_toplevel:
            return [v for v in views if v["mapped"] is True and v["role"] != "desktop-environment" and v["pid"] != -1]
        return views

    def configure_view(self, view_id: int, x: int, y: int, w: int, h: int, output_id = None):
        """
        Configures the properties of a specific view.

        This method sends a request to configure the position, size, and optionally the output assignment
        for a view identified by its unique ID. The view's geometry is specified by its x and y coordinates, 
        width, and height. If `output_id` is provided, it assigns the view to the specified output.

        Args:
            view_id (int): The unique ID of the view to be configured.
            x (int): The x-coordinate of the view's position.
            y (int): The y-coordinate of the view's position.
            w (int): The width of the view.
            h (int): The height of the view.
            output_id (Optional[int]): The ID of the output to which the view should be assigned. Defaults to `None`.

        Returns:
            The response from sending the JSON message, which confirms the configuration of the view.
        """
        message = get_msg_template("window-rules/configure-view")
        message["data"]["id"] = view_id
        message["data"]["geometry"] = geometry_to_json(x, y, w, h)
        if output_id is not None:
            message["data"]["output_id"] = output_id
        return self.send_json(message)

    def assign_slot(self, view_id: int, slot: str):
        """
        Assigns a view to a specified grid slot.

        This method sends a request to assign a view, identified by its unique ID, to a specified slot 
        within the grid. The slot is determined by the `slot` parameter, which should correspond to a valid 
        grid slot identifier.

        Args:
            view_id (int): The unique ID of the view to be assigned.
            slot (str): The identifier of the grid slot to which the view should be assigned.

        Returns:
            The response from sending the JSON message, which confirms the assignment of the view to the 
            specified slot.

        Examples:
            Assign a view with ID 1 to the top-left slot:
            >>> assign_slot(1, "slot_tl")

            Assign a view with ID 2 to the top-right slot:
            >>> assign_slot(2, "slot_tr")

            Assign a view with ID 3 to the bottom-left slot:
            >>> assign_slot(3, "slot_bl")

            Assign a view with ID 4 to the bottom-right slot:
            >>> assign_slot(4, "slot_br")

            Assign a view with ID 5 to the top slot:
            >>> assign_slot(5, "slot_t")

            Assign a view with ID 6 to the bottom slot:
            >>> assign_slot(6, "slot_b")

            Assign a view with ID 7 to the left slot:
            >>> assign_slot(7, "slot_l")

            Assign a view with ID 8 to the right slot:
            >>> assign_slot(8, "slot_r")

            Assign a view with ID 9 to the center slot:
            >>> assign_slot(9, "slot_c")
        """
        message = get_msg_template("grid/" + slot)
        message["data"]["view_id"] = view_id
        return self.send_json(message)

    def set_focus(self, view_id: int):
        """
        Sets focus to a specific view.

        This method sends a request to change the focus to the view identified by its unique ID. The 
        view will be brought to the foreground and receive input focus.

        Args:
            view_id (int): The unique ID of the view to be focused.

        Returns:
            The response from sending the JSON message, which confirms the focus change to the specified view.
        """
        message = get_msg_template("window-rules/focus-view")
        message["data"]["id"] = view_id
        return self.send_json(message)

    def get_view(self, view_id: int):
        """
        Retrieves information about a specific view.

        This method sends a request to obtain detailed information about a view identified by its unique ID. 
        The information retrieved includes various attributes of the view.

        Args:
            view_id (int): The unique ID of the view for which information is to be retrieved.

        Returns:
            dict: A dictionary containing detailed information about the specified view. The information
                  includes various attributes related to the view.
        """
        message = get_msg_template("window-rules/view-info")
        message["data"]["id"] = view_id
        return self.send_json(message)["info"]

    def configure_input_device(self, id: int, enabled: bool):
        """
        Configures an input device.

        This method sends a request to enable or disable an input device identified by its unique ID. 
        The `enabled` parameter determines whether the device should be activated or deactivated.

        Args:
            id (int): The unique ID of the input device to be configured.
            enabled (bool): Whether to enable (`True`) or disable (`False`) the input device.

        Returns:
            The response from sending the JSON message, which confirms the configuration change for the specified input device.
        """
        message = get_msg_template("input/configure-device")
        message["data"]["id"] = id
        message["data"]["enabled"] = enabled
        return self.send_json(message)

    def close_view(self, view_id: int):
        """
        Closes a specific view.

        This method sends a request to close the view identified by its unique ID. The view will be terminated 
        and removed from the display.

        Args:
            view_id (int): The unique ID of the view to be closed.

        Returns:
            The response from sending the JSON message, which confirms the request to close the specified view.
        """
        message = get_msg_template("window-rules/close-view")
        message["data"]["id"] = view_id
        return self.send_json(message)

    def get_focused_view(self):
        """
        Retrieves information about the currently focused view.

        This method sends a request to obtain details about the view that is currently in focus. The 
        returned information includes various attributes of the focused view.

        Returns:
            dict: A dictionary containing detailed information about the currently focused view. The 
                  information includes various attributes related to the view.
        """
        message = get_msg_template("window-rules/get-focused-view")
        return self.send_json(message)["info"]

    def get_focused_output(self):
        """
        Retrieves information about the currently focused output.

        This method sends a request to obtain details about the output that is currently in focus. The 
        returned information includes various attributes of the focused output.

        Returns:
            dict or any: A dictionary containing detailed information about the currently focused output 
                         if available. If the information is not present in the response, the raw response 
                         is returned instead.
        """
        message = get_msg_template("window-rules/get-focused-output")
        message = self.send_json(message)
        if "info" in message:
            return message["info"]
        else:
            return message

    def set_view_fullscreen(self, view_id: int, state: bool):
        """
        Sets the fullscreen state for a specific view.

        This method sends a request to toggle the fullscreen state of a view identified by its unique ID. 
        The `state` parameter determines whether the view should be set to fullscreen (`True`) or exit 
        fullscreen mode (`False`).

        Args:
            view_id (int): The unique ID of the view to be modified.
            state (bool): Whether to set the view to fullscreen (`True`) or exit fullscreen mode (`False`).

        Returns:
            None: This method does not return any value. It sends a JSON message to update the fullscreen 
                  state of the specified view.
        """
        message = get_msg_template("wm-actions/set-fullscreen")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        self.send_json(message)

    def toggle_expo(self):
        message = get_msg_template("expo/toggle")
        self.send_json(message)

    def set_workspace(self, workspace_x: int, workspace_y: int, view_id: Optional[int]=None, output_id: Optional[int]=None):
        """
        Sets the workspace on a specific output and optionally moves a view to that workspace.

        This method sends a request to switch to a specified workspace identified by `workspace_x` and
        `workspace_y` coordinates. If an `output_id` is not provided, the method uses the currently focused
        output. Additionally, if a `view_id` is provided, the view will be moved to the specified workspace
        on the chosen output.

        Args:
            workspace_x (int): The x-coordinate of the workspace to switch to.
            workspace_y (int): The y-coordinate of the workspace to switch to.
            view_id (Optional[int]): The unique ID of the view to be moved to the new workspace. If `None`,
                                     no view will be moved. Defaults to `None`.
            output_id (Optional[int]): The ID of the output where the workspace switch should occur. If `None`,
                                       the currently focused output will be used. Defaults to `None`.

        Returns:
            dict: The response from sending the JSON message, which typically confirms the workspace switch 
                  and view movement if applicable.
        """
        if output_id is None:
            focused_output = self.get_focused_output()
            output_id = focused_output["id"]

        message = get_msg_template("vswitch/set-workspace")
        message["data"]["x"] = workspace_x
        message["data"]["y"] = workspace_y
        message["data"]["output-id"] = output_id
        if view_id is not None:
            message["data"]["view-id"] = view_id
        return self.send_json(message)

    def toggle_showdesktop(self):
        message = get_msg_template("wm-actions/toggle_showdesktop")
        return self.send_json(message)

    def set_view_sticky(self, view_id: int, state: bool):
        """
        Sets the sticky state for a specific view.

        This method sends a request to change the sticky state of a view identified by its unique ID. 
        The `state` parameter determines whether the view should be marked as sticky (`True`) or not 
        sticky (`False`). A sticky view remains visible across all workspaces.

        Args:
            view_id (int): The unique ID of the view to be modified.
            state (bool): Whether to mark the view as sticky (`True`) or remove its sticky status (`False`).

        Returns:
            dict: The response from sending the JSON message, which typically confirms the update to the view’s
                  sticky state.
        """
        message = get_msg_template("wm-actions/set-sticky")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def send_view_to_back(self, view_id: int, state: bool):
        """
        Sends a view to the back or brings it to the front.

        This method sends a request to change the z-order of a view identified by its unique ID. 
        If `state` is `True`, the view is sent to the back of the stack, making it the lowest in 
        z-order. If `state` is `False`, the view is brought to the front, making it the highest in 
        z-order.

        Args:
            view_id (int): The unique ID of the view whose z-order is to be changed.
            state (bool): Whether to send the view to the back (`True`) or bring it to the front (`False`).

        Returns:
            dict: The response from sending the JSON message, which typically confirms the update to the view’s
                  z-order state.
        """
        message = get_msg_template("wm-actions/send-to-back")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def set_view_minimized(self, view_id: int, state: bool):
        """
        Sets the minimized state for a specific view.

        This method sends a request to change the minimized state of a view identified by its unique ID.
        If `state` is `True`, the view is minimized. If `state` is `False`, the view is restored to its
        normal size.

        Args:
            view_id (int): The unique ID of the view to be minimized or restored.
            state (bool): Whether to minimize the view (`True`) or restore it (`False`).

        Returns:
            dict: The response from sending the JSON message, which typically confirms the update to the view’s
                  minimized state.
        """
        message = get_msg_template("wm-actions/set-minimized")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = state
        return self.send_json(message)

    def scale_toggle(self):
        message = get_msg_template("scale/toggle")
        self.send_json(message)
        return True

    def scale_toggle_all(self):
        message = get_msg_template("scale/toggle_all")
        self.send_json(message)
        return True

    def cube_activate(self):
        message = get_msg_template("cube/activate")
        self.send_json(message)
        return True

    def cube_rotate_left(self):
        message = get_msg_template("cube/rotate_left")
        self.send_json(message)
        return True

    def cube_rotate_right(self):
        message = get_msg_template("cube/rotate_right")
        self.send_json(message)
        return True

    def set_view_always_on_top(self, view_id: int, always_on_top: bool):
        """
        Sets the "always on top" state for a specific view.

        This method sends a request to change the "always on top" state of a view identified by its unique ID.
        If `always_on_top` is `True`, the view will be kept on top of other windows. If `always_on_top` is
        `False`, the view will not have this priority and can be obscured by other windows.

        Args:
            view_id (int): The unique ID of the view to be set as always on top or to remove this attribute.
            always_on_top (bool): Whether to keep the view always on top (`True`) or allow it to be obscured (`False`).

        Returns:
            dict: The response from sending the JSON message, which typically confirms the update to the view’s
                  "always on top" state.
        """
        message = get_msg_template("wm-actions/set-always-on-top")
        message["data"]["view_id"] = view_id
        message["data"]["state"] = always_on_top
        return self.send_json(message)

    def set_view_alpha(self, view_id: int, alpha: float):
        """
        Sets the transparency level (alpha) for a specific view.

        This method sends a request to adjust the transparency of a view identified by its unique ID. The `alpha`
        value determines the view's transparency level, where `0.0` is fully transparent and `1.0` is fully opaque.

        Args:
            view_id (int): The unique ID of the view whose transparency is to be set.
            alpha (float): The transparency level to set for the view. Should be a value between `0.0` (fully transparent)
                           and `1.0` (fully opaque).

        Returns:
            dict: The response from sending the JSON message, which typically confirms the update to the view’s transparency.
        """
        message = get_msg_template("wf/alpha/set-view-alpha")
        message["data"] = {}
        message["data"]["view-id"] = view_id
        message["data"]["alpha"] = alpha
        return self.send_json(message)

    def get_view_alpha(self, view_id: int):
        """
        Retrieves the transparency level (alpha) of a specific view.

        This method sends a request to obtain the current transparency level of a view identified by its unique ID.
        The transparency level, also known as alpha, ranges from `0.0` (fully transparent) to `1.0` (fully opaque).

        Args:
            view_id (int): The unique ID of the view whose transparency level is to be retrieved.

        Returns:
            dict: The response from sending the JSON message, typically containing the current transparency level
                  of the view under the key `"alpha"`.
        """
        message = get_msg_template("wf/alpha/get-view-alpha")
        message["data"]["view-id"] = view_id
        return self.send_json(message)

    def list_input_devices(self):
        """
        Retrieves a list of all input devices.

        This method sends a request to obtain information about all input devices currently recognized by the system. 
        The response includes details about each device, such as its ID, type, and state.

        Returns:
            dict: The response from sending the JSON message, which typically contains a list of input devices 
                  with their associated details.
        """
        message = get_msg_template("input/list-devices")
        return self.send_json(message)

    def get_cursor_position(self):
        """
        Get the current cursor coordinates.

        Returns:
            tuple[float, float]: (x, y) coordinates in pixels relative to the output.

        Example:
            >>> x, y = socket.get_cursor_position()
            >>> print(f"Cursor at ({x}, {y})")

        Note:
            Coordinates are floating-point values for sub-pixel precision.
        """
        message = get_msg_template("window-rules/get_cursor_position")
        coord = self.send_json(message)
        return (coord["pos"]["x"], coord["pos"]["y"])

    def get_tiling_layout(self, wset: int, x: int, y: int):
        """
        Retrieves the tiling layout for a specific workspace and workspace set.

        This method sends a request to get the current tiling layout for the specified workspace and workspace set. 
        The layout information includes how views are arranged in the given workspace.

        Args:
            wset (int): The index of the workspace set.
            x (int): The x-coordinate of the workspace within the workspace set.
            y (int): The y-coordinate of the workspace within the workspace set.

        Returns:
            dict: A dictionary containing the layout information for the specified workspace and workspace set.
                  The dictionary typically includes details about the arrangement of views.
        """
        method = "simple-tile/get-layout"
        msg = get_msg_template(method)
        msg["data"]["wset-index"] = wset
        msg["data"]["workspace"] = {}
        msg["data"]["workspace"]["x"] = x
        msg["data"]["workspace"]["y"] = y
        return self.send_json(msg)["layout"]

    def set_tiling_layout(self, wset: int, x: int, y: int, layout):
        """
        Sets the tiling layout for a specific workspace and workspace set.

        This method sends a request to configure the tiling layout for the specified workspace and workspace set. 
        The provided layout defines how views should be arranged in the given workspace.

        Args:
            wset (int): The index of the workspace set.
            x (int): The x-coordinate of the workspace within the workspace set.
            y (int): The y-coordinate of the workspace within the workspace set.
            layout (dict): A dictionary representing the new layout to apply. 

        Returns:
            dict: The response from sending the JSON message, confirming the layout has been set.
        """
        msg = get_msg_template("simple-tile/set-layout")
        msg["data"]["wset-index"] = wset
        msg["data"]["workspace"] = {}
        msg["data"]["workspace"]["x"] = x
        msg["data"]["workspace"]["y"] = y
        msg["data"]["layout"] = layout
        return self.send_json(msg)
