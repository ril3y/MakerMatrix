from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import field_validator, ConfigDict
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.sqlite import JSON
import uuid


# Association table to link UserModel and RoleModel
class UserRoleLink(SQLModel, table=True):
    user_id: str = Field(foreign_key="usermodel.id", primary_key=True)
    role_id: str = Field(foreign_key="rolemodel.id", primary_key=True)


class RoleModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    users: List["UserModel"] = Relationship(back_populates="roles", link_model=UserRoleLink)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """ Custom serialization method for RoleModel """
        return self.model_dump(exclude={"users"})


class UserModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    password_change_required: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    roles: List[RoleModel] = Relationship(back_populates="users", link_model=UserRoleLink)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """ Custom serialization method for UserModel """
        base_dict = self.model_dump(exclude={"hashed_password"})
        # Handle datetime fields
        if isinstance(base_dict["created_at"], datetime):
            base_dict["created_at"] = base_dict["created_at"].isoformat()
        if isinstance(base_dict["last_login"], datetime):
            base_dict["last_login"] = base_dict["last_login"].isoformat()
        # Handle roles
        base_dict["roles"] = [role.to_dict() for role in self.roles] if self.roles else []
        return base_dict


class UserCreate(SQLModel):
    username: str
    email: str
    password: str
    roles: Optional[List[str]] = None  # List of role names

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None  # List of role names

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if v is not None:
            if len(v) < 3:
                raise ValueError("Username must be at least 3 characters long")
            if not v.isalnum():
                raise ValueError("Username must be alphanumeric")
        return v


class PasswordUpdate(SQLModel):
    current_password: str
    new_password: str

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v 