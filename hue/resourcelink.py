#
# resourcelink.py - Contains Hue 'resourcelink' definitions
#

from . import common

class ResourceLink(common.Object):
    """
    Represents a Hue resourcelink.

    """
    @property
    def name(self):
        return self._data['name']

    @property
    def description(self):
        return self._data['description']

    @property
    def recycle(self):
        return self._data["recycle"]

    @property
    def links(self):
        full_ids = self._data['links']
        resources = self.bridge.get_from_full_ids(full_ids)

        return [resources[fid] for fid in full_ids]