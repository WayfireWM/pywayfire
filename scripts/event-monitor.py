from wayfire import WayfireSocket

sock = WayfireSocket()
sock.watch()

while True:
    try:
        msg = sock.read_next_event()
        if "event" in msg:
            print(msg)
    except KeyboardInterrupt:
        exit(0)
