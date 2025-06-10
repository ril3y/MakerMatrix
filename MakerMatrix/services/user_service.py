from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    UserAlreadyExistsError,
    InvalidReferenceError
)

class UserService:
    user_repo = UserRepository()

    @staticmethod
    def get_all_users() -> dict:
        """
        Returns all users in a consistent API response format.
        """
        try:
            users = UserService.user_repo.get_all_users()
            return {
                "status": "success",
                "message": "All users retrieved successfully",
                "data": users
            }
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve users: {str(e)}")
