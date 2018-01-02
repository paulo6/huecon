
from . import object

class Group(object.Object):

    @property
    def name(self):
        return self._data['name']

