#!/usr/bin/env python3
#
# huecon.py
#
# Interactive command line Hue console
#
import argparse
import os
import sys

import config
import hue
import cli

# Config file location
CONFIG_FILE = os.path.expanduser("~/.huecon")
CLI_HISTORY_FILE = os.path.expanduser("~/.huecon_history")

CLI_DEF = {
    "show|:Show various Hue system info": {
        "lights:Show the lights": {
            "None:Show summary": "show_lights",
            "detail:Show detail": "show_lights_detail",
            "name:Show specific light by name": {
                "<light-name>:Show light with this name": "show_light",
            },
            "id:Show specific light by id": {
                "<light-id>:Show light with this id": "show_light",
            },
        },
        "scenes:Show the scenes": {
            "None:Show summary": "show_scenes",
            "detail:Show detail": "show_scenes",
            "name:Show specific scene by name": {
                "<scene-name>:Show scene with this name": "show_scene",
            },
            "id:Show specific scene by id": {
                "<scene-id>:Show scene with this id": "show_scene",
            },
        },
        "resourcelinks:Show the resourcelinks": {
            "None:Show summary": "show_resourcelinks",
            "name:Show specific resourcelink by name": {
                "<rlink-name>:Show resourcelink with this name":
                    "show_resourcelink",
            },
            "id:Show specific resourcelink by id": {
                "<rlink-id>:Show resourcelinl with this id":
                    "show_resourcelink",
            },
        },
        "groups:Show the groups": {
            "None:Show summary": "show_groups",
            "name:Show specific group by name": {
                "<group-name>:Show group with this name": "show_group",
            },
            "id:Show specific group by id": {
                "<group-id>:Show group with this id": "show_group",
            },
        },
        "sensors:Show the sensors": {
            "None:Show summary": "show_sensors",
            "name:Show specific sensor by name": {
                "<sensor-name>:Show sensor with this name": "show_sensor",
            },
            "id:Show specific sensor by id": {
                "<sensor-id>:Show sensor with this id": "show_sensor",
            },
        },
    },
    "light:Perform actions for a light": {
        "id:Perform action for a light id": {
            "<light-id>:Perform action for this light id": {
                "on:Turn light on": "light_on",
                "off:Turn light off": "light_off",
            },
        },
        "name:Perform action for a light name": {
            "<light-name>:Perform action for this light name": {
                "on:Turn light on": "light_on",
                "off:Turn light off": "light_off",
            },
        },
    },
    "group:Perform actions for a group": {
        "id:Perform action for a group id": {
            "<group-id>:Perform action for this group id": {
                "on:Turn group on": "group_on",
                "off:Turn group off": "group_off",
            },
        },
        "name:Perform action for a group name": {
            "<group-name>:Perform action for this group name": {
                "on:Turn group on": "group_on",
                "off:Turn group off": "group_off",
            },
        },
    },
    "exit:Exit Huecon": "do_exit",
}


def exit_error(message):
    print(message)
    sys.exit(1)


class ObjectIDArg(cli.ArgumentDef):
    def __init__(self, get_fn, arg_name):
        self.get_fn = get_fn
        super().__init__(arg_name + "-id", arg_name)

    def complete(self, ctx, arg):
        return [o.id for o in self.get_fn()
                if o.id.startswith(arg)]

    def process(self, ctx, arg):
        # Find the object!
        objects = {o.id: o for o in self.get_fn()}
        try:
            return objects[arg]
        except KeyError as exc:
            raise cli.ArgumentError("Unknown {} ID".format(self.name)) from exc

    def help_options(self, ctx):
        return [(o.id, o.name) for o in self.get_fn()]


class ObjectNameArg(cli.ArgumentDef):
    def __init__(self, get_fn, arg_name):
        self.get_fn = get_fn
        super().__init__(arg_name + "-name", arg_name)

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
        return ['"{}"'.format(o.name)
                for o in self.get_fn()
                if '"{}"'.format(o.name).startswith(arg)]

    def process(self, ctx, arg):
        # Find the object!
        objects = {o.name: o for o in self.get_fn()}

        # Strip quotes
        if len(arg) > 1 and arg[0] == '"' and arg[-1] == '"':
            arg = arg[1:-1]

        try:
            return objects[arg]
        except KeyError as exc:
            raise cli.ArgumentError("Unknown {} name".format(self.name),
                                    arg) from exc


