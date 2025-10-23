from datetime import datetime
from passlib.hash import pbkdf2_sha256
from sqlalchemy.orm import joinedload
from sqlmodel import Session, select
from typing import Optional, List

from MakerMatrix.models.models import engine
from MakerMatrix.models.user_models import UserModel, RoleModel
from MakerMatrix.repositories.custom_exceptions import (
    ResourceNotFoundError,
    UserAlreadyExistsError,
    InvalidReferenceError,
)

pwd_context = pbkdf2_sha256


class UserRepository:
    def __init__(self):
        self.engine = engine

    def create_user(self, username: str, email: str, hashed_password: str, roles: List[str] = None) -> UserModel:
        with Session(self.engine) as session:
            # Check if username or email already exists
            existing_user = session.exec(
                select(UserModel).where((UserModel.username == username) | (UserModel.email == email))
            ).first()
            if existing_user:
                if existing_user.username == username:
                    raise UserAlreadyExistsError(
                        status="error",
                        message=f"Username '{username}' already exists",
                        data={"field": "username", "value": username},
                    )
                else:
                    raise UserAlreadyExistsError(
                        status="error",
                        message=f"Email '{email}' already exists",
                        data={"field": "email", "value": email},
                    )

            # Create new user
            user = UserModel(username=username, email=email, hashed_password=hashed_password)

            # Add roles if provided
            if roles:
                role_models = []
                for role_name in roles:
                    role = session.exec(select(RoleModel).where(RoleModel.name == role_name)).first()
                    if not role:
                        raise InvalidReferenceError(
                            status="error", message=f"Role '{role_name}' not found", data={"role_name": role_name}
                        )
                    role_models.append(role)
                user.roles = role_models

            session.add(user)
            session.commit()
            session.refresh(user)

            # Create a dictionary of the user data while the session is still open
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "password_change_required": user.password_change_required,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "roles": [
                    {"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions}
                    for role in user.roles
                ],
            }

            # Create a new detached instance with the loaded data
            detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
            detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]

            return detached_user

    def get_user_by_id(self, user_id: str) -> UserModel:
        with Session(self.engine) as session:
            statement = select(UserModel).options(joinedload(UserModel.roles)).where(UserModel.id == user_id)
            user = session.exec(statement).first()
            if not user:
                raise ResourceNotFoundError(status="error", message=f"User with ID '{user_id}' not found", data=None)

            # Create a dictionary of the user data while the session is still open
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "password_change_required": user.password_change_required,
                "created_at": (
                    datetime.fromisoformat(user.created_at.isoformat())
                    if isinstance(user.created_at, datetime)
                    else datetime.fromisoformat(user.created_at)
                ),
                "last_login": (
                    datetime.fromisoformat(user.last_login.isoformat())
                    if user.last_login and isinstance(user.last_login, datetime)
                    else user.last_login
                ),
                "hashed_password": user.hashed_password,
                "roles": [
                    {"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions}
                    for role in user.roles
                ],
            }

            # Create a new detached instance with the loaded data
            detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
            detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]

            return detached_user

    def get_user_by_username(self, username: str) -> UserModel:
        try:
            with Session(self.engine) as session:
                statement = select(UserModel).options(joinedload(UserModel.roles)).where(UserModel.username == username)
                user = session.exec(statement).first()
                if not user:
                    raise ResourceNotFoundError(
                        status="error", message=f"User with username '{username}' not found", data=None
                    )

                # Create a dictionary of the user data while the session is still open
                user_dict = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_active": user.is_active,
                    "password_change_required": user.password_change_required,
                    "created_at": (
                        datetime.fromisoformat(user.created_at.isoformat())
                        if isinstance(user.created_at, datetime)
                        else datetime.fromisoformat(user.created_at)
                    ),
                    "last_login": (
                        datetime.fromisoformat(user.last_login.isoformat())
                        if user.last_login and isinstance(user.last_login, datetime)
                        else user.last_login
                    ),
                    "hashed_password": user.hashed_password,
                    "roles": [
                        {
                            "id": role.id,
                            "name": role.name,
                            "description": role.description,
                            "permissions": role.permissions,
                        }
                        for role in user.roles
                    ],
                }

                # Create a new detached instance with the loaded data
                detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
                detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]

                return detached_user
        except Exception as e:
            # Log the database error and re-raise with more context
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Database error in get_user_by_username: {e}")
            logger.error(f"Database URL: {self.engine.url}")
            raise

    def get_user_by_email(self, email: str) -> UserModel:
        with Session(self.engine) as session:
            statement = select(UserModel).options(joinedload(UserModel.roles)).where(UserModel.email == email)
            user = session.exec(statement).first()
            if not user:
                raise ResourceNotFoundError(status="error", message=f"User with email '{email}' not found", data=None)

            # Create a dictionary of the user data while the session is still open
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "password_change_required": user.password_change_required,
                "created_at": (
                    datetime.fromisoformat(user.created_at.isoformat())
                    if isinstance(user.created_at, datetime)
                    else datetime.fromisoformat(user.created_at)
                ),
                "last_login": (
                    datetime.fromisoformat(user.last_login.isoformat())
                    if user.last_login and isinstance(user.last_login, datetime)
                    else user.last_login
                ),
                "hashed_password": user.hashed_password,
                "roles": [
                    {"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions}
                    for role in user.roles
                ],
            }

            # Create a new detached instance with the loaded data
            detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
            detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]

            return detached_user

    def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        is_active: Optional[bool] = None,
        roles: Optional[List[str]] = None,
        password_change_required: Optional[bool] = None,
        last_login: Optional[datetime] = None,
    ) -> Optional[UserModel]:
        with Session(self.engine) as session:
            statement = select(UserModel).options(joinedload(UserModel.roles)).where(UserModel.id == user_id)
            user = session.exec(statement).first()
            if not user:
                raise ResourceNotFoundError(status="error", message=f"User with ID '{user_id}' not found", data=None)

            if email is not None:
                # Check if email is already used by another user
                existing_user = session.exec(
                    select(UserModel).where((UserModel.email == email) & (UserModel.id != user_id))
                ).first()
                if existing_user:
                    raise UserAlreadyExistsError(
                        status="error",
                        message=f"Email '{email}' already exists",
                        data={"field": "email", "value": email},
                    )
                user.email = email

            if is_active is not None:
                user.is_active = is_active

            if password_change_required is not None:
                user.password_change_required = password_change_required

            if last_login is not None:
                user.last_login = last_login

            if roles is not None:
                role_models = []
                for role_name in roles:
                    role = session.exec(select(RoleModel).where(RoleModel.name == role_name)).first()
                    if not role:
                        raise InvalidReferenceError(
                            status="error", message=f"Role '{role_name}' not found", data={"role_name": role_name}
                        )
                    role_models.append(role)
                user.roles = role_models

            session.add(user)
            session.commit()
            session.refresh(user)

            # Create a dictionary of the user data while the session is still open
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "password_change_required": user.password_change_required,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "roles": [
                    {"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions}
                    for role in user.roles
                ],
            }

            # Create a new detached instance with the loaded data
            detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
            detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]

            return detached_user

    def update_password(self, user_id: str, new_hashed_password: str) -> Optional[UserModel]:
        with Session(self.engine) as session:
            statement = select(UserModel).options(joinedload(UserModel.roles)).where(UserModel.id == user_id)
            user = session.exec(statement).first()
            if not user:
                return None

            user.hashed_password = new_hashed_password
            session.add(user)
            session.commit()
            session.refresh(user)

            # Create a dictionary of the user data while the session is still open
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "password_change_required": user.password_change_required,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "roles": [
                    {"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions}
                    for role in user.roles
                ],
            }

            # Create a new detached instance with the loaded data
            detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
            detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]

            return detached_user

    def delete_user(self, user_id: str) -> bool:
        with Session(self.engine) as session:
            user = session.exec(select(UserModel).where(UserModel.id == user_id)).first()
            if not user:
                raise ResourceNotFoundError(status="error", message=f"User with ID '{user_id}' not found", data=None)

            session.delete(user)
            session.commit()
            return True

    def create_role(
        self, name: str, description: Optional[str] = None, permissions: Optional[List[str]] = None
    ) -> RoleModel:
        with Session(self.engine) as session:
            # Check if role name already exists
            existing_role = session.exec(select(RoleModel).where(RoleModel.name == name)).first()
            if existing_role:
                raise RuntimeError(f"Role '{name}' already exists")

            role = RoleModel(name=name, description=description, permissions=permissions or [])
            session.add(role)
            session.commit()
            session.refresh(role)
            return role

    def get_all_roles(self) -> List[RoleModel]:
        """Get all roles in the system"""
        with Session(self.engine) as session:
            return session.exec(select(RoleModel)).all()

    def get_role_by_name(self, name: str) -> Optional[RoleModel]:
        with Session(self.engine) as session:
            role = session.exec(select(RoleModel).where(RoleModel.name == name)).first()
            if not role:
                raise ResourceNotFoundError(status="error", message=f"Role with name '{name}' not found", data=None)
            return role

    def get_role_by_id(self, role_id: str) -> Optional[RoleModel]:
        with Session(self.engine) as session:
            return session.exec(select(RoleModel).where(RoleModel.id == role_id)).first()

    def update_role(
        self, role_id: str, description: Optional[str] = None, permissions: Optional[List[str]] = None
    ) -> Optional[RoleModel]:
        with Session(self.engine) as session:
            role = session.exec(select(RoleModel).where(RoleModel.id == role_id)).first()
            if not role:
                return None

            if description is not None:
                role.description = description
            if permissions is not None:
                role.permissions = permissions

            session.add(role)
            session.commit()
            session.refresh(role)
            return role

    def delete_role(self, role_id: str) -> bool:
        with Session(self.engine) as session:
            role = session.exec(select(RoleModel).where(RoleModel.id == role_id)).first()
            if not role:
                return False

            session.delete(role)
            session.commit()
            return True

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pbkdf2_sha256.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pbkdf2_sha256.hash(password)

    def get_all_users(self) -> list[dict]:
        """
        Retrieve all users with their roles and relevant fields as dicts.
        """
        with Session(self.engine) as session:
            users = session.exec(select(UserModel).options(joinedload(UserModel.roles))).unique().all()
            user_dicts = []
            for user in users:
                user_dicts.append(
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "is_active": user.is_active,
                        "password_change_required": user.password_change_required,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                        "last_login": user.last_login.isoformat() if user.last_login else None,
                        "roles": [
                            {
                                "id": role.id,
                                "name": role.name,
                                "description": role.description,
                                "permissions": role.permissions,
                            }
                            for role in user.roles
                        ],
                    }
                )
            return user_dicts
