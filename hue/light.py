#
# bridge.py
#
# Hue Light interactions
#

class Light:
    def __init__(self, id, resource, data):
        self.id = id
        self._resource = resource
        self._data = data

    @property
    def name(self):
        return self._data['name']

    @property
    def is_on(self):
        return self._data['state']['on']

    def refresh(self):
        self._data = self._resource()
