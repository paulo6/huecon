#
# config.py
#
# Huecon config manager
#

import json
import enum

class Error(Exception):
    """Base exception for this module."""


class ConfigError(Error):
    """Exception raised when config file contains bad data."""


class Config:
    """
    Represents Huecon configuration data.

    """

    def __init__(self, filename):
        """
        Initialize the Config class.

        Arguments:
                filename:
                    The config filename

        """
        # Attempt to load file
        try:
            self._data = self._read_file(filename)
        except FileNotFoundError:
            self._data = {}

        self._filename = filename

    def get_bridges(self):
        """Generates tuples of (address, username) for known bridges."""
        for bridge in self._data.get(_ConfigField.BRIDGES.value, []):
            yield (bridge[_BridgeField.ADDRESS.value],
                   bridge[_BridgeField.USERNAME.value])

    def add_bridge(self, address, username):
        """Add a bridge to the config file."""
        if _ConfigField.BRIDGES.value not in self._data:
            self._data[_ConfigField.BRIDGES.value] = []

        self._data[_ConfigField.BRIDGES.value].append(
            {_BridgeField.ADDRESS.value: address,
             _BridgeField.USERNAME.value: username})

    def write_file(self):
        """Write the config file."""
        with open(self._filename, mode="w") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)

    def _read_file(self, filename):
        """Private helper for reading and validating a config file."""
        with open(filename, mode="r") as f:
            data = json.load(f)

        # Check top level fields
        for key in data:
            try:
                _ConfigField(key)
            except TypeError:
                raise ConfigError("Unexpected config field '{}'".format(key))

        # Check bridges
        bridges = data.get(_ConfigField.BRIDGES.value)
        if bridges:
            if not isinstance(bridges, list):
                raise ConfigError("{} should be a list of objects"
                                  .format(_ConfigField.BRIDGES.value))
            for idx, bridge in enumerate(bridges):

                for key in bridge:
                    try:
                        _BridgeField(key)
                    except TypeError:
                        raise ConfigError(
                            "Bridge index {} has unexpected field '{}'"
                            .format(idx, key))
        return data



class _ConfigField(enum.Enum):
    BRIDGES = "bridges"


class _BridgeField(enum.Enum):
    ADDRESS = "address"
    USERNAME = "username"