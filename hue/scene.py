#
# scene.py - Contains Hue 'scene' definitions
#

from . import common


class Scene(common.Object):
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
        return common.Time(self._data['lastupdated'])

    @property
    def recycle(self):
        return self._data['recycle']

    @property
    def locked(self):
        return self._data['locked']

    @property
    def owner(self):
        user = self.bridge.get_whitelist().get(self._data['owner'])
        return "??" if user is None else user.name