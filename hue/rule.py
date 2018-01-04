#
# rule.py - Contains Hue 'rule' definitions
#
import re
import enum

from . import common
from . import error


class Rule(common.Object):
    """
    Represents a Hue rule.

    """
    @property
    def name(self):
        return self._data['name']

    @property
    def status(self):
        return self._data['status']

    @property
    def last_triggered(self):
        return common.Time(self._data['lasttriggered'])

    @property
    def times_triggered(self):
        return self._data['timestriggered']

    @property
    def owner(self):
        user = self.bridge.get_whitelist().get(self._data['owner'])
        return "??" if user is None else user.name

    @property
    def conditions(self):
        def lookup(address, op, val):
            match = re.match(r"(/\w+/\d+)/(.*)", address)
            if not match:
                raise error.ConditionError("Bad address {}".format(address))
            full_id, item_addr = match.groups()
            obj = self.bridge.get_from_full_id(full_id)
            return obj.parse_condition(item_addr, common.Operator(op), val)

        return [lookup(c["address"], c["operator"],
                       c.get("value")) for c in self._data['conditions']]

    @property
    def actions(self):
        def lookup(address, body):
            match = re.match(r"(/\w+/\d+)/?(.*)", address)
            if not match:
                raise error.ConditionError("Bad address {}".format(address))
            full_id, item_addr = match.groups()
            obj = self.bridge.get_from_full_id(full_id)
            return obj.parse_action(item_addr, body)

        return [lookup(a['address'], a['body']) for a in self._data['actions']]

