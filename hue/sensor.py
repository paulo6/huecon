
import enum
from collections import namedtuple

from . import object


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


class Sensor(object.Object):
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
        return value

    @property
    def state_str(self):
        if self.sensor_type is SensorType.DIMMER_SWITCH:
            text = self.state.name.lower().replace("_", "-")
        else:
            text = str(self.state)
        return text

    @property
    def state_name(self):
        return self._STATE_NAMES[self.sensor_type]

    @property
    def last_updated(self):
        return self._data['state']['lastupdated']

    @property
    def recycle(self):
        return self._data.get("recycle")

