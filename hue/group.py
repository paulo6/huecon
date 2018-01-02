#
# group.py - Contains Hue 'group' definitions
#
from . import object

class Group(object.Object):

    @property
    def name(self):
        return self._data['name']

    @property
    def type(self):
        return self._data["type"]

    @property
    def group_class(self):
        return self._data.get("class")

    @property
    def lights(self):
        lights = {l.id: l for l in self.bridge.get_lights(False)}
        return [lights[lid] for lid in self._data["lights"]]

    @property
    def is_any_on(self):
        return self._data["state"]["any_on"]

    @property
    def is_all_on(self):
        return self._data["state"]["all_on"]

    @property
    def state_str(self):
        if self.is_all_on:
            return "all on"
        elif self.is_any_on:
            return "some on"
        else:
            return "all off"

    @property
    def recycle(self):
        return self._data["recycle"]

    def turn_on(self):
        self._resource.action(on=True)
        self.refresh()

    def turn_off(self):
        self._resource.action(on=False)
        self.refresh()

    def parse_action(self, item_addr, body):
        scene_id = body.get('scene')
        scene = (self.bridge.get_scene(scene_id)
                 if scene_id is not None else None)
        return Action(self, body.get('on'), scene)


class Action(object.Action):
    def __init__(self, group, is_on=None, scene=None):
        self._group = group
        self._is_on = is_on
        self._scene = scene

    @property
    def address(self):
        return "{}/action".format(self._group.name)

    @property
    def body(self):
        out = {}
        if self._is_on is not None:
            out['on'] = self._is_on
        if self._scene is not None:
            out['scene'] = self._scene.id

    def __str__(self):
        actions = []
        if self._is_on is not None:
            if self._is_on:
                actions.append("turn on")
            else:
                actions.append("turn off")
        if self._scene is not None:
            actions.append("enable '{}'".format(self._scene.name))
        return "Group '{}': {}".format(self._group.name,
                                       ", ".join(actions))

