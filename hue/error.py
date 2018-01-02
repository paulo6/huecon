#
# error.py - Contains error definitions used within the hue subpackage
#

class Error(Exception):
    """
    Base hue error class.

    """
    pass


class ResourceError(Error):
    """
    Error occurred requesting resource from bridge.

    """
    pass


class ConnectionError(ResourceError):
    """
    Connection error occurred when requesting resource from bridge.

    """
    pass


class BridgeError(Error):
    """
    Bridge error

    """
    pass


class LightError(Error):
    """
    Light error

    """
    pass

class ConditionError(Error):
    pass

class ActionError(Error):
    pass
