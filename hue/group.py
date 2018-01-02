
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

