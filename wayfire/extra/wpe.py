from wayfire.core.template import get_msg_template
from wayfire.ipc import WayfireSocket

class WPE:
    def __init__(self, socket: WayfireSocket):
        self.socket = socket

    def filters_set_view_shader(self, view_id: int, shader: str):
        message = get_msg_template("wf/filters/set-view-shader")
        if message is None:
            return
        message["data"] = {}
        message["data"]["view-id"] = view_id
        message["data"]["shader-path"] = shader
        return self.socket.send_json(message)

    def filters_unset_view_shader(self, view_id: int):
        message = get_msg_template("wf/filters/unset-view-shader")
        if message is None:
            return
        message["data"] = {}
        message["data"]["view-id"] = view_id
        return self.socket.send_json(message)


    def set_view_opacity(self, view_id: int, opacity: float, duration: int):
        message = get_msg_template("wf/obs/set-view-opacity")
        message["data"] = {}
        message["data"]["view-id"] = view_id
        message["data"]["opacity"] = opacity
        message["data"]["duration"] = duration
        return self.socket.send_json(message)

    def set_view_brightness(self, view_id: int, brightness: float, duration: int):
        message = get_msg_template("wf/obs/set-view-brightness")
        message["data"] = {}
        message["data"]["view-id"] = view_id
        message["data"]["brightness"] = brightness
        message["data"]["duration"] = duration
        return self.socket.send_json(message)

    def set_view_saturation(self, view_id: int, saturation: float, duration: int):
        message = get_msg_template("wf/obs/set-view-saturation")
        message["data"] = {}
        message["data"]["view-id"] = view_id
        message["data"]["saturation"] = saturation
        message["data"]["duration"] = duration
        return self.socket.send_json(message)

    def ghost_view_toggle(self, view_id: int):
        message = get_msg_template("ghost/ghost_toggle")
        message["data"]["view-id"] = view_id
        return self.socket.send_json(message)
