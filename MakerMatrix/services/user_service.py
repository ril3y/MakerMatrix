from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    UserAlreadyExistsError,
    InvalidReferenceError,
)
from MakerMatrix.services.base_service import BaseService, ServiceResponse


class UserService(BaseService):
    """
    User service with BaseService foundation for consistency.

    Note: This service uses repository patterns that don't require session management,
    but inherits BaseService for consistent error handling and logging.
    """

    def __init__(self):
        super().__init__()
        self.user_repo = UserRepository()
        self.entity_name = "User"

    def get_all_users(self) -> ServiceResponse[list]:
        """
        Returns all users using consistent ServiceResponse format.
        """
        try:
            self.log_operation("get_all", self.entity_name)
            users = self.user_repo.get_all_users()
            return self.success_response(f"All {self.entity_name.lower()}s retrieved successfully", users)
        except Exception as e:
            return self.handle_exception(e, f"retrieve all {self.entity_name.lower()}s")
