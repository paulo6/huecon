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
            "name:Show specific light by name": {
                "<light-name>:The light name to show": "show_light",
            },
            "id:Show specific light by id": {
                "<light-id>:The light id to show": "show_light",
            },
        },
        "scenes:Show the scenes": {
            "None:Show summary": "show_scenes",
            "detail:Show detail": "show_scenes",
            "name:Show specific scene by name": {
                "<scene-name>:The scene name to show": "show_scene",
            },
            "id:Show specific scene by id": {
                "<scene-id>:The scene id to show": "show_scene",
            },
        },
        "resourcelinks:Show the resourcelinks": {
            "None:Show summary": "show_resourcelinks",
            "name:Show specific resourcelink by name": {
                "<rlink-name>:The resourcelink name to show":
                    "show_resourcelink",
            },
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


class ObjectIDArg(cli.ArgumentDef):
    def __init__(self, get_fn, arg_name):
        self.get_fn = get_fn
        super().__init__(arg_name)

    def complete(self, ctx, arg):
        return [o.id for o in self.get_fn()
                if o.id.startswith(arg)]

    def process(self, ctx, arg):
        # Find the object!
        objects = {o.id: o for o in self.get_fn()}
        try:
            return objects[arg]
        except KeyError as exc:
            raise cli.ArgumentError("Unknown {}".format(self.name)) from exc

    def help_options(self, ctx):
        return [(o.id, o.name) for o in self.get_fn()]


class ObjectNameArg(cli.ArgumentDef):
    def __init__(self, get_fn, arg_name):
        self.get_fn = get_fn
        super().__init__(arg_name)

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
            raise cli.ArgumentError("Unknown {}".format(self.name),
                                    arg) from exc


class HueCon(cli.Interface):
    intro = 'Welcome HueCon.   Type help or ? to list commands.\n'
    prompt = '(huecon) '

    def __init__(self):
        # Load config file
        self.config_file = config.Config(CONFIG_FILE)

        # Connect to bridge
        self.bridge = self._connect_to_bridge()

        arg_defs = {
            "<light-id>": ObjectIDArg(self.bridge.get_lights, "light-id"),
            "<light-name>": ObjectNameArg(self.bridge.get_lights, "light-name"),
            "<scene-name>": ObjectNameArg(self.bridge.get_scenes, "scene-name"),
            "<scene-id>": ObjectNameArg(self.bridge.get_scenes, "scene-id"),
            "<rlink-name>": ObjectNameArg(self.bridge.get_resourcelinks,
                                          "resourcelink-name"),
        }

        super().__init__(CLI_DEF, arg_defs)

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

    def _print_light(self, light):
        print(light.name)
        print("  ID:", light.id)
        print("  Reachable:", light.is_reachable)
        print("  On:", light.is_on)
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

    def show_lights(self, ctx):
        print("Lights:")
        for light in self.bridge.get_lights():
            if not light.is_reachable:
                state = "??"
            elif light.is_on:
                state = "on"
            else:
                state = "off"
            print("  {}  (state: {}, id: {})".format(light.name, state,
                                                     light.id))

    def show_light(self, ctx):
        if "name" in ctx.kws:
            self._print_light(ctx.args['light-name'])
        else:
            self._print_light(ctx.args['light-id'])

    def show_lights_detail(self, ctx):
        print("Detailed lights info")
        for light in self.bridge.get_lights():
            print("")
            self._print_light(light)

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
        if "name" in ctx.kws:
            self._print_scene(ctx.args['scene-name'])
        else:
            self._print_scene(ctx.args['scene-id'])

    def show_resourcelinks(self, ctx):
        print("Resourcelinks:")
        for rlink in self.bridge.get_resourcelinks():
            print("  {}  (id: {})".format(rlink.name, rlink.id))
            print("    '{}'".format(rlink.description))

    def show_resourcelink(self, ctx):
        rlink = ctx.args['resourcelink-name']
        print(rlink.name)
        print("Description: {}".format(rlink.description))
        print("Links:")
        objects = rlink.links
        maxlen = max(len(type(obj).__name__) + len(obj.name) + 3
                     for obj in objects)
        for obj in objects:
            name = "{} '{}'".format(type(obj).__name__,
                                    obj.name)
            print("  {:{}}  (id: {})".format(name, maxlen, obj.id))

    def do_exit(self, ctx):
        print("Bye!")
        ctx.end = True


if __name__ == '__main__':
    HueCon()

