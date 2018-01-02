#
# rule.py - Contains Hue 'rule' definitions
#
from . import object

class Rule(object.Object):
    """
    Represents a Hue rule.

    """
    @property
    def name(self):
        return self._data['name']

