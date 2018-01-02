
from . import object

class Schedule(object.Object):

    @property
    def name(self):
        return self._data['name']

