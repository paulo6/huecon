
from . import object

class ResourceLink(object.Object):
    @property
    def name(self):
        return self._data['name']

    @property
    def description(self):
        return self._data['description']

    @property
    def links(self):
        full_ids = self._data['links']
        resources = self.bridge.get_from_full_ids(full_ids)

        return [resources[fid] for fid in full_ids]