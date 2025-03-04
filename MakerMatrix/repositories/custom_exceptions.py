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

    def __init__(self, category_name: str, category_data: dict):
        self.category_name = category_name
        self.category_data = category_data
        super().__init__(f"Category with name '{category_name}' already exists.")
