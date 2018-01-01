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
    def __init__(self, address, timeout=_DEFAULT_TIMEOUT):
        self.address = address
        self.timeout = timeout
        self.name = self._get_basic_config(address)['name']
        self._bridge = None

        self._cache = cachetools.TTLCache(10, _CACHE_TIMEOUT)

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
        self._bridge = _Resource(_CONNECT_URL.format(address=self.address,
                                                     username=username),
                                 self.timeout)

        # Execute a get on the bridge to check username is ok!
        self._bridge.config()

    @cachetools.cachedmethod(operator.attrgetter('_cache'))
    def get_lights(self, sort_by_name=True):
        if self._bridge is None:
            raise BridgeError("Not connected to bridge")

        lights =  [Light(id, self._bridge.lights[id], data)
                   for id, data in self._bridge.lights().items()]
        if sort_by_name:
            lights = sorted(lights, key=lambda l: l.name)
        return lights


