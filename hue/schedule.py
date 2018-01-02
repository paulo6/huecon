#
# schedule.py - Contains Hue 'schedule' definitions
#
from . import object

class Schedule(object.Object):
    """
    Represents a Hue schedule.

    """
    @property
    def name(self):
        return self._data['name']

