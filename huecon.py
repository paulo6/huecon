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
    "light:Perform actions for a light": {
        "id:Perform action for this light id": {
            "<light-id>:The light id": {
                "on:Turn light on": "light_on",
                "off:Turn light off": "light_off",
            },
        },
        "name:Perform action for this light name": {
            "<light-name>:The light name": {
                "on:Turn light on": "light_on",
                "off:Turn light off": "light_off",
            },
        },
    },
    "exit:Exit Huecon": "do_exit",
}


def exit_error(message):
    print(message)
    sys.exit(1)


class LightIDArg(cli.ArgumentDef):
    def __init__(self, bridge):
        self.bridge = bridge
        super().__init__("light-id")

    def complete(self, ctx, arg):
        return [l.id for l in self.bridge.get_lights()
                if l.id.startswith(arg)]

    def process(self, ctx, arg):
        # Find the light!
        lights = {l.id: l for l in self.bridge.get_lights()}
        try:
            return lights[arg]
        except KeyError as exc:
            raise cli.ArgumentError("Unknown light ID") from exc

    def help_options(self, ctx):
        return [(l.id, l.name) for l in self.bridge.get_lights()]


class LightNameArg(cli.ArgumentDef):
    def __init__(self, bridge):
        self.bridge = bridge
        super().__init__("light-name")

    def splitline(self, ctx, arg):
        # If there are quotes, then walk till we find last
        if arg and arg[0] == '"':
            if '" ' not in arg[1:]:
                return arg, None
            else:
                end = arg[1:].index('" ')
                return arg[:end + 2], arg[end + 2:].lstrip()
        else:
            return super().splitline(ctx, arg)

    def complete(self, ctx, arg):
        return ['"{}"'.format(l.name)
                for l in self.bridge.get_lights()
                if '"{}"'.format(l.name).startswith(arg)]

    def process(self, ctx, arg):
        # Find the light!
        lights = {l.name: l for l in self.bridge.get_lights()}

        # Strip quotes
        if len(arg) > 1 and arg[0] == '"' and arg[-1] == '"':
            arg = arg[1:-1]

        try:
            return lights[arg]
        except KeyError as exc:
            raise cli.ArgumentError("Unknown light name", arg) from exc


class HueCon(cli.Interface):
    intro = 'Welcome HueCon.   Type help or ? to list commands.\n'
    prompt = '(huecon) '

    def __init__(self):
        # Load config file
        self.config_file = config.Config(CONFIG_FILE)

        # Connect to bridge
        self.bridge = self._connect_to_bridge()

        arg_defs = {
            "<light-id>": LightIDArg(self.bridge),
            "<light-name>": LightNameArg(self.bridge),
        }

        super().__init__(CLI_DEF,
                         arg_defs)

    def _connect_to_bridge(self):
        # Get known bridges
        known_bridges = {bid: user
                         for bid, user in self.config_file.get_bridges()}

        address = input("Enter hue bridge host: ")

        # Create a bridge
        try:
            bridge = hue.Bridge(address)
        except hue.Error as exc:
            exit_error("Bad bridge address: {!s}".format(exc))

        print("Connected to bridge '{}'".format(bridge.name))

        if bridge.id not in known_bridges:
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
            username = known_bridges[bridge.id]

        print("Logging in...")
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

    def light_on(self, ctx):
        light = ctx.args.get("light-id", None)
        if light is None:
            light = ctx.args["light-name"]
        print("Turning light '{}' on".format(light.name))
        light.turn_on()

    def light_off(self, ctx):
        light = ctx.args.get("light-id", None)
        if light is None:
            light = ctx.args["light-name"]
        print("Turning light '{}' off".format(light.name))
        light.turn_off()

    def do_exit(self, ctx):
        print("Bye!")
        ctx.end = True


if __name__ == '__main__':
    HueCon()

