#
# huecon.py
#
# Interactive command line Hue console
#

import os
import sys
import cmd

import config
import hue

# Config file location
CONFIG_FILE = os.path.expanduser("~/.huecon")


def exit_error(message):
    print(message)
    sys.exit(1)


class HueCon(cmd.Cmd):
    intro = 'Welcome HueCon.   Type help or ? to list commands.\n'
    prompt = '(huecon) '

    def __init__(self):
        # Load config file
        self.config_file = config.Config(CONFIG_FILE)

        # Connect to bridge
        self.bridge = self._connect_to_bridge()

        super().__init__()

    def _connect_to_bridge(self):
        # Get known bridges
        known_bridges = {a: u for a, u in self.config_file.get_bridges()}

        address = input("Enter hue bridge address: ")

        # Create a bridge
        try:
            bridge = hue.Bridge(address)
        except hue.Error as exc:
            exit_error("Bad bridge address: {!s}".format(exc))

        if address not in known_bridges:
            print("Bridge not known, registering with bridge")
            input("Press bridge button then press enter to continue...")

            try:
                username = bridge.register("huecon")
            except hue.Error as exc:
                exit_error("Failed to register with bridge: {!s}".format(exc))

            # Update config
            self.config_file.add_bridge(address, username)
            self.config_file.write_file()
        else:
            username = known_bridges[address]

        print("Connecting...")
        try:
            bridge.connect(username)
        except hue.Error as exc:
            exit_error("Failed to connect to bridge: {!s}".format(exc))

        return bridge

    def do_show(self, arg):
        """Show various information. Supported options: lights, """
        if arg == "lights":
            print("Lights:")
            for light in sorted(self.bridge.get_lights(), key=lambda l: l.name):
                print("  {} ({})".format(light.name,
                                         "on" if light.is_on else "off"))
        else:
            print("Unknown option", arg)

    def do_exit(self, arg):
        """Exit huecon"""
        print("Bye!")
        return False


if __name__ == '__main__':
    HueCon().cmdloop()

