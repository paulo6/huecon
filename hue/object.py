class Object:
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