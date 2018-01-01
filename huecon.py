#!/usr/bin/env python3
#
# huecon.py
#
# Interactive command line Hue console
#

import os
import sys

import config
import hue
import cli

# Config file location
CONFIG_FILE = os.path.expanduser("~/.huecon")

CLI_DEF = {
    "show:Show various Hue system info": {
        "lights:Show the lights": {
            "None:Show summary": "show_lights",
            "detail:Show detail": "show_lights_detail",
        },
    },
    "exit:Exit Huecon": "do_exit",
}


def exit_error(message):
    print(message)
    sys.exit(1)


class HueCon(cli.Interface):
    intro = 'Welcome HueCon.   Type help or ? to list commands.\n'
    prompt = '(huecon) '

    def __init__(self):
        # Load config file
        self.config_file = config.Config(CONFIG_FILE)

        # Connect to bridge
        self.bridge = self._connect_to_bridge()

        super().__init__(CLI_DEF)

    def _connect_to_bridge(self):
        # Get known bridges
        known_bridges = {a: u for a, u in self.config_file.get_bridges()}

        address = input("Enter hue bridge host: ")

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

    def show_lights(self, ctx):
        print("Lights:")
        for light in self.bridge.get_lights():
            if not light.is_reachable:
                state = "??"
            elif light.is_on:
                state = "on"
            else:
                state = "off"
            print("  {} ({})".format(light.name, state))

    def show_lights_detail(self, ctx):
        print("Detailed lights info")
        for light in self.bridge.get_lights():
            print("")
            print(light.name)
            print("  ID:", light.id)
            print("  Reachable:", light.is_reachable)
            print("  On:", light.is_on)
            print("  Brightness:", light.state.bri)
            print("  Hue:", light.state.hue)
            print("  Saturation:", light.state.sat)
            print("  Effect:", light.state.effect)

    def do_exit(self, ctx):
        print("Bye!")
        ctx.end = True


if __name__ == '__main__':
    HueCon()

