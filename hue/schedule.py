#
# schedule.py - Contains Hue 'schedule' definitions
#
import enum
import re

from . import common

class Schedule(common.Object):
    """
    Represents a Hue schedule.

    """
    @property
    def name(self):
        return self._data['name']

    @property
    def is_enabled(self):
        return Status(self._data['status']) is Status.ENABLED

    @property
    def timer_time(self):
        return self._data['localtime']

    @property
    def created_time(self):
        return common.Time(self._data['created'])

    @property
    def start_time(self):
        return common.Time(self._data['starttime'])

    @property
    def auto_delete(self):
        return self._data['autodelete']

    @property
    def recycle(self):
        return self._data['recycle']

    @property
    def command_action(self):
        command = self._data['command']
        # Address is /api/<username>/<resource>/<id>/<item>
        #   where /<item> may be omitted
        match = re.match(r"/api/.*(/\w+/\d+)/?(.*)", command['address'])
        full_id, item_addr = match.groups()
        obj = self.bridge.get_from_full_id(full_id)
        return obj.parse_action(item_addr, command['body'])

    def parse_action(self, item_addr, body):
        status = body.get("status")
        return Action(self, body.get("localtime"),
                      None if status is None else Status(status))


class Status(enum.Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class Action(common.Action):
    def __init__(self, schedule, localtime=None, status=None):
        self._schedule = schedule
        self._localtime = localtime
        self._status = status

    @property
    def address(self):
        return "{}/state".format(self._sensor.full_id)

    @property
    def body(self):
        out = {}
        if self._status is not None:
            out['status'] = self._status.value
        if self._localtime is not None:
            out['localtime'] = self._localtime
        return out

    def __str__(self):
        actions = []
        if self._status is not None:
            actions.append("set status = {}".format(self._status.value))
        if self._localtime is not None:
            actions.append("set time = {}".format(self._localtime))
        return "Schedule '{}': {}".format(self._schedule.name,
                                          ", ".join(actions))