class HueCon(cli.Interface):
    intro = 'Welcome HueCon.   Type help or ? to list commands.\n'
    prompt = '(huecon) '

    def __init__(self, bridge_address=None):
        # Load config file
        self.config_file = config.Config(CONFIG_FILE)

        # Connect to bridge
        self.bridge = self._connect_to_bridge(bridge_address)

        # Create argument definitions
        arg_defs = {}
        for name, arg_name in (("light", None),
                               ("scene", None),
                               ("group", None),
                               ("sensor", None),
                               ("resourcelink", "rlink")):
            if arg_name is None:
                arg_name = name
            func = getattr(self.bridge, "get_{}s".format(name))
            arg_defs["<{}-id>".format(arg_name)] = ObjectIDArg(func, name)
            arg_defs["<{}-name>".format(arg_name)] = ObjectNameArg(func, name)

        super().__init__(CLI_DEF, arg_defs, CLI_HISTORY_FILE)

    # ------------------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------------------
    def _connect_to_bridge(self, bridge_address):
        # Get known bridges
        known_bridges = {bid: user
                         for bid, user in self.config_file.get_bridges()}

        if bridge_address is None:
            address = input("Enter hue bridge host: ")
        else:
            address = bridge_address

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
            bridge.auth(username)
        except hue.Error as exc:
            exit_error("Failed to connect to bridge: {!s}".format(exc))

        return bridge

    def _print_light(self, light):
        print(light.name)
        print("  ID:", light.id)
        print("  Reachable:", bool_str(light.is_reachable))
        print("  On:", bool_str(light.is_on))
        print("  Brightness:", light.state.bri)
        print("  Hue:", light.state.hue)
        print("  Saturation:", light.state.sat)
        print("  Effect:", light.state.effect)

    def _print_scene(self, scene):
        print(scene.name)
        print("  ID: {}".format(scene.id))
        print("  Lights:")
        print("    " + "\n    ".join(l.name for l in scene.lights))
        print("  Last updated: {!s}".format(scene.last_updated))
        print("  Recycle: {}".format(bool_str(scene.recycle)))
        print("  Locked: {}".format(bool_str(scene.locked)))


    # ------------------------------------------------------------------------
    # Action functions
    # ------------------------------------------------------------------------
    def show_lights(self, ctx):
        print("Lights:")
        for light in self.bridge.get_lights():
            print("  {}  (state: {}, id: {})".format(light.name,
                                                     light.state_str,
                                                     light.id))

    def show_light(self, ctx):
        self._print_light(ctx.args['light'])

    def show_lights_detail(self, ctx):
        print("Detailed lights info")
        for light in self.bridge.get_lights():
            print("")
            self._print_light(light)

    def light_on(self, ctx):
        light = ctx.args["light"]
        print("Turning light '{}' on".format(light.name))
        light.turn_on()

    def light_off(self, ctx):
        light = ctx.args["light"]
        print("Turning light '{}' off".format(light.name))
        light.turn_off()

    def show_scenes(self, ctx):
        print("Scenes:")
        scenes = self.bridge.get_scenes()
        maxlen = max(len(s.name) for s in scenes)
        for scene in scenes:
            if "detail" in ctx.kws:
                print("")
                self._print_scene(scene)
            else:
                print("  {:{}}  (id: {})".format(scene.name, maxlen, scene.id))

    def show_scene(self, ctx):
        self._print_scene(ctx.args['scene'])

    def show_resourcelinks(self, ctx):
        print("Resourcelinks:")
        for rlink in self.bridge.get_resourcelinks():
            print("  {}  (id: {})".format(rlink.name, rlink.id))
            print("    '{}'".format(rlink.description))

    def show_resourcelink(self, ctx):
        rlink = ctx.args['resourcelink']
        print(rlink.name)
        print("  Description: {}".format(rlink.description))
        print("  ID: {}".format(rlink.id))
        print("  Recycle: {}".format(bool_str(rlink.recycle)))
        print("  Links:")
        objects = rlink.links
        maxlen = max(len(type(obj).__name__) + len(obj.name) + 3
                     for obj in objects)
        for obj in objects:
            name = "{} '{}'".format(type(obj).__name__,
                                    obj.name)
            print("    {:{}}  (id: {})".format(name, maxlen, obj.id))

    def show_groups(self, ctx):
        print("Groups:")
        groups = self.bridge.get_groups()
        maxlen = max(len(group.name) for group in groups)
        for group in groups:
            print("  {:{}}  (state: {}, type: {}, id: {})"
                  .format(group.name, maxlen, group.state_str,
                          group.type, group.id))

    def show_group(self, ctx):
        group = ctx.args['group']
        print(group.name)
        print("  ID: {}".format(group.id))
        print("  Type: {}".format(group.type))
        print("  Class: {}".format(group.group_class))
        print("  State: {}".format(group.state_str))
        print("  Recycle: {}".format(bool_str(group.recycle)))
        print("  Lights:")
        for light in group.lights:
            print("    {} ({})".format(light.name, light.state_str))

    def show_sensors(self, ctx):
        print("Sensors:")
        sensors = self.bridge.get_sensors()
        maxlen = max(len(sensor.name) for sensor in sensors)
        for sensor in sensors:
            print("  {:{}}  (type: {}, state: {}, id: {})"
                  .format(sensor.name, maxlen,
                          sensor.type_str,
                          sensor.state_str, sensor.id))

    def show_sensor(self, ctx):
        sensor = ctx.args['sensor']
        print(sensor.name)
        print("  ID: {}".format(sensor.id))
        print("  Type: {}".format(sensor.type_str))
        print("  State: {}".format(sensor.state_str))
        print("  Last updated: {}".format(sensor.last_updated))
        print("  Recycle: {}".format(bool_str(sensor.recycle)))

    def group_on(self, ctx):
        group = ctx.args["group"]
        print("Turning group '{}' on".format(group.name))
        group.turn_on()

    def group_off(self, ctx):
        group = ctx.args["group"]
        print("Turning group '{}' off".format(group.name))
        group.turn_off()

    def do_exit(self, ctx):
        print("Bye!")
        ctx.end = True


def bool_str(val):
    if val is None:
        return "--"
    elif val:
        return "Yes"
    else:
        return "No"


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Interactive console for managing Hue lights")
    parser.add_argument("-b", "--bridge", help="Connect to this bridge")
    args = parser.parse_args()
    HueCon(args.bridge)

