#
# bridge.py - Contains the main Hue bridge interface
#
import qhue
import requests
import cachetools
import operator
import socket

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
_AUTH_URL = "http://{address}/api/{username}"

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
        """
        Initialize bridge instance.

        This will perform basic connectivity check and obtain the bridge name.

        After init, 'auth' must be called before any further operations can be
        done.

        If no username has been created for this app yet, then 'register' can
        be called before auth to add a registration.

        Args:
            address: Address of the bridge. Can be IP or hostname.
            timeout: The timeout to use (default 5)

        """
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

    def register(self, devicetype):
        """
        Create a registration with the bridge.

        Before calling this, the user needs to press the bridge button.

        The result of this should be saved for future usage.

        Args:
            devicetype: The device type - used by the bridge to give some
                        context to who the registration belongs to.

                        This is usually of the form "app#user" - if the #user
                        part is not present, then hostname will be
                        automatically added.

        Returns: The unique username that this app should use with 'auth'.
                 This should be saved for future usage.

        """
        res = _Resource(_REGISTER_URL.format(address=self.address),
                        self.timeout)
        if "#" not in devicetype:
            devicetype += "#{}".format(socket.gethostname())
        response = res(devicetype=devicetype, http_method="post")
        return response[0]["success"]["username"]

    def auth(self, username):
        """
        Authenticate with the bridge using a previous

        Args:
            username: The username from a previous call to 'register'

        """
        self._resource = _Resource(_AUTH_URL.format(address=self.address,
                                                    username=username),
                                   self.timeout)

        # Execute a get on the bridge to check username is ok!
        self._resource.config()

    def get_lights(self, sort_by_name=True):
        return self._get_objects("lights", sort_by_name)

    def get_light(self, light_id):
        return self._get_object('lights', light_id)

    def get_scenes(self, sort_by_name=True):
        return self._get_objects("scenes", sort_by_name)

    def get_scene(self, scene_id):
        return self._get_object('scenes', scene_id)

    def get_resourcelinks(self, sort_by_name=True):
        return self._get_objects("resourcelinks", sort_by_name)

    def get_resourcelink(self, rlink_id):
        return self._get_object('resourcelinks', rlink_id)

    def get_groups(self, sort_by_name=True):
        return self._get_objects("groups", sort_by_name)

    def get_sensors(self, sort_by_name=True):
        return self._get_objects("sensors", sort_by_name)

    def get_rules(self, sort_by_name=True):
        return self._get_objects("rules", sort_by_name)

    def get_from_full_id(self, full_id):
        _, res_name, res_id = full_id.split("/")
        return self._get_object(res_name, res_id)

    def get_from_full_ids(self, full_ids):
        # Find the set of resources we need to lookup.
        res_names = {fid.split("/")[1] for fid in full_ids}
        resources = {obj.full_id: obj for name in res_names
                                      for obj in self._get_objects(name, False)}
        return {fid: resources[fid] for fid in full_ids}


    @cachetools.cachedmethod(operator.attrgetter('_cache'))
    def _get_objects(self, res_name, sort_by_name):
        if self._resource is None:
            raise BridgeError("Not authed with bridge")

        objects = [self._CLASSES[res_name](self, i,
                                           self._resource[res_name][i], data)
                   for i, data in self._resource[res_name]().items()]
        if sort_by_name:
            objects = sorted(objects, key=lambda o: o.name)
        return objects

    @cachetools.cachedmethod(operator.attrgetter('_cache'))
    def _get_object(self, res_name, res_id):
        if self._resource is None:
            raise BridgeError("Not authed with bridge")

        return self._CLASSES[res_name](self, res_id,
                                       self._resource[res_name][res_id])

