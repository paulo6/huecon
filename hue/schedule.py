#
# schedule.py - Contains Hue 'schedule' definitions
#
from . import common

class Schedule(common.Object):
    """
    Represents a Hue schedule.

    """
    @property
    def name(self):
        return self._data['name']

