#
# object.py - Contains generic representation of Hue objects
#

import enum

class Object:
    """
    The base class for all Hue objects.

    """
    def __init__(self, bridge, obj_id, resource, data=None):
        self.id = obj_id
        self.bridge = bridge
        self._resource = resource
        self._data = data if data is not None else resource()

    @property
    def full_id(self):
        return self._resource.short_address

    def refresh(self):
        self._data = self._resource()

    def parse_action(self, item_addr, body):
        pass

    def parse_condition(self, item_addr, operator, value):
        pass


class Operator(enum.Enum):
    LT = "lt"
    GT = "gt"
    EQ = "eq"
    DX = "dx"


class Condition:
    def str_helper(self, prefix, name, item, operator, value):
        _OP_STRS = {
            Operator.LT: "<",
            Operator.GT: ">",
            Operator.EQ: "==",
            Operator.DX: "changed"
        }
        if self.operator is Operator.DX:
            return "{} '{}': {} changed".format(prefix, name, item)
        else:
            return "{} '{}': {} {} {}".format(prefix, name, item,
                                              _OP_STRS[operator], value)
    @property
    def address(self):
        pass

    @property
    def operator(self):
        pass

    @property
    def value(self):
        pass

    def __str__(self):
        pass


class Action:
    @property
    def address(self):
        pass

    @property
    def body(self):
        pass

    def __str__(self):
        pass