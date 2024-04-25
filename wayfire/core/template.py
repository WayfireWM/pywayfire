def get_msg_template(method: str, methods=None):
    plugin = None
    # just in case there is a unknow situation where the method has no plugin
    if "/" in method:
        plugin = method.split("/")[0]
    if methods:
        if method not in methods:
            if plugin is not None:
                print(
                    "To utilize this feature, please ensure that the '{0}' Wayfire plugin is enabled.".format(
                        plugin
                    )
                )
                print("Once enabled, reload the Wayfire module to apply the changes.")
            else:
                print(
                    "No plugin found in the given method, cannot utilize this feature"
                )
            return None
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
