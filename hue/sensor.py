#
# sensor.py - Contains Hue 'sensor' definitions
#

import enum

from . import common
from . import error


class SensorType(enum.Enum):
    """
    Enum of sensor types.

    """
    DAYLIGHT = "Daylight"
    DIMMER_SWITCH = "ZLLSwitch"
    TAP_SWITCH = "ZGPSwitch"
    GENERIC_STATUS = "CLIPGenericStatus"


class DimmerButtonEvent(enum.Enum):
    """
    Enum of dimmer button events.

    """
    ON_INITIAL_PRESSED = 1000
    ON_HOLD = 1001
    ON_SHORT_RELEASED = 1002
    ON_LONG_RELEASED = 1003

    DIM_UP_INITIAL_PRESSED = 2000
    DIM_UP_HOLD = 2001
    DIM_UP_SHORT_RELEASED = 2002
    DIM_UP_LONG_RELEASED = 2003

    DIM_DOWN_INITIAL_PRESSED = 3000
    DIM_DOWN_HOLD = 3001
    DIM_DOWN_SHORT_RELEASED = 3002
    DIM_DOWN_LONG_RELEASED = 3003

    OFF_INITIAL_PRESSED = 4000
    OFF_HOLD = 4001
    OFF_SHORT_RELEASED = 4002
    OFF_LONG_RELEASED = 4003


class TapButtonEvent(enum.Enum):
    """
    Enum of Hue tap button events
    """
    BUTTON1 = 34
    BUTTON2 = 16
    BUTTON3 = 17
    BUTTON4 = 18


class Sensor(common.Object):
    """
    Represents a Hue sensor.

    """
    _STATE_NAMES = {
        SensorType.DAYLIGHT: "daylight",
        SensorType.DIMMER_SWITCH: "buttonevent",
        SensorType.TAP_SWITCH: "buttonevent",
        SensorType.GENERIC_STATUS: "status",
    }

    @property
    def name(self):
        return self._data['name']

    @property
    def sensor_type(self):
        return SensorType(self._data['type'])

    @property
    def type_str(self):
        return self.sensor_type.name.lower().replace("_", "-")

    @property
    def state(self):
        value = self._data['state'][self.state_name]
        if self.sensor_type is SensorType.DIMMER_SWITCH:
            value = DimmerButtonEvent(value)
        elif self.sensor_type is SensorType.TAP_SWITCH:
            value = TapButtonEvent(value)
        return value

    @property
    def state_str(self):
        if self.sensor_type is SensorType.DIMMER_SWITCH:
            text = self.state.name.lower().replace("_", "-")
        elif self.sensor_type is SensorType.DAYLIGHT:
            text = "on" if self.state else "off"
        else:
            text = str(self.state)
        return text

    @property
    def state_name(self):
        return self._STATE_NAMES[self.sensor_type]

    @property
    def last_updated(self):
        return common.Time(self._data['state']['lastupdated'])

    @property
    def recycle(self):
        return self._data.get("recycle")

    @property
    def condition_items(self):
        return [ConditionItem.LAST_UPDATED,
                ConditionItem("state/{}".format(self.state_name))]

    def parse_condition(self, item_addr, operator, value):
        return Condition(self, ConditionItem(item_addr),
                         operator, value)

    def parse_action(self, item_addr, body):
        return Action(self, body.get('status'))


class ConditionItem(enum.Enum):
    DAYLIGHT = "state/daylight"
    BUTTON_EVENT = "state/buttonevent"
    STATUS = "state/status"
    LAST_UPDATED = "state/lastupdated"


class Condition(common.Condition):
    def __init__(self, sensor, item, operator, value):
        self._sensor = sensor
        self._item = item
        self._operator = operator

        if item is ConditionItem.LAST_UPDATED:
            self._value = value

        elif item is ConditionItem.STATUS:
            self._value = int(value)

        elif item is ConditionItem.BUTTON_EVENT:
            if sensor.sensor_type is SensorType.DIMMER_SWITCH:
                self._value = DimmerButtonEvent(int(value))
            else:
                self._value = TapButtonEvent(int(value))

        elif item is ConditionItem.DAYLIGHT:
            if isinstance(value, str):
                self._value = (value.lower() == "true")
            else:
                self._value = bool(value)

        else:
            raise error.ConditionError("Unknown condition item {!s}"
                                       .format(item))

    @property
    def address(self):
        return "{}/{}".format(self._sensor.full_id,
                              self._item.value)

    @property
    def operator(self):
        return self._operator

    @property
    def value_str(self):
        if isinstance(self._value, enum.Enum):
            return str(self._value.value)

        elif isinstance(self._value, bool):
            return "true" if self._value else "false"

        else:
            return str(self._value)

    def __str__(self):
        if isinstance(self._value, enum.Enum):
            val_str = self._value.name.lower().replace("_", "-")
        else:
            val_str = self._value
        return self.str_helper("Sensor", self._sensor.name,
                               self._item.name.lower().replace("_", "-"),
                               self.operator, val_str)


class Action(common.Action):
    def __init__(self, sensor, value):
        # Can only have actions for GENERIC_STATUS sensors
        if sensor.sensor_type != SensorType.GENERIC_STATUS:
            raise error.ActionError("Actions only permitted for generic status")

        self._sensor = sensor
        self._value = value

    @property
    def address(self):
        return "{}/state".format(self._sensor.full_id)

    @property
    def body(self):
        return { 'status': self._value }

    def __str__(self):
        return "Sensor '{}': set status = {}".format(self._sensor.name,
                                                     self._value)





