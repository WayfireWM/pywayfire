#!/usr/bin/python3

# This script gets or sets a wayfire configuration option
#
# NOTE: After setting an option with this script,
#       changes to the option in config and wcm
#       will be ignored until wayfire restart
#
# Usage:
# ./cfg.py get plugin-section/option_name
# ./cfg.py set plugin-section/option_name value

from wayfire import WayfireSocket
import sys

sock = WayfireSocket()

if sys.argv[1] == "get":
    opt = sock.get_option_value(sys.argv[2])
    if 'value' in opt:
        print(f"Current value='{opt['value']}', default='{opt['default']}'")
    else:
        print("Option not found: " + sys.argv[2])

elif sys.argv[1] == "set":
    print(sock.set_option_values({sys.argv[2] : sys.argv[3]}))
else:
    print("Invalid usage, either get <option> or set <option> <value>")
