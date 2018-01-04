#
# common.py - Contains common definitions and base object definitions
#
import datetime
import enum

MAX_BRIGHTNESS = 254

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
    def value_str(self):
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


class Time:
    IN_FORMAT = "%Y-%m-%dT%H:%M:%S"
    OUT_FORMAT = "%d/%m/%Y %H:%M:%S"
    def __init__(self, time_str):
        if time_str == "none":
            self.datetime = None
        else:
            self.datetime = datetime.datetime.strptime(time_str, self.IN_FORMAT)

    def __str__(self):
        return (self.datetime.strftime(self.OUT_FORMAT)
                if self.datetime is not None else "none")
