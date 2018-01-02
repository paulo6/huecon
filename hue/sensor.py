
from . import object

class Sensor(object.Object):

    @property
    def name(self):
        return self._data['name']

    @property
    def stype(self):
        return self._data['type']
