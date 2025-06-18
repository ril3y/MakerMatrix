class ResourceNotFoundError(Exception):
    """Custom exception to be raised when a requested resource is not found."""

    def __init__(self, status: str,
                 message: str,
                 data=None):
        self.status = status
        self.message = message
        self.data = data

        super().__init__(f"{message}")


class PartAlreadyExistsError(Exception):
    """Custom exception to be raised when a part already exists."""

    def __init__(self, status: str, message: str, data: dict):
        self.status = status
        self.message = message
        self.data = data
        super().__init__(message)


class CategoryAlreadyExistsError(Exception):
    """Custom exception to be raised when a category already exists."""

    def __init__(self, status: str, message: str, data: dict):
        self.status = status
        self.message = message
        self.data = data
        super().__init__(message)


class LocationAlreadyExistsError(Exception):
    """Custom exception to be raised when a location already exists."""

    def __init__(self, status: str, message: str, data: dict):
        self.status = status
        self.message = message
        self.data = data
        super().__init__(message)


class UserAlreadyExistsError(Exception):
    """Custom exception to be raised when a user already exists."""

    def __init__(self, status: str, message: str, data: dict):
        self.status = status
        self.message = message
        self.data = data
        super().__init__(message)


class InvalidReferenceError(Exception):
    """Custom exception to be raised when an invalid reference (foreign key) is provided."""

    def __init__(self, status: str, message: str, data=None):
        self.status = status
        self.message = message
        self.data = data
        super().__init__(message)


class SupplierConfigAlreadyExistsError(Exception):
    """Custom exception to be raised when a supplier configuration already exists."""

    def __init__(self, message: str, status: str = "error", data=None):
        self.status = status
        self.message = message
        self.data = data
        super().__init__(message)
