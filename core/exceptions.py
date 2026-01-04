class KherimoyaPathNotFoundError(Exception):
    """Raised when Kherimoya can't resolve its root path"""

class ServerNotInPathError(Exception):
    """Raised if a server is not in the servers/ directory"""

class ServerDoesNotExistError(Exception):
    """Raised when a method which requires the server to exist is called when it does not"""

class ServerNotRunningError(Exception):
    """Raised when a method which requires the server to be running is called when it is not"""

class ServerCreationError(Exception):
    """Raised when a server could not be created"""

class ServerStartError(Exception):
    """Raised when a server could not be started"""

class ServerStopError(Exception):
    """Raised when a sercer could not be stopped"""

class ServerRenameError(Exception):
    """Raised when a server could not be renamed"""

class InvalidParameterError(Exception):
    """Raised when an invalid parameter is provided to a method"""