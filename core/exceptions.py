class KherimoyaPathNotFoundError(Exception):
    """Raised when Kherimoya can't resolve its root path"""

class ServerNotInPathError(Exception):
    """Raised if a server is not in the servers/ directory"""

class ServerDoesNotExistError(Exception):
    """Raised when a method which requires the server to exist is fired when it does not"""

class ServerCreationError(Exception):
    """Raised when a server could not be created"""