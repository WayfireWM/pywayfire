import argparse
from subprocess import check_output, call
from wayfire import WayfireSocket

class DPMSManager:
    def __init__(self, sock):
        self.sock = sock

    def dpms_status(self):
        status = check_output(["wlopm"]).decode().strip().split("\n")
        dpms_status = {}
        for line in status:
            line = line.split()
            dpms_status[line[0]] = line[1]
        return dpms_status

    def dpms_manager(self, state, output_name=None):
        if state == "off" and output_name is None:
            outputs = [output["name"] for output in self.sock.list_outputs()]
            for output in outputs:
                call("wlopm --off {}".format(output).split())
        elif state == "on" and output_name is None:
            outputs = [output["name"] for output in self.sock.list_outputs()]
            for output in outputs:
                call("wlopm --on {}".format(output).split())
        elif state == "on":
            call("wlopm --on {}".format(output_name).split())
        elif state == "off":
            call("wlopm --off {}".format(output_name).split())
        elif state == "toggle":
            call("wlopm --toggle {}".format(output_name).split())
        else:
            raise ValueError("Invalid state provided. Choose from 'on', 'off', or 'toggle'.")

def main():
    parser = argparse.ArgumentParser(description="Manage DPMS status.")
    parser.add_argument("action", choices=["status", "on", "off", "toggle"], help="Action to perform.")
    parser.add_argument("--output", help="Specify output name for 'on', 'off', or 'toggle' actions.")

    args = parser.parse_args()

    sock = WayfireSocket()
    manager = DPMSManager(sock)

    if args.action == "status":
        status = manager.dpms_status()
        for output, state in status.items():
            print(f"{output}: {state}")
    else:
        manager.dpms_manager(args.action, args.output)

if __name__ == "__main__":
    main()

