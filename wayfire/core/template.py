from typing import Any, Dict

def get_msg_template(method: str, methods=None) -> Dict[str, Any]:
    plugin: str = "unknown"
    # just in case there is a unknow situation where the method has no plugin
    if "/" in method:
        plugin = method.split("/")[0]
    if methods:
        if method not in methods:
            raise Exception(f"To utilize {method}, please ensure that the '{plugin}' Wayfire plugin is enabled.\n \
                    Once enabled, reload the Wayfire module to apply the changes.")
    # Create generic message template
    message = {}
    message["method"] = method
    message["data"] = {}
    return message


def geometry_to_json(x: int, y: int, w: int, h: int):
    geometry = {}
    geometry["x"] = x
    geometry["y"] = y
    geometry["width"] = w
    geometry["height"] = h
    return geometry
