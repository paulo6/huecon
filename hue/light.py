#
# bridge.py
#
# Hue Light interactions
#

from collections import namedtuple

from . import object


State = namedtuple("State", ["on", "bri", "hue", "sat", "effect"])


class Light(object.Object):
    @property
    def name(self):
        return self._data['name']

    @property
    def is_on(self):
        return self._data['state']['on']

    @property
    def state(self):
        return State(self._data['state']['on'],
                     self._data['state']['bri'],
                     self._data['state']['hue'],
                     self._data['state']['sat'],
                     self._data['state']['effect'])

    @property
    def is_reachable(self):
        return self._data['state']['reachable']

    def turn_on(self):
        self._resource.state(on=True)
        self.refresh()

    def turn_off(self):
        self._resource.state(on=False)
        self.refresh()
