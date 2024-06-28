from typing import Any, Dict

def get_msg_template(method: str) -> Dict[str, Any]:
    '''
    Create generic message template for the given method call.
    '''
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
