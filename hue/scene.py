#
# scene.py - Contains Hue 'scene' definitions
#

from . import object


class Scene(object.Object):
    """
    Represents a Hue scene.

    """
    @property
    def name(self):
        return self._data['name']

    @property
    def lights(self):
        return [self.bridge.get_light(lid) for lid in self._data['lights']]

    @property
    def last_updated(self):
        return self._data['lastupdated']