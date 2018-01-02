#
# bridge.py
#
# Hue Bridge interactions
#
import qhue
import requests
import cachetools
import operator

from .error import *
from .light import Light
from .scene import Scene
from .resourcelink import ResourceLink
from .sensor import Sensor
from .rule import Rule
from .group import Group
from .schedule import Schedule

# Basic config URL
_BASIC_CONFIG_URL = "http://{address}/api/config"

# Register URL
_REGISTER_URL = "http://{address}/api"

# URL to connect to bridge
_CONNECT_URL = "http://{address}/api/{username}"

# default timeout in seconds
_DEFAULT_TIMEOUT = 5

# Cache timeout
_CACHE_TIMEOUT = 2


class _Resource(qhue.qhue.Resource):
    """
    Wrapper around qhue resource to ensure it handles connection errors too.

    """

    def __call__(self, *args, **kwargs):
        try:
            return super().__call__(*args, **kwargs)
        except qhue.QhueException as exc:
            raise ResourceError(str(exc)) from exc
        except requests.ConnectionError as exc:
            raise ConnectionError("Failed to connect") from exc

    def __getattr__(self, name):
        return _Resource(self.url + "/" + str(name), timeout=self.timeout)


class Bridge:
    """
    Represents a hue bridge class.

    """

    _CLASSES = {
        "lights": Light,
        "scenes": Scene,
        "resourcelinks": ResourceLink,
        "sensors": Sensor,
        "rules": Rule,
        "groups": Group,
        "schedules": Schedule,
    }

    def __init__(self, address, timeout=_DEFAULT_TIMEOUT):
        self.address = address
        self.timeout = timeout
        self.name = None
        self.id = None

        # The bridge resource
        self._resource = None
        self._cache = cachetools.TTLCache(100, _CACHE_TIMEOUT)

        # Validate bridge address and get name and id
        config = self._get_basic_config(address)
        self.name = config['name']
        self.id = config['bridgeid']

    def _get_basic_config(self, address):
        return _Resource(_BASIC_CONFIG_URL.format(address=address),
                         self.timeout)()

    def register(self, devicetype, timeout=None):
        if timeout is None:
            timeout = self.timeout
        res = _Resource(_REGISTER_URL.format(address=self.address), timeout)
        response = res(devicetype=devicetype, http_method="post")
        return response[0]["success"]["username"]

    def connect(self, username):
        self._resource = _Resource(_CONNECT_URL.format(address=self.address,
                                                       username=username),
                                   self.timeout)

        # Execute a get on the bridge to check username is ok!
        self._resource.config()

    def get_lights(self, sort_by_name=True):
        return self._get_objects("lights", sort_by_name)

    def get_light(self, light_id):
        return self.get_object('lights', light_id)

    def get_scenes(self, sort_by_name=True):
        return self._get_objects("scenes", sort_by_name)

    def get_scene(self, scene_id):
        return self.get_object('scenes', scene_id)

    def get_resourcelinks(self, sort_by_name=True):
        return self._get_objects("resourcelinks", sort_by_name)

    def get_resourcelink(self, rlink_id):
        return self.get_object('resourcelinks', rlink_id)

    def get_from_full_id(self, full_id):
        _, res_name, res_id = full_id.split("/")
        return self.get_object(res_name, res_id)

    def get_from_full_ids(self, full_ids):
        # Find the set of resources we need to lookup.
        res_names = {fid.split("/")[1] for fid in full_ids}
        resources = {obj.full_id: obj for name in res_names
                                      for obj in self._get_objects(name, False)}
        return {fid: resources[fid] for fid in full_ids}


    @cachetools.cachedmethod(operator.attrgetter('_cache'))
    def _get_objects(self, res_name, sort_by_name):
        if self._resource is None:
            raise BridgeError("Not connected to bridge")

        objects = [self._CLASSES[res_name](self, i,
                                           self._resource[res_name][i], data)
                   for i, data in self._resource[res_name]().items()]
        if sort_by_name:
            objects = sorted(objects, key=lambda o: o.name)
        return objects

    @cachetools.cachedmethod(operator.attrgetter('_cache'))
    def get_object(self, res_name, res_id):
        if self._resource is None:
            raise BridgeError("Not connected to bridge")

        return self._CLASSES[res_name](self, res_id,
                                       self._resource[res_name][res_id])

