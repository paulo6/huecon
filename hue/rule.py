
from . import object

class Rule(object.Object):

    @property
    def name(self):
        return self._data['name']

