This file is a merged representation of the entire codebase, combined into a single document by Repomix.
The content has been processed where security check has been disabled.

# File Summary

## Purpose
This file contains a packed representation of the entire repository's contents.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Security check has been disabled - content may contain sensitive information
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
```
MakerMatrix/
  api/
    easyeda.py
  database/
    db.py
  dependencies/
    __init__.py
    auth.py
  handlers/
    exception_handlers.py
  integration_tests/
    .gitkeep
    test_printer_service.py
  models/
    label_model.py
    models.py
    printer_config_model.py
    printer_request_model.py
    user_models.py
  parsers/
    boltdepot_parser.py
    lcsc_parser.py
    mouser_parser.py
    parser.py
  printers/
    abstract_printer.py
    brother_ql.py
  repositories/
    base_repository.py
    category_repositories.py
    custom_exceptions.py
    location_repositories.py
    parts_repositories.py
    printer_repository.py
    user_repository.py
  routers/
    auth_routes.py
    categories_routes.py
    locations_routes.py
    parts_routes.py
    printer_routes.py
    role_routes.py
    user_routes.py
    utility_routes.py
  schemas/
    location_delete_response.py
    part_create.py
    part_response.py
    response.py
  scripts/
    setup_admin.py
  services/
    auth_service.py
    category_service.py
    label_service.py
    location_service.py
    part_service.py
    printer_service.py
    user_service.py
  tests/
    conftest.py
    printer_config.json
    test_admin_login.py
    test_advanced_search.py
    test_auth_centralized.py
    test_auth.py
    test_categories.py
    test_integration_create_part.py
    test_integration_get_all_users.py
    test_locations_cleanup.py
    test_locations_crud.py
    test_locations_hierarchy.py
    test_mobile_login.py
    test_part_service.py
    test_test_model.py
    test_user_routes_smoke.py
    test_user_service.py
  dependencies.py
  main.py
  part_inventory.json
  PROJECT_STATUS.md
  README.md
venv310/
  Include/
    site/
      python3.12/
        greenlet/
          greenlet.h
  Scripts/
    activate
    activate.bat
    Activate.ps1
    deactivate.bat
    prichunkpng
    pricolpng
    priditherpng
    priforgepng
    prigreypng
    pripalpng
    pripamtopng
    priplan9topng
    pripnglsch
    pripngtopam
    prirowpng
    priweavepng
  share/
    man/
      man1/
        qr.1
  pyvenv.cfg
.gitignore
part_inventory.json
printer_config.json
project_status.md
pyproject.toml
pytest.ini
README.md
requirements-dev.txt
requirements.txt
```

# Files

## File: MakerMatrix/api/easyeda.py
````python
# Global imports
import logging
import requests

API_ENDPOINT = "https://easyeda.com/api/products/{lcsc_id}/components?version=6.4.19.5"
ENDPOINT_3D_MODEL = "https://easyeda.com/analyzer/api/3dmodel/{uuid}"
# ------------------------------------------------------------


class EasyedaApi:
    def __init__(self) -> None:
        self.headers = {
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": f"easyeda2kicad v0.6.6",
        }

    def get_info_from_easyeda_api(self, lcsc_id: str) -> dict:
        r = requests.get(url=API_ENDPOINT.format(lcsc_id=lcsc_id), headers=self.headers)
        api_response = r.json()

        if not api_response or (
            "code" in api_response and api_response["success"] is False
        ):
            logging.debug(f"{api_response}")
            return {}

        return r.json()

    def get_cad_data_of_component(self, lcsc_id: str) -> dict:
        cp_cad_info = self.get_info_from_easyeda_api(lcsc_id=lcsc_id)
        if cp_cad_info == {}:
            return {}
        return cp_cad_info["result"]

    def get_raw_3d_model_obj(self, uuid: str) -> str:
        r = requests.get(
            url=ENDPOINT_3D_MODEL.format(uuid=uuid),
            headers={"User-Agent": self.headers["User-Agent"]},
        )
        if r.status_code != requests.codes.ok:
            logging.error(f"No 3D model data found for uuid:{uuid} on easyeda")
            return None
        return r.content.decode()
````

## File: MakerMatrix/database/db.py
````python
from typing import Generator

from sqlmodel import Session, SQLModel
from MakerMatrix.models.models import engine
from sqlalchemy import inspect, event
from sqlalchemy import event


# Dependency that will provide a session to FastAPI routes
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


# Function to create tables in the SQLite database
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)




@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
````

## File: MakerMatrix/dependencies/__init__.py
````python
# This file makes the dependencies directory a proper Python package 
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
````

## File: MakerMatrix/dependencies/auth.py
````python
from typing import Optional, Callable, List, Dict, Any
from fastapi import Depends, HTTPException, status, APIRouter, Request
from fastapi.security import OAuth2PasswordBearer
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.models.user_models import UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
auth_service = AuthService()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserModel:
    """Dependency to get the current authenticated user."""
    return auth_service.get_current_user(token)


async def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Dependency to get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_permission(required_permission: str):
    """Dependency factory to check if the current user has the required permission."""
    async def permission_dependency(current_user: UserModel = Depends(get_current_active_user)) -> UserModel:
        if not auth_service.has_permission(current_user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {required_permission} required"
            )
        return current_user
    return permission_dependency


def require_admin(current_user: UserModel = Depends(get_current_active_user)) -> UserModel:
    """Dependency to check if the current user is an admin."""
    for role in current_user.roles:
        if role.name == "admin" or "all" in role.permissions:
            return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )


def secure_all_routes(router: APIRouter, exclude_paths: List[str] = None, permissions: Dict[str, str] = None):
    """
    Apply authentication dependencies to all routes in a router.
    
    Args:
        router: The router to secure
        exclude_paths: List of path operations to exclude from authentication (e.g., ["/public-endpoint"])
        permissions: Dict mapping paths to required permissions (e.g., {"/admin-endpoint": "admin:access"})
        
    Returns:
        The secured router
    """
    if exclude_paths is None:
        exclude_paths = []
    
    if permissions is None:
        permissions = {}
    
    # Store the original routes
    original_routes = router.routes.copy()
    
    # Clear the router routes
    router.routes.clear()
    
    # Add the routes back with dependencies
    for route in original_routes:
        path = route.path
        
        # Skip excluded paths
        if path in exclude_paths:
            router.routes.append(route)
            continue
        
        # Check if this path needs specific permissions
        if path in permissions:
            # Add permission-specific dependency
            route.dependencies.append(Depends(require_permission(permissions[path])))
        else:
            # Add general authentication dependency
            route.dependencies.append(Depends(get_current_active_user))
        
        router.routes.append(route)
    
    return router
````

## File: MakerMatrix/handlers/exception_handlers.py
````python
from fastapi import Request
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_409_CONFLICT

from MakerMatrix.repositories.custom_exceptions import PartAlreadyExistsError, ResourceNotFoundError
from MakerMatrix.schemas.response import ResponseSchema


def register_exception_handlers(app):
    """Register all exception handlers for the FastAPI app."""
    
    @app.exception_handler(PartAlreadyExistsError)
    async def part_already_exists_handler(request: Request, exc: PartAlreadyExistsError):
        return JSONResponse(
            status_code=HTTP_409_CONFLICT,
            content=ResponseSchema(
                status="error",
                message=exc.message,
                data=None
            ).model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Extract validation error details
        errors = exc.errors()

        messages = []
        for error in errors:
            loc = error.get("loc")
            msg = error.get("msg")
            typ = error.get("type")
            messages.append(f"Error in {loc}: {msg} ({typ})")

        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            content=ResponseSchema(
                status="error",
                message="Validation error",
                data=messages
            ).model_dump()
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # For all HTTP exceptions, use the ResponseSchema format
        return JSONResponse(
            status_code=exc.status_code,
            content=ResponseSchema(
                status="error",
                message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                data=None
            ).model_dump()
        )

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(
            status_code=404,
            content=ResponseSchema(
                status="error",
                message=str(exc),
                data=None
            ).model_dump()
        )
````

## File: MakerMatrix/integration_tests/.gitkeep
````

````

## File: MakerMatrix/integration_tests/test_printer_service.py
````python
import uuid

import pytest
pytestmark = pytest.mark.integration
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlmodel import SQLModel

from MakerMatrix.lib.print_settings import PrintSettings
from MakerMatrix.main import app
from MakerMatrix.models.label_model import LabelData
from MakerMatrix.models.models import PartModel, engine, create_db_and_tables
from MakerMatrix.repositories.printer_repository import PrinterRepository
from MakerMatrix.services.printer_service import PrinterService
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Set up the database (tables creation)
    create_db_and_tables()
    
    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)

    yield  # Let the tests run

    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def admin_token():
    """Get an admin token for authentication."""
    # Login data for the admin user
    login_data = {
        "username": "admin",
        "password": "Admin123!"  # Updated to match the default password in setup_admin.py
    }
    
    # Post to the login endpoint
    response = client.post("/auth/login", json=login_data)
    
    # Check that the login was successful
    assert response.status_code == 200
    
    # Extract and return the access token
    assert "access_token" in response.json()
    return response.json()["access_token"]


@pytest.fixture
def printer_service() -> PrinterService:
    """Construct a PrinterService that uses the same repository fixture."""
    # Create a test configuration in memory
    test_config = {
        "backend": "network",
        "driver": "brother_ql",
        "printer_identifier": "tcp://192.168.1.71",
        "model": "QL-800",
        "dpi": 300,
        "scaling_factor": 1.1
    }

    # Create a printer service with the test configuration
    printer_service = PrinterService(PrinterRepository())
    printer_service.set_printer_config(test_config)
    return printer_service


def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def setup_part_update_part(admin_token):
    # Initial setup: create a part to update later
    part_data = {
        "part_number": "323329329dj91",
        "part_name": "hammer drill",
        "quantity": 500,
        "description": "A standard hex head screw",
        "location_id": None,
        "category_names": ["hammers", "screwdrivers"],
        "additional_properties": {
            "color": "silver",
            "material": "stainless steel"
        }
    }

    # Make a POST request to add the part to the database
    response = client.post(
        "/parts/add_part", 
        json=part_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    return response.json()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_qr_code_with_name(printer_service, setup_part_update_part, admin_token):
    # Get the part ID from the setup
    part_id = setup_part_update_part["id"]
    
    # Make a request to print a QR code for the part
    response = client.post(
        f"/printer/print_qr_code/{part_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "QR code printed successfully" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_part_name(printer_service, setup_part_update_part, admin_token):
    # Get the part ID from the setup
    part_id = setup_part_update_part["id"]
    
    # Make a request to print the part name
    response = client.post(
        f"/printer/print_part_name/{part_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Part name printed successfully" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_text_label(printer_service, admin_token):
    # Make a request to print a text label
    response = client.post(
        "/printer/print_text",
        json={"text": "Test Label"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "Text label printed successfully" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_qr_and_text_combined(printer_service, admin_token):
    # Set up printer config
    printer_config = {
        "backend": "network",
        "driver": "brother_ql",
        "printer_identifier": "tcp://192.168.1.71",
        "model": "QL-800",
        "dpi": 300,
        "scaling_factor": 1.1
    }
    
    # Set up label data
    label_data = {
        "qr_data": "https://example.com",
        "text": "Example Label",
        "font_size": 24,
        "qr_size": 200,
        "label_width": 62,
        "label_margin": 5
    }
    
    # Make a request to print a combined QR code and text label
    response = client.post(
        "/printer/print_qr_and_text",
        json={"printer_config": printer_config, "label_data": label_data},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "QR code and text label printed successfully" in response.json()["message"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_print_qr_and_text_combined_fixed_length(printer_service, admin_token):
    # Set up printer config
    printer_config = {
        "backend": "network",
        "driver": "brother_ql",
        "printer_identifier": "tcp://192.168.1.71",
        "model": "QL-800",
        "dpi": 300,
        "scaling_factor": 1.1
    }
    
    # Set up label data with fixed length
    label_data = {
        "qr_data": "https://example.com",
        "text": "Example Label",
        "font_size": 24,
        "qr_size": 200,
        "label_width": 62,
        "label_margin": 5,
        "fixed_label_length": 100
    }
    
    # Make a request to print a combined QR code and text label with fixed length
    response = client.post(
        "/printer/print_qr_and_text",
        json={"printer_config": printer_config, "label_data": label_data},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "QR code and text label printed successfully" in response.json()["message"]
````

## File: MakerMatrix/models/label_model.py
````python
from pydantic import BaseModel, model_validator, Field, ValidationError, ConfigDict

from MakerMatrix.parts.parts import Part


class LabelData(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "part_number": "c1591",
                "part_name": "cl10b104kb8nnnc"
            }
        }
    )

    part: Part = Field(default=None, description="The part that contains the data for the label")
    label_size: str = Field(None, description="The label size")
    part_name: str = Field(None, description="The part name")

    @model_validator(mode='before')
    @classmethod
    def check_at_least_one(cls, values):
        part_number = values.get('part_number')
        part_name = values.get('part_name')

        # Raise an error if neither part_number nor part_name is provided
        if not part_number and not part_name:
            raise ValueError('At least one of part_number or part_name must be provided.')

        return values

    # class Config:
    #     schema_extra = {
    #         "example": {
    #             "part_number": "c1591",
    #             "part_name": "cl10b104kb8nnnc"
    #         }
    #     }
````

## File: MakerMatrix/models/models.py
````python
from typing import Optional, Dict, Any, List, Union
from pydantic import model_validator, field_validator, BaseModel, ConfigDict
from sqlalchemy import create_engine, ForeignKey, String, or_, cast, UniqueConstraint
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import SQLModel, Field, Relationship, Session, select
import uuid
from pydantic import Field as PydanticField
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.sqlite import JSON
from datetime import datetime
from MakerMatrix.models.user_models import UserModel, RoleModel, UserRoleLink

# Association table to link PartModel and CategoryModel
class PartCategoryLink(SQLModel, table=True):
    part_id: str = Field(foreign_key="partmodel.id", primary_key=True)
    category_id: str = Field(foreign_key="categorymodel.id", primary_key=True)


class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    children: Optional[List[str]] = None  # List of child category IDs


# CategoryModel
class CategoryModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    parts: List["PartModel"] = Relationship(back_populates="categories", link_model=PartCategoryLink, sa_relationship_kwargs={"lazy": "selectin"})

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """ Custom serialization method for CategoryModel """
        return self.model_dump(exclude={"parts"})


class LocationQueryModel(SQLModel):
    id: Optional[str] = None
    name: Optional[str] = None


class LocationModel(SQLModel, table=True):

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: Optional[str] = Field(index=True)
    description: Optional[str] = None
    parent_id: Optional[str] = Field(default=None, foreign_key="locationmodel.id")
    location_type: str = Field(default="standard")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Add SQLAlchemy table constraints
    __table_args__ = (
        UniqueConstraint('name', 'parent_id', name='uix_location_name_parent'),
    )

    parent: Optional["LocationModel"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "LocationModel.id"}
    )
    children: List["LocationModel"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    parts: List["PartModel"] = Relationship(
        back_populates="location",
        sa_relationship_kwargs={"passive_deletes": True}
    )


    @classmethod
    def get_with_children(cls, session: Session, location_id: str) -> Optional["LocationModel"]:
        """ Custom method to get a location with its children """
        statement = select(cls).options(selectinload(cls.children)).where(cls.id == location_id)
        return session.exec(statement).first()

    def to_dict(self) -> Dict[str, Any]:
        """ Custom serialization method for LocationModel """
        base_dict = self.model_dump(exclude={"parent"})
        # Convert the related children to a list of dictionaries
        if "children" in base_dict and base_dict["children"]:
            base_dict["children"] = [child.to_dict() for child in base_dict["children"]]
        return base_dict


class LocationUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    location_type: Optional[str] = None


# PartModel
class PartModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_number: Optional[str] = Field(index=True)
    part_name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    quantity: Optional[int]
    supplier: Optional[str] = None

    location_id: Optional[str] = Field(
        default=None,
        sa_column=Column(
            String, ForeignKey("locationmodel.id", ondelete="SET NULL")
        )
    )

    location: Optional["LocationModel"] = Relationship(
        back_populates="parts",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    image_url: Optional[str] = None
    additional_properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )

    categories: List["CategoryModel"] = Relationship(
        back_populates="parts",
        link_model=PartCategoryLink,
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "PartModel":
        """
        Create a PartModel from a JSON dictionary.
        If the JSON includes a list of categories (as dicts), they will be converted
        to CategoryModel instances.
        """
        data_copy = data.copy()
        if "categories" in data_copy and isinstance(data_copy["categories"], list):
            data_copy["categories"] = [
                CategoryModel(**item) if isinstance(item, dict) else item
                for item in data_copy["categories"]
            ]
        return cls(**data_copy)

    @classmethod
    def search_properties(cls, session: Session, search_term: str):
        """Search through additional_properties and description"""
        return session.query(cls).filter(
            or_(
                cls.description.ilike(f'%{search_term}%'),
                cls.additional_properties.cast(String).ilike(f'%{search_term}%')
            )
        ).all()

    def to_dict(self) -> Dict[str, Any]:
        """ Custom serialization method for PartModel """
        base_dict = self.model_dump(exclude={"location"})
        # Always include categories, even if empty
        base_dict["categories"] = [
            {"id": category.id, "name": category.name, "description": category.description}
            for category in self.categories
        ] if self.categories else []
        return base_dict

    @model_validator(mode='before')
    @classmethod
    def check_unique_part_name(cls, values):
        # Remove the circular import and validation since it's handled in the service layer
        return values


# Additional models for operations
class UpdateQuantityRequest(SQLModel):
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer_pn: Optional[str] = None
    new_quantity: int

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode='before')
    @classmethod
    def check_at_least_one_identifier(cls, values):
        part_id = values.get('part_id')
        part_number = values.get('part_number')
        manufacturer_pn = values.get('manufacturer_pn')

        if not part_id and not part_number and not manufacturer_pn:
            raise ValueError("At least one of part_id, part_number, or manufacturer_pn must be provided.")
        return values


class GenericPartQuery(SQLModel):
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer_pn: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode='before')
    @classmethod
    def check_at_least_one_identifier(cls, values):
        part_id = values.get('part_id')
        part_number = values.get('part_number')
        manufacturer_pn = values.get('manufacturer_pn')

        if not part_id and not part_number and not manufacturer_pn:
            raise ValueError("At least one of part_id, part_number, or manufacturer_pn must be provided.")
        return values


class AdvancedPartSearch(SQLModel):
    search_term: Optional[str] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    category_names: Optional[List[str]] = None
    location_id: Optional[str] = None
    supplier: Optional[str] = None
    sort_by: Optional[str] = None  # "part_name", "part_number", "quantity", "location"
    sort_order: Optional[str] = "asc"  # "asc" or "desc"
    page: int = 1
    page_size: int = 10

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v):
        if v and v not in ["part_name", "part_number", "quantity", "location"]:
            raise ValueError("sort_by must be one of: part_name, part_number, quantity, location")
        return v

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        if v and v not in ["asc", "desc"]:
            raise ValueError("sort_order must be one of: asc, desc")
        return v

# Create an engine for SQLite
sqlite_file_name = "makers_matrix.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=False)


# Create tables if they don't exist
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
````

## File: MakerMatrix/models/printer_config_model.py
````python
from typing import Dict, Any

from pydantic import BaseModel


class PrinterConfig(BaseModel):
    backend: str
    driver: str
    printer_identifier: str
    dpi: int
    model: str
    scaling_factor: float = 1.0
    additional_settings: Dict[str, Any] = {}
````

## File: MakerMatrix/models/printer_request_model.py
````python
from pydantic import BaseModel


class PrintRequest(BaseModel):
    image_path: str
    label: str = '29x90'
    rotate: str = '90'
````

## File: MakerMatrix/models/user_models.py
````python
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
````

## File: MakerMatrix/parsers/boltdepot_parser.py
````python
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from MakerMatrix.parsers.parser import Parser
from MakerMatrix.parts.parts import Part


class BoltDepotParser(Parser):

    def submit(self):
        pass

    def __init__(self):
        self._pattern = re.compile(r"http://boltdepot.com/Product-Details.aspx\?product=")
        self.part = Part(categories=['hardware'],
                         part_vendor="bolt depot",
                         part_type="hardware",
                         supplier="bolt depot")
        self.required_inputs = []
        # Required Inputs
        # req_part_name = RequiredInput(field_name="part_name", data_type="string", prompt="Enter the part name")
        # req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")

        # Set the required inputs
        self.add_required_input(field_name="quantity", data_type="int", prompt="Enter the quantity.")

    def matches(self, data):
        decoded_data = self.decode_json_data(data)
        new_part_data = self._pattern.search(decoded_data)
        # if new_part_data:
        #     self.part = Part(categories=['hardware'])
        return new_part_data

    # Specific to bolt depot parsing
    def _extract_properties(self, document):
        for element in document.select('.product-details-table .property-name'):
            key = element.get_text().strip().lower()  # Convert key to lowercase
            value_element = element.find_next_sibling()
            if value_element and value_element.span:
                value = value_element.span.get_text().strip()
                value = value.replace('"', '').lower()  # Remove double quotes and convert value to lowercase

                if key == 'category':
                    self.part.categories.append(value)
                else:
                    self.part.additional_properties[key] = value

    def enrich(self):
        try:
            url = f'https://www.boltdepot.com/Product-Details.aspx?product={self.part.part_number}'
            response = requests.get(url)

            if response.status_code == 200:
                document = BeautifulSoup(response.text, 'html.parser')
                self.part.part_url = url
                table = document.find('table', class_='product-details-table')
                names_values = {}

                # Iterate through rows in the table
                # Inside your loop that iterates through table rows
                for row in table.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) == 2:
                        property_name = cells[0].text.strip()
                        # Check for 'value-message' within the second cell
                        value_message = cells[1].find('div', class_='value-message')
                        if value_message and property_name.lower() != "category":
                            # If 'value-message' exists, use its text
                            property_value = value_message.text.strip()
                        else:
                            # Otherwise, use the text directly from the cell
                            property_value = cells[1].text.strip()
                        names_values[property_name] = property_value

                # Print the extracted names and values
                for name, value in names_values.items():
                    if name.lower() == "category":
                        self.part.categories.append(value.lower())
                    else:
                        self.part.add_additional_property(name, value.replace("\r\n"," "))


                # # Extract the description
                content_main = document.find('div', id='content-main')
                if content_main:
                    description = content_main.find('h1').text
                    self.part.description = description

                if not description:
                    self.add_required_input(field_name="description", data_type="string",
                                                    prompt="Enter the description.")


            else:
                raise Exception('Failed to load product page')

        except Exception as e:
            print(f'Error enriching data: {e}')
            return None

    def parse(self, json_data):
        try:
            decoded_data = self.decode_json_data(json_data)
            uri = urlparse(decoded_data)
            _pn = parse_qs(uri.query)['product'][0]
            self.part.part_number = _pn
            self.set_property("part.manufacturer_part_number", _pn)
            self.set_property("part_vendor", "Bolt Depot")
            self.part.categories.append("hardware")

            return self

        except Exception as e:
            print(f'Error parsing byte data: {e}')
            return None
````

## File: MakerMatrix/parsers/lcsc_parser.py
````python
import re
from MakerMatrix.lib.required_input import RequiredInput
from MakerMatrix.parts.parts import Part
from MakerMatrix.parsers.parser import Parser
from MakerMatrix.api.easyeda import EasyedaApi


def get_nested_value(data, keys, default=""):
    """Safely extract a value from nested dictionaries.

    Args:
        data (dict): The dictionary to extract the value from.
        keys (list): A list of keys representing the path to the desired value.
        default (str, optional): The default value to return if the key is not found. Defaults to "".

    Returns:
        The extracted value or the default value.
    """
    for key in keys:
        data = data.get(key, {})
        if not data:
            return default
    return data if data != default else default


class LcscParser(Parser):

    def __init__(self):
        super().__init__(pattern=re.compile(r"(\w+):([^,']+)"))
        self.api = EasyedaApi()

        self.part = Part(categories=['electronics'],
                         part_vendor="LCSC",
                         part_type="electronic component",
                         supplier="LCSC")

        # Define required inputs, you can remove / set them during enrich stage too.
        # req_part_name = RequiredInput(field_name="part_name", data_type="string", prompt="Enter the part name")
        req_part_type = RequiredInput(field_name="part_type", data_type="string", prompt="Enter the part type.")
        req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")

        self.required_inputs = [req_part_type, req_part_quantity]

    def matches(self, data):
        match_data = self.decode_json_data(data)
        return bool(self.pattern.search(match_data))

    def enrich(self):
        # Specific to LCSC data enrichment
        try:
            lcsc_data = self.api.get_info_from_easyeda_api(
                lcsc_id=self.part.part_number.upper())  # This is cases sensitive on lcsc servers side
            if lcsc_data != {}:
                if lcsc_data['result']['SMT']:
                    # This is a SMT part
                    self.part.add_category("SMT")

                self.set_property('part_name', f" {self.part.manufacturer_part_number}")
                # self.part.additional_properties['datasheet_url'] = \
                #     lcsc_data['result']['packageDetail']['dataStr']['head']['c_para']['link']
                # self.part.additional_properties['url'] = lcsc_data['result']['szlcsc']['url']

                # Using the function to set additional properties
                self.part.additional_properties['value'] = get_nested_value(
                    lcsc_data, ['result', 'dataStr', 'head', 'c_para', 'Value'])

                self.part.additional_properties['package'] = get_nested_value(
                    lcsc_data, ['result', 'dataStr', 'head', 'c_para', 'package'])

                self.part.additional_properties['manufacturer'] = get_nested_value(
                    lcsc_data, ['result', 'dataStr', 'head', 'c_para', 'Manufacturer'])

                self.part.additional_properties['datasheet_url'] = get_nested_value(
                    lcsc_data, ['result', 'packageDetail', 'dataStr', 'head', 'c_para', 'link'])

                self.part.additional_properties['url'] = get_nested_value(
                    lcsc_data, ['result', 'szlcsc', 'url'])

                if get_nested_value(lcsc_data, ['result','dataStr','head','c_para','pre']).startswith('C?'):
                    self.part_type = "capacitor"
                    self.part.additional_properties['value'] = get_nested_value(lcsc_data, ['result','dataStr','head','c_para','Value']).lower()
                    self.part.additional_properties['package'] = get_nested_value(lcsc_data, ['result','dataStr','head','c_para','package'])

                elif get_nested_value(lcsc_data, ['result','dataStr','head','c_para','pre']).startswith('R?'):
                    self.part_type = "resistor"
                    self.part.additional_properties['value'] = get_nested_value(lcsc_data, ['result','dataStr','head','c_para','Value']).lower()
                    self.part.additional_properties['package'] = get_nested_value(lcsc_data, ['result','dataStr','head','c_para','package'])




                # Check if 'datasheet_url' exists in additional_properties and is not empty
                if 'datasheet_url' in self.part.additional_properties and self.part.additional_properties[
                    'datasheet_url']:
                    # Process the datasheet_url and set the 'description' property
                    description = self.part.additional_properties['datasheet_url'].strip(
                        "https://lcsc.com/product-detail").replace("-", ", ").rstrip(".html")
                    self.set_property('description', description)
                else:
                    # Handle the case where 'datasheet_url' is not available or empty
                    # For example, set 'description' to an empty string or a default value
                    self.set_property('description', "")
            else:
                # Looks like this part is not on LCSC perhaps only easyeda
                self.add_required_input(field_name="part_type", data_type="string", prompt="Enter the part type. IE: "
                                                                                           "resistor, capacitor")
                self.add_required_input(field_name="package", data_type="string", prompt="Enter the package type.")
                self.add_required_input(field_name="value", data_type="string", prompt="Enter the component value.")

        except Exception as e:
            print(f'Error enriching data: {e}')
            return None

    def parse(self, json_data):
        try:
            decoded_data = self.decode_json_data(json_data)
            # Parsing logic specific to LCSC data
            key_value_pairs = re.findall(r"(\w+):([^,']+)", decoded_data)
            data = {key: value for key, value in key_value_pairs}

            self.set_property("quantity", int(data.get('qty')))
            self.set_property('part_number', data.get('pc', '').lower())
            self.set_property('manufacturer_part_number', data.get('pm', '').lower())
            # self.part.additional_properties['order_date'] = parse_to_datetime(data.get('on', ''))
            # self.part.order_date = parse_to_datetime(data.get('on', ''))
            #
            #
            # self.part_type = self.set_property('part_type',part_type)

        except Exception as e:
            print(f'Error parsing byte data: {e}')
            return None

    def submit(self):
        # Implementation for data submission specific to LcscParser
        pass
````

## File: MakerMatrix/parsers/mouser_parser.py
````python
import os
import re
from datetime import datetime

from mouser.api import MouserPartSearchRequest

from MakerMatrix.lib.required_input import RequiredInput
from MakerMatrix.parsers.parser import Parser
from MakerMatrix.parts.parts import Part


def get_nested_value(data, keys, default=""):
    """Safely extract a value from nested dictionaries.

    Args:
        data (dict): The dictionary to extract the value from.
        keys (list): A list of keys representing the path to the desired value.
        default (str, optional): The default value to return if the key is not found. Defaults to "".

    Returns:
        The extracted value or the default value.
    """
    for key in keys:
        data = data.get(key, {})
        if not data:
            return default
    return data if data != default else default


def parse_to_datetime(input_string):
    try:
        # Extract the date part (ignoring the first two characters and the last four)
        if input_string:
            date_part = input_string[2:8]
            parsed_date = datetime.strptime(date_part, '%y%m%d')
            # Format the date as a string in the desired format
            return parsed_date.strftime('%Y-%m-%d')  # e.g., "2023-03-15"
        else:
            return None
    except ValueError as ve:
        print(f"Error parsing date: {ve}")
        return None


def _extract_quantity(quantity_string):
    qn = next((x for x in quantity_string if x.startswith("Q")), None)
    return int(qn[1:] if qn is not None else None)


def _extract_part_vendor(part_vendor):
    vendor = next((x for x in part_vendor if x.startswith("1V")), None)
    return vendor[2:] if vendor is not None else None


def _extract_pn(pn_string):
    pn = next((x for x in pn_string if "1P" in x), None)
    result = pn[2:] if pn is not None else None
    return result


class Mouser(Parser):

    def __init__(self):
        self.mouser_version = ""
        self.required_inputs = []
        super().__init__(pattern=[
            {'current': '[)>\x1e06\x1d'},
            {'legacy': '>[)>06\x1d'}
        ])

        self.part = Part(categories=['electronics'],
                         part_vendor="Mouser",
                         part_type="electronic component",
                         supplier="Mouser")

        # Define required inputs, you can remove / set them during enrich stage too.
        # req_part_name = RequiredInput(field_name="part_name", data_type="string", prompt="Enter the part name")
        # req_part_type = RequiredInput(field_name="part_type", data_type="string", prompt="Enter the part type.")
        # req_part_quantity = RequiredInput(field_name="quantity", data_type="int", prompt="Enter the quantity.")

    def _extract_categories(self, category):
        cats = None
        if "-" in category:
            cats = category.split("-")
        elif "/" in category:
            cats = category.split("/")
        else:
            self.part.categories.append(category.lstrip().rstrip().lower())

        if cats is not None:
            for c in cats:
                if c not in self.part.categories:
                    self.part.categories.append(c)

    def submit(self):
        # Implementation for data submission specific to LcscParser
        pass

    def _process_description(self, description_string):
        description = [word.lower() for word in description_string.split()]
        description_string = description_string.lower()

        if "resistor" in description_string or "resistance" in description_string:
            pattern_tolerance = r'(\d+(\.\d+)?%)'
            # resistance_pattern = r'(\d+(?:\.\d+)?[a-zA-Z]?)\sOhms'
            resistance_pattern = r'(\d+(?:\.\d+)?)\s?[Oo]hms?'

            self.part.categories.append('resistors')

            if "ohm" in description_string:
                resistance_match = re.search(resistance_pattern, description_string, re.IGNORECASE)
                if resistance_match:
                    resistance = resistance_match.group(1)
                    self.part.add_additional_property('resistance', resistance + "Ω")

            if "%" in description_string:
                tolerance_match = re.search(pattern_tolerance, description_string)
                self.part.add_additional_property('tolerance', tolerance_match.group(1))

            # Sometimes we can't get the regex to match due to things being different
            # So we need to add the required inputs for missing data.
            if "resistance" not in self.part.additional_properties.keys():
                # Parsing the resistance did not work manually add this
                self.part.part_type = "resistor"

                self.required_inputs.append(
                    RequiredInput(field_name="value", data_type="string", prompt="Enter the resistance value"))

                self.add_required_input(field_name="package", data_type="string", prompt="Enter the package. IE: 0402")

        elif "capacitance" in description_string or "capacitor" in description_string:
            self.part.categories.append('capacitors')
            self.add_required_input(field_name="value", data_type="string", prompt="Enter the capacitance value. IE: "
                                                                                   "22pf")
            self.add_required_input(field_name="package", data_type="string", prompt="Enter the package. IE: 0402")

            if 'SMD' in description_string:
                self.part.add_additional_property('type', 'smd')
                self.part.part_type = "capacitor"
                self.part.categories.append('smd')

        elif " ic " in description_string.lower():
            self.part.part_type = "integrated circuit"
            self.add_optional_input(field_name="ic_type", data_type="string", prompt="Enter the type of IC.")
            self.add_required_input(field_name="package", data_type="string", prompt="Enter the package type.")

    def _parse_legacy(self, qr_data):
        fields = qr_data.split('\x1d')
        self.part.quantity = int(fields[4].lstrip("Q"))
        self.part.part_number = fields[3].lstrip("1P")

    def _parse_current(self, qr_data):
        records = qr_data.split('\x1e')
        fields = records[1].split('\x1d')

        self.part.part_number = _extract_pn(fields)
        self.part.quantity = _extract_quantity(fields)
        self.part.vendor = _extract_part_vendor(fields)

    def enrich(self):
        args = []
        request = MouserPartSearchRequest('partnumber', None, *args)
        search = request.part_search(self.part.part_number)

        if search:
            results = request.get_clean_response()
            self.part.description = results.get('Description')
            self._extract_categories(results.get('Category'))
            self.part.manufacturer = results.get('Manufacturer')
            self.part.add_additional_property("datasheet_url", results.get('DataSheetUrl'))
            self.part.image_url = results.get('ImagePath')
            self.part.manufacturer_part_number = results.get('ManufacturerPartNumber')
            self._process_description(self.part.description)

    def parse(self, data):
        qr_data = self.decode_json_data(data)
        self.part.categories.append("electronics")  # Set default categories
        self.part.categories.append("components")
        match self.mouser_version:
            case 'current':
                self._parse_current(qr_data)
                # self.enrich()

            case 'legacy':
                self._parse_legacy(qr_data)
                # self.enrich()

    def matches(self, data):
        if os.getenv("MOUSER_PART_API_KEY") is not None:
            match_data = self.decode_json_data(data)

        for pat in self.pattern:
            for key, value in pat.items():
                if match_data.startswith(value):
                    self.mouser_version = key
                    return True

        return False
````

## File: MakerMatrix/parsers/parser.py
````python
from abc import ABC, abstractmethod

from MakerMatrix.lib.optional_input import OptionalInput
from MakerMatrix.parts.parts import Part
from MakerMatrix.lib.required_input import RequiredInput
import json

import base64


# Assuming the Part class is defined elsewhere
# from parts.parts import Part

class Parser(ABC):
    def __init__(self, pattern):
        self.optional_inputs = []
        self.pattern = pattern
        self.part = Part
        self.required_inputs = []

    @staticmethod
    def create_question_dict(event, question_type, question_text, positive_text, negative_text):
        data = {
            "event": event,
            "data": {
                "questionType": question_type,
                "questionText": question_text,
                "positiveResponseText": positive_text,
                "negativeResponseText": negative_text
            }
        }
        return data

    # Example usage
    # nfc_question_dict = create_question_dict(
    #     "question",
    #     "regular",
    #     "Do you want to write the part number to an NFC tag?",
    #     "Yes",
    #     "No"
    # )

    def validate(self, json_string):
        try:
            data = json.loads(json_string)

            # Extract required inputs and part number from the JSON data
            required_inputs = data.get('required_inputs', [])
            part_number = data.get('part_number')

            for input in required_inputs:
                field_name = input.get('field_name')
                data_type = input.get('data_type')
                value = input.get('value')

                # Perform type validation
                if data_type == "string":
                    if not isinstance(value, str):
                        return False, f"Invalid type for field {field_name}. Expected string."
                elif data_type == "int":
                    try:
                        int_value = int(value)  # Attempt to convert to int
                        value = int_value  # Update value with converted int
                    except ValueError:
                        return False, f"Invalid type for field {field_name}. Expected integer."

                # Dynamically update the fields on parser.part based on field_name
                setattr(self.part, field_name, value)

            # # Update part number if necessary
            # if part_number:
            #     self.part.part_number = part_number

            return True, "Validation successful and data updated."

        except json.JSONDecodeError as e:
            return False, f"JSON decoding error: {e}"

    def add_required_input(self, field_name, data_type, prompt):
        self.required_inputs.append(RequiredInput(field_name, data_type, prompt))

    def add_optional_input(self, field_name, data_type, prompt):
        self.optional_inputs.append(OptionalInput(field_name, data_type, prompt))

    def remove_required_input(self, field_name):
        for r in self.required_inputs:
            if r.field_name == field_name:
                print(f"Removed requirement: {r}")
                self.required_inputs.remove(r)

    def get_required_inputs_json(self):
        return json.dumps([input_field.to_dict() for input_field in self.required_inputs], indent=4)

    def decode_data(self, json_data):
        _data = json.loads(json_data)
        return _data

    def set_property(self, property_name, value):
        # Initialize a variable to keep track of whether the property was successfully set
        property_set_successfully = False

        # Try to set the property
        try:
            # Check if the property exists in the Part object or in the class itself
            target = self.part if hasattr(self.part, property_name) else self if hasattr(self, property_name) else None

            if target is not None:
                # Set the property
                setattr(target, property_name, value)
                property_set_successfully = True
        except Exception as e:
            # Handle any exceptions that might occur
            print(f"Error setting property: {e}")

        # If the property was not set successfully, set it to an empty string
        if not property_set_successfully:
            if hasattr(self.part, property_name):
                setattr(self.part, property_name, "")
            elif hasattr(self, property_name):
                setattr(self, property_name, "")

        # The rest of your code for handling the required inputs
        if property_set_successfully:
            should_remove_input = False
            if isinstance(value, str) and value.strip():
                should_remove_input = True
            elif value is not None:
                should_remove_input = True
            if should_remove_input:
                self.required_inputs = [req for req in self.required_inputs if req.field_name != property_name]

    def decode_json_data(self, json_data):
        byte_data = self.decode_data(json_data)
        _data = base64.b64decode(byte_data['qrData'])
        decoded_data = _data.decode('utf-8')
        return decoded_data

    def to_dict(self, obj=None):
        """
        Converts the object's attributes to a dictionary, excluding methods,
        and removes leading underscores from attribute names. If no object is
        provided, it converts the attributes of the current instance.
        """
        if obj is None:
            obj = self

        attr_dict = {}
        for attr in dir(obj):
            if not callable(getattr(obj, attr)) and not attr.startswith("_"):
                # Remove leading underscore from attribute names
                key = attr.lstrip('_')
                attr_dict[key] = getattr(obj, attr)
        return attr_dict

    def format_required_data(self, requirements, clientId, part_number):
        obj = self.to_dict(requirements)
        obj['client_id'] = clientId
        obj['required_inputs'] = requirements
        obj['part_number'] = part_number
        return self.to_json(obj)

    def append_event(self, event_type):
        """
        Appends an event type to the object's attributes.
        """
        obj = self.to_dict()
        obj['event'] = event_type
        return self.to_json(obj)

    def to_json(self, obj=None):
        """
        Converts the given object's attributes to a JSON string.
        If no object is provided, converts the current object's attributes.
        """

        def serialize(obj_to_serialize):
            if hasattr(obj_to_serialize, '__dict__'):
                return {k.lstrip('_'): v for k, v in obj_to_serialize.__dict__.items()}
            # elif isinstance(obj_to_serialize, (datetime, date)):
            #     return obj_to_serialize.isoformat()
            return str(obj_to_serialize)  # Fallback to string representation

        # Use the provided object or self if no object is provided
        obj_to_convert = obj if obj is not None else self

        return json.dumps(obj_to_convert, default=serialize)

    @abstractmethod
    def parse(self, fields):
        pass

    @abstractmethod
    def submit(self):
        pass
````

## File: MakerMatrix/printers/abstract_printer.py
````python
import json
from abc import ABC, abstractmethod

from PIL import Image

from MakerMatrix.lib.print_settings import PrintSettings


class AbstractPrinter(ABC):
    """Abstract base class for printers."""

    def __init__(self, dpi: int = 300, scaling_factor: float = 1.0,
                 name: str = "Generic Printer", version: str = "1.0",
                 additional_settings: dict = None):
        self.dpi = dpi
        self.scaling_factor = scaling_factor
        self.name = name
        self.version = version
        self.additional_settings = additional_settings or {}

    @abstractmethod
    def print_text_label(self, label: str, print_config: PrintSettings) -> int:
        pass

    @abstractmethod
    def print_image(self, image: Image, label: str = "") -> None:
        pass

    @abstractmethod
    def configure_printer(self, config: dict) -> None:
        pass

    @abstractmethod
    def get_status(self) -> str:
        pass

    @abstractmethod
    def cancel_print(self) -> None:
        pass

    @abstractmethod
    def check_availability(self) -> bool:
        """Check if the printer is available.

        Returns:
            bool: True if the printer is available, False otherwise.
        """
        pass

    def save_config(self, config_path: str) -> None:
        config = {
            'dpi': self.dpi,
            'scaling_factor': self.scaling_factor,
            'name': self.name,
            'version': self.version,
            'additional_settings': self.additional_settings,
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)

    def load_config(self, config_path: str) -> None:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.additional_settings = config.get("additional_settings", {})
                self.configure_printer(config)
        except Exception as e:
            print(f"Error loading config file: {str(e)}")
````

## File: MakerMatrix/printers/brother_ql.py
````python
import traceback
import socket

from PIL import Image, ImageDraw, ImageFont
from brother_ql.backends.helpers import send
from brother_ql.conversion import convert
from brother_ql.raster import BrotherQLRaster

from MakerMatrix.lib.print_settings import PrintSettings
from MakerMatrix.printers.abstract_printer import AbstractPrinter
from MakerMatrix.services.label_service import LabelService
from PIL import Image


class LabelSizeError(Exception):
    """Raised when image dimensions exceed label capabilities"""

    def __init__(self, width: float, length: float, max_width: float, max_length: float):
        self.message = f"Image size ({width}\"x{length}\") exceeds maximum label size ({max_width}\"x{max_length}\")"
        super().__init__(self.message)


class BrotherQL(AbstractPrinter):
    def __init__(self, model: str = None, backend: str = None, printer_identifier: str = None, dpi: int = 300,
                 scaling_factor: float = 1.0, additional_settings: dict = None):
        super().__init__(dpi=dpi, scaling_factor=scaling_factor, name="BrotherQL")
        self.model = model
        self.backend = backend
        self.printer_identifier = printer_identifier
        self.additional_settings = additional_settings or {}
        self.qlr = BrotherQLRaster(self.model) if model else None

    # def print_label(self, image: Image, pconf: PrintSettings):
    #     print("[DEBUG] Converting image to printer instructions")
    #     instructions = convert(
    #         qlr=self.qlr,
    #         images=[image],
    #         label=str(pconf.label_size),
    #         rotate=pconf.rotation,
    #         threshold=70.0,
    #         dither=False,
    #         compress=False,
    #         red=False,
    #         dpi_600=(self.dpi == 600),
    #         hq=True,
    #         cut=True
    #     )
    #
    #     print("[DEBUG] Sending print job")
    #     result = send(
    #         instructions=instructions,
    #         printer_identifier=self.printer_identifier,
    #         backend_identifier=self.backend,
    #         blocking=True
    #     )
    #
    #     print("[DEBUG] Print job sent successfully")
    #     return result

    def print_text_label(self, text: str, print_settings: PrintSettings) -> bool:
        """
        Print a text-only label. If label_len is not set, auto-calculate the label
        length in mm based on the text width plus margins. Then generate the final
        text image and print it.
        """
        dpi = print_settings.dpi
        available_height_pixels = LabelService.get_available_height_pixels(print_settings)

        # We'll use a 5% margin, just like in generate_combined_label.
        margin_fraction = 0.05
        margin_pixels = int(margin_fraction * available_height_pixels)

        # If label_len is None, compute it based on measured text size.
        if print_settings.label_len is None:
            # 1) Measure text size for the given height.
            text_width_px, _ = LabelService.measure_text_size(
                text=text,
                print_settings=print_settings,
                allowed_height=available_height_pixels
            )
            # 2) Convert text+margin to mm (no QR in text-only labels).
            label_len_mm = LabelService.compute_label_len_mm_for_text_and_qr(
                text_width_px=text_width_px,
                margin_px=margin_pixels,
                dpi=dpi,
                qr_width_px=0
            )
        else:
            label_len_mm = float(print_settings.label_len)

        # Convert mm -> final px, apply a scaling factor (e.g. 1.1 for printer shrinkage).
        total_label_width_px = LabelService.finalize_label_width_px(
            label_len_mm=label_len_mm,
            print_settings=print_settings,
            scaling_factor=1.1
        )

        # Now generate the text label image with the computed width/height.
        text_label_img = LabelService.generate_text_label(
            text=text,
            print_settings=print_settings,
            allowed_width=total_label_width_px,
            allowed_height=available_height_pixels
        )

        # Rotate if needed (90 degrees, etc.).
        rotated_label_img = text_label_img.rotate(90, expand=True)

        # Finally, send to your printer or do whatever "print" means in your app.
        return self._resize_and_print(rotated_label_img, print_settings=print_settings)

    def set_backend(self, backend: str):
        self.backend = backend

    def set_printer_identifier(self, printer_identifier: str):
        self.printer_identifier = printer_identifier

    def set_dpi(self, dpi: int):
        if dpi not in [300, 600]:
            raise ValueError("DPI must be 300 or 600.")
        self.dpi = dpi

    def set_model(self, model: str):
        self.model = model
        self.qlr = BrotherQLRaster(self.model)

    def _resize_and_print(self, image: Image.Image, label: str = '12', rotate: str = '0',
                          max_length_inches: float = None, print_settings: PrintSettings = None):
        """Convert the provided image to printer instructions and send it."""
        try:
            print(f"[DEBUG] Starting _resize_and_print() with label: {label}, rotate: {rotate}")
            self.qlr.data = b''
            print("[DEBUG] Converting image to printer instructions")
            instructions = convert(
                qlr=self.qlr,
                images=[image],
                label=label,
                rotate=rotate,
                threshold=70.0,
                dither=False,
                compress=False,
                red=False,
                dpi_600=(self.dpi == 600),
                hq=True,
                cut=True
            )
            print("[DEBUG] Sending print job")
            if print_settings and print_settings.copies > 1:
                result = True
                for i in range(0, print_settings.copies):
                    if result is False:
                        break  # Previous send had an issue
                    result = send(
                        instructions=instructions,
                        printer_identifier=self.printer_identifier,
                        backend_identifier=self.backend,
                        blocking=True
                    )
            else:
                result = send(
                    instructions=instructions,
                    printer_identifier=self.printer_identifier,
                    backend_identifier=self.backend,
                    blocking=True
                )
                print("[DEBUG] Print job sent successfully")

            return result
        except Exception as e:
            print(f"[ERROR] Exception in _resize_and_print: {e}")
            import traceback
            print(traceback.format_exc())
            return False

    def check_availability(self) -> bool:
        """
        Check if the printer is available.

        For network printers (backend=="network"), this attempts to connect
        to the printer's IP (extracted from self.printer_identifier) on port 9100.

        For USB printers (backend=="usb"), this implementation simply returns True,
        but you could extend it with platform-specific checks.
        """
        try:
            if self.backend == "network":
                # Assuming printer_identifier is in the format "tcp://192.168.1.71"
                host = self.printer_identifier.replace("tcp://", "").split(":")[0]
                port = 9100  # default port for many network printers
                # Attempt a connection with a short timeout
                sock = socket.create_connection((host, port), timeout=5)
                sock.close()
                return True
            elif self.backend == "usb":
                # TODO: Implement USB availability check if needed.
                return True
            else:
                return False
        except Exception as e:
            print(f"Availability check failed: {e}")
            return False

    def print_image(self, image: Image, label: str = "") -> None:
        self._resize_and_print(image, label)

    def configure_printer(self, config: dict) -> None:
        self.model = config.get('model', self.model)
        self.backend = config.get('backend', self.backend)
        self.printer_identifier = config.get('printer_identifier', self.printer_identifier)
        self.dpi = config.get('dpi', self.dpi)
        self.scaling_factor = config.get('scaling_factor', self.scaling_factor)
        if self.model:
            self.qlr = BrotherQLRaster(self.model)

    def get_status(self) -> str:
        return "Ready"

    def cancel_print(self) -> None:
        print("Print job cancelled")

    def print_qr_and_text(self, text: str, part, print_settings):
        try:
            # Generate the combined label image using LabelService.
            combined_img = LabelService.generate_combined_label(part, print_settings, custom_text=text)
            # For debugging, you can save the image.
            combined_img.save("test_label.png")

            # Apply the printer's scaling factor (from printer_config, i.e. self.scaling_factor)
            if self.scaling_factor != 1.0:
                scaled_width = int(combined_img.width * self.scaling_factor)
                scaled_height = int(combined_img.height * self.scaling_factor)
                combined_img = combined_img.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
                combined_img.save("scaled_label.png")

            # Now send the image to print (using print_settings.label_size for the label parameter).
            return self._resize_and_print(combined_img, label=str(print_settings.label_size), print_settings=print_settings)
        except Exception as e:
            print(f"[ERROR] Exception in print_qr_and_text: {e}")
            import traceback
            print(traceback.format_exc())
            return False
````

## File: MakerMatrix/repositories/base_repository.py
````python
from sqlmodel import SQLModel, Session, select
from typing import TypeVar, Generic, Type, Optional, List

T = TypeVar('T', bound=SQLModel)

class BaseRepository(Generic[T]):
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class

    def get_by_id(self, session: Session, id: str) -> Optional[T]:
        return session.exec(select(self.model_class).where(self.model_class.id == id)).first()

    def get_all(self, session: Session) -> List[T]:
        return session.exec(select(self.model_class)).all()

    def create(self, session: Session, model: T) -> T:
        session.add(model)
        session.commit()
        session.refresh(model)
        return model

    def update(self, session: Session, model: T) -> T:
        session.add(model)
        session.commit()
        session.refresh(model)
        return model

    def delete(self, session: Session, id: str) -> bool:
        model = self.get_by_id(session, id)
        if model:
            session.delete(model)
            session.commit()
            return True
        return False
````

## File: MakerMatrix/repositories/category_repositories.py
````python
from typing import Any, Dict, Optional, List, Type
from sqlalchemy import delete
from sqlmodel import Session, select

from MakerMatrix.database.db import get_session
from MakerMatrix.models.models import CategoryModel
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError


class CategoryRepository:
    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_category(session: Session, category_id: Optional[str] = None, name: Optional[str] = None) -> Optional[CategoryModel]:
        """
        Get a category by ID or name.
        
        Args:
            session: The database session
            category_id: Optional ID of the category to retrieve
            name: Optional name of the category to retrieve
            
        Returns:
            Optional[CategoryModel]: The category if found, None otherwise
        """
        try:
            if category_id:
                category_identifier = "category ID"
                category = session.exec(
                    select(CategoryModel).where(CategoryModel.id == category_id)
                ).first()
            elif name:
                category_identifier = "category name"
                category = session.exec(
                    select(CategoryModel).where(CategoryModel.name == name)
                ).first()
            else:
                raise ValueError("Either 'category_id' or 'name' must be provided")
                
            return category
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise ValueError(f"Failed to retrieve category: {str(e)}")

    @staticmethod
    def create_category(session: Session, new_category: Dict[str, Any]) -> CategoryModel:
        """
        Create a new category.
        
        Args:
            session: The database session
            new_category: The category data to create
            
        Returns:
            CategoryModel: The created category
        """
        try:
            cmodel = CategoryModel(**new_category)
            session.add(cmodel)
            session.commit()
            session.refresh(cmodel)
            return cmodel
        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to create category: {str(e)}")

    @staticmethod
    def remove_category(session: Session, rm_category: CategoryModel) -> CategoryModel:
        """
        Remove a category and its associations.
        
        Args:
            session: The database session
            rm_category: The category to remove
            
        Returns:
            CategoryModel: The removed category
        """
        # Remove associations between parts and the category
        from MakerMatrix.models.models import PartModel

        parts = session.exec(
            select(PartModel).where(PartModel.categories.any(id=rm_category.id))
        ).all()
        for part in parts:
            part.categories = [category for category in part.categories if category.id != rm_category.id]
            session.add(part)

        session.commit()

        # Delete the category
        session.delete(rm_category)
        session.commit()
        return rm_category

    @staticmethod
    def delete_all_categories(session: Session) -> dict:
        """
        Delete all categories from the system.
        
        Args:
            session: The database session
            
        Returns:
            dict: A dictionary containing the status, message, and deletion count
        """
        try:
            # Count the number of categories before deleting
            categories = session.exec(select(CategoryModel)).all()
            count = len(categories)

            # Delete all categories using SQLModel syntax
            session.exec(delete(CategoryModel))
            session.commit()

            return {
                "status": "success",
                "message": f"All {count} categories removed successfully",
                "data": {"deleted_count": count}
            }

        except Exception as e:
            raise ValueError(f"Error deleting categories: {str(e)}")

    @staticmethod
    def get_all_categories(session: Session) -> dict:
        """
        Get all categories from the system.
        
        Args:
            session: The database session
            
        Returns:
            dict: A dictionary containing the status, message, and all categories
        """
        try:
            categories = session.exec(select(CategoryModel)).all()
            return {
                "status": "success",
                "message": "All categories retrieved successfully",
                "data": categories
            }
        except Exception as e:
            raise ValueError(f"Error retrieving categories: {str(e)}")

    @staticmethod
    def update_category(session: Session, category_id: str, category_data: Dict[str, Any]) -> CategoryModel:
        """
        Update a category's fields.
        
        Args:
            session: The database session
            category_id: The ID of the category to update
            category_data: The fields to update
            
        Returns:
            CategoryModel: The updated category
        """
        category = session.get(CategoryModel, category_id)
        if not category:
            raise ResourceNotFoundError(
                status="error",
                message=f"Category with ID {category_id} not found",
                data=None
            )

        # Update fields that are not None
        for key, value in category_data.model_dump().items():
            if value is not None:
                setattr(category, key, value)

        session.add(category)
        session.commit()
        session.refresh(category)
        return category
````

## File: MakerMatrix/repositories/custom_exceptions.py
````python
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
````

## File: MakerMatrix/repositories/location_repositories.py
````python
from typing import Optional, List, Dict, Any, Sequence
from sqlalchemy import delete, func
from sqlmodel import Session, select
from MakerMatrix.models.models import LocationModel, LocationQueryModel, PartModel
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from sqlalchemy.orm import joinedload, selectinload


class LocationRepository:
    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_all_locations(session: Session) -> Sequence[LocationModel]:
        return session.exec(select(LocationModel)).all()

    @staticmethod
    def delete_location(session: Session, location: LocationModel):
        session.delete(location)
        session.commit()
        return True

    @staticmethod
    def get_location_hierarchy(session: Session, location_id: str) -> Dict[str, Any]:
        """Get a location and its complete hierarchy of descendants"""
        location = session.exec(
            select(LocationModel)
            .options(selectinload(LocationModel.children))
            .where(LocationModel.id == location_id)
        ).first()

        if not location:
            raise ResourceNotFoundError(resource="Location", resource_id=location_id)

        affected_ids = []

        def build_hierarchy(loc: LocationModel) -> Dict[str, Any]:
            affected_ids.append(loc.id)
            children = session.exec(
                select(LocationModel)
                .options(selectinload(LocationModel.children))
                .where(LocationModel.parent_id == loc.id)
            ).all()

            hierarchy = {
                "id": loc.id,
                "name": loc.name,
                "description": loc.description,
                "children": [build_hierarchy(child) for child in children]
            }
            return hierarchy

        hierarchy = build_hierarchy(location)
        return {
            "hierarchy": hierarchy,
            "affected_location_ids": affected_ids
        }

    @staticmethod
    def get_affected_part_ids(session: Session, location_ids: List[str]) -> List[str]:
        """Get IDs of all parts associated with a list of location IDs"""
        parts = session.exec(
            select(PartModel.id).where(PartModel.location_id.in_(location_ids))
        ).all()

        return parts

    @staticmethod
    def get_location(session: Session, location_query: LocationQueryModel) -> Optional[LocationModel]:
        if location_query.id:
            location = session.exec(select(LocationModel).where(LocationModel.id == location_query.id)).first()
        elif location_query.name:
            location = session.exec(select(LocationModel).where(LocationModel.name == location_query.name)).first()
        else:
            raise ValueError("Either 'id' or 'name' must be provided")
        if location:
            return location
        else:
            location_id_or_name = location_query.id if location_query.id is not None else location_query.name

            raise ResourceNotFoundError(
                status="error",
                message=f"Location {location_id_or_name} not found",
                data=None)

    @staticmethod
    def add_location(session: Session, location_data: Dict[str, Any]) -> LocationModel:
        new_location = LocationModel(**location_data)
        session.add(new_location)
        session.commit()
        session.refresh(new_location)
        return new_location

    @staticmethod
    def get_location_details(session: Session, location_id: str) -> dict:
        """
        Get detailed information about a location, including its children.

        Args:
            session: The database session
            location_id: The ID of the location to get details for

        Returns:
            dict: A dictionary containing the location details and its children in the standard response format
        """
        try:
            location = session.exec(
                select(LocationModel)
                .options(joinedload(LocationModel.children))
                .where(LocationModel.id == location_id)
            ).first()
            
            if not location:
                raise ResourceNotFoundError(resource="Location", resource_id=location_id)

            # Convert location to dictionary and include children
            location_data = location.to_dict()
            location_data["children"] = [child.to_dict() for child in location.children]

            return {
                "status": "success",
                "message": "Location details retrieved successfully",
                "data": location_data
            }

        except ResourceNotFoundError as e:
            return {
                "status": "error",
                "message": str(e),
                "data": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error retrieving location details: {str(e)}",
                "data": None
            }

    @staticmethod
    def get_location_path(session: Session, location_id: str) -> Dict[str, Any]:
        """Get the full path from a location to its root, including all parent locations.
        
        Args:
            session: The database session
            location_id: The ID of the location to get the path for
            
        Returns:
            A dictionary containing the location path with parent references
            
        Raises:
            ResourceNotFoundError: If the location is not found
        """
        location = session.get(LocationModel, location_id)
        if not location:
            raise ResourceNotFoundError(f"Location {location_id} not found")
        
        # Build the path from the target location up to the root
        path = []
        current = location
        
        while current:
            path.append({
                "id": current.id,
                "name": current.name,
                "description": current.description,
                "location_type": current.location_type
            })
            if current.parent_id:
                current = session.get(LocationModel, current.parent_id)
            else:
                current = None
        
        # Convert the list into a nested dictionary structure
        if not path:
            return {}
            
        result = path[0].copy()
        current = result
        
        for i in range(1, len(path)):
            current["parent"] = path[i].copy()
            current = current["parent"]
        
        return result
    
    @staticmethod
    def delete_all_locations(session: Session) -> dict:
        try:
            locations = session.exec(select(LocationModel)).all()
            count = len(locations)
            session.exec(delete(LocationModel))
            session.commit()
            return {"status": "success", "message": f"All {count} locations removed successfully", "data": None}
        except Exception as e:
            return {"status": "error", "message": f"Error deleting locations: {str(e)}", "data": None}
        
    @staticmethod
    def update_location(session: Session, location_id: str, location_data: Dict[str, Any]) -> LocationModel:
        """
        Update a location's fields. This method can update any combination of name, description, parent_id, and location_type.
        
        Args:
            session: The database session
            location_id: The ID of the location to update
            location_data: Dictionary containing the fields to update
            
        Returns:
            LocationModel: The updated location model
            
        Raises:
            ResourceNotFoundError: If the location or parent location is not found
        """
        location = session.get(LocationModel, location_id)
        if not location:
            raise ResourceNotFoundError(
                status="error",
                message="Location not found",
                data=None
            )
        
        # If parent_id is being updated, verify the new parent exists
        if "parent_id" in location_data and location_data["parent_id"]:
            parent = session.get(LocationModel, location_data["parent_id"])
            if not parent:
                raise ResourceNotFoundError(
                    status="error",
                    message="Parent Location not found",
                    data=None
                )
        
        # Update only the provided fields
        for key, value in location_data.items():
            setattr(location, key, value)
        
        session.add(location)
        session.commit()
        session.refresh(location)
        return location

    @staticmethod
    def cleanup_locations(session: Session) -> dict:
        """
        Clean up locations by removing those with invalid parent IDs and their descendants.
        
        Args:
            session: The database session
            
        Returns:
            dict: A dictionary containing the cleanup results in the standard response format
        """
        try:
            # Get all locations
            all_locations = session.exec(select(LocationModel)).all()
            
            # Create a set of all valid location IDs
            valid_ids = {loc.id for loc in all_locations}
            
            # Identify invalid locations (those with parent_id not in valid_ids)
            invalid_locations = [
                loc for loc in all_locations
                if loc.parent_id and loc.parent_id not in valid_ids
            ]
            
            # Delete invalid locations and their descendants
            deleted_count = 0
            for loc in invalid_locations:
                # Get the hierarchy to delete
                hierarchy = LocationRepository.get_location_hierarchy(session, loc.id)
                affected_ids = hierarchy["affected_location_ids"]
                
                # Delete all affected locations
                for loc_id in affected_ids:
                    location = session.get(LocationModel, loc_id)
                    if location:
                        session.delete(location)
                        deleted_count += 1
            
            session.commit()
            
            return {
                "status": "success",
                "message": f"Cleanup completed. Removed {deleted_count} invalid locations.",
                "data": {"deleted_count": deleted_count}
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during location cleanup: {str(e)}",
                "data": None
            }

    @staticmethod
    def preview_delete(session: Session, location_id: str) -> dict:
        """
        Preview what will be affected when deleting a location.
        
        Args:
            session: The database session
            location_id: The ID of the location to preview deletion for
            
        Returns:
            dict: A dictionary containing the preview information in the standard response format
        """
        try:
            # Get all affected locations (including children)
            hierarchy = LocationRepository.get_location_hierarchy(session, location_id)
            affected_location_ids = hierarchy["affected_location_ids"]
            
            # Get all affected parts
            affected_parts = LocationRepository.get_affected_part_ids(session, affected_location_ids)
            
            return {
                "status": "success",
                "message": "Delete preview generated successfully",
                "data": {
                    "affected_parts_count": len(affected_parts),
                    "affected_locations_count": len(affected_location_ids),
                    "location_hierarchy": hierarchy["hierarchy"]
                }
            }
            
        except ResourceNotFoundError as e:
            return {
                "status": "error",
                "message": str(e),
                "data": None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generating delete preview: {str(e)}",
                "data": None
            }
````

## File: MakerMatrix/repositories/parts_repositories.py
````python
from typing import Optional, List, Dict, Any

from sqlalchemy import func, or_, delete
from sqlalchemy.orm import joinedload
from sqlmodel import Session, select
# from MakerMatrix.models.category_model import CategoryModel
# from MakerMatrix.models.part_model import PartModel
# from MakerMatrix.repositories.base_repository import BaseRepository

from MakerMatrix.models.models import PartModel, CategoryModel, AdvancedPartSearch
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError


# noinspection PyTypeChecker
def handle_categories(session: Session, category_names: List[str]) -> List[CategoryModel]:
    categories = []
    for name in category_names:
        category = session.exec(select(CategoryModel).where(CategoryModel.name == name)).first()
        if not category:
            category = CategoryModel(name=name)
            session.add(category)
            session.commit()
            session.refresh(category)
        categories.append(category)
    return categories


# noinspection PyTypeChecker
class PartRepository:

    def __init__(self, engine):
        self.engine = engine

    @staticmethod
    def get_parts_by_location_id(session: Session, location_id: str, recursive: bool = False) -> List[Dict]:
        """
        Retrieve parts associated with the given location ID.

        If recursive is True, it will also fetch parts associated with child locations.
        """
        # Fetch parts directly associated with the given location
        parts = session.exec(
            select(PartModel)
            .options(joinedload(PartModel.location))
            .where(PartModel.location_id == location_id)
        ).all()

        if recursive:
            # If recursive, find parts associated with all child locations
            child_location_ids = PartRepository.get_child_location_ids(session, location_id)
            for child_id in child_location_ids:
                parts.extend(PartRepository.get_parts_by_location_id(session, child_id, recursive=True))

        return parts

    @staticmethod
    def dynamic_search(session: Session, search_term: str) -> List[PartModel]:
        """
        Search for parts by name, part_number, or any other fields you choose.
        Returns a list of PartModels or raises an error if none found.
        """
        results = session.exec(
            select(PartModel).where(
                or_(
                    PartModel.part_name.ilike(f"%{search_term}%"),
                    PartModel.part_number.ilike(f"%{search_term}%")
                )
            )
        ).all()

        if results:
            return results
        else:
            raise ResourceNotFoundError(
                status="error",
                message=f"No parts found for search term '{search_term}'",
                data=None
            )

    ###

    @staticmethod
    def delete_part(session: Session, part_id: str) -> Optional[PartModel]:
        """
        Delete a part by ID. Raises ResourceNotFoundError if the part doesn't exist.
        Returns a dictionary summarizing the deletion.
        """
        try:
            part = PartRepository.get_part_by_id(session, part_id)
            session.delete(part)
            session.commit()
            return part
        except Exception as e:
            raise ResourceNotFoundError(
                status="error",
                message=f"Part with ID {part_id} not found",
                data=None
            )

    @staticmethod
    def get_child_location_ids(session: Session, location_id: str) -> List[str]:
        """
        Get a list of child location IDs for the given location ID.
        """
        from MakerMatrix.models.models import LocationModel
        child_locations = session.exec(
            select(LocationModel).where(LocationModel.parent_id == location_id)
        ).all()
        return [location.id for location in child_locations]

    @staticmethod
    def get_part_by_part_number(session: Session, part_number: str) -> Optional[PartModel]:
        part = session.exec(
            select(PartModel)
            .options(
                joinedload(PartModel.categories),
                joinedload(PartModel.location)
            )
            .where(PartModel.part_number == part_number)
        ).first()
        if part:
            return part
        else:
            raise ResourceNotFoundError(
                status="error",
                message=f"Error: Part with part number {part_number} not found",
                data=None)

    @staticmethod
    def get_part_by_id(session: Session, part_id: str) -> Optional[PartModel]:
        part = session.exec(
            select(PartModel)
            .options(
                joinedload(PartModel.categories),
                joinedload(PartModel.location)
            )
            .where(PartModel.id == part_id)
        ).first()

        if part:
            return part
        else:
            raise ResourceNotFoundError(
                status="error",
                message=f"Part with ID {part_id} not found",
                data=None
            )

    @staticmethod
    def get_part_by_name(session: Session, part_name: str) -> Optional[PartModel]:
        part = session.exec(
            select(PartModel)
            .options(
                joinedload(PartModel.categories),
                joinedload(PartModel.location)
            )
            .where(PartModel.part_name == part_name)
        ).first()

        if part:
            return part
        else:
            return None  # We return none and do not raise an error because we want to create a new part

    @staticmethod
    def get_all_parts(session: Session, page: int = 1, page_size: int = 10) -> List[PartModel]:
        offset = (page - 1) * page_size
        results = session.exec(
            select(PartModel)
            .options(
                joinedload(PartModel.categories),
                joinedload(PartModel.location)
            )
            .offset(offset)
            .limit(page_size)
        )
        return results.unique().all()

    @staticmethod
    def get_part_counts(session: Session) -> int:
        return session.exec(select(func.count()).select_from(PartModel)).one()

    @staticmethod
    def add_part(session: Session, part_data: PartModel) -> PartModel:
        """
        Add a new part to the database. Categories are expected to be already created
        and associated with the part.
        
        Args:
            session: The database session
            part_data: The PartModel instance to add with categories already set
            
        Returns:
            PartModel: The created part with all relationships loaded
        """
        try:
            # Add the part to the session
            session.add(part_data)
            
            # Commit the transaction
            session.commit()
            
            # Refresh the part with relationships loaded
            session.refresh(part_data, ['categories', 'location'])
            
            return part_data
            
        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to add part: {str(e)}")

    def is_part_name_unique(self, name: str, exclude_id: Optional[str] = None) -> bool:
        with Session(self.engine) as session:
            # Create a base query to find parts with the same name
            query = select(PartModel).where(PartModel.part_name == name)

            # If exclude_id is provided, add condition to exclude that ID from the query
            if exclude_id:
                query = query.where(PartModel.id != exclude_id)

            # Execute the query
            result = session.exec(query).first()

            # Return True if no other parts with the same name exist, otherwise False
            return result is None

    @staticmethod
    def update_part(session: Session, part: PartModel) -> PartModel | dict[str, str]:
        try:
            session.add(part)
            session.commit()
            session.refresh(part)
            return part

        except ResourceNotFoundError as rnfe:
            raise rnfe

        except Exception as e:
            session.rollback()
            return {
                "status": "error",
                "message": f"Failed to update part with id '{part.id}': {str(e)}"
            }

    @staticmethod
    def advanced_search(session: Session, search_params: AdvancedPartSearch) -> tuple[List[PartModel], int]:
        """
        Perform an advanced search on parts with multiple filters and sorting options.
        Returns a tuple of (results, total_count).
        """
        # Start with a base query
        query = select(PartModel).options(
            joinedload(PartModel.categories),
            joinedload(PartModel.location)
        )

        # Start with a base count query
        count_query = select(func.count(PartModel.id.distinct())).select_from(PartModel)

        # Apply search term filter
        if search_params.search_term:
            search_term = f"%{search_params.search_term}%"
            search_filter = or_(
                PartModel.part_name.ilike(search_term),
                PartModel.part_number.ilike(search_term),
                PartModel.description.ilike(search_term)
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Apply quantity range filter
        if search_params.min_quantity is not None:
            query = query.where(PartModel.quantity >= search_params.min_quantity)
            count_query = count_query.where(PartModel.quantity >= search_params.min_quantity)
        if search_params.max_quantity is not None:
            query = query.where(PartModel.quantity <= search_params.max_quantity)
            count_query = count_query.where(PartModel.quantity <= search_params.max_quantity)

        # Apply category filter
        if search_params.category_names:
            category_ids = [
                category.id for category in handle_categories(session, search_params.category_names)
            ]
            query = query.join(PartModel.categories).where(CategoryModel.id.in_(category_ids))
            count_query = count_query.join(PartModel.categories).where(CategoryModel.id.in_(category_ids))

        # Apply location filter
        if search_params.location_id:
            query = query.where(PartModel.location_id == search_params.location_id)
            count_query = count_query.where(PartModel.location_id == search_params.location_id)

        # Apply supplier filter
        if search_params.supplier:
            query = query.where(PartModel.supplier == search_params.supplier)
            count_query = count_query.where(PartModel.supplier == search_params.supplier)

        # Apply sorting
        if search_params.sort_by:
            sort_column = getattr(PartModel, search_params.sort_by)
            if search_params.sort_order == "desc":
                sort_column = sort_column.desc()
            query = query.order_by(sort_column)

        # Apply pagination
        offset = (search_params.page - 1) * search_params.page_size
        query = query.offset(offset).limit(search_params.page_size)

        # Execute the queries
        results = session.exec(query).unique().all()
        total_count = session.exec(count_query).one()

        return results, total_count

    # def add_part(self, part_data: dict, overwrite: bool) -> dict:
    #     # Check if a part with the same part_number or part_name already exists
    #     part_id = part_data.get('part_id')
    #     existing_part = self.get_part_by_id(part_id)
    #
    #     if existing_part and not overwrite:
    #         return {
    #             "status": "part exists",
    #             "message": f"Part id {part_id} already exists. Overwrite is set to False.",
    #             "data": None
    #         }
    #
    #     # Remove the existing part if overwrite is allowed
    #     if existing_part:
    #         self.table.remove(doc_ids=[existing_part.doc_id])
    #
    #     # Process categories if they are present
    #     if 'categories' in part_data and part_data['categories']:
    #         processed_categories = []
    #         for category in part_data['categories']:
    #             if isinstance(category, str):
    #                 # Convert a string category into a CategoryModel
    #                 category_obj = CategoryModel(name=category)
    #             elif isinstance(category, dict):
    #                 # Create a CategoryModel from the provided dict
    #                 category_obj = CategoryModel(**category)
    #             else:
    #                 continue
    #
    #             # Add the category to the list
    #             processed_categories.append(category_obj.dict())
    #
    #         part_data['categories'] = processed_categories
    #
    #     # Process additional_properties if present
    #     if 'additional_properties' in part_data and part_data['additional_properties']:
    #         processed_properties = {}
    #         for key, value in part_data['additional_properties'].items():
    #             # Convert the keys and values to strings for consistency
    #             processed_properties[key] = str(value)
    #
    #         part_data['additional_properties'] = processed_properties
    #
    #     # Insert or update the part record
    #     document_id = self.table.insert(part_data)
    #
    #     return {
    #         "status": "success",
    #         "message": "Part added successfully",
    #         "data": part_data,
    #         "document_id": document_id
    #     }

    # def delete_part(self, part_id: str) -> bool:
    #     part = self.table.get(self.query().part_id == part_id)
    #     if part:
    #         self.table.remove(self.query().part_id == part_id)
    #         return True
    #     return False
    #
    # def dynamic_search(self, term: str) -> List[dict]:
    #     # Search the database for all parts first
    #     all_parts = self.table.all()
    #
    #     # Filter parts based on whether they match the search term
    #     def matches(part):
    #         matched_fields = []
    #         # Check all top-level fields
    #         top_level_fields = ['part_name', 'part_number', 'description', 'supplier']
    #         for field in top_level_fields:
    #             if term.lower() in str(part.get(field, '')).lower():
    #                 matched_fields.append({"field": field})
    #
    #         # Check additional_properties
    #         additional_props = part.get('additional_properties', {})
    #         for key, value in additional_props.items():
    #             if term.lower() in str(key).lower() or term.lower() in str(value).lower():
    #                 matched_fields.append({"field": "additional_properties", "key": key})
    #
    #         return matched_fields if matched_fields else None
    #
    #     # Filter parts that match the term and include matched fields
    #     results = []
    #     for part in all_parts:
    #         matched_fields = matches(part)
    #         if matched_fields:
    #             results.append({"part": part, "matched_fields": matched_fields})
    #
    #     return results
    #
    # def update_quantity(self, part_id: str, new_quantity: int) -> bool:
    #     """
    #     Update the quantity of a part based on part_id, part_number, or manufacturer_pn.
    #     Raises an exception if no part is found or if no identifier is provided.
    #     """
    #     # Update the quantity if the part is found
    #     self.table.update({'quantity': new_quantity}, self.query().part_id == part_id)
    #

    #
    # def decrement_count_repo(self, part_id: str) -> PartModel | None:
    #     query = self.query()
    #     try:
    #         part = self.table.get(query.part_id == part_id)
    #         if part:
    #             new_quantity = part['quantity'] - 1
    #             self.table.update({'quantity': new_quantity}, query.part_id == part_id)
    #
    #             # Fetch the updated part from the database to return the updated quantity
    #             updated_part = self.table.get(query.part_id == part_id)
    #             return updated_part
    #         else:
    #             return None
    #     except Exception as e:
    #         return None
    #
    # def get_all_parts(self) -> List[PartModel]:
    #     return self.table.all()
    #
    # def get_paginated_parts(self, page: int, page_size: int) -> List[PartModel]:
    #     offset = (page - 1) * page_size
    #     return self.table.all()[offset:offset + page_size]
    #
    # def get_total_parts_count(self) -> int:
    #     return len(self.table)
    #

    #
    # def get_child_location_ids(self, parent_id: str) -> List[str]:
    #     """
    #     Recursively retrieve all child location IDs for a given parent location.
    #     """
    #     from MakerMatrix.repositories.location_repositories import LocationRepository
    #     location_repo = LocationRepository()
    #     child_locations = location_repo.get_child_locations(parent_id)
    #
    #     # Extract IDs and recursively find all nested children
    #     child_ids = [loc['id'] for loc in child_locations]
    #     for loc in child_locations:
    #         child_ids.extend(self.get_child_location_ids(loc['id']))
    #
    #     return child_ids
````

## File: MakerMatrix/repositories/printer_repository.py
````python
import importlib
import json
from typing import Optional, Dict, Any

from MakerMatrix.models.printer_config_model import PrinterConfig

# Map config driver names to the actual class names.
DRIVER_CLASS_MAP = {
    "brother_ql": "BrotherQL"
}


class PrinterRepository:
    """
    Loads the printer configuration from a JSON file or in-memory configuration,
    dynamically imports the correct driver, and instantiates the printer driver.
    """

    def __init__(self, config_path: Optional[str] = None, config_data: Optional[Dict[str, Any]] = None):
        self.config_path = config_path
        self._printer = None
        self._printer_config: Optional[PrinterConfig] = None
        self._driver_cls = None

        if config_data:
            self._load_config_data(config_data)
        elif config_path:
            self.load_config()
        else:
            raise ValueError("Either config_path or config_data must be provided")

        self._import_driver()

    def _load_config_data(self, config_data: Dict[str, Any]) -> None:
        """Load configuration from a dictionary instead of a file."""
        self._printer_config = PrinterConfig(
            backend=config_data["backend"],
            driver=config_data["driver"],
            printer_identifier=config_data["printer_identifier"],
            dpi=config_data["dpi"],
            model=config_data["model"],
            scaling_factor=config_data.get("scaling_factor", 1.0),
            additional_settings=config_data.get("additional_settings", {})
        )
        # Reset any existing printer/driver so that changes take effect.
        self._printer = None
        self._driver_cls = None

    def load_config(self) -> None:
        """Load configuration from a JSON file."""
        if not self.config_path:
            raise ValueError("No config path provided")
            
        with open(self.config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            
        self._load_config_data(config_data)

    def _import_driver(self) -> None:
        if not self._printer_config:
            raise ValueError("Printer configuration is missing.")

        module_name = "MakerMatrix.printers." + self._printer_config.driver
        try:
            driver_module = importlib.import_module(module_name)
        except ImportError as e:
            raise ValueError(f"Could not import printer driver for '{module_name}'") from e

        driver_class_name = DRIVER_CLASS_MAP.get(self._printer_config.driver)
        if not driver_class_name:
            # Fallback: convert snake_case to CamelCase.
            driver_class_name = ''.join(word.capitalize() for word in self._printer_config.driver.split('_'))

        self._driver_cls = getattr(driver_module, driver_class_name, None)
        if not self._driver_cls:
            raise ValueError(f"No valid class '{driver_class_name}' found in {module_name}")

    def get_printer(self):
        if not self._printer:
            if not self._printer_config:
                raise ValueError("Printer configuration is missing.")
            if not self._driver_cls:
                self._import_driver()
            # Instantiate the driver by passing configuration parameters including additional_settings.
            self._printer = self._driver_cls(
                model=self._printer_config.model,
                backend=self._printer_config.backend,
                printer_identifier=self._printer_config.printer_identifier,
                dpi=self._printer_config.dpi,
                scaling_factor=self._printer_config.scaling_factor,
                additional_settings=self._printer_config.additional_settings
            )
        return self._printer

    def configure_printer(self, config: PrinterConfig, save: bool = True) -> None:
        self._printer_config = config
        self._printer = None
        self._driver_cls = None
        if save and self.config_path:
            self.save_config()

    def save_config(self) -> None:
        if not self._printer_config:
            raise ValueError("Printer config is not set.")
        if not self.config_path:
            raise ValueError("No config path provided")
            
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({
                "backend": self._printer_config.backend,
                "driver": self._printer_config.driver,
                "printer_identifier": self._printer_config.printer_identifier,
                "dpi": self._printer_config.dpi,
                "model": self._printer_config.model,
                "scaling_factor": self._printer_config.scaling_factor,
                "additional_settings": self._printer_config.additional_settings
            },
                f,
                indent=4
            )

    def get_configuration(self) -> dict:
        if not self._printer_config:
            return {}
        return {
            "backend": self._printer_config.backend,
            "driver": self._printer_config.driver,
            "printer_identifier": self._printer_config.printer_identifier,
            "dpi": self._printer_config.dpi,
            "model": self._printer_config.model,
            "scaling_factor": self._printer_config.scaling_factor,
            "additional_settings": self._printer_config.additional_settings
        }
````

## File: MakerMatrix/repositories/user_repository.py
````python
from typing import Optional, List
from sqlmodel import Session, select
from sqlalchemy.orm import joinedload
from MakerMatrix.models.user_models import UserModel, RoleModel, UserRoleLink
from MakerMatrix.models.models import engine
from passlib.hash import pbkdf2_sha256
from datetime import datetime

pwd_context = pbkdf2_sha256

class UserRepository:
    def __init__(self):
        self.engine = engine

    def create_user(self, username: str, email: str, hashed_password: str, roles: List[str] = None) -> UserModel:
        with Session(self.engine) as session:
            # Check if username or email already exists
            existing_user = session.exec(
                select(UserModel).where(
                    (UserModel.username == username) | (UserModel.email == email)
                )
            ).first()
            if existing_user:
                if existing_user.username == username:
                    raise ValueError(f"Username '{username}' already exists")
                else:
                    raise ValueError(f"Email '{email}' already exists")

            # Create new user
            user = UserModel(
                username=username,
                email=email,
                hashed_password=hashed_password
            )

            # Add roles if provided
            if roles:
                role_models = []
                for role_name in roles:
                    role = session.exec(
                        select(RoleModel).where(RoleModel.name == role_name)
                    ).first()
                    if not role:
                        raise ValueError("Role not found")
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
                "roles": [{"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions} for role in user.roles]
            }
            
            # Create a new detached instance with the loaded data
            detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
            detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]
            
            return detached_user

    def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        with Session(self.engine) as session:
            statement = select(UserModel).options(joinedload(UserModel.roles)).where(UserModel.id == user_id)
            user = session.exec(statement).first()
            if not user:
                return None
            
            # Create a dictionary of the user data while the session is still open
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "password_change_required": user.password_change_required,
                "created_at": datetime.fromisoformat(user.created_at.isoformat()) if isinstance(user.created_at, datetime) else datetime.fromisoformat(user.created_at),
                "last_login": datetime.fromisoformat(user.last_login.isoformat()) if user.last_login and isinstance(user.last_login, datetime) else user.last_login,
                "hashed_password": user.hashed_password,
                "roles": [{"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions} for role in user.roles]
            }
            
            # Create a new detached instance with the loaded data
            detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
            detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]
            
            return detached_user

    def get_user_by_username(self, username: str) -> Optional[UserModel]:
        with Session(self.engine) as session:
            statement = select(UserModel).options(joinedload(UserModel.roles)).where(UserModel.username == username)
            user = session.exec(statement).first()
            if not user:
                return None
            
            # Create a dictionary of the user data while the session is still open
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "password_change_required": user.password_change_required,
                "created_at": datetime.fromisoformat(user.created_at.isoformat()) if isinstance(user.created_at, datetime) else datetime.fromisoformat(user.created_at),
                "last_login": datetime.fromisoformat(user.last_login.isoformat()) if user.last_login and isinstance(user.last_login, datetime) else user.last_login,
                "hashed_password": user.hashed_password,
                "roles": [{"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions} for role in user.roles]
            }
            
            # Create a new detached instance with the loaded data
            detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
            detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]
            
            return detached_user

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        with Session(self.engine) as session:
            statement = select(UserModel).options(joinedload(UserModel.roles)).where(UserModel.email == email)
            user = session.exec(statement).first()
            if not user:
                return None
            
            # Create a dictionary of the user data while the session is still open
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "password_change_required": user.password_change_required,
                "created_at": datetime.fromisoformat(user.created_at.isoformat()) if isinstance(user.created_at, datetime) else datetime.fromisoformat(user.created_at),
                "last_login": datetime.fromisoformat(user.last_login.isoformat()) if user.last_login and isinstance(user.last_login, datetime) else user.last_login,
                "hashed_password": user.hashed_password,
                "roles": [{"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions} for role in user.roles]
            }
            
            # Create a new detached instance with the loaded data
            detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
            detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]
            
            return detached_user

    def update_user(self, user_id: str, email: Optional[str] = None, 
                   is_active: Optional[bool] = None, roles: Optional[List[str]] = None,
                   password_change_required: Optional[bool] = None,
                   last_login: Optional[datetime] = None) -> Optional[UserModel]:
        with Session(self.engine) as session:
            statement = select(UserModel).options(joinedload(UserModel.roles)).where(UserModel.id == user_id)
            user = session.exec(statement).first()
            if not user:
                return None

            if email is not None:
                # Check if email is already used by another user
                existing_user = session.exec(
                    select(UserModel).where(
                        (UserModel.email == email) & (UserModel.id != user_id)
                    )
                ).first()
                if existing_user:
                    raise ValueError(f"Email '{email}' already exists")
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
                    role = session.exec(
                        select(RoleModel).where(RoleModel.name == role_name)
                    ).first()
                    if not role:
                        raise ValueError(f"Role '{role_name}' not found")
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
                "roles": [{"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions} for role in user.roles]
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
                "roles": [{"id": role.id, "name": role.name, "description": role.description, "permissions": role.permissions} for role in user.roles]
            }
            
            # Create a new detached instance with the loaded data
            detached_user = UserModel(**{k: v for k, v in user_dict.items() if k != "roles"})
            detached_user.roles = [RoleModel(**role_data) for role_data in user_dict["roles"]]
            
            return detached_user

    def delete_user(self, user_id: str) -> bool:
        with Session(self.engine) as session:
            user = session.exec(select(UserModel).where(UserModel.id == user_id)).first()
            if not user:
                return False

            session.delete(user)
            session.commit()
            return True

    def create_role(self, name: str, description: Optional[str] = None, 
                   permissions: Optional[List[str]] = None) -> RoleModel:
        with Session(self.engine) as session:
            # Check if role name already exists
            existing_role = session.exec(
                select(RoleModel).where(RoleModel.name == name)
            ).first()
            if existing_role:
                raise ValueError(f"Role '{name}' already exists")

            role = RoleModel(
                name=name,
                description=description,
                permissions=permissions or []
            )
            session.add(role)
            session.commit()
            session.refresh(role)
            return role

    def get_role_by_name(self, name: str) -> Optional[RoleModel]:
        with Session(self.engine) as session:
            return session.exec(select(RoleModel).where(RoleModel.name == name)).first()

    def get_role_by_id(self, role_id: str) -> Optional[RoleModel]:
        with Session(self.engine) as session:
            return session.exec(select(RoleModel).where(RoleModel.id == role_id)).first()

    def update_role(self, role_id: str, description: Optional[str] = None, 
                   permissions: Optional[List[str]] = None) -> Optional[RoleModel]:
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
            users = session.exec(select(UserModel).options(joinedload(UserModel.roles))).all()
            user_dicts = []
            for user in users:
                user_dicts.append({
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
                            "permissions": role.permissions
                        } for role in user.roles
                    ]
                })
            return user_dicts
````

## File: MakerMatrix/routers/auth_routes.py
````python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Cookie, Body, Request, Form
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError
from MakerMatrix.services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.user_models import UserCreate, UserModel, PasswordUpdate
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.dependencies import oauth2_scheme
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Define a standard OAuth2 token response model
class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenResponse(ResponseSchema[Token]):
    pass

# Define a model for mobile login
class MobileLoginRequest(BaseModel):
    username: str
    password: str

router = APIRouter()
auth_service = AuthService()
user_repository = UserRepository()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserModel:
    return auth_service.get_current_user(token)


@router.post("/auth/login")
async def login(request: Request):
    # Try to get form data first
    try:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
    except Exception:
        username = None
        password = None
    if username and password:
        user_in = {"username": username, "password": password}
    else:
        # Try JSON body
        try:
            data = await request.json()
            username = data.get("username")
            password = data.get("password")
            if username and password:
                user_in = {"username": username, "password": password}
            else:
                print("[DEBUG] /auth/login: Missing credentials in both form and JSON")
                raise HTTPException(status_code=400, detail="Missing credentials")
        except Exception:
            print("[DEBUG] /auth/login: Could not parse JSON body")
            raise HTTPException(status_code=400, detail="Missing credentials")

    print(f"[DEBUG] /auth/login: using username={username}")
    user = auth_service.authenticate_user(user_in["username"], user_in["password"])
    if not user:
        print(f"[DEBUG] /auth/login: Invalid credentials for username={user_in['username']}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth_service.create_access_token(
        data={"sub": user.username, "password_change_required": user.password_change_required}
    )
    refresh_token = auth_service.create_refresh_token(data={"sub": user.username})

    user.last_login = datetime.utcnow()
    user_repository.update_user(user.id, last_login=user.last_login)

    content = {
        "access_token": access_token,
        "token_type": "bearer",
        "status": "success",
        "message": "Login successful",
    }
    response = JSONResponse(content=content)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,  # For HTTPS in production
        samesite="lax",
        max_age=60 * 60 * 24 * 7
    )
    print(f"[DEBUG] /auth/login: Successful login for username={user.username}")
    return response


@router.post("/auth/refresh")
async def refresh_token(refresh_token: Optional[str] = Cookie(None)) -> JSONResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    try:
        payload = auth_service.verify_token(refresh_token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user = user_repository.get_user_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Create new access token
        access_token = auth_service.create_access_token(
            data={
                "sub": username,
                "password_change_required": user.password_change_required
            }
        )

        return JSONResponse(
            content=ResponseSchema(
                status="success",
                message="Token refreshed successfully",
                data={
                    "access_token": access_token,
                    "token_type": "bearer",
                    "password_change_required": user.password_change_required
                }
            ).model_dump()
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post("/auth/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(
        content=ResponseSchema(
            status="success",
            message="Logout successful",
            data=None
        ).model_dump()
    )

    # Clear the refresh token cookie
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return response


@router.post("/users/register")
async def register_user(user_data: UserCreate) -> ResponseSchema:
    try:
        # Hash the password
        hashed_password = user_repository.get_password_hash(user_data.password)
        
        # Create the user
        user = user_repository.create_user(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            roles=user_data.roles
        )

        return ResponseSchema(
            status="success",
            message="User registered successfully",
            data=user.to_dict()
        )

    except ValueError as e:
        return ResponseSchema(
            status="error",
            message=str(e),
            data=None
        )
````

## File: MakerMatrix/routers/categories_routes.py
````python
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from MakerMatrix.models.models import CategoryModel, CategoryUpdate
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError, CategoryAlreadyExistsError
from MakerMatrix.schemas.part_response import CategoryResponse, DeleteCategoriesResponse, CategoriesListResponse
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.category_service import CategoryService

router = APIRouter()


@router.get("/get_all_categories", response_model=ResponseSchema[CategoriesListResponse])
async def get_all_categories() -> ResponseSchema[CategoriesListResponse]:
    """
    Get all categories in the system.
    
    Returns:
        ResponseSchema: A response containing all categories
    """
    try:
        response = CategoryService.get_all_categories()
        print(f"Service response: {response}")  # Debug log
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=CategoriesListResponse(**response["data"])
        )
    except Exception as e:
        print(f"Error in get_all_categories: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_category", response_model=ResponseSchema[CategoryResponse])
async def add_category(category_data: CategoryModel) -> ResponseSchema[CategoryResponse]:
    """
    Add a new category to the system.
    
    Args:
        category_data: The category data to add
        
    Returns:
        ResponseSchema: A response containing the created category
    """
    try:
        if not category_data.name:
            raise HTTPException(status_code=400, detail="Category name is required")
            
        response = CategoryService.add_category(category_data)
        print(f"Service response: {response}")  # Debug log
        
        # Ensure we have a data field in the response
        if "data" not in response:
            raise HTTPException(status_code=500, detail="Invalid response format from service")
            
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=CategoryResponse.model_validate(response["data"])
        )
    except CategoryAlreadyExistsError as cae:
        raise HTTPException(status_code=400, detail=str(cae))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error in add_category: {str(e)}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_category/{category_id}", response_model=ResponseSchema[CategoryResponse])
async def update_category(category_id: str, category_data: CategoryUpdate) -> ResponseSchema[CategoryResponse]:
    """
    Update a category's fields.
    
    Args:
        category_id: The ID of the category to update
        category_data: The fields to update
        
    Returns:
        ResponseSchema: A response containing the updated category
    """
    try:
        if not category_id:
            raise HTTPException(status_code=400, detail="Category ID is required")
            
        response = CategoryService.update_category(category_id, category_data)
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=CategoryResponse.model_validate(response["data"])
        )
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_category", response_model=ResponseSchema[CategoryResponse])
async def get_category(category_id: Optional[str] = None, name: Optional[str] = None) -> ResponseSchema[CategoryResponse]:
    """
    Get a category by ID or name.
    
    Args:
        category_id: Optional ID of the category to retrieve
        name: Optional name of the category to retrieve
        
    Returns:
        ResponseSchema: A response containing the requested category
    """
    try:
        if not category_id and not name:
            raise HTTPException(status_code=400, detail="Either 'category_id' or 'name' must be provided")
            
        response = CategoryService.get_category(category_id=category_id, name=name)
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=CategoryResponse.model_validate(response["data"])
        )
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/remove_category", response_model=ResponseSchema[CategoryResponse])
async def remove_category(cat_id: Optional[str] = None, name: Optional[str] = None) -> ResponseSchema[CategoryResponse]:
    """
    Remove a category by ID or name.
    
    Args:
        cat_id: Optional ID of the category to remove
        name: Optional name of the category to remove
        
    Returns:
        ResponseSchema: A response containing the removed category
    """
    if not cat_id and not name:
        raise HTTPException(
            status_code=400,
            detail="Either category ID or name must be provided"
        )
            
    try:
        response = CategoryService.remove_category(id=cat_id, name=name)
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=CategoryResponse.model_validate(response["data"])
        )
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete_all_categories", response_model=ResponseSchema[DeleteCategoriesResponse])
async def delete_all_categories() -> ResponseSchema[DeleteCategoriesResponse]:
    """
    Delete all categories from the system.
    
    Returns:
        ResponseSchema: A response containing the deletion status
    """
    try:
        response = CategoryService.delete_all_categories()
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=DeleteCategoriesResponse(deleted_count=response["data"]["deleted_count"])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
````

## File: MakerMatrix/routers/locations_routes.py
````python
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from starlette.responses import JSONResponse

from MakerMatrix.models.models import LocationModel, LocationQueryModel
from MakerMatrix.models.models import LocationUpdate
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.location_service import LocationService
from MakerMatrix.dependencies import oauth2_scheme

router = APIRouter()


@router.get("/get_all_locations")
async def get_all_locations():
    try:
        locations = LocationService.get_all_locations()
        # noinspection PyArgumentList
        return ResponseSchema(
            status="success",
            message="All locations retrieved successfully",
            data=locations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_location")
async def get_location(
    location_id: Optional[str] = None, 
    name: Optional[str] = None
):
    try:
        if not location_id and not name:
            raise HTTPException(status_code=400, detail="Either 'location_id' or 'name' must be provided")
        location_query = LocationQueryModel(id=location_id, name=name)
        location = LocationService.get_location(location_query)
        if location:
            # noinspection PyArgumentList
            return ResponseSchema(
                status="success",
                message="Location retrieved successfully",
                data=location.to_dict()
            )

    except ResourceNotFoundError as rnfe:
        raise rnfe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_location/{location_id}", response_model=ResponseSchema[LocationModel])
async def update_location(location_id: str, location_data: LocationUpdate) -> ResponseSchema[LocationModel]:
    """
    Update a location's fields. This endpoint can update any combination of name, description, parent_id, and location_type.
    
    Args:
        location_id: The ID of the location to update
        location_data: The fields to update (name, description, parent_id, location_type)
        
    Returns:
        ResponseSchema: A response containing the updated location data
    """
    try:
        # Convert the Pydantic model to a dict and remove None values
        update_data = {k: v for k, v in location_data.model_dump().items() if v is not None}
        updated_location = LocationService.update_location(location_id, update_data)
        return ResponseSchema(
            status="success",
            message="Location updated successfully",
            data=updated_location.model_dump()
        )
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_location")
async def add_location(location_data: LocationModel, token: str = Depends(oauth2_scheme)) -> ResponseSchema[LocationModel]:
    try:
        # Check if a location with the same name and parent_id already exists
        existing_location = None
        try:
            location_query = LocationQueryModel(name=location_data.name)
            existing_location = LocationService.get_location(location_query)
            
            # If we found a location with the same name, check if it has the same parent_id
            if existing_location and existing_location.parent_id == location_data.parent_id:
                return JSONResponse(
                    status_code=409,
                    content={
                        "status": "error",
                        "message": f"Location with name '{location_data.name}' already exists under the same parent"
                    }
                )
        except ResourceNotFoundError:
            # If no location with this name exists, we can proceed
            pass
            
        location = LocationService.add_location(location_data.model_dump())
        return ResponseSchema(
            status="success",
            message="Location added successfully",
            data=location.to_dict()
        )
    except Exception as e:
        # Check if this is an integrity error (likely a duplicate name + parent_id)
        if "UNIQUE constraint failed" in str(e) or "unique constraint" in str(e).lower():
            return JSONResponse(
                status_code=409,
                content={
                    "status": "error",
                    "message": f"Location with name '{location_data.name}' already exists under the same parent"
                }
            )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_location_details/{location_id}")
async def get_location_details(location_id: str):
    """
    Get detailed information about a location, including its children.

    Args:
        location_id (str): The ID of the location to get details for.

    Returns:
        ResponseSchema: A response containing the location details and its children.
    """
    response = LocationService.get_location_details(location_id)
    if response["status"] == "success":
        return ResponseSchema(
            status=response["status"],
            message=response.get("message", "Location details retrieved successfully"),
            data=response.get("data")
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=response.get("message", "Location not found")
        )


@router.get("/get_location_path/{location_id}", response_model=ResponseSchema)
async def get_location_path(location_id: str):
    """Get the full path from a location to its root.
    
    Args:
        location_id: The ID of the location to get the path for
        
    Returns:
        A ResponseSchema containing the location path with parent references
    """
    try:
        response = LocationService.get_location_path(location_id)
        return response
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview-location-delete/{location_id}")
async def preview_location_delete(location_id: str) -> ResponseSchema:
    """
    Preview what will be affected when deleting a location.
    
    Args:
        location_id: The ID of the location to preview deletion for
        
    Returns:
        ResponseSchema: A response containing the preview information
    """
    try:
        preview_response = LocationService.preview_location_delete(location_id)
        return ResponseSchema(
            status="success",
            message="Delete preview generated",
            data=preview_response
        )
    except ResourceNotFoundError as rnfe:
        raise rnfe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete_location/{location_id}")
async def delete_location(location_id: str) -> ResponseSchema:
    try:
        response = LocationService.delete_location(location_id)
        return ResponseSchema(
            status=response['status'],
            message=response['message'],
            data=response['data']
        )
    except ResourceNotFoundError as rnfe:
        raise rnfe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup-locations")
async def cleanup_locations():
    """
    Clean up locations by removing those with invalid parent IDs and their descendants.
    
    Returns:
        ResponseSchema: A response containing the cleanup results.
    """
    response = LocationService.cleanup_locations()
    if response["status"] == "success":
        return ResponseSchema(
            status=response["status"],
            message=response.get("message", "Locations cleaned up successfully"),
            data=response.get("data")
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=response.get("message", "Failed to clean up locations")
        )


@router.get("/preview-delete/{location_id}")
async def preview_delete(location_id: str):
    """
    DEPRECATED: Use /preview-location-delete/{location_id} instead.
    Preview what will be affected when deleting a location.
    
    Args:
        location_id: The ID of the location to preview deletion for
        
    Returns:
        JSONResponse: A JSON response containing the preview information.
    """
    return await preview_location_delete(location_id)
````

## File: MakerMatrix/routers/parts_routes.py
````python
from typing import Dict, Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status

from MakerMatrix.models.models import PartModel, AdvancedPartSearch
from MakerMatrix.repositories.custom_exceptions import PartAlreadyExistsError, ResourceNotFoundError
from MakerMatrix.schemas.part_create import PartCreate, PartUpdate
from MakerMatrix.schemas.part_response import PartResponse
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.category_service import CategoryService
from MakerMatrix.services.part_service import PartService
from MakerMatrix.models.user_models import UserModel
from MakerMatrix.models.models import PartModel, UpdateQuantityRequest, GenericPartQuery
from MakerMatrix.services.part_service import PartService

router = APIRouter()

import logging

logger = logging.getLogger(__name__)


@router.post("/add_part", response_model=ResponseSchema[PartResponse])
async def add_part(part: PartCreate) -> ResponseSchema[PartResponse]:
    try:
        # Convert PartCreate to dict and include category_names
        part_data = part.model_dump()
        
        # Process to add part
        response = PartService.add_part(part_data)

        # noinspection PyArgumentList
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=PartResponse.model_validate(response["data"])
        )
    except PartAlreadyExistsError as pae:
        raise HTTPException(
            status_code=409,
            detail=f"Part with name '{part_data['part_name']}' already exists"
        )
    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=str(rnfe))
    except ValueError as ve:
        if "Input should be a valid string" in str(ve):
            raise HTTPException(
                status_code=422,
                detail=[{
                    "loc": ["body", "category_names", 0],
                    "msg": "Input should be a valid string",
                    "type": "string_type"
                }]
            )
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_part_counts", response_model=ResponseSchema[int])
async def get_part_counts():
    try:
        response = PartService.get_part_counts()
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=response["total_parts"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


###


@router.delete("/delete_part", response_model=ResponseSchema[Dict[str, Any]])
def delete_part(
        part_id: Optional[str] = Query(None, description="Part ID"),
        part_name: Optional[str] = Query(None, description="Part Name"),
        part_number: Optional[str] = Query(None, description="Part Number")
) -> ResponseSchema[Dict[str, Any]]:
    """
    Delete a part based on ID, part name, or part number.
    Raises HTTP 400 if no identifier is provided.
    Raises HTTP 404 if the part is not found.
    """
    try:
        # Retrieve part using details
        part = PartService.get_part_by_details(part_id=part_id, part_name=part_name, part_number=part_number)

        # if part is None:
        #     raise HTTPException(
        #         status_code=400,
        #         detail="At least one identifier (part_id, part_name, or part_number) must be provided."
        #     )

        # Perform the deletion using the actual part ID
        response = PartService.delete_part(part['id'])

        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=PartResponse.model_validate(response["data"])
        )

    except ResourceNotFoundError as rnfe:
        raise HTTPException(status_code=404, detail=rnfe.message)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete part: {str(e)}")


###

@router.get("/get_all_parts", response_model=ResponseSchema[List[PartResponse]])
async def get_all_parts(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=10, ge=1)
) -> ResponseSchema[List[PartResponse]]:
    try:
        response = PartService.get_all_parts(page, page_size)

        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=[PartResponse.model_validate(part) for part in response["data"]],
            page=response["page"],
            page_size=response["page_size"],
            total_parts=response["total_parts"]
        )

    except ResourceNotFoundError as rnfe:
        raise rnfe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_part")
async def get_part(
        part_id: Optional[str] = Query(None),
        part_number: Optional[str] = Query(None),
        part_name: Optional[str] = Query(None)
) -> ResponseSchema[PartResponse]:
    try:
        # Use the PartService to determine which parameter to use for fetching
        if part_id:
            response = PartService.get_part_by_id(part_id)
        elif part_number:
            response = PartService.get_part_by_part_number(part_number)
        elif part_name:
            response = PartService.get_part_by_part_name(part_name)
        else:
            # If no identifier is provided, return a 400 error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one identifier (part_id, part_number, or part_name) must be provided"
            )

        return ResponseSchema(

            status=response["status"],
            message=response["message"],
            data=PartResponse.model_validate(response["data"])
        )

    except ResourceNotFoundError as rnfe:
        raise rnfe

    except HTTPException as http_exc:
        # Re-raise any caught HTTP exceptions
        raise http_exc
    except Exception as e:
        # For other exceptions, raise a general HTTP error
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all_parts/")
async def get_all_parts():
    try:
        parts = PartService.get_all_parts()
        return parts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_part/{part_id}", response_model=ResponseSchema[PartResponse])
async def update_part(part_id: str, part_data: PartUpdate) -> ResponseSchema[PartResponse]:
    try:
        # Use part_id from the path
        response = PartService.update_part(part_id, part_data)

        if response["status"] == "error":
            raise HTTPException(status_code=404, detail=response["message"])

        # noinspection PyArgumentList
        return ResponseSchema(

            status="success",
            message="Part updated successfully.",
            data=PartResponse.model_validate(response["data"])
        )

    except ResourceNotFoundError as rnfe:
        # Let the custom exception handler handle this
        raise rnfe
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#
# @router.put("/decrement_count/")
# async def decrement_count(generic_part_query: GenericPartQuery):
#     try:
#         part, part_field, previous_quantity = PartService.decrement_count_service(generic_part_query)
#         return {
#             "message": f"Quantity decremented from {previous_quantity} to {part['quantity']} part {part[part_field]}",
#             "previous_quantity": previous_quantity,
#             "new_quantity": part['quantity']}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#

#
#
# @router.put("/update_quantity/")
# def update_part_quantity(update_request: UpdateQuantityRequest):
#     try:
#         part_updated = PartService.update_quantity_service(
#             new_quantity=update_request.new_quantity,
#             part_id=update_request.part_id,
#             part_number=update_request.part_number,
#             manufacturer_pn=update_request.manufacturer_pn
#
#         )
#
#         if part_updated:
#             return {"message": f"Quantity updated to {update_request.new_quantity}"}
#         else:
#             raise HTTPException(status_code=404, detail="Part not found")
#     except ValidationError as e:
#         raise HTTPException(status_code=422, detail=str(e))
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.post("/search-parts/")
# async def search_parts(criteria: Dict[str, str] = Body(...)):
#     if not criteria:
#         raise HTTPException(status_code=400, detail="Search criteria are required")
#     results = PartService.dynamic_search(criteria)
#     return results
#
#
# @router.get("/all_parts/")
# async def get_all_parts():
#     try:
#         parts = PartService.get_all_parts()
#         return parts
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#

#
#
# @router.get("/get_parts/")
# async def get_parts(page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1)):
#     try:
#         parts = PartService.get_all_parts_paginated(page=page, page_size=page_size)
#         total_count = PartService.get_total_parts_count()
#         return {"parts": parts, "page": page, "page_size": page_size, "total": total_count}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#

#
#
# @router.get("/get_part_by_details")
# def get_part_by_details(part_id: Optional[str] = None, part_number: Optional[str] = None,
#                         part_name: Optional[str] = None):
#     try:
#         # Pass the search criteria directly to the service
#         part = PartService.get_part_by_details(part_id=part_id, part_number=part_number, part_name=part_name)
#         if part:
#             return part
#         else:
#             raise HTTPException(status_code=404, detail=f"Part Details with part_number '{part_number}' not found")
#     except HTTPException as http_exc:
#         # Re-raise HTTPException (such as the 404) without catching it
#         raise http_exc
#     except Exception as e:
#         # Catch other generic exceptions and raise a 500 error
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.get("/get_parts/")
# async def get_parts(page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1)):
#     try:
#         result = PartService.get_parts_paginated(page, page_size)
#
#         if "error" in result:
#             raise HTTPException(status_code=500, detail=result["error"])
#
#         return JSONResponse(
#             content=result,
#             status_code=200
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.delete("/clear_parts")
# def clear_all_parts():
#     try:
#         PartService.part_repo.clear_all_parts()
#         return {"status": "success", "message": "All parts have been cleared."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.post("/add_part")
# async def add_part(part: PartModel, overwrite: bool = False) -> Dict:
#     try:
#         response = PartService.add_part(part, overwrite)
#
#         # Check if the response asks for confirmation
#         if response.get("status") == "part exists":
#             return {
#                 "status": "pending_confirmation",
#                 "message": response.get("message"),
#                 "data": response["data"]
#             }
#
#         # Return success response if the part was added
#         return {
#             "status": "success",
#             "message": "Part added successfully",
#             "data": response["data"]
#         }
#
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.delete("/delete_part/{part_id}")
# async def delete_part(part_id: str):
#     try:
#         deleted_part = PartService.part_repo.delete_part(part_id)
#         if deleted_part:
#             return {"message": "Part deleted successfully", "deleted_part_id": part_id}
#         else:
#             # Properly raise the 404 error if no part was found
#             raise HTTPException(status_code=404, detail="Part not found")
#     except HTTPException as http_exc:
#         raise http_exc
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.get("/search-parts/")
# async def search(term: str):
#     min_length = 2
#     if len(term) < min_length:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Search term must be at least {min_length} characters long."
#         )
#     try:
#         results = PartService.dynamic_search(term)
#         if isinstance(results, dict) and "error" in results:
#             raise HTTPException(status_code=500, detail=results["error"])
#         # Return results directly
#         return {"status": "success", "data": results}
#     except HTTPException as http_exc:
#         raise http_exc
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))
#
#
# @router.get("/get_parts_by_location/{location_id}")
# async def get_parts_by_location(location_id: str, recursive: bool = False):
#     try:
#         result = PartService.get_parts_by_location_id(location_id, recursive)
#         if result:
#             return {
#                 "status": "success",
#                 "message": f"Parts found for location {location_id}",
#                 "location_id": location_id,
#                 "data": result,
#                 "part_count": len(result)
#             }
#         else:
#             raise HTTPException(
#                 status_code=404,
#                 detail={
#                     "status": "error",
#                     "message": f"No parts found for location {location_id}",
#                     "location_id": location_id,
#                 }
#             )
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail={
#                 "status": "error",
#                 "message": f"An error occurred while retrieving parts for location {location_id}",
#                 "location_id": location_id,
#                 "error": str(e)
#             }
#         )

@router.post("/search", response_model=ResponseSchema[Dict[str, Any]])
async def advanced_search(search_params: AdvancedPartSearch) -> ResponseSchema[Dict[str, Any]]:
    """
    Perform an advanced search on parts with multiple filters and sorting options.
    """
    try:
        response = PartService.advanced_search(search_params)
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=response["data"]
        )
    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        raise HTTPException(status_code=500, detail=str(e))
````

## File: MakerMatrix/routers/printer_routes.py
````python
from fastapi import APIRouter, HTTPException

from MakerMatrix.models import printer_config_model
from MakerMatrix.models.label_model import LabelData
from MakerMatrix.services.printer_service import PrinterService

router = APIRouter()


@router.post("/print_label")
async def print_label(label_data: LabelData):
    try:
        response = await PrinterService.print_label(label_data)
        return {"message": "QR code printed successfully"} if response else HTTPException(status_code=500,
                                                                                          detail="Failed to print QR code")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/print_qr")
async def print_qr_code(label_data: LabelData):
    try:
        response = await PrinterService.print_qr_code(label_data)
        return {"message": "QR code printed successfully"} if response else HTTPException(status_code=500,
                                                                                          detail="Failed to print QR code")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def configure_printer(config: printer_config_model.PrinterConfig):
    try:
        response = await PrinterService.configure_printer(config)
        return {"message": "Printer configuration updated and saved."} if response else HTTPException(status_code=500,
                                                                                          detail="Failed to configure printer")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load_config")
async def load_printer_config():
    try:
        PrinterService.load_printer_config()
        return {"message": "Printer configuration loaded."}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Config file not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current_printer")
async def get_current_printer():
    try:
        current_printer = PrinterService.get_current_configuration()
        return {"current_printer": current_printer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
````

## File: MakerMatrix/routers/role_routes.py
````python
from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import Optional, List
from pydantic import BaseModel
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.dependencies import oauth2_scheme


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleUpdate(BaseModel):
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


router = APIRouter()
user_repository = UserRepository()
auth_service = AuthService()


async def get_current_user(token: str = Depends(oauth2_scheme)):
    return auth_service.get_current_user(token)


@router.post("/add_role", response_model=ResponseSchema)
async def create_role(role_data: RoleCreate):
    try:
        role = user_repository.create_role(
            name=role_data.name,
            description=role_data.description,
            permissions=role_data.permissions
        )
        return ResponseSchema(
            status="success",
            message="Role created successfully",
            data=role.to_dict()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/by-name/{name}", response_model=ResponseSchema)
async def get_role_by_name(name: str):
    role = user_repository.get_role_by_name(name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return ResponseSchema(
        status="success",
        message="Role retrieved successfully",
        data=role.to_dict()
    )


@router.get("/{role_id}", response_model=ResponseSchema)
async def get_role(role_id: str):
    role = user_repository.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return ResponseSchema(
        status="success",
        message="Role retrieved successfully",
        data=role.to_dict()
    )


@router.put("/{role_id}", response_model=ResponseSchema)
async def update_role(role_id: str, role_data: RoleUpdate):
    try:
        role = user_repository.update_role(
            role_id=role_id,
            description=role_data.description,
            permissions=role_data.permissions
        )
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        return ResponseSchema(
            status="success",
            message="Role updated successfully",
            data=role.to_dict()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{role_id}", response_model=ResponseSchema)
async def delete_role(role_id: str):
    if user_repository.delete_role(role_id):
        return ResponseSchema(
            status="success",
            message="Role deleted successfully",
            data=None
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Role not found"
    )
````

## File: MakerMatrix/routers/user_routes.py
````python
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from MakerMatrix.models.user_models import UserCreate, UserUpdate, PasswordUpdate
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.dependencies import oauth2_scheme

router = APIRouter()
user_repository = UserRepository()
auth_service = AuthService()


async def get_current_user(token: str = Depends(oauth2_scheme)):
    return auth_service.get_current_user(token)


@router.post("/register", response_model=ResponseSchema)
async def register_user(user_data: UserCreate):
    try:
        # Hash the password
        hashed_password = user_repository.get_password_hash(user_data.password)
        
        # Create the user
        user = user_repository.create_user(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            roles=user_data.roles
        )
        print(f"[DEBUG] Registered user: {user.username}, roles: {user.roles}")
        return ResponseSchema(
            status="success",
            message="User registered successfully",
            data=user.to_dict()
        )

    except ValueError as e:
        print(f"[DEBUG] Registration error: {str(e)}")
        return ResponseSchema(
            status="error",
            message=str(e),
            data=None
        )


@router.get("/{user_id}", response_model=ResponseSchema)
async def get_user(user_id: str):
    user = user_repository.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return ResponseSchema(
        status="success",
        message="User retrieved successfully",
        data=user.to_dict()
    )


@router.get("/by-username/{username}", response_model=ResponseSchema)
async def get_user_by_username(username: str):
    user = user_repository.get_user_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return ResponseSchema(
        status="success",
        message="User retrieved successfully",
        data=user.to_dict()
    )


@router.put("/{user_id}", response_model=ResponseSchema)
async def update_user(user_id: str, user_data: UserUpdate):
    try:
        user = user_repository.update_user(
            user_id=user_id,
            email=user_data.email,
            is_active=user_data.is_active,
            roles=user_data.roles
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return ResponseSchema(
            status="success",
            message="User updated successfully",
            data=user.to_dict()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{user_id}/password", response_model=ResponseSchema)
async def update_password(user_id: str, password_data: PasswordUpdate):
    user = user_repository.get_user_by_id(user_id)
    if not user:
        return ResponseSchema(
            status="error",
            message="User not found",
            data=None
        )

    # Verify current password
    if not user_repository.verify_password(password_data.current_password, user.hashed_password):
        return ResponseSchema(
            status="error",
            message="Current password is incorrect",
            data=None
        )

    # Hash and update new password
    new_hashed_password = user_repository.get_password_hash(password_data.new_password)
    updated_user = user_repository.update_password(user_id, new_hashed_password)

    return ResponseSchema(
        status="success",
        message="Password updated successfully",
        data=updated_user.to_dict()
    )


@router.get("/all", response_model=ResponseSchema)
async def get_all_users(current_user=Depends(get_current_user)):
    # Only admin users can access this route
    if not any(role.name == "admin" for role in getattr(current_user, "roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    from MakerMatrix.services.user_service import UserService
    response = UserService.get_all_users()
    return ResponseSchema(**response)


@router.delete("/{user_id}", response_model=ResponseSchema)
async def delete_user(user_id: str):
    if user_repository.delete_user(user_id):
        return ResponseSchema(
            status="success",
            message="User deleted successfully",
            data=None
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
````

## File: MakerMatrix/routers/utility_routes.py
````python
import os
import shutil
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from starlette.responses import FileResponse, JSONResponse

from MakerMatrix.services.category_service import CategoryService
from MakerMatrix.services.location_service import LocationService
from MakerMatrix.services.part_service import PartService
from MakerMatrix.schemas.response import ResponseSchema

router = APIRouter()


@router.post("/upload_image")
async def upload_image(file: UploadFile = File(...)):
    file_extension = os.path.splitext(file.filename)[1]
    image_id = str(uuid.uuid4())
    file_path = f"uploaded_images/{image_id}{file_extension}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"image_id": image_id}


@router.get("/")
async def serve_index_html():
    return FileResponse("static/part_inventory_ui/build/index.html")


@router.get("/get_image/{image_id}")
async def get_image(image_id: str):
    file_path = f"uploaded_images/{image_id}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Image not found")


@router.get("/get_counts")
async def get_counts():
    """
    Returns all counts for parts, locations, and categories
    """
    # db_manager = DatabaseManager.get_instance()
    try:
        parts_count = len(PartService.get_all_parts()['data'])
        locations_count = len(LocationService.get_all_locations())
        categories_count = len(CategoryService.get_all_categories()['data'])

        return ResponseSchema(
            status="success",
            message="Counts retrieved successfully",
            data={"parts": parts_count, "locations": locations_count, "categories": categories_count}
        )
    except Exception as e:
        print(f"Error getting counts: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while fetching counts")
````

## File: MakerMatrix/schemas/location_delete_response.py
````python
from typing import List, Optional
from pydantic import BaseModel


class LocationDeleteResponse(BaseModel):
    location_ids_to_delete: List[str]
    affected_parts_count: int
    affected_locations_count: int
    location_hierarchy: dict

    class Config:
        from_attributes = True
````

## File: MakerMatrix/schemas/part_create.py
````python
from typing import Optional, List

from pydantic import BaseModel, model_validator


class PartCreate(BaseModel):
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[int]
    description: Optional[str] = None
    supplier: Optional[str] = None
    location_id: Optional[str] = None
    image_url: Optional[str] = None
    additional_properties: Optional[dict] = {}
    category_names: Optional[List[str]] = []

    @model_validator(mode='before')
    def check_part_identifiers(cls, values):
        if not values.get('part_name') and not values.get('part_number'):
            raise ValueError('Either part_name or part_number must be provided')
        return values

    class Config:
        from_attributes = True


class PartUpdate(BaseModel):
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[int] = None
    description: Optional[str] = None
    supplier: Optional[str] = None
    location_id: Optional[str] = None
    image_url: Optional[str] = None
    additional_properties: Optional[dict] = {}
    category_names: Optional[List[str]] = []

    class Config:
        from_attributes = True
````

## File: MakerMatrix/schemas/part_response.py
````python
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class CategoryResponse(BaseModel):
    id: Optional[str]
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CategoriesListResponse(BaseModel):
    categories: List[CategoryResponse]

    model_config = ConfigDict(from_attributes=True)


class PartResponse(BaseModel):
    id: Optional[str]
    part_number: Optional[str]
    part_name: Optional[str]
    quantity: Optional[int]
    description: Optional[str] = None
    supplier: Optional[str] = None
    location_id: Optional[str] = None
    image_url: Optional[str] = None
    additional_properties: Optional[dict] = {}
    categories: Optional[List[CategoryResponse]] = []

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_categories(cls, orm_obj):
        # Convert the ORM model to a dictionary
        part_dict = orm_obj.model_dump()
        part_dict["categories"] = [
            {"id": cat.id, "name": cat.name, "description": cat.description}
            for cat in orm_obj.categories
        ]
        return cls(**part_dict)


class DeleteCategoriesResponse(BaseModel):
    deleted_count: int

    model_config = ConfigDict(from_attributes=True)
````

## File: MakerMatrix/schemas/response.py
````python
from typing import Optional, Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")

class ResponseSchema(BaseModel, Generic[T]):
    status: str
    message: str
    data: Optional[T] = None
    page: Optional[int] = None  # For pagination
    page_size: Optional[int] = None  # For pagination
    total_parts: Optional[int] = None  # Total count for pagination
````

## File: MakerMatrix/scripts/setup_admin.py
````python
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.models import engine
from sqlmodel import SQLModel
from MakerMatrix.database.db import create_db_and_tables
from passlib.hash import pbkdf2_sha256

# Default admin credentials
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@makermatrix.local"
DEFAULT_ADMIN_PASSWORD = "Admin123!"  # This should be changed on first login

def setup_default_roles(user_repo: UserRepository):
    """Set up default roles if they don't exist."""
    roles = [
        {
            "name": "admin",
            "description": "Administrator with full access",
            "permissions": ["all"]
        },
        {
            "name": "manager",
            "description": "Manager with write access",
            "permissions": ["read", "write", "update"]
        },
        {
            "name": "user",
            "description": "Regular user with read access",
            "permissions": ["read"]
        }
    ]

    for role_data in roles:
        try:
            existing_role = user_repo.get_role_by_name(role_data["name"])
            if not existing_role:
                user_repo.create_role(**role_data)
                print(f"Created role: {role_data['name']}")
            else:
                print(f"Role already exists: {role_data['name']}")
        except Exception as e:
            print(f"Error creating role {role_data['name']}: {str(e)}")


def setup_default_admin(user_repo: UserRepository):
    """Set up default admin user if it doesn't exist."""
    try:
        existing_admin = user_repo.get_user_by_username(DEFAULT_ADMIN_USERNAME)
        if existing_admin:
            print("Admin user already exists")
            return

        # Hash the default password
        hashed_password = pbkdf2_sha256.hash(DEFAULT_ADMIN_PASSWORD)
        
        # Create admin user with password change required
        admin_user = user_repo.create_user(
            username=DEFAULT_ADMIN_USERNAME,
            email=DEFAULT_ADMIN_EMAIL,
            hashed_password=hashed_password,
            roles=["admin"]
        )
        
        # Set password change required
        user_repo.update_user(
            user_id=admin_user.id,
            password_change_required=True
        )
        
        print(f"Created default admin user: {DEFAULT_ADMIN_USERNAME}")
        print("Please change the password on first login!")
        
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")


def main():
    """Main setup function."""
    print("Setting up MakerMatrix admin user and roles...")
    
    # Create tables if they don't exist
    print("Ensuring database tables exist...")
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()
    
    # Initialize repository
    user_repo = UserRepository()
    
    # Set up roles and admin user
    print("\nSetting up default roles...")
    setup_default_roles(user_repo)
    
    print("\nSetting up default admin user...")
    setup_default_admin(user_repo)
    
    print("\nSetup complete!")


if __name__ == "__main__":
    main()
````

## File: MakerMatrix/services/auth_service.py
````python
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.user_models import UserModel

# These should be moved to environment variables in production
SECRET_KEY = "your-secret-key-keep-it-secret"  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthService:
    def __init__(self):
        self.user_repository = UserRepository()

    def authenticate_user(self, username: str, password: str) -> Optional[UserModel]:
        user = self.user_repository.get_user_by_username(username)
        if not user:
            return None
        if not self.user_repository.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "password_change_required": data.get("password_change_required", False)
        })
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def get_current_user(self, token: str) -> UserModel:
        payload = self.verify_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = self.user_repository.get_user_by_username(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user

    def has_permission(self, user: UserModel, required_permission: str) -> bool:
        if not user.roles:
            return False
        
        for role in user.roles:
            if "all" in role.permissions or required_permission in role.permissions:
                return True
        return False
````

## File: MakerMatrix/services/category_service.py
````python
from typing import Optional, Any

from sqlmodel import Session
from MakerMatrix.models.models import CategoryModel
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.category_repositories import CategoryRepository
from MakerMatrix.database.db import get_session
from MakerMatrix.repositories.custom_exceptions import CategoryAlreadyExistsError, ResourceNotFoundError
from sqlalchemy import select, delete


class CategoryService:
    category_repo = CategoryRepository(engine)

    @staticmethod
    def add_category(category_data: CategoryModel) -> dict:
        """
        Add a new category to the system.
        
        Args:
            category_data: The category data to add
            
        Returns:
            dict: A dictionary containing the status, message, and created category data
        """
        try:
            if not category_data.name:
                raise ValueError("Category name is required")

            session = next(get_session())
            existing_category = CategoryRepository.get_category(session, name=category_data.name)
            
            if existing_category:
                return {
                    "status": "success",
                    "message": f"Category with name '{category_data.name}' already exists",
                    "data": existing_category.model_dump()
                }
            
            new_category = CategoryRepository.create_category(session, category_data.model_dump())
            if not new_category:
                raise ValueError("Failed to create category")
            
            return {
                "status": "success",
                "message": f"Category with name '{category_data.name}' created successfully",
                "data": new_category.model_dump()
            }
                
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise ValueError(f"Failed to create category: {str(e)}")

    @staticmethod
    def get_category(category_id: Optional[str] = None, name: Optional[str] = None) -> dict:
        """
        Get a category by ID or name.
        
        Args:
            category_id: Optional ID of the category to retrieve
            name: Optional name of the category to retrieve
            
        Returns:
            dict: A dictionary containing the status, message, and category data
        """
        try:
            session = next(get_session())
            category = CategoryRepository.get_category(session, category_id=category_id, name=name)
            if not category:
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category not found with {'ID' if category_id else 'name'} {category_id or name}",
                    data=None
                )
            return {
                "status": "success",
                "message": f"Category with name '{category.name}' retrieved successfully",
                "data": category.model_dump(),
            }
        except ResourceNotFoundError as rnfe:
            raise rnfe
        except Exception as e:
            raise ValueError(f"Failed to retrieve category: {str(e)}")

    @staticmethod
    def remove_category(id: Optional[str] = None, name: Optional[str] = None) -> dict:
        """
        Remove a category by ID or name.
        
        Args:
            id: Optional ID of the category to remove
            name: Optional name of the category to remove
            
        Returns:
            dict: A dictionary containing the status, message, and removed category data
        """
        try:
            if not id and not name:
                raise ValueError("Either 'id' or 'name' must be provided")

            session = next(get_session())
            if id:
                identifier = id
                field = "ID"
                rm_cat = session.get(CategoryModel, id)
            else:
                identifier = name
                field = "name"
                rm_cat = session.exec(select(CategoryModel).where(CategoryModel.name == name)).first()

            if not rm_cat:
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category with {field} {identifier} not found",
                    data=None
                )
            
            result = CategoryService.category_repo.remove_category(session, rm_cat)
            if not result:
                raise ValueError("Failed to remove category")
            
            return {
                "status": "success",
                "message": f"Category with name '{rm_cat.name}' removed",
                "data": rm_cat.model_dump()
            }
            
        except ResourceNotFoundError as rnfe:
            raise rnfe
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise ValueError(f"Failed to remove category: {str(e)}")
    
    @staticmethod
    def delete_all_categories() -> dict:
        """
        Delete all categories from the system.
        
        Returns:
            dict: A dictionary containing the status, message, and deletion count
        """
        try:
            session = next(get_session())
            categories = session.exec(select(CategoryModel)).all()
            count = len(categories)
            
            session.exec(delete(CategoryModel))
            session.commit()
            
            return {
                "status": "success",
                "message": f"All {count} categories removed successfully",
                "data": {"deleted_count": count}
            }
        except Exception as e:
            raise ValueError(f"Failed to delete all categories: {str(e)}")

    @staticmethod
    def get_all_categories() -> dict:
        """
        Get all categories from the system.
        
        Returns:
            dict: A dictionary containing the status, message, and all categories
        """
        try:
            session = next(get_session())
            categories = session.exec(select(CategoryModel)).all()
            return {
                "status": "success",
                "message": "All categories retrieved successfully",
                "data": {
                    "categories": [cat._asdict()['CategoryModel'].model_dump() for cat in categories] if categories else []
                }
            }
        except Exception as e:
            print(f"Error in get_all_categories: {str(e)}")  # Debug log
            raise ValueError(f"Failed to retrieve categories: {str(e)}")
    
    @staticmethod
    def update_category(category_id: str, category_update: CategoryModel) -> dict:
        """
        Update a category's fields.
        
        Args:
            category_id: The ID of the category to update
            category_update: The fields to update
            
        Returns:
            dict: A dictionary containing the status, message, and updated category data
        """
        try:
            if not category_id:
                raise ValueError("Category ID is required")
            
            session = next(get_session())
            updated_category = CategoryRepository.update_category(session, category_id, category_update)
            if not updated_category:
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Category with ID {category_id} not found",
                    data=None
                )
            
            return {
                "status": "success",
                "message": f"Category with ID '{category_id}' updated.",
                "data": updated_category.model_dump()
            }
        except ResourceNotFoundError as rnfe:
            raise rnfe
        except ValueError as ve:
            raise ve
        except Exception as e:
            raise ValueError(f"Failed to update category: {str(e)}")

    #
    # @staticmethod
    # def get_category(category_id: Optional[str] = None, name: Optional[str] = None) -> Optional[dict]:
    #     if not category_id and not name:
    #         raise ValueError("Either 'category_id' or 'name' must be provided")
    #
    #     return CategoryService.category_repo.get_category(category_id=category_id, name=name)
    #
    # @staticmethod
    # def add_category(category_data: CategoryModel) -> dict:
    #     # Call the repository to add the category
    #     return CategoryService.category_repo.add_category(category_data)
    #
````

## File: MakerMatrix/services/label_service.py
````python
import math
from typing import Dict, Optional, Any

import qrcode
from PIL import Image, ImageOps, ImageDraw, ImageFont

from MakerMatrix.lib.print_settings import PrintSettings


class LabelService:
    @staticmethod
    def get_label_width_inches(label_size: int | str) -> float:
        """
        Convert a label size (in mm or a string containing mm) to inches.

        Args:
            label_size (int | str): The label size in mm or a string representation.

        Returns:
            float: The label width in inches.
        """
        if isinstance(label_size, int):
            width_mm = label_size
        else:
            width_mm = int(''.join(filter(str.isdigit, str(label_size))))
        return width_mm / 25.4

    @staticmethod
    def get_available_height_pixels(print_settings: PrintSettings) -> int:
        """
        Convert label height (in mm) from print_settings to pixels.
        """
        inches = print_settings.label_size / 25.4
        return round(inches * print_settings.dpi)

    @staticmethod
    def measure_text_size(
        text: str,
        print_settings: PrintSettings,
        allowed_height: int
    ) -> (int, int):
        """
        Measure the width/height of a text block given the label's allowed height.
        Returns the final text width and text height in pixels (after auto-scaling).

        We ignore allowed_width here and just find the maximum font size that
        fits the provided allowed_height. Then we measure the text's width
        at that font size.

        Returns:
            (max_line_width_px, total_text_height_px)
        """
        dummy_img = Image.new("RGB", (1, 1), "white")
        draw = ImageDraw.Draw(dummy_img)

        lines = text.split("\n") if text.strip() else [""]
        font_file = print_settings.font
        spacing_factor = 0.1  # 10% of font size for spacing

        candidate_font_size = print_settings.font_size
        max_font_size = 300
        best_font_size = candidate_font_size
        best_metrics = None

        while candidate_font_size < max_font_size:
            try:
                font = ImageFont.truetype(font_file, candidate_font_size)
            except Exception as e:
                print(
                    f"[ERROR] Could not load font '{font_file}' "
                    f"at size {candidate_font_size}: {e}. Using default font."
                )
                font = ImageFont.load_default()

            # Font metrics
            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * candidate_font_size) if len(lines) > 1 else 0

            # Calculate total height needed
            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)

            # We only check the height constraint here
            if total_text_height <= allowed_height:
                # Now find the max line width
                max_line_width = 0
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    line_width = bbox[2] - bbox[0]
                    max_line_width = max(max_line_width, line_width)

                best_font_size = candidate_font_size
                best_metrics = (max_line_width, total_text_height, line_height, inter_line)
                candidate_font_size += 1
            else:
                break

        # If no suitable size was found, use the original font size
        if best_metrics is None:
            best_font_size = print_settings.font_size
            try:
                font = ImageFont.truetype(font_file, best_font_size)
            except Exception as e:
                print(f"[ERROR] Could not load font '{font_file}' at size {best_font_size}: {e}. Using default font.")
                font = ImageFont.load_default()

            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * best_font_size) if len(lines) > 1 else 0

            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)

            max_line_width = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

            best_metrics = (max_line_width, total_text_height, line_height, inter_line)
        else:
            # Recreate the font with the best size to measure final width accurately
            try:
                font = ImageFont.truetype(font_file, best_font_size)
            except Exception as e:
                print(f"[ERROR] Could not load font '{font_file}' at size {best_font_size}: {e}. Using default font.")
                font = ImageFont.load_default()

            # Re-measure width with that final best size
            max_line_width = 0
            lines = text.split("\n") if text.strip() else [""]
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

            # Update the best_metrics
            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * best_font_size) if len(lines) > 1 else 0
            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)
            best_metrics = (max_line_width, total_text_height, line_height, inter_line)

        max_line_width, total_text_height, _, _ = best_metrics
        return max_line_width, total_text_height

    @staticmethod
    def generate_qr(part: Dict[str, Any], print_settings: PrintSettings) -> Image.Image:
        """
        Generate a QR code image using the part's unique identifier.
        """
        qr_data = getattr(part, "id", None) or part.get("id", "UNKNOWN")
        qr_image = qrcode.make(str(qr_data))

        # If there's a specified qr_size, resize
        if hasattr(print_settings, "qr_size") and print_settings.qr_size is not None:
            qr_image = qr_image.resize(
                (print_settings.qr_size, print_settings.qr_size),
                Image.Resampling.LANCZOS
            )
        return qr_image

    @staticmethod
    def compute_label_len_mm_for_text_and_qr(
        text_width_px: int,
        margin_px: int,
        dpi: int,
        qr_width_px: int = 0
    ) -> float:
        """
        Given the measured text width (in pixels), optional QR width (in pixels),
        and margin (in pixels), compute the total label length in mm.
        """
        total_width_px = qr_width_px + margin_px + text_width_px + margin_px
        return (total_width_px / dpi) * 25.4  # px -> mm

    @staticmethod
    def finalize_label_width_px(
        label_len_mm: float,
        print_settings: PrintSettings,
        scaling_factor: float = 1.1
    ) -> int:
        """
        Converts a label length (in mm) to a final pixel width, applying
        a scaling factor to compensate for printing shrinkage.
        """
        return int((label_len_mm * scaling_factor / 25.4) * print_settings.dpi)

    @staticmethod
    def generate_text_label(
        text: str,
        print_settings: PrintSettings,
        allowed_width: int,
        allowed_height: int
    ) -> Image.Image:
        """
        Generate a text label image that scales its font size to fit within the allowed area.
        Uses the font's ascent + descent to avoid clipping descenders.
        Centers the resulting text block in the final image.
        """
        dummy_img = Image.new("RGB", (1, 1), "white")
        draw = ImageDraw.Draw(dummy_img)

        lines = text.split("\n") if text.strip() else [""]
        font_file = print_settings.font
        spacing_factor = 0.1  # 10% of font size for spacing

        candidate_font_size = print_settings.font_size
        max_font_size = 300
        best_font_size = candidate_font_size
        best_metrics = None

        while candidate_font_size < max_font_size:
            try:
                font = ImageFont.truetype(font_file, candidate_font_size)
            except Exception as e:
                print(
                    f"[ERROR] Could not load font '{font_file}' at size {candidate_font_size}: {e}. "
                    f"Using default font."
                )
                font = ImageFont.load_default()

            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * candidate_font_size) if len(lines) > 1 else 0

            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)

            # Measure max line width
            max_line_width = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

            # Check if this fits in allowed_width, allowed_height
            if max_line_width <= allowed_width and total_text_height <= allowed_height:
                best_font_size = candidate_font_size
                best_metrics = (max_line_width, total_text_height, line_height, inter_line)
                candidate_font_size += 1
            else:
                break

        # If we never updated best_metrics, revert to the original font size
        if best_metrics is None:
            best_font_size = print_settings.font_size
            try:
                font = ImageFont.truetype(font_file, best_font_size)
            except Exception as e:
                print(f"[ERROR] Could not load font '{font_file}' at size {best_font_size}: {e}. Using default font.")
                font = ImageFont.load_default()

            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * best_font_size) if len(lines) > 1 else 0

            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)

            max_line_width = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

            best_metrics = (max_line_width, total_text_height, line_height, inter_line)
        else:
            # Recreate the font at the best found size
            try:
                font = ImageFont.truetype(font_file, best_font_size)
            except Exception as e:
                print(f"[ERROR] Could not load font '{font_file}' at size {best_font_size}: {e}. Using default font.")
                font = ImageFont.load_default()

            # Re-check final width
            max_line_width = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)

            ascent, descent = font.getmetrics()
            line_height = ascent + descent
            inter_line = math.ceil(spacing_factor * best_font_size) if len(lines) > 1 else 0
            total_text_height = (line_height * len(lines)) + inter_line * (len(lines) - 1)
            best_metrics = (max_line_width, total_text_height, line_height, inter_line)

        max_line_width, total_text_height, line_height, inter_line = best_metrics

        # Create the text block
        text_block = Image.new("RGB", (max_line_width, total_text_height), "white")
        draw_block = ImageDraw.Draw(text_block)

        y_cursor = 0
        for i, line in enumerate(lines):
            draw_block.text((0, y_cursor), line, font=font, fill=print_settings.text_color)
            y_cursor += line_height
            if i < len(lines) - 1:
                y_cursor += inter_line

        # Center this text block in the final image
        final_img = Image.new("RGB", (allowed_width, allowed_height), "white")
        x_offset = (allowed_width - max_line_width) // 2
        y_offset = (allowed_height - total_text_height) // 2
        final_img.paste(text_block, (x_offset, y_offset))

        return final_img

    @staticmethod
    def generate_combined_label(
        part: Dict[str, Any],
        print_settings: PrintSettings,
        custom_text: Optional[str] = None
    ) -> Image.Image:
        """
        Generate a combined label with a QR code and text. If label_len is not set,
        we auto-calculate the label length in mm based on the text size + QR code size
        with a small margin.
        """
        dpi = print_settings.dpi
        available_height_pixels = LabelService.get_available_height_pixels(print_settings)

        # Decide on the text
        if custom_text is None:
            if custom_text is None:
                custom_text = part.part_number or part.part_name

        # Calculate the QR code size
        qr_scale_factor = getattr(print_settings, "qr_scale", 0.99)
        qr_size_px = int(available_height_pixels * qr_scale_factor)

        # We'll use a 5% margin around the content
        margin_fraction = 0.05
        margin_pixels = int(margin_fraction * available_height_pixels)

        # If label_len is None, auto-calculate based on text + QR width
        if print_settings.label_len is None:
            # 1) Measure text size given the allowed height
            text_width_px, _ = LabelService.measure_text_size(
                text=custom_text,
                print_settings=print_settings,
                allowed_height=available_height_pixels
            )
            # 2) Compute the label length in mm (text + QR + margins)
            label_len_mm = LabelService.compute_label_len_mm_for_text_and_qr(
                text_width_px=text_width_px,
                margin_px=margin_pixels,
                dpi=dpi,
                qr_width_px=qr_size_px
            )
        else:
            # Otherwise, just use the provided label_len
            label_len_mm = float(print_settings.label_len)

        # Convert mm -> final px (with a scaling factor for shrinkage)
        total_label_width_px = LabelService.finalize_label_width_px(
            label_len_mm=label_len_mm,
            print_settings=print_settings,
            scaling_factor=1.1
        )

        # Create the QR code image
        qr_image = LabelService.generate_qr(part, print_settings)
        qr_image = ImageOps.fit(qr_image, (qr_size_px, qr_size_px), Image.Resampling.LANCZOS)

        # Create a blank canvas for the label
        combined_img = Image.new('RGB', (total_label_width_px, available_height_pixels), 'white')

        # Paste the QR code, centered vertically
        qr_y = (available_height_pixels - qr_size_px) // 2
        combined_img.paste(qr_image, (0, qr_y))

        # Now we know how much space remains for text
        qr_total_width = qr_size_px + margin_pixels
        remaining_text_width = max(1, total_label_width_px - qr_total_width)

        # Generate the text label image
        text_img = LabelService.generate_text_label(
            text=custom_text,
            print_settings=print_settings,
            allowed_width=remaining_text_width,
            allowed_height=available_height_pixels
        )

        # Center the text vertically in the remaining area
        text_x = qr_total_width
        text_y = (available_height_pixels - text_img.height) // 2
        combined_img.paste(text_img, (text_x, text_y))

        # Rotate if needed (e.g., 90 degrees)
        rotated_img = combined_img.rotate(90, expand=True)
        return rotated_img

    # -------------------------------------------------------------------
    # EXAMPLE: A text-only print method that reuses the same dimension logic
    # -------------------------------------------------------------------
    @staticmethod
    def print_text_label(text: str, print_settings: PrintSettings) -> Image.Image:
        """
        Example text-only label. If label_len is not set, auto-calculate the label
        length in mm based on the text width plus margins. Then generate the final
        text image.
        """
        dpi = print_settings.dpi
        available_height_pixels = LabelService.get_available_height_pixels(print_settings)

        margin_fraction = 0.05
        margin_pixels = int(margin_fraction * available_height_pixels)

        if print_settings.label_len is None:
            # Measure text size for the given height
            text_width_px, _ = LabelService.measure_text_size(
                text=text,
                print_settings=print_settings,
                allowed_height=available_height_pixels
            )
            # Convert to mm with margins
            label_len_mm = LabelService.compute_label_len_mm_for_text_and_qr(
                text_width_px=text_width_px,
                margin_px=margin_pixels,
                dpi=dpi,
                qr_width_px=0  # no QR code in text-only label
            )
        else:
            label_len_mm = float(print_settings.label_len)

        # Convert mm -> final px (with a scaling factor)
        total_label_width_px = LabelService.finalize_label_width_px(
            label_len_mm=label_len_mm,
            print_settings=print_settings,
            scaling_factor=1.1
        )

        # Generate the text label
        text_label_img = LabelService.generate_text_label(
            text=text,
            print_settings=print_settings,
            allowed_width=total_label_width_px,
            allowed_height=available_height_pixels
        )

        # Rotate if needed
        rotated_label_img = text_label_img.rotate(90, expand=True)

        # In practice, you'd send this to your printer. For now, return the image.
        return rotated_label_img
````

## File: MakerMatrix/services/location_service.py
````python
from typing import Any, Optional, Dict, List, Set
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from MakerMatrix.models.models import LocationModel, LocationQueryModel, engine, PartModel
from MakerMatrix.repositories.location_repositories import LocationRepository
from MakerMatrix.database.db import get_session
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from MakerMatrix.schemas.location_delete_response import LocationDeleteResponse


class LocationService:
    location_repo = LocationRepository(engine)

    @staticmethod
    def get_all_locations() -> List[LocationModel]:
        session = next(get_session())
        try:
            return LocationService.location_repo.get_all_locations(session)
        except Exception as e:
            raise ValueError(f"Failed to retrieve all locations: {str(e)}")

    @staticmethod
    def get_location(location_query: LocationQueryModel) -> Optional[LocationModel]:
        session = next(get_session())
        try:
            location = LocationService.location_repo.get_location(session, location_query)
            if location:
                return location

        except ResourceNotFoundError as rnfe:
            raise rnfe
        except Exception as e:
            raise ValueError(f"Failed to retrieve location: {str(e)}")

    @staticmethod
    def add_location(location_data: Dict[str, Any]) -> LocationModel:
        session = next(get_session())
        try:
            return LocationService.location_repo.add_location(session, location_data)
        except Exception as e:
            raise ValueError(f"Failed to add location: {str(e)}")

    @staticmethod
    def update_location(location_id: str, location_data: Dict[str, Any]) -> LocationModel:
        """
        Update a location's fields. This method can update any combination of name, description, parent_id, and location_type.
        
        Args:
            location_id: The ID of the location to update
            location_data: Dictionary containing the fields to update
            
        Returns:
            LocationModel: The updated location model
            
        Raises:
            ResourceNotFoundError: If the location or parent location is not found
        """
        session = next(get_session())
        try:
            return LocationService.location_repo.update_location(session, location_id, location_data)
        except ResourceNotFoundError as rnfe:
            raise rnfe  # Re-raise the ResourceNotFoundError to be handled by the route
        except Exception as e:
            raise ValueError(f"Failed to update location: {str(e)}")

    @staticmethod
    def get_location_details(location_id: str) -> dict:
        """
        Get detailed information about a location, including its children.

        Args:
            location_id (str): The ID of the location to get details for.

        Returns:
            dict: A dictionary containing the location details and its children in the standard response format.
        """
        try:
            with Session(engine) as session:
                return LocationRepository.get_location_details(session, location_id)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error retrieving location details: {str(e)}",
                "data": None
            }

    @staticmethod
    def get_location_path(location_id: str) -> Dict[str, Any]:
        """Get the full path from a location to its root.
        
        Args:
            location_id: The ID of the location to get the path for
            
        Returns:
            A dictionary containing the location path with parent references
            
        Raises:
            ResourceNotFoundError: If the location is not found
        """
        session = next(get_session())
        try:
            path = LocationRepository.get_location_path(session, location_id)
            return {
                "status": "success",
                "message": f"Location path retrieved for location {location_id}",
                "data": path
            }
        except ResourceNotFoundError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error retrieving location path: {str(e)}")

    @staticmethod
    def preview_location_delete(location_id: str) -> dict[str, Any]:
        session = next(get_session())
        try:
            # Get all affected locations (including children) This should always return at LEAST 1, if not the location does not exist
            affected_locations = LocationService.location_repo.get_location_hierarchy(session, location_id)

            if not affected_locations:
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Location with ID {location_id} not found",
                    data=None)

            # Get all affected parts
            affected_parts_count = LocationService.location_repo.get_affected_part_ids(session, affected_locations[
                'affected_location_ids'])
            location_response = LocationDeleteResponse(
                location_ids_to_delete=affected_locations['affected_location_ids'],
                affected_parts_count=len(affected_parts_count),
                affected_locations_count=len(affected_locations['affected_location_ids']),
                location_hierarchy=affected_locations['hierarchy']).model_dump()
            return location_response

        except ResourceNotFoundError as rnfe:
            raise rnfe

    @staticmethod
    def get_parts_effected_locations(location_id: str):
        return LocationService.location_repo.get_parts_effected_locations(location_id)

    @staticmethod
    def delete_location(location_id: str) -> Dict:
        session = next(get_session())

        query_model = LocationQueryModel(id=location_id)
        location = LocationRepository.get_location(session, location_query=query_model)

        if not location:
            return {
                "status": "error",
                "message": f"Location {location_id} not found",
                "data": None
            }

        # Delete location and its children
        LocationRepository.delete_location(session, location)

        # Debug: Verify parts with NULL location_id
        orphaned_parts = session.query(PartModel).filter(PartModel.location_id == None).all()
        print(f"Orphaned Parts: {orphaned_parts}")

        return {
            "status": "success",
            "message": f"Deleted location_id: {location_id} and its children",
            "data": {
                "deleted_location_name": location.name,
                "deleted_location_id": location_id,
            }
        }

    @staticmethod
    def delete_all_locations():
        session = next(get_session())
        return LocationService.location_repo.delete_all_locations(session)

    @staticmethod
    def cleanup_locations() -> dict:
        """
        Clean up locations by removing those with invalid parent IDs and their descendants.
        
        Returns:
            dict: A dictionary containing the cleanup results in the standard response format
        """
        try:
            with Session(engine) as session:
                return LocationRepository.cleanup_locations(session)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during location cleanup: {str(e)}",
                "data": None
            }

    @staticmethod
    def preview_delete(location_id: str) -> dict:
        """
        Preview what will be affected when deleting a location.
        
        Args:
            location_id: The ID of the location to preview deletion for
            
        Returns:
            dict: A dictionary containing the preview information in the standard response format
        """
        try:
            with Session(engine) as session:
                return LocationRepository.preview_delete(session, location_id)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generating delete preview: {str(e)}",
                "data": None
            }
````

## File: MakerMatrix/services/part_service.py
````python
import logging
from http.client import HTTPException
from typing import List, Optional, Any, Dict, Coroutine

from pydantic import ValidationError
from sqlalchemy import select
from sqlmodel import Session
from typing import Optional, TYPE_CHECKING

from MakerMatrix.models.models import CategoryModel, LocationQueryModel, AdvancedPartSearch
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError, PartAlreadyExistsError
from MakerMatrix.repositories.parts_repositories import PartRepository, handle_categories
from MakerMatrix.models.models import PartModel, UpdateQuantityRequest, GenericPartQuery
from MakerMatrix.models.models import engine  # Import the engine from db.py
from MakerMatrix.database.db import get_session
from MakerMatrix.schemas.part_create import PartUpdate
from MakerMatrix.services.category_service import CategoryService
from MakerMatrix.services.location_service import LocationService

if TYPE_CHECKING:
    from MakerMatrix.models.models import PartModel  # Only imports for type checking, avoiding circular import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PartService:
    # Initialize a part repository instance
    part_repo = PartRepository(engine)
    session = next(get_session())

    #####
    @staticmethod
    def get_part_by_details(
            part_id: Optional[str] = None,
            part_number: Optional[str] = None,
            part_name: Optional[str] = None
    ) -> Optional[dict]:
        """
        Determine which parameter is provided and call the appropriate repository method.
        Returns the part as a dict, or None if not found.
        """
        session = next(get_session())
        try:
            found_part = None
            if part_id:
                found_part = PartService.part_repo.get_part_by_id(session, part_id)
            elif part_number:
                found_part = PartService.part_repo.get_part_by_part_number(session, part_number)
            elif part_name:
                found_part = PartService.part_repo.get_part_by_name(session, part_name)
            else:
                raise ValueError("At least one of part_id, part_number, or part_name must be provided.")

            return found_part.to_dict() if found_part else None

        except Exception as e:
            logger.error(f"Failed to get part by details: {e}")
            return None


    @staticmethod
    def update_quantity_service(
            new_quantity: int,
            manufacturer_pn: Optional[str] = None,
            part_number: Optional[str] = None,
            part_id: Optional[str] = None
    ) -> bool:
        """
        Update the quantity of a part based on part_id, part_number, or manufacturer_pn.
        Returns True if the update was successful, False otherwise.
        """
        session = next(get_session())
        try:
            # Attempt to find the part using the provided identifier
            found_part = None
            if part_id:
                found_part = PartService.part_repo.get_part_by_id(session, part_id)
            elif part_number:
                found_part = PartService.part_repo.get_part_by_part_number(session, part_number)
            elif manufacturer_pn:
                # Example method if it exists in your repository:
                found_part = PartService.part_repo.get_part_by_manufacturer_pn(session, manufacturer_pn)
            else:
                raise ValueError("At least one of part_id, part_number, or manufacturer_pn must be provided.")

            if not found_part:
                logger.error("Part not found using provided details.")
                return False

            # Update the quantity using a hypothetical repo method
            PartService.part_repo.update_quantity(session, found_part.id, new_quantity)
            logger.info(f"Updated quantity for part '{found_part.part_name}' to {new_quantity}.")
            return True

        except Exception as e:
            logger.error(f"Failed to update quantity: {e}")
            raise

    @staticmethod
    def delete_part(part_id: str) -> Dict[str, Any]:
        """
        Delete a part by its ID using the repository.
        Returns a structured response dictionary with deleted part info.
        """
        session = next(get_session())
        try:
            # Ensure the part exists before deletion
            part = PartService.part_repo.get_part_by_id(session, part_id)

            if not part:
                raise ResourceNotFoundError(
                    status="error",
                    message=f"Part with ID '{part_id}' not found.",
                    data=None
                )

            # Perform deletion
            deleted_part = PartService.part_repo.delete_part(session, part_id)

            return {
                "status": "success",
                "message": f"Part with ID '{part_id}' was deleted.",
                "data": deleted_part.model_dump()
            }

        except ResourceNotFoundError as rnfe:
            raise rnfe  # Propagate known error

        except Exception as e:
            logger.error(f"Failed to delete part {part_id}: {e}")
            raise ValueError(f"Failed to delete part {part_id}: {str(e)}")

    @staticmethod
    def dynamic_search(search_term: str) -> Any:
        """
        Perform a dynamic search on parts using part_repo.
        """
        session = next(get_session())
        try:
            return PartService.part_repo.dynamic_search(session, search_term)
        except Exception as e:
            logger.error(f"Error performing dynamic search: {e}")
            return {"error": "An error occurred while searching."}

    @staticmethod
    def clear_all_parts() -> Any:
        """
        Clear all parts from the database using the part_repo.
        """
        session = next(get_session())
        try:
            return PartService.part_repo.clear_all_parts(session)
        except Exception as e:
            logger.error(f"Failed to clear all parts: {e}")
            return None


    #####

    @staticmethod
    def add_part(part_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new part to the database after ensuring that if a location is provided,
        it exists. Categories are created/retrieved before creating the part.
        """
        session = next(get_session())
        try:
            # Validate required fields
            if not part_data.get("part_name"):
                raise ValueError("Part name is required")

            # Check if the part already exists by its name
            part_exists = PartRepository.get_part_by_name(session, part_data["part_name"])
            if part_exists:
                raise PartAlreadyExistsError(
                    status="error",
                    message=f"Part with name '{part_data['part_name']}' already exists",
                    data=part_exists.model_dump()
                )

            # Verify that the location exists, but only if a location_id is provided
            if part_data.get("location_id"):
                location = LocationService.get_location(LocationQueryModel(id=part_data["location_id"]))
                if not location:
                    raise ResourceNotFoundError(
                        status="error",
                        message=f"Location with id '{part_data['location_id']}' does not exist.",
                        data=None
                    )

            try:
                # Handle categories first
                category_names = part_data.pop("category_names", [])
                categories = []

                if category_names:
                    for name in category_names:
                        # Try to get existing category
                        category = session.exec(
                            select(CategoryModel).where(CategoryModel.name == name)
                        ).first()

                        if not category:
                            # Create new category if it doesn't exist
                            category = CategoryModel(name=name)
                            session.add(category)
                            session.flush()  # Flush to get the ID but don't commit yet

                        categories.append(category)

                part_data["categories"] = categories
                # Create the part with the prepared categories
                new_part = PartModel(**part_data)
                #new_part.categories = categories

                # Add the part via repository
                part_obj = PartRepository.add_part(session, new_part)
                return {
                    "status": "success",
                    "message": "Part added successfully",
                    "data": part_obj.to_dict()
                }
            except Exception as e:
                logger.error(f"Failed to create part: {e}")
                raise ValueError(f"Failed to create part: {e}")

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def is_part_name_unique(part_name: str) -> bool:
        """
        Check if the part name is unique.

        Args:
            part_name (str): The name of the part to be checked.

        Returns:
            bool: True if the part name is unique, False otherwise.
        """
        return PartService.part_repo.is_part_name_unique(part_name)

    @staticmethod
    def get_part_by_part_number(part_number: str) -> dict[str, str | dict[str, Any]] | None:
        identifier = "part number"
        session = next(get_session())
        part = PartService.part_repo.get_part_by_part_number(session, part_number)
        if part:
            return {
                "status": "success",
                "message": f"Part with {identifier} '{part_number}' found.",
                "data": part.to_dict(),
            }

    @staticmethod
    def get_part_by_part_name(part_name: str) -> dict[str, str | dict[str, Any]] | None:
        """
        Get a part by its part name.

        Args:
            part_name (str): The name of the part to be retrieved.

        Returns:
            dict[str, str | dict[str, Any]] | None: A dictionary containing the status, message, and data of the found part, or None if not found.
        """
        identifier = "part name"
        session = next(get_session())
        part = PartService.part_repo.get_part_by_name(session, part_name)
        if part:
            return {
                "status": "success",
                "message": f"Part with {identifier} '{part_name}' found.",
                "data": part.to_dict(),
            }

    @staticmethod
    def get_part_by_id(part_id: str) -> Dict[str, Any]:
        try:
            # Use the get_session function to get a session
            identifier = "ID"
            session = next(get_session())

            # Fetch part using the repository layer
            part = PartRepository.get_part_by_id(session, part_id)

            if part:
                return {
                    "status": "success",
                    "message": f"Part with {identifier} '{part_id}' found.",
                    "data": part.to_dict(),
                }

            raise ResourceNotFoundError(
                status="error",
                message=f"Part with {identifier} '{part_id}' not found.",
                data=None
            )

        except ResourceNotFoundError as rnfe:
            raise rnfe

    @staticmethod
    def get_part_counts() -> Dict[str, int]:
        try:
            session = next(get_session())
            total_parts = PartRepository.get_part_counts(session)

            return {
                "status": "success",
                "message": "Total part count retrieved successfully.",
                "total_parts": total_parts
            }
        except Exception as e:
            raise Exception(f"Error retrieving part counts: {str(e)}")

    @staticmethod
    def get_all_parts(page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        try:
            session = next(get_session())

            # Fetch parts using the repository
            parts = PartRepository.get_all_parts(session=session, page=page, page_size=page_size)
            total_parts = PartRepository.get_part_counts(session)

            if parts:
                return {
                    "status": "success",
                    "message": f"Retrieved {len(parts)} parts (Page {page}/{(total_parts + page_size - 1) // page_size}).",
                    "data": [part.model_dump() for part in parts],
                    "page": page,
                    "page_size": page_size,
                    "total_parts": total_parts
                }

            raise ResourceNotFoundError(
                status="error",
                message="No parts found.",
                data=None
            )

        except ResourceNotFoundError as rnfe:
            raise rnfe

    @staticmethod
    def get_parts_by_location_id(location_id: str, recursive=False) -> List[Dict]:
        return PartService.part_repo.get_parts_by_location_id(location_id, recursive)

    @staticmethod
    def update_part(part_id: str, part_update: PartUpdate) -> Dict[str, Any]:
        try:
            session = next(get_session())
            part = PartRepository.get_part_by_id(session, part_id)
            if not part:
                raise ResourceNotFoundError(resource="Part", resource_id=part_id)

            # Update only the provided fields
            update_data = part_update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if key == "category_names" and value is not None:
                    # Special handling for categories
                    categories = handle_categories(session, value)
                    part.categories.clear()  # Clear existing categories
                    part.categories.extend(categories)  # Add new categories
                elif hasattr(part, key):
                    try:
                        setattr(part, key, value)
                    except AttributeError as e:
                        print(f"Skipping read-only or problematic attribute '{key}': {e}")

            # Pass the updated part to the repository for the actual update
            updated_part = PartRepository.update_part(session, part)
            if update_data:
                return {"status": "success", "message": "Part updated successfully", "data": updated_part.to_dict()}
            else:
                # TODO: What should we do if no updates were made?
                # What if we return None
                return {"status": "success", "message": "No updates provided", "data": updated_part}

        except ResourceNotFoundError:
            raise
        except Exception as e:
            session.rollback()
            raise ValueError(f"Failed to update part with ID {part_id}: {e}")

    @staticmethod
    def advanced_search(search_params: AdvancedPartSearch) -> Dict[str, Any]:
        """
        Perform an advanced search on parts with multiple filters and sorting options.
        Returns a dictionary containing the search results and metadata.
        """
        session = next(get_session())
        try:
            results, total_count = PartService.part_repo.advanced_search(session, search_params)
            
            return {
                "status": "success",
                "message": "Search completed successfully",
                "data": {
                    "items": [part.to_dict() for part in results],
                    "total": total_count,
                    "page": search_params.page,
                    "page_size": search_params.page_size,
                    "total_pages": (total_count + search_params.page_size - 1) // search_params.page_size
                }
            }
        except Exception as e:
            logger.error(f"Error performing advanced search: {e}")
            return {
                "status": "error",
                "message": f"An error occurred while searching: {str(e)}",
                "data": None
            }

    # def get_part_by_details(part_id: Optional[str] = None, part_number: Optional[str] = None,
    #                         part_name: Optional[str] = None) -> Optional[dict]:
    #     # Determine which parameter is provided and call the appropriate repo method
    #     if part_id:
    #         return PartService.part_repo.get_part_by_id(part_id)
    #     elif part_number:
    #         return PartService.part_repo.get_part_by_part_number(part_number)
    #     elif part_name:
    #         return PartService.part_repo.get_part_by_part_name(part_name)
    #     else:
    #         raise ValueError("At least one of part_id, part_number, or part_name must be provided.")

    # @staticmethod
    # def update_quantity_service(new_quantity: int,
    #                             manufacturer_pn: str = None,
    #                             part_number: str = None,
    #                             part_id: str = None) -> bool:
    #     """
    #     Update the quantity of a part based on part_id, part_number, or manufacturer_pn.
    #     Returns True if the update was successful, False if the part was not found.
    #     """
    #     try:
    #         # Attempt to find the part using the provided identifiers
    #         part = None
    #         _generic_part = GenericPartQuery(part_id=part_id, part_number=part_number, manufacturer_pn=manufacturer_pn)
    #         part, _ = PartService.get_generic_part(_generic_part)
    #
    #         if not part:
    #             logger.error("Part not found using provided details.")
    #             return False
    #
    #         PartService.part_repo.update_quantity(part["part_id"], new_quantity)
    #         logger.info(
    #             f"Updated quantity for part {part.get('part_number', part.get('manufacturer_pn'))} to {new_quantity}.")
    #         return True
    #
    #     except Exception as e:
    #         logger.error(f"Failed to update quantity: {e}")
    #         raise
    #
    # @staticmethod
    # def decrement_count_service(generic_part_query: GenericPartQuery) -> tuple[PartModel | None, Any, Any] | None:
    #     try:
    #         part, part_field = PartService.get_generic_part(generic_part_query)
    #         previous_quantity = part.get('quantity')
    #         if part:
    #             part = PartService.part_repo.decrement_count_repo(part['part_id'])
    #             logger.info(f"Decremented count for {part.get('part_id', part.get("part_id"))}.")
    #             return part, part_field, previous_quantity
    #         else:
    #             logger.error(f"Part not found using provided details.")
    #         return None
    #
    #     except Exception as e:
    #         logger.error(f"Failed to decrement count for {part}: {e}")
    #         return None
    #
    # @staticmethod
    # def get_all_parts() -> List[PartModel]:
    #     try:
    #         return PartService.part_repo.get_all_parts()
    #     except Exception as e:
    #         logger.error(f"Failed to retrieve all parts: {e}")
    #         return []
    #
    # @staticmethod
    # def get_all_parts_paginated(page: int, page_size: int) -> tuple[Any, Any] | list[Any]:
    #     try:
    #         results = PartService.part_repo.get_all_parts_paginated(page=page, page_size=page_size)
    #         return results
    #     except Exception as e:
    #         logger.error(f"Failed to retrieve paginated parts: {e}")
    #         return []
    #
    # @staticmethod
    # def get_total_parts_count() -> int:
    #     try:
    #         return PartService.part_repo.get_total_parts_count()
    #     except Exception as e:
    #         logger.error(f"Failed to retrieve total parts count: {e}")
    #         return 0
    #
    # @staticmethod
    # def get_part_by_id(part_id: str) -> Coroutine[Any, Any, PartModel | None] | None:
    #     try:
    #         return PartService.part_repo.get_part_by_id(part_id)
    #     except Exception as e:
    #         logger.error(f"Failed to retrieve part by ID {part_id}: {e}")
    #         return None
    #
    # @staticmethod

    #

    #
    # @staticmethod
    # def get_parts_paginated(page: int, page_size: int) -> Dict[str, Any]:
    #     try:
    #         parts = PartService.part_repo.get_all_parts_paginated(page=page, page_size=page_size)
    #         total_count = PartService.part_repo.get_total_parts_count()
    #         return {"parts": parts, "page": page, "page_size": page_size, "total": total_count}
    #     except Exception as e:
    #         print(f"Failed to retrieve paginated parts: {e}")
    #         return {"error": str(e)}
    #
    # @staticmethod
    # def add_part(part: PartModel, overwrite: bool = False) -> dict | None:
    #     try:
    #         return PartService.part_repo.add_part(part.dict(), overwrite=overwrite)
    #     except Exception as e:
    #         logger.error(f"Failed to add part {part}: {e}")
    #         return None
    #
    # @staticmethod
    # def delete_part(part_id: str) -> Any | None:
    #     part_exists = PartService.get_part_by_id(part_id)
    #     if not part_exists:
    #         return None
    #     return PartService.part_repo.delete_part(part_id)
    #
    # @staticmethod
    # def dynamic_search(search_term: str):
    #     try:
    #         return PartService.part_repo.dynamic_search(search_term)
    #     except Exception as e:
    #         print(f"Error performing dynamic search: {e}")
    #         return {"error": "An error occurred while searching."}
    #
    # @staticmethod
    # def clear_all_parts():
    #     return PartService.part_repo.clear_all_parts()
    #

    #
    # @staticmethod
    # def preview_delete_location(location_id: str) -> Dict:
    #     # Get all parts affected under this location
    #     parts = PartService.part_repo.get_parts_by_location_id(location_id, recursive=True)
    #     affected_parts_count = len(parts)
    #
    #     # Get all child locations under this location
    #     from MakerMatrix.repositories.location_repositories import LocationRepository
    #     location_repo = LocationRepository()
    #     child_locations = location_repo.get_child_locations(location_id)
    #     affected_children_count = len(child_locations)
    #
    #     return {
    #         "location_id": location_id,
    #         "affected_parts_count": affected_parts_count,
    #         "affected_children_count": affected_children_count,
    #         "parts": parts,
    #         "children": child_locations
    #     }
    #

    #
````

## File: MakerMatrix/services/printer_service.py
````python
from MakerMatrix.lib.print_settings import PrintSettings
from MakerMatrix.models.models import PartModel
from MakerMatrix.repositories.printer_repository import PrinterRepository


class PrinterService:
    """
    This service is called by your routes. It calls into the repository, which in turn
    creates/configures the correct printer driver.
    """

    def __init__(self, printer_repo: PrinterRepository):
        self.printer_repo = printer_repo
        self.printer = self.printer_repo.get_printer()

    async def print_part_name(self, part: PartModel, print_settings: PrintSettings):
        printer = self.printer_repo.get_printer()
        try:
            # Now, we pass the PrintConfig to the printer's print_text_label method.
            return printer.print_text_label(part.part_name, print_settings)
        except Exception as e:
            raise RuntimeError(f"Error printing part name: {e}")

    async def print_text_label(self, text: str, print_settings: PrintSettings):
        printer = self.printer_repo.get_printer()
        try:
            # Now, we pass the PrintConfig to the printer's print_text_label method.
            return printer.print_text_label(text, print_settings)
        except Exception as e:
            raise RuntimeError(f"Error printing text: {e}")

    # async def print_qr_code_with_name(self, label_data: LabelData):
    #     printer = self.printer_repo.get_printer()
    #     try:
    #         # Create a temporary PartModel using LabelData.
    #         part = PartModel(part_number=label_data.part_number, part_name=label_data.part_name)
    #         qr_image = self._generate_qr_code(part)
    #         return printer.print_qr_from_memory(qr_image)
    #     except Exception as e:
    #         raise RuntimeError(f"Error printing QR code with name: {e}")

    async def print_qr_and_text(self, part: PartModel, print_settings: PrintSettings, text: str = None):
        printer = self.printer_repo.get_printer()

        if text:
            if text == "name":
                text = part['data']['part_name']
            elif text == "number":
                text = part['data']['part_number']

        try:

            return printer.print_qr_and_text(
                text=text,
                part=part,
                print_settings=print_settings)

        except Exception as e:
            raise RuntimeError(f"Error printing QR code + text: {e}")

    def load_printer_config(self):
        """
        Reloads the printer configuration and re-imports the driver.
        Useful if the config file is changed at runtime.
        """
        self.printer_repo.load_config()
        self.printer_repo._import_driver()
````

## File: MakerMatrix/services/user_service.py
````python
from MakerMatrix.repositories.user_repository import UserRepository

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
            return {
                "status": "error",
                "message": f"Failed to retrieve users: {str(e)}",
                "data": None
            }
````

## File: MakerMatrix/tests/conftest.py
````python
import pytest
from sqlmodel import SQLModel
from MakerMatrix.models import user_models  # Ensure all models are registered
from MakerMatrix.models.models import engine
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

@pytest.fixture(scope="session", autouse=True)
def init_db():
    # Drop existing tables
    SQLModel.metadata.drop_all(engine)
    # Create tables for all models
    create_db_and_tables()
    # Log tables present after creation
    from sqlalchemy import inspect
    inspector = inspect(engine)
    print('Tables after creation:', inspector.get_table_names())
    # Setup default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    yield
    # Clean up tables after session
    SQLModel.metadata.drop_all(engine)
````

## File: MakerMatrix/tests/printer_config.json
````json
{
  "model": "QL-800",
  "driver": "brother_ql",
  "backend": "network",
  "printer_identifier": "tcp://192.168.1.71",
  "dpi": 300,
  "scaling_factor": 1.1
}
````

## File: MakerMatrix/tests/test_admin_login.py
````python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.main import app
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.scripts.setup_admin import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from MakerMatrix.models.models import engine
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin


client = TestClient(app)

@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()

    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)

    yield  # Let the tests run
    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)
    

def test_admin_login():
    """Test that the admin user can log in."""
    response = client.post(
        "/auth/login",
        data={"username": DEFAULT_ADMIN_USERNAME, "password": DEFAULT_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    
    # Get the token
    token = response_data["access_token"]
    
    # Test that the token works for a protected route
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/parts/get_all_parts", headers=headers)
    assert response.status_code != 401  # Should not be unauthorized
````

## File: MakerMatrix/tests/test_advanced_search.py
````python
import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from MakerMatrix.models.models import PartModel, CategoryModel, LocationModel, AdvancedPartSearch
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.services.part_service import PartService

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="test_data")
def test_data_fixture(session: Session):
    # Create test categories
    categories = [
        CategoryModel(name="Electronics"),
        CategoryModel(name="Mechanical"),
        CategoryModel(name="Tools")
    ]
    for category in categories:
        session.add(category)
    session.commit()

    # Create test locations
    locations = [
        LocationModel(name="Workshop A"),
        LocationModel(name="Storage B"),
        LocationModel(name="Lab C")
    ]
    for location in locations:
        session.add(location)
    session.commit()

    # Create test parts
    parts = [
        PartModel(
            part_name="Arduino Uno",
            part_number="A001",
            description="Microcontroller board",
            quantity=10,
            supplier="Arduino",
            location_id=locations[0].id,
            categories=[categories[0]]
        ),
        PartModel(
            part_name="Stepper Motor",
            part_number="SM001",
            description="NEMA 17 stepper motor",
            quantity=5,
            supplier="Adafruit",
            location_id=locations[1].id,
            categories=[categories[0], categories[1]]
        ),
        PartModel(
            part_name="Screwdriver Set",
            part_number="SD001",
            description="Professional screwdriver set",
            quantity=3,
            supplier="ToolCo",
            location_id=locations[2].id,
            categories=[categories[2]]
        )
    ]
    for part in parts:
        session.add(part)
    session.commit()

    return {
        "categories": categories,
        "locations": locations,
        "parts": parts
    }


def test_search_by_term(session: Session, test_data):
    search_params = AdvancedPartSearch(search_term="Arduino")
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 1
    assert len(results) == 1
    assert results[0].part_name == "Arduino Uno"


def test_search_by_category(session: Session, test_data):
    search_params = AdvancedPartSearch(category_names=["Electronics"])
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 2
    assert len(results) == 2
    assert all("Electronics" in [cat.name for cat in part.categories] for part in results)


def test_search_by_location(session: Session, test_data):
    search_params = AdvancedPartSearch(location_id=test_data["locations"][0].id)
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 1
    assert len(results) == 1
    assert results[0].location_id == test_data["locations"][0].id


def test_search_by_quantity_range(session: Session, test_data):
    search_params = AdvancedPartSearch(min_quantity=5, max_quantity=10)
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 2
    assert len(results) == 2
    assert all(5 <= part.quantity <= 10 for part in results)


def test_search_by_supplier(session: Session, test_data):
    search_params = AdvancedPartSearch(supplier="Arduino")
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 1
    assert len(results) == 1
    assert results[0].supplier == "Arduino"


def test_search_with_sorting(session: Session, test_data):
    search_params = AdvancedPartSearch(sort_by="quantity", sort_order="desc")
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 3
    assert len(results) == 3
    assert results[0].quantity == 10  # Should be highest quantity


def test_search_with_pagination(session: Session, test_data):
    search_params = AdvancedPartSearch(page=1, page_size=2)
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 3
    assert len(results) == 2  # Should only return 2 items per page


def test_search_with_multiple_filters(session: Session, test_data):
    search_params = AdvancedPartSearch(
        search_term="motor",
        category_names=["Electronics"],
        min_quantity=1,
        max_quantity=10
    )
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 1
    assert len(results) == 1
    assert results[0].part_name == "Stepper Motor"


def test_search_with_no_results(session: Session, test_data):
    search_params = AdvancedPartSearch(search_term="NonexistentPart")
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 0
    assert len(results) == 0


def test_search_with_empty_params(session: Session, test_data):
    search_params = AdvancedPartSearch()
    results, total = PartRepository.advanced_search(session, search_params)

    assert total == 3  # Should return all parts
    assert len(results) == 3
````

## File: MakerMatrix/tests/test_auth_centralized.py
````python
import pytest
import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session, select, SQLModel
from MakerMatrix.main import app
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.models.user_models import RoleModel, UserModel, UserRoleLink
from MakerMatrix.database.db import engine
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create database tables and setup default roles and admin user."""
    # Create all tables
    SQLModel.metadata.create_all(engine)
    
    # Create user repository
    user_repo = UserRepository()
    
    # Setup default roles and admin user
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    
    # No teardown needed for tests


@pytest.fixture
def test_role():
    """Create a test role for authentication tests."""
    with Session(engine) as session:
        # Check if role already exists
        role = session.exec(select(RoleModel).where(RoleModel.name == "user")).first()
        if role:
            # Update the role with the necessary permissions
            role.permissions = ["parts:read", "parts:create", "locations:read", "categories:read"]
            session.add(role)
            session.commit()
            session.refresh(role)
        else:
            # Create test role
            role = RoleModel(
                name="user",
                description="Regular user role",
                permissions=["parts:read", "parts:create", "locations:read", "categories:read"]
            )
            session.add(role)
            session.commit()
            session.refresh(role)
        return role


@pytest.fixture
def test_user(test_role):
    """Create a test user for authentication tests."""
    user_repo = UserRepository()
    # Check if test user already exists
    user = user_repo.get_user_by_username("testuser")
    if not user:
        # Create test user
        hashed_password = user_repo.get_password_hash("testpassword")
        user = user_repo.create_user(
            username="testuser",
            email="test@example.com",
            hashed_password=hashed_password,
            roles=["user"]
        )
    return user


@pytest.fixture
def auth_token(test_user):
    """Get an authentication token for the test user."""
    auth_service = AuthService()
    token = auth_service.create_access_token(data={"sub": test_user.username})
    return token


def test_protected_route_without_token():
    """Test that a protected route returns 401 without a token."""
    response = client.get("/parts/get_all_parts")
    assert response.status_code == 401
    assert "Not authenticated" in response.text


def test_protected_route_with_token(auth_token):
    """Test that a protected route works with a valid token."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/parts/get_all_parts", headers=headers)
    # The endpoint might return 200 or 404 depending on whether there are parts in the database
    # We just want to make sure it's not a 401 Unauthorized
    assert response.status_code != 401


def test_login_endpoint():
    """Test that the login endpoint is accessible without authentication."""
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data


def test_public_endpoint():
    """Test that the root endpoint is accessible without authentication."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to MakerMatrix API"}


def test_permission_required_endpoint(auth_token):
    """Test that an endpoint requiring specific permissions works with the right permissions."""
    # Generate a unique part name to avoid conflicts
    unique_part_name = f"Test Part {uuid.uuid4()}"
    
    # This test assumes the test user has the 'parts:create' permission
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.post(
        "/parts/add_part",
        headers=headers,
        json={
            "part_name": unique_part_name,
            "part_number": f"TP-{uuid.uuid4().hex[:8]}",
            "quantity": 10,
            "description": "A test part"
        }
    )
    
    # The endpoint should return 200 OK or 409 Conflict (if the part already exists)
    # We just want to make sure it's not a 401 Unauthorized or 403 Forbidden
    assert response.status_code not in [401, 403]
````

## File: MakerMatrix/tests/test_auth.py
````python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel
from MakerMatrix.main import app
from MakerMatrix.services.auth_service import AuthService
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()

    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)

    yield  # Let the tests run
    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def test_user():
    """Get the admin user for authentication tests."""
    user_repo = UserRepository()
    user = user_repo.get_user_by_username("admin")
    if not user:
        raise ValueError("Admin user not found. Make sure setup_database fixture is running.")
    return user


@pytest.fixture
def auth_token(test_user):
    """Get an authentication token for the test user."""
    auth_service = AuthService()
    token = auth_service.create_access_token(data={"sub": test_user.username})
    return token


def test_protected_route_without_token():
    """Test that a protected route returns 401 without a token."""
    response = client.get("/parts/get_all_parts")
    assert response.status_code == 401
    assert "Not authenticated" in response.text


def test_protected_route_with_token(auth_token):
    """Test that a protected route works with a valid token."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/parts/get_part_counts", headers=headers)
    assert response.status_code == 200


def test_login_endpoint():
    """Test that the login endpoint returns a token."""
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "Admin123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_public_endpoint():
    """Test that the root endpoint is accessible without authentication."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to MakerMatrix API"}
````

## File: MakerMatrix/tests/test_categories.py
````python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.schemas.part_create import PartCreate  # Import PartCreate
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.main import app
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository

client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)

    # Set up the database (tables creation)
    create_db_and_tables()
    
    # Create default roles and admin user
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)

    yield  # Let the tests run

    # Clean up the tables after running the tests
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def admin_token():
    """Get an admin token for authentication."""
    # Login data for the admin user
    login_data = {
        "username": "admin",
        "password": "Admin123!"  # Updated to match the default password in setup_admin.py
    }
    
    # Post to the login endpoint
    response = client.post("/auth/login", json=login_data)
    
    # Check that the login was successful
    assert response.status_code == 200
    
    # Extract and return the access token
    assert "access_token" in response.json()
    return response.json()["access_token"]


def test_add_category(admin_token):
    """Test adding a new category via the API."""
    category_data = {"name": "Test Category", "description": "This is a test category"}
    response = client.post(
        "/categories/add_category/", 
        json=category_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print(f"Response body: {response.json()}")  # Debug log
    assert response.status_code == 200
    
    response_json = response.json()
    assert response_json["status"] == "success"
    assert "Category with name 'Test Category' created successfully" in response_json["message"]
    assert response_json["data"]["name"] == "Test Category"
    assert response_json["data"]["description"] == "This is a test category"
    assert "id" in response_json["data"]


def test_remove_category(admin_token):
    category_data = {"name": "Test Category", "description": "This is a test category"}
    response = client.post(
        "/categories/add_category/", 
        json=category_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    response_json = response.json()
    # Add a category to ensure it exists before attempting to remove it
    category_id = response_json["data"]["id"]

    # Now attempt to remove the category
    remove_response = client.delete(
        "/categories/remove_category", 
        params={"cat_id": category_id},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert remove_response.status_code == 200
    assert remove_response.json()["status"] == "success"


def test_remove_non_existent_category_by_id(admin_token):
    # Attempt to remove a category with a non-existent ID
    response = client.delete(
        "/categories/remove_category", 
        params={"cat_id": "non-existent-id"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert response.json()["status"] == "error"


def test_remove_non_existent_category_by_name(admin_token):
    # Attempt to remove a category with a non-existent name
    response = client.delete(
        "/categories/remove_category", 
        params={"name": "Non-Existent Category"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert response.json()["status"] == "error"


def test_remove_category_without_id_or_name(admin_token):
    # Attempt to remove a category without providing either ID or name
    response = client.delete(
        "/categories/remove_category",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert response.json()["status"] == "error"


def test_delete_all_categories(admin_token):
    # Add a few categories
    client.post(
        "/categories/add_category/", 
        json={"name": "Category 1"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    client.post(
        "/categories/add_category/", 
        json={"name": "Category 2"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Attempt to delete all categories
    response = client.delete(
        "/categories/delete_all_categories",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200

    # Verify that no categories remain
    get_response = client.get(
        "/categories/get_all_categories",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200
    assert len(get_response.json()["data"]["categories"]) == 0


@pytest.fixture
def setup_test_data_category_update(admin_token):
    # Add a category to set up the initial data for testing
    category_data = {"name": "Test Category", "description": "Initial description"}
    add_response = client.post(
        "/categories/add_category/", 
        json=category_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert add_response.status_code == 200
    return add_response.json()["data"]


def test_update_category(admin_token):
    """Test to update a category via the API."""
    # First, add a category
    category_data = {
        "name": "Electronics",
        "description": "Electronic components"
    }
    response = client.post(
        "/categories/add_category", 
        json=category_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    category_id = response.json()["data"]["id"]

    # Now update the category
    update_data = {
        "name": "Electronics",
        "description": "Updated description for electronic components"
    }
    update_response = client.put(
        f"/categories/update_category/{category_id}", 
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_response.status_code == 200
    
    # Verify the update
    get_response = client.get(
        f"/categories/get_category?category_id={category_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200
    updated_category = get_response.json()["data"]
    assert updated_category["description"] == "Updated description for electronic components"


def test_update_category_name(setup_test_data_category_update, admin_token):
    # Retrieve the category ID from the setup
    category_id = setup_test_data_category_update["id"]
    
    # Update the category name
    update_data = {
        "name": "Updated Category Name",
        "description": "Initial description"
    }
    update_response = client.put(
        f"/categories/update_category/{category_id}", 
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert update_response.status_code == 200
    
    # Verify the update
    get_response = client.get(
        f"/categories/get_category?category_id={category_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200
    updated_category = get_response.json()["data"]
    assert updated_category["name"] == "Updated Category Name"


@pytest.fixture
def setup_categories_for_get_categories(admin_token):
    # Add some unique categories for testing
    categories = [
        {"name": "Electronics", "description": "Devices and components related to electronics"},
        {"name": "Mechanical Parts", "description": "Gears, screws, and other mechanical components"},
        {"name": "Software Tools", "description": "Tools and software utilities for development"},
    ]

    added_categories = []
    for category_data in categories:
        response = client.post(
            "/categories/add_category/", 
            json=category_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        added_categories.append(response.json()["data"])
    
    return added_categories


def test_get_category_by_id(setup_categories_for_get_categories, admin_token):
    # Use the first category added in the fixture
    category_id = setup_categories_for_get_categories[0]["id"]
    
    # Get the category by ID
    response = client.get(
        f"/categories/get_category?category_id={category_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Verify the response
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["data"]["id"] == category_id
    assert response_data["data"]["name"] == "Electronics"


def test_get_category_by_name(setup_categories_for_get_categories, admin_token):
    # Use the name of the second category added in the fixture
    category_name = setup_categories_for_get_categories[1]["name"]
    
    # Get the category by name
    response = client.get(
        f"/categories/get_category?name={category_name}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Verify the response
    response_data = response.json()
    assert response_data["status"] == "success"
    assert response_data["data"]["name"] == category_name
    assert response_data["data"]["description"] == "Gears, screws, and other mechanical components"


def test_get_all_categories(admin_token):
    # First test with no categories
    response = client.get(
        "/categories/get_all_categories/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()["data"]["categories"]) == 0
    
    # Add some categories
    categories = [
        {"name": "Category 1", "description": "Description 1"},
        {"name": "Category 2", "description": "Description 2"},
        {"name": "Category 3", "description": "Description 3"},
    ]
    
    for category_data in categories:
        client.post(
            "/categories/add_category/", 
            json=category_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
    
    # Get all categories
    response = client.get(
        "/categories/get_all_categories/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Verify the response
    response_data = response.json()
    assert response_data["status"] == "success"
    assert len(response_data["data"]["categories"]) == 3
````

## File: MakerMatrix/tests/test_integration_create_part.py
````python
import pytest
from fastapi.testclient import TestClient
import os

from MakerMatrix.main import app
from MakerMatrix.scripts.setup_admin import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from MakerMatrix.models.models import engine
from sqlmodel import SQLModel

def get_auth_token(client):
    login_data = {
        "username": DEFAULT_ADMIN_USERNAME,
        "password": DEFAULT_ADMIN_PASSWORD
    }
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    return response.json()["access_token"]

def test_create_part_integration():
    with TestClient(app) as client:
        # Authenticate and get token
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Define part data
        part_data = {
            "part_name": "Test Part",
            "part_number": "TP-001",
            "manufacturer": "Test Manufacturer",
            "quantity": 10,
            "location_id": None,  # Add a real location if needed
            "category_names": ["Test Category"]
        }

        # Create the part
        response = client.post("/parts/add_part", json=part_data, headers=headers)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["data"]["part_name"] == part_data["part_name"]
        assert response_data["data"]["part_number"] == part_data["part_number"]
        assert response_data["data"]["quantity"] == part_data["quantity"]

        # Optionally, fetch the part and check
        get_response = client.get(f"/parts/get_part?part_name={part_data['part_name']}", headers=headers)
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["status"] == "success"
        assert get_data["data"]["part_name"] == part_data["part_name"]
````

## File: MakerMatrix/tests/test_integration_get_all_users.py
````python
import pytest
from fastapi.testclient import TestClient

# Utility: login as admin and get token
def get_admin_token(client):
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

def test_get_all_users_admin():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = get_admin_token(client)
        response = client.get(
            "/users/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert any(user["username"] == "admin" for user in data["data"])

def test_get_all_users_non_admin():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        # Register a non-admin user
        client.post("/users/register", json={
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "testpass",
            "roles": ["user"]
        })
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpass"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        response = client.get(
            "/users/all",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403
        assert "Admin privileges required" in response.text
````

## File: MakerMatrix/tests/test_locations_cleanup.py
````python
import pytest
from fastapi.testclient import TestClient

def admin_token(client):
    login_data = {"username": "admin", "password": "Admin123!"}
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]

# --- CLEANUP AND VALIDATION TESTS ---
def test_cleanup_locations():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        # Add a location
        location = {"name": "ToDelete", "description": "To be cleaned"}
        add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {token}"})
        assert add_resp.status_code == 200
        # Cleanup
        cleanup_resp = client.delete("/locations/delete_all_locations", headers={"Authorization": f"Bearer {token}"})
        assert cleanup_resp.status_code == 200
        assert cleanup_resp.json()["status"] == "success"

def test_location_type_validation():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        # Invalid location (missing name)
        invalid = {"description": "No name"}
        resp = client.post("/locations/add_location", json=invalid, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in [400, 422]
````

## File: MakerMatrix/tests/test_locations_crud.py
````python
import pytest
from fastapi.testclient import TestClient

def admin_token(client):
    login_data = {"username": "admin", "password": "Admin123!"}
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]

# --- CRUD TESTS ---
def test_add_location():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        location = {"name": "Warehouse", "description": "Main warehouse storage"}
        response = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["data"]["name"] == "Warehouse"

def test_get_location_by_id():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        location = {"name": "Warehouse", "description": "Main warehouse storage"}
        add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {token}"})
        loc_id = add_resp.json()["data"]["id"]
        get_resp = client.get(f"/locations/get_location?location_id={loc_id}", headers={"Authorization": f"Bearer {token}"})
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["id"] == loc_id

def test_update_location():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        location = {"name": "Warehouse", "description": "Main warehouse storage"}
        add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {token}"})
        loc_id = add_resp.json()["data"]["id"]
        update = {"name": "Warehouse Updated", "description": "Updated desc"}
        update_resp = client.put(f"/locations/update_location/{loc_id}", json=update, headers={"Authorization": f"Bearer {token}"})
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["name"] == "Warehouse Updated"

def test_delete_location():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        location = {"name": "Warehouse", "description": "Main warehouse storage"}
        add_resp = client.post("/locations/add_location", json=location, headers={"Authorization": f"Bearer {token}"})
        loc_id = add_resp.json()["data"]["id"]
        del_resp = client.delete(f"/locations/delete_location/{loc_id}", headers={"Authorization": f"Bearer {token}"})
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "success"
````

## File: MakerMatrix/tests/test_locations_hierarchy.py
````python
import pytest
from fastapi.testclient import TestClient

def admin_token(client):
    login_data = {"username": "admin", "password": "Admin123!"}
    response = client.post("/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]

# --- HIERARCHY TESTS ---
def test_parent_child_relationships():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        parent = {"name": "Warehouse", "description": "Main warehouse"}
        child = {"name": "Shelf 1", "description": "Shelf in warehouse"}
        parent_resp = client.post("/locations/add_location", json=parent, headers={"Authorization": f"Bearer {token}"})
        parent_id = parent_resp.json()["data"]["id"]
        child["parent_id"] = parent_id
        child_resp = client.post("/locations/add_location", json=child, headers={"Authorization": f"Bearer {token}"})
        assert child_resp.status_code == 200
        assert child_resp.json()["data"]["parent_id"] == parent_id

def test_get_location_path():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        token = admin_token(client)
        parent = {"name": "Warehouse", "description": "Main warehouse"}
        child = {"name": "Shelf 1", "description": "Shelf in warehouse"}
        parent_resp = client.post("/locations/add_location", json=parent, headers={"Authorization": f"Bearer {token}"})
        parent_id = parent_resp.json()["data"]["id"]
        child["parent_id"] = parent_id
        child_resp = client.post("/locations/add_location", json=child, headers={"Authorization": f"Bearer {token}"})
        child_id = child_resp.json()["data"]["id"]
        path_resp = client.get(f"/locations/get_location_path?location_id={child_id}", headers={"Authorization": f"Bearer {token}"})
        assert path_resp.status_code == 200
        path = path_resp.json()["data"]
        assert path[0]["id"] == parent_id
        assert path[-1]["id"] == child_id
````

## File: MakerMatrix/tests/test_mobile_login.py
````python
import pytest
from fastapi.testclient import TestClient
import os
import json

from MakerMatrix.main import app
from MakerMatrix.scripts.setup_admin import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from MakerMatrix.models.models import engine
from sqlmodel import SQLModel

# Ensure test DB is always clean and tables are created for both app and test client
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Remove test DB file if it exists (for file-based SQLite)
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)

def test_mobile_login():
    """Test that the mobile login endpoint works correctly."""
    with TestClient(app) as client:
        # Create login data
        login_data = {
            "username": DEFAULT_ADMIN_USERNAME,
            "password": DEFAULT_ADMIN_PASSWORD
        }
        
        # Send login request
        response = client.post("/auth/login", json=login_data)
        
        # Check response status and structure
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "success"
        assert response_data["message"] == "Login successful"
        assert "access_token" in response_data
        assert "token_type" in response_data
        assert response_data["token_type"] == "bearer"
        
        # Extract token
        token = response_data["access_token"]
        assert token is not None and token != ""
        
        # Test token by accessing a protected route
        headers = {"Authorization": f"Bearer {token}"}
        protected_response = client.get("/parts/get_all_parts", headers=headers)
        
        # Verify we can access protected route with the token
        assert protected_response.status_code != 401  # Not unauthorized
        
        # Test with invalid credentials
        invalid_login = {
            "username": "invalid_user",
            "password": "invalid_password"
        }
        invalid_response = client.post("/auth/login", json=invalid_login)
        assert invalid_response.status_code == 401  # Unauthorized
````

## File: MakerMatrix/tests/test_part_service.py
````python
# add_part_with_categories.py (Updated Test)
import logging
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session
from MakerMatrix.database.db import get_session

from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import CategoryModel, PartModel
from MakerMatrix.models.models import engine
from MakerMatrix.repositories.parts_repositories import PartRepository
from MakerMatrix.schemas.part_create import PartCreate
from MakerMatrix.services.category_service import CategoryService  # Import PartCreate
from MakerMatrix.repositories.user_repository import UserRepository
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
import logging
import uuid

# Suppress SQLAlchemy INFO logs (which include SQL statements)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Use TestClient context manager for all tests
from MakerMatrix.main import app

def admin_token():
    with TestClient(app) as client:
        login_data = {
            "username": "admin",
            "password": "Admin123!"
        }
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        return response.json()["access_token"]

# Update all test functions to use with TestClient(app) as client:
# Example for one test (repeat for all):
def test_get_part_by_name(admin_token):
    with TestClient(app) as client:
        token = admin_token
        tmp_part = setup_part_update_part(token)
        response = client.get(
            f"/parts/get_part?part_name={tmp_part['data']['part_name']}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["data"]["part_name"] == tmp_part["data"]["part_name"]


def test_add_part(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Define the part data to be sent to the API
        part_data = {
            "part_number": "Screw-001",
            "part_name": "Hex Head Screw",
            "quantity": 500,
            "description": "A standard hex head screw",
            "location_id": None,
            "category_names": ["hardware"],
            "supplier": "Acme Hardware",
            "additional_properties": {"material": "steel", "size": "M6"}
        }

        # Make a POST request to the /add_part endpoint
        response = client.post(
            "/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check the response status code
        assert response.status_code == 200

        # Check the response data
        response_data = response.json()
        assert response_data["status"] == "success"
        assert "data" in response_data
        assert response_data["data"]["part_name"] == "Hex Head Screw"
        assert response_data["data"]["part_number"] == "Screw-001"
        assert response_data["data"]["quantity"] == 500


def test_add_existing_part(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Define the part data
        part_data = {
            "part_number": "Screw-001",
            "part_name": "Hex Head Screw",
            "quantity": 500,
            "description": "A standard hex head screw",
            "location_id": None,
            "category_names": ["hardware"],
            "supplier": "Acme Hardware"
        }

        # Add the part initially
        initial_response = client.post(
            "/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert initial_response.status_code == 200

        # Try to add the same part again
        duplicate_response = client.post(
            "/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check that we get a conflict error
        assert duplicate_response.status_code == 409
        # The error message might be in different formats depending on the API implementation
        response_json = duplicate_response.json()
        assert "already exists" in str(response_json).lower()


def test_add_part_with_invalid_data(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Define part data with missing required fields
        part_data = {
            "part_number": "Screw-002",
            # Missing 'part_name' which is required
            "quantity": 100
        }

        # Make a POST request to the /add_part endpoint
        response = client.post(
            "/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check that we get a validation error
        assert response.status_code in [400, 422]  # Either 400 Bad Request or 422 Unprocessable Entity
        # Check for the specific error message about part name being required
        response_json = response.json()
        assert "part name is required" in str(response_json).lower()


def test_add_part_with_categories(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Define part data with multiple categories
        part_data = {
            "part_number": "Tool-001",
            "part_name": "Power Drill",
            "quantity": 10,
            "description": "A cordless power drill",
            "location_id": None,
            "category_names": ["tools", "power tools", "drills"],
            "supplier": "DeWalt",
            "additional_properties": {"voltage": "18V", "type": "cordless"}
        }

        # Add the part
        response = client.post(
            "/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check the response
        assert response.status_code == 200
        response_data = response.json()
        assert "success" in response_data["status"].lower()
        
        # Verify the part was created with the categories
        part_id = response_data["data"]["id"]
        get_response = client.get(
            f"/parts/get_part?part_id={part_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        part_data = get_response.json()["data"]
        # Check that categories exist, but don't assert the exact count as it might vary
        assert "categories" in part_data
        assert len(part_data["categories"]) > 0


def test_add_part_with_invalid_category(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Define part data with an invalid category (number instead of string)
        part_data = {
            "part_number": "Screw-003",
            "part_name": "Invalid Category Screw",
            "quantity": 100,
            "description": "A screw with invalid category",
            "location_id": None,
            "category_names": [123]  # Invalid category type
        }

        # Make the request
        response = client.post(
            "/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check that we get a validation error
        assert response.status_code in [400, 422]  # Either 400 Bad Request or 422 Unprocessable Entity
        # The error message might be in different formats depending on the API implementation
        response_json = response.json()
        assert "error" in str(response_json).lower() or "validation" in str(response_json).lower()


def test_get_part_by_id(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # First, add a part to the database with a known part number
        part_data = PartCreate(
            part_number="Screw-001",
            part_name="Hex Head Screw",
            quantity=500,
            description="A standard hex head screw",
            location_id=None,
            category_names=["hardware"]
        )

        # Make a POST request to add the part to the database
        response = client.post(
            "/parts/add_part", 
            json=part_data.model_dump(),
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        # Extract the part ID from the response
        part_id = response.json()["data"]["id"]

        # Make a GET request to retrieve the part by ID
        get_response = client.get(
            f"/parts/get_part?part_id={part_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check the response status code
        assert get_response.status_code == 200

        # Check the response data
        response_data = get_response.json()
        # Accept either "success" or "found" as valid status values
        assert response_data["status"] in ["success", "found"]
        assert response_data["data"]["id"] == part_id
        assert response_data["data"]["part_name"] == "Hex Head Screw"


def test_get_part_by_invalid_part_id(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Make a GET request to retrieve a part by a non-existent ID
        part_id = "invalid-id"
        get_response = client.get(
            f"/parts/get_part?part_id={part_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check the response status code
        assert get_response.status_code == 404
        # The error message might be in different formats depending on the API implementation
        response_json = get_response.json()
        assert "not found" in str(response_json).lower() or "error" in str(response_json).lower()


def test_get_part_by_part_number(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # First, add a part to the database with a known part number
        part_data = PartCreate(
            part_number="Screw-002",
            part_name="Round Head Screw",
            quantity=300,
            description="A round head screw",
            location_id=None,
            category_names=["tools"]
        )

        # Make a POST request to add the part to the database
        response = client.post(
            "/parts/add_part", 
            json=part_data.model_dump(),
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        # Extract the part number from the response
        part_number = response.json()["data"]["part_number"]

        # Make a GET request to retrieve the part by part number
        get_response = client.get(
            f"/parts/get_part?part_number={part_number}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Check the response status code
        assert get_response.status_code == 200

        # Check the response data
        response_data = get_response.json()
        # Accept either "success" or "found" as valid status values
        assert response_data["status"] in ["success", "found"]
        assert response_data["data"]["part_number"] == part_number
        assert response_data["data"]["part_name"] == "Round Head Screw"


def test_update_existing_part(admin_token):
    with TestClient(app) as client:
        token = admin_token
        # Create a unique part number to avoid conflicts
        unique_part_number = f"PART-{uuid.uuid4().hex[:8]}"
        
        # Define part data with a unique part number - use a dictionary with minimal fields
        part_data = {
            "part_number": unique_part_number,
            "part_name": "Test Hammer",
            "quantity": 100,
            "description": "A test hammer for updating"
        }

        # Make a POST request to add the part to the database
        response = client.post(
            "/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        part_id = response.json()["data"]["id"]

        # Now update the part
        update_data = {
            "part_name": "Updated Test Hammer",
            "quantity": 200,
            "description": "An updated test hammer"
        }

        update_response = client.put(
            f"/parts/update_part/{part_id}", 
            json=update_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 200

        # Verify the update
        get_response = client.get(
            f"/parts/get_part?part_id={part_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 200
        updated_part = get_response.json()["data"]
        assert updated_part["part_name"] == "Updated Test Hammer"
        assert updated_part["quantity"] == 200
        assert updated_part["description"] == "An updated test hammer"


def setup_part_update_part(admin_token):
    with TestClient(app) as client:
        token = admin_token
        part_data = {
            "part_number": "PN001",
            "part_name": "B1239992810A",
            "quantity": 100,
            "description": "A 1k Ohm resistor",
            "supplier": "Supplier A",
            "additional_properties": {
                "color": "brown",
                "material": "carbon film"
            }
        }

        # Add the part
        response = client.post(
            "/parts/add_part", 
            json=part_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        return response.json()
````

## File: MakerMatrix/tests/test_test_model.py
````python
import pytest
from sqlmodel import Session, SQLModel, create_engine
from MakerMatrix.models.models import PartModel, LocationModel, CategoryModel
from sqlmodel import select
import json


# Create an in-memory SQLite database engine for reuse
@pytest.fixture(scope="function")
def engine():
    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)
    return engine


# Create a test fixture for a session
@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


# Test function to verify if we can create and read a part model
def test_create_part(session):
    location = LocationModel(name="Warehouse A", description="Primary warehouse location")
    session.add(location)
    session.commit()
    session.refresh(location)

    part = PartModel(part_number="12345", part_name="Resistor", quantity=100, location_id=location.id)
    session.add(part)
    session.commit()
    session.refresh(part)

    fetched_part = session.get(PartModel, part.id)

    assert fetched_part is not None
    assert fetched_part.part_number == "12345"
    assert fetched_part.location.name == "Warehouse A"

    # Print the part as JSON
    print(fetched_part.model_dump_json(indent=2))


# Test function to verify if we can create and read a location model
def test_create_location(session):
    location = LocationModel(name="Storage Room B", description="Backup storage room")
    session.add(location)
    session.commit()
    session.refresh(location)

    fetched_location = session.get(LocationModel, location.id)

    assert fetched_location is not None
    assert fetched_location.name == "Storage Room B"

    # Print the location as JSON
    print(fetched_location.model_dump_json(indent=2))


# Test function to verify if we can create a category and assign it to a part
def test_create_category_and_assign_to_part(session):
    category = CategoryModel(name="Electronics", description="Electronic components")
    session.add(category)
    session.commit()
    session.refresh(category)

    part = PartModel(part_number="54321", part_name="Capacitor", quantity=200, categories=[category])
    session.add(part)
    session.commit()
    session.refresh(part)

    fetched_part = session.get(PartModel, part.id)

    assert fetched_part is not None
    assert len(fetched_part.categories) > 0
    assert fetched_part.categories[0].name == "Electronics"

    # Print the part with category as JSON
    print(fetched_part.model_dump_json(indent=2))


# Test updating a part's quantity
def test_update_part_quantity(session):
    part = PartModel(part_number="11111", part_name="Inductor", quantity=50)
    session.add(part)
    session.commit()
    session.refresh(part)

    # Update the quantity
    part.quantity = 75
    session.add(part)
    session.commit()
    session.refresh(part)

    fetched_part = session.get(PartModel, part.id)

    assert fetched_part is not None
    assert fetched_part.quantity == 75

    # Print the updated part as JSON
    print(fetched_part.model_dump_json(indent=2))


# Test deleting a location
def test_delete_location(session):
    location = LocationModel(name="Temporary Storage", description="Temporary holding area")
    session.add(location)
    session.commit()
    session.refresh(location)

    # Delete the location
    session.delete(location)
    session.commit()

    fetched_location = session.get(LocationModel, location.id)

    assert fetched_location is None

    # Print the location state as JSON (for demonstration, although it's deleted)
    # The following will raise an AttributeError since fetched_location is None.
    # Uncomment to observe behavior if required:
    # print(fetched_location.model_dump_json(indent=2)) if fetched_location else print("Location deleted.")


# Test function to create nested locations (e.g., Building -> Room -> Desk -> Drawer)
def test_create_nested_locations(session):
    # Create the top-level building
    building = LocationModel(name="Building A", description="Main office building")
    session.add(building)
    session.commit()
    session.refresh(building)

    # Create a few rooms in the building
    room_101 = LocationModel(name="Room 101", description="Conference Room", parent_id=building.id)
    room_102 = LocationModel(name="Room 102", description="Office Room", parent_id=building.id)
    session.add_all([room_101, room_102])
    session.commit()
    session.refresh(room_101)
    session.refresh(room_102)

    # Create a desk inside Room 102
    desk = LocationModel(name="Desk A", description="Manager's Desk", parent_id=room_102.id)
    session.add(desk)
    session.commit()
    session.refresh(desk)

    # Create drawers inside the desk
    drawer_1 = LocationModel(name="Drawer 1", description="Top drawer", parent_id=desk.id)
    drawer_2 = LocationModel(name="Drawer 2", description="Bottom drawer", parent_id=desk.id)
    session.add_all([drawer_1, drawer_2])
    session.commit()
    session.refresh(drawer_1)
    session.refresh(drawer_2)

    # Fetch the entire structure starting from the building
    fetched_building = session.get(LocationModel, building.id)

    assert fetched_building is not None
    assert fetched_building.name == "Building A"

    # Print the entire nested structure as JSON
    from sqlmodel import select

    def serialize_location(location):
        # Recursive function to serialize the location and its children
        serialized = {
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "parent_id": location.parent_id,
            "location_type": location.location_type,

            "children": []
        }
        statement = select(LocationModel).where(LocationModel.parent_id == location.id)
        child_locations = session.exec(statement).all()
        for child in child_locations:
            serialized["children"].append(serialize_location(child))
        return serialized

    building_structure = serialize_location(fetched_building)
    print(json.dumps(building_structure, indent=2))


def test_create_nested_locations_with_categories_and_parts(session):
    # Create the top-level building
    building = LocationModel(name="Building A", description="Main office building")
    session.add(building)
    session.commit()
    session.refresh(building)

    # Create a few rooms in the building
    room_101 = LocationModel(name="Room 101", description="Conference Room", parent_id=building.id)
    room_102 = LocationModel(name="Room 102", description="Office Room", parent_id=building.id)
    session.add_all([room_101, room_102])
    session.commit()
    session.refresh(room_101)
    session.refresh(room_102)

    # Create a desk inside Room 102
    desk = LocationModel(name="Desk A", description="Manager's Desk", parent_id=room_102.id)
    session.add(desk)
    session.commit()
    session.refresh(desk)

    # Create drawers inside the desk
    drawer_1 = LocationModel(name="Drawer 1", description="Top drawer", parent_id=desk.id)
    drawer_2 = LocationModel(name="Drawer 2", description="Bottom drawer", parent_id=desk.id)
    session.add_all([drawer_1, drawer_2])
    session.commit()
    session.refresh(drawer_1)
    session.refresh(drawer_2)

    # Create Categories
    hardware_category = CategoryModel(name="Hardware", description="Mechanical parts like screws, bolts, etc.")
    electronic_components_category = CategoryModel(name="Electronic Components",
                                                   description="Electronic components like resistors and microcontrollers")
    session.add_all([hardware_category, electronic_components_category])
    session.commit()
    session.refresh(hardware_category)
    session.refresh(electronic_components_category)

    # Create Parts
    screw = PartModel(part_number="S1234", part_name="Screw", quantity=500, location_id=drawer_1.id,
                      categories=[hardware_category])
    resistor = PartModel(part_number="R5678", part_name="Resistor", quantity=1000, location_id=drawer_2.id,
                         categories=[electronic_components_category])
    microcontroller = PartModel(part_number="MCU910", part_name="Microcontroller", quantity=50, location_id=desk.id,
                                categories=[electronic_components_category])
    session.add_all([screw, resistor, microcontroller])
    session.commit()
    session.refresh(screw)
    session.refresh(resistor)
    session.refresh(microcontroller)

    # Fetch the entire structure starting from the building
    fetched_building = session.get(LocationModel, building.id)

    assert fetched_building is not None
    assert fetched_building.name == "Building A"

    # Print the entire nested structure with categories and parts as JSON
    def serialize_location(location):
        # Recursive function to serialize the location and its children
        serialized = {
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "parent_id": location.parent_id,
            "children": [],
            "parts": []
        }
        # Add parts in the current location
        part_statement = select(PartModel).where(PartModel.location_id == location.id)
        parts = session.exec(part_statement).all()
        for part in parts:
            serialized["parts"].append({
                "id": part.id,
                "part_number": part.part_number,
                "part_name": part.part_name,
                "quantity": part.quantity,
                "categories": [category.name for category in part.categories]
            })

        # Add child locations
        location_statement = select(LocationModel).where(LocationModel.parent_id == location.id)
        child_locations = session.exec(location_statement).all()
        for child in child_locations:
            serialized["children"].append(serialize_location(child))
        return serialized

    building_structure = serialize_location(fetched_building)
    print(json.dumps(building_structure, indent=2))


def test_create_nested_locations_with_categories_and_parts(session):
    # Create the top-level building
    building = LocationModel(name="Building A", description="Main office building")
    session.add(building)
    session.commit()
    session.refresh(building)

    # Create a few rooms in the building
    room_101 = LocationModel(name="Room 101", description="Conference Room", parent_id=building.id)
    room_102 = LocationModel(name="Room 102", description="Office Room", parent_id=building.id)
    session.add_all([room_101, room_102])
    session.commit()
    session.refresh(room_101)
    session.refresh(room_102)

    # Create a desk inside Room 102
    desk = LocationModel(name="Desk A", description="Manager's Desk", parent_id=room_102.id)
    session.add(desk)
    session.commit()
    session.refresh(desk)

    # Create drawers inside the desk
    drawer_1 = LocationModel(name="Drawer 1", description="Top drawer", parent_id=desk.id)
    drawer_2 = LocationModel(name="Drawer 2", description="Bottom drawer", parent_id=desk.id)
    session.add_all([drawer_1, drawer_2])
    session.commit()
    session.refresh(drawer_1)
    session.refresh(drawer_2)

    # Create Categories
    hardware_category = CategoryModel(name="Hardware", description="Mechanical parts like screws, bolts, etc.")
    electronic_components_category = CategoryModel(name="Electronic Components",
                                                   description="Electronic components like resistors and microcontrollers")
    session.add_all([hardware_category, electronic_components_category])
    session.commit()
    session.refresh(hardware_category)
    session.refresh(electronic_components_category)

    # Create Parts
    screw = PartModel(part_number="S1234", part_name="Screw", quantity=500, location_id=drawer_1.id,
                      categories=[hardware_category])
    resistor = PartModel(part_number="R5678", part_name="Resistor", quantity=1000, location_id=drawer_2.id,
                         categories=[electronic_components_category])
    microcontroller = PartModel(part_number="MCU910", part_name="Microcontroller", quantity=50, location_id=desk.id,
                                categories=[electronic_components_category])
    session.add_all([screw, resistor, microcontroller])
    session.commit()
    session.refresh(screw)
    session.refresh(resistor)
    session.refresh(microcontroller)

    # Fetch the entire structure starting from the building
    fetched_building = session.get(LocationModel, building.id)

    assert fetched_building is not None
    assert fetched_building.name == "Building A"

    # Print the entire nested structure with categories and parts as JSON
    def serialize_location(location):
        # Recursive function to serialize the location and its children
        serialized = {
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "parent_id": location.parent_id,
            "children": [],
            "location_type": location.location_type,
            "parts": []
        }
        # Add parts in the current location
        part_statement = select(PartModel).where(PartModel.location_id == location.id)
        parts = session.exec(part_statement).all()
        for part in parts:
            serialized["parts"].append({
                "id": part.id,
                "part_number": part.part_number,
                "part_name": part.part_name,
                "quantity": part.quantity,
                "categories": [category.name for category in part.categories]
            })

        # Add child locations
        location_statement = select(LocationModel).where(LocationModel.parent_id == location.id)
        child_locations = session.exec(location_statement).all()
        for child in child_locations:
            serialized["children"].append(serialize_location(child))
        return serialized

    building_structure = serialize_location(fetched_building)
    print(json.dumps(building_structure, indent=2))
````

## File: MakerMatrix/tests/test_user_routes_smoke.py
````python
import pytest
from fastapi.testclient import TestClient
from MakerMatrix.main import app

def test_users_all_route_available():
    with TestClient(app) as client:
        # Log in as admin
        login_data = {"username": "admin", "password": "Admin123!"}
        response = client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]
        # Call /users/all
        response = client.get("/users/all", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        assert any(user["username"] == "admin" for user in data["data"])
        print("[DEBUG] /users/all route smoke test passed.")

def test_print_routes():
    from MakerMatrix.main import app
    with TestClient(app) as client:
        print("[DEBUG ROUTES]", [route.path for route in app.routes])
````

## File: MakerMatrix/tests/test_user_service.py
````python
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session
from MakerMatrix.main import app
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.models.models import engine
from MakerMatrix.models.user_models import UserModel, RoleModel, UserCreate, UserUpdate
from passlib.hash import pbkdf2_sha256
from passlib.context import CryptContext
from MakerMatrix.scripts.setup_admin import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

client = TestClient(app)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Set up the database before running tests and clean up afterward."""
    # Create tables
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    create_db_and_tables()
    
    # Create admin user and roles directly
    from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
    from MakerMatrix.repositories.user_repository import UserRepository
    
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def admin_token():
    """Get an admin token for authentication using the mobile login endpoint."""
    # Use the mobile login endpoint which accepts JSON
    login_data = {
        "username": DEFAULT_ADMIN_USERNAME,
        "password": DEFAULT_ADMIN_PASSWORD
    }
    
    response = client.post(
        "/auth/login",
        json=login_data
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    return response.json()["access_token"]


@pytest.fixture
def setup_test_roles(admin_token):
    """Get existing roles or create them if they don't exist."""
    # First, try to get the roles
    roles = []
    role_names = ["admin", "manager", "user"]
    
    for role_name in role_names:
        response = client.get(
            f"/roles/by-name/{role_name}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        if response.status_code == 200:
            # Role exists, add it to the list
            roles.append(response.json()["data"])
        else:
            # Role doesn't exist, create it
            role_data = {
                "name": role_name,
                "description": f"{role_name.capitalize()} role",
                "permissions": ["all"] if role_name == "admin" else 
                              ["read", "write", "update"] if role_name == "manager" else 
                              ["read"]
            }
            
            create_response = client.post(
                "/roles/add_role",
                json=role_data,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert create_response.status_code == 200
            roles.append(create_response.json()["data"])
    
    return roles


@pytest.fixture
def setup_test_user(setup_test_roles, admin_token):
    """Create a test user with roles or get it if it already exists."""
    # First, try to get the user
    response = client.get(
        "/users/by-username/testuser",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code == 200:
        # User exists, return it
        return response.json()["data"]
    
    # User doesn't exist, create it
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123",
        "roles": ["user", "manager"]
    }
    
    create_response = client.post(
        "/users/register", 
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert create_response.status_code == 200
    return create_response.json()["data"]


def test_create_user(setup_test_roles, admin_token):
    """Test user creation with roles."""
    user_data = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "NewPass123",
        "roles": ["user"]
    }
    
    response = client.post(
        "/users/register", 
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "hashed_password" not in data
    assert len(data["roles"]) == 1
    assert data["roles"][0]["name"] == "user"


def test_get_user_by_id(setup_test_user, admin_token):
    """Test retrieving a user by ID."""
    user_id = setup_test_user["id"]
    response = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == user_id
    assert data["username"] == "testuser"
    assert "hashed_password" not in data


def test_get_user_by_username(setup_test_user, admin_token):
    """Test retrieving a user by username."""
    response = client.get(
        "/users/by-username/testuser",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data


def test_update_user(setup_test_user, admin_token):
    """Test updating a user."""
    user_id = setup_test_user["id"]
    update_data = {
        "email": "updated@example.com",
        "roles": ["user"]  # Remove manager role
    }
    
    response = client.put(
        f"/users/{user_id}", 
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == update_data["email"]
    assert len(data["roles"]) == 1
    assert data["roles"][0]["name"] == "user"


def test_update_password(setup_test_user, admin_token):
    """Test updating a user's password."""
    # First login with the test user
    login_data = {
        "username": "testuser",
        "password": "TestPass123"
    }
    login_response = client.post(
        "/auth/login",
        json=login_data
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    access_token = login_response.json()["access_token"]
    
    # Now update the password with the token
    password_data = {
        "current_password": "TestPass123",
        "new_password": "NewPass456"
    }
    
    user_id = setup_test_user["id"]
    response = client.put(
        f"/users/{user_id}/password",
        json=password_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    
    # Try logging in with the new password
    new_login_data = {
        "username": "testuser",
        "password": "NewPass456"
    }
    
    new_login_response = client.post(
        "/auth/login",
        json=new_login_data
    )
    
    assert new_login_response.status_code == 200
    assert "access_token" in new_login_response.json()
    new_access_token = new_login_response.json()["access_token"]


def test_delete_user(setup_test_user, admin_token):
    """Test deleting a user."""
    user_id = setup_test_user["id"]
    
    response = client.delete(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    
    # Verify the user is deleted
    get_response = client.get(
        f"/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 404


def test_create_role(admin_token):
    """Test role creation."""
    role_data = {
        "name": "supervisor",
        "description": "Supervisor role",
        "permissions": ["read", "write"]
    }
    
    response = client.post(
        "/roles/add_role", 
        json=role_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    
    assert data["name"] == role_data["name"]
    assert data["description"] == role_data["description"]
    assert data["permissions"] == role_data["permissions"]


def test_get_role_by_name(setup_test_roles, admin_token):
    """Test retrieving a role by name."""
    response = client.get(
        "/roles/by-name/manager",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "manager"
    assert data["description"] == "Manager with write access"
    assert "write" in data["permissions"]


def test_update_role(setup_test_roles, admin_token):
    """Test updating a role."""
    # Get the role ID
    role_response = client.get(
        "/roles/by-name/user",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    role_id = role_response.json()["data"]["id"]
    
    update_data = {
        "description": "Updated User Role",
        "permissions": ["read", "write"]  # Add write permission
    }
    
    response = client.put(
        f"/roles/{role_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["description"] == update_data["description"]
    assert set(data["permissions"]) == set(update_data["permissions"])


def test_delete_role(setup_test_roles, admin_token):
    """Test deleting a role."""
    # Create a new role to delete
    role_data = {
        "name": "temp_role",
        "description": "Temporary Role",
        "permissions": ["read"]
    }
    
    create_response = client.post(
        "/roles/add_role", 
        json=role_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    role_id = create_response.json()["data"]["id"]
    
    # Delete the role
    response = client.delete(
        f"/roles/{role_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    
    # Verify the role is deleted
    get_response = client.get(
        f"/roles/by-name/temp_role",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 404


def test_invalid_password_format():
    """Test validation for password format."""
    user_data = {
        "username": "badpassuser",
        "email": "badpass@example.com",
        "password": "weak",  # Too short, no uppercase, no digit
        "roles": ["user"]
    }
    
    response = client.post("/users/register", json=user_data)
    assert response.status_code == 422  # Validation error


def test_duplicate_username(setup_test_user, admin_token):
    """Test that duplicate usernames are rejected."""
    user_data = {
        "username": "testuser",  # Same as existing user
        "email": "another@example.com",
        "password": "AnotherPass123",
        "roles": ["user"]
    }
    
    response = client.post(
        "/users/register", 
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    # The API now returns a 200 status code with an error message in the response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "error"
    assert "already exists" in response_data["message"].lower()


def test_invalid_role_assignment():
    """Test that invalid role assignments are rejected."""
    user_data = {
        "username": "invalidroleuser",
        "email": "invalid@example.com",
        "password": "ValidPass123",
        "roles": ["nonexistent_role"]
    }
    
    response = client.post("/users/register", json=user_data)
    
    # The API now returns a 200 status code with an error message in the response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "error"
    assert "role not found" in response_data["message"].lower()
````

## File: MakerMatrix/dependencies.py
````python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
````

## File: MakerMatrix/main.py
````python
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from MakerMatrix.repositories.printer_repository import PrinterRepository
from MakerMatrix.routers import (
    parts_routes, locations_routes, categories_routes, printer_routes,
    utility_routes, auth_routes, user_routes, role_routes
)
from MakerMatrix.services.printer_service import PrinterService
from MakerMatrix.database.db import create_db_and_tables
from MakerMatrix.handlers.exception_handlers import register_exception_handlers
from MakerMatrix.dependencies.auth import secure_all_routes
from MakerMatrix.scripts.setup_admin import setup_default_roles, setup_default_admin
from MakerMatrix.repositories.user_repository import UserRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    # Run the database setup
    create_db_and_tables()
    
    # Set up default roles and admin user
    print("Setting up default roles and admin user...")
    user_repo = UserRepository()
    setup_default_roles(user_repo)
    setup_default_admin(user_repo)
    print("Setup complete!")
    
    yield  # App continues running
    print("Shutting down...")  # If you need cleanup, add it here


# Initialize the FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Register exception handlers
register_exception_handlers(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Define permissions for specific routes
parts_permissions = {
    "/add_part": "parts:create",
    "/update_part/{part_id}": "parts:update",
    "/delete_part": "parts:delete"
}

locations_permissions = {
    "/add_location": "locations:create",
    "/update_location/{location_id}": "locations:update",
    "/delete_location/{location_id}": "locations:delete"
}

categories_permissions = {
    "/add_category/": "categories:create",
    "/update_category/{category_id}": "categories:update",
    "/remove_category": "categories:delete",
    "/delete_all_categories": "categories:delete_all"
}

# Define paths that should be excluded from authentication
auth_exclude_paths = [
    "/login",
    "/refresh",
    "/logout"
]

# Secure routers with authentication
secure_all_routes(parts_routes.router, permissions=parts_permissions)
secure_all_routes(locations_routes.router, permissions=locations_permissions)
secure_all_routes(categories_routes.router, permissions=categories_permissions)
secure_all_routes(printer_routes.router)
secure_all_routes(utility_routes.router)
# Don't secure auth routes - they need to be accessible without authentication
# secure_all_routes(auth_routes.router, exclude_paths=auth_exclude_paths)
secure_all_routes(user_routes.router)
secure_all_routes(role_routes.router)

# Public routes that don't need authentication
public_paths = ["/", "/docs", "/redoc", "/openapi.json"]

# Include routers
app.include_router(parts_routes.router, prefix="/parts", tags=["parts"])
app.include_router(locations_routes.router, prefix="/locations", tags=["locations"])
app.include_router(categories_routes.router, prefix="/categories", tags=["categories"])
app.include_router(printer_routes.router, prefix="/printer", tags=["printer"])
app.include_router(utility_routes.router, prefix="/utility", tags=["utility"])
app.include_router(auth_routes.router, tags=["Authentication"])
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(role_routes.router, prefix="/roles", tags=["Roles"])

@app.get("/")
async def root():
    return {"message": "Welcome to MakerMatrix API"}

if __name__ == "__main__":
    # Load printer config at startup
    try:
        printer_service = PrinterService(PrinterRepository())
        printer_service.load_printer_config()
        print("Printer configuration loaded on startup.")
    except FileNotFoundError:
        print("No config file found. Using default printer configuration.")
    except Exception as e:
        print(f"Error loading configuration: {e}")

    # Start the FastAPI server
    uvicorn.run(app, host='0.0.0.0', port=57891)
````

## File: MakerMatrix/part_inventory.json
````json
{"locations": {"1": {"id": "2333322", "name": "Office", "description": null, "parent_id": null}, "2": {"id": "2333323", "name": "Warehouse", "description": null, "parent_id": null}, "3": {"id": "2333324", "name": "Desk", "description": null, "parent_id": "2333322"}, "4": {"id": "2333325", "name": "Top Drawer", "description": null, "parent_id": "2333324"}}}
````

## File: MakerMatrix/PROJECT_STATUS.md
````markdown
# MakerMatrix Project Status

## Project Overview
MakerMatrix is a Python-based API for managing a maker's inventory system. It provides functionality for managing parts, locations, categories, and printer configurations, with additional features for label generation and utility functions.

## Core Features Status

### 1. Parts Management
- [x] Basic CRUD operations
- [x] Part categorization
- [x] Location tracking
- [x] Advanced search functionality
- [ ] Bulk operations
- [ ] Stock level tracking
- [ ] Low stock alerts
- [ ] Part history/audit trail

### 2. Location Management
- [x] Basic CRUD operations for locations
- [x] Location hierarchy (parent-child relationships)
- [x] Location types (flexible)
- [x] Location path traversal
- [x] Location cleanup for invalid references
- [x] Location delete preview
- [x] Location hierarchy operations
- [x] Error handling for location operations
- [ ] Location capacity tracking
- [ ] Location utilization metrics
- [ ] Location history

### 3. Category Management
- [x] Basic CRUD operations
- [x] Category hierarchy
- [ ] Category statistics
- [ ] Category-based reporting

### 4. Printer Management
- [x] Basic printer configuration
- [x] Label generation
- [ ] Printer status monitoring
- [ ] Print queue management
- [ ] Printer maintenance tracking

### 5. Label Generation
- [x] Basic label generation
- [ ] Custom label templates
- [ ] Batch label printing
- [ ] Label preview
- [ ] Label history

## Technical Infrastructure

### 1. Security
- [x] Authentication system
- [x] Authorization system
- [ ] API key management
- [ ] Security headers
- [ ] SSL/TLS configuration
- [ ] CORS configuration

### 2. Database
- [x] SQLite implementation
- [ ] Database migrations
- [ ] Backup system
- [ ] Data validation
- [ ] Index optimization
- [ ] Connection pooling

### 3. API Features
- [ ] API versioning
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Health check endpoint
- [ ] Error handling improvements
- [ ] Request/Response logging
- [ ] API metrics
- [ ] Rate limiting
- [ ] Pagination

### 4. Monitoring & Logging
- [ ] Application logging
- [ ] Error tracking
- [ ] Performance monitoring
- [ ] Usage analytics
- [ ] System health monitoring
- [ ] Alert system

## User Interface & Integration

### 1. API Endpoints
- [x] Parts endpoints
- [x] Locations endpoints
- [x] Categories endpoints
- [x] Printer endpoints
- [x] Utility endpoints
- [x] Authentication/Authorization endpoints
- [ ] System management endpoints

### 2. Integration Features
- [ ] Webhook support
- [ ] External API integration
- [ ] Import/Export functionality
- [ ] Data synchronization
- [ ] Third-party service integration

## Testing & Quality Assurance

### 1. Testing
- [ ] Unit tests
- [ ] Integration tests
- [ ] End-to-end tests
- [ ] Performance tests
- [ ] Security tests
- [ ] Load tests

### 2. Code Quality
- [x] Code linting
- [x] Code formatting
- [x] Type checking
- [ ] Code coverage
- [x] Documentation
- [ ] Code review process

## Deployment & DevOps

### 1. Deployment
- [ ] Containerization (Docker)
- [ ] CI/CD pipeline
- [ ] Environment configuration
- [ ] Deployment automation
- [ ] Rollback procedures

### 2. Infrastructure
- [ ] Server configuration
- [ ] Load balancing
- [ ] High availability
- [ ] Disaster recovery
- [ ] Backup procedures

## Documentation

### 1. Technical Documentation
- [ ] API documentation
- [ ] Database schema
- [ ] Architecture diagrams
- [ ] Setup instructions
- [ ] Deployment guide
- [ ] Troubleshooting guide

### 2. User Documentation
- [ ] User manual
- [ ] API usage guide
- [ ] Best practices
- [ ] FAQ
- [ ] Troubleshooting guide

## Future Enhancements

### 1. Advanced Features
- [ ] Barcode/QR code support
- [ ] Mobile app integration
- [ ] Advanced reporting
- [ ] Analytics dashboard
- [ ] Machine learning integration
- [ ] Predictive inventory management

### 2. Integration Possibilities
- [ ] E-commerce platforms
- [ ] Supplier APIs
- [ ] Shipping providers
- [ ] Accounting software
- [ ] Project management tools
- [ ] CAD software

## Project Timeline

### Phase 1: Core Features (Current)
- [x] Basic CRUD operations
- [x] Database setup
- [x] Basic API structure
- [x] Security & Authentication

### Phase 2: Enhanced Features
- [ ] Advanced search
- [ ] Bulk operations
- [ ] Reporting
- [ ] User management
- [ ] Advanced security

### Phase 3: Integration & Optimization
- [ ] External integrations
- [ ] Performance optimization
- [ ] Advanced monitoring
- [ ] Mobile support
- [ ] Advanced analytics

## Notes
- Priority should be given to security and authentication features
- Focus on completing core features before adding advanced functionality
- Regular backups and data safety measures should be implemented early
- Documentation should be maintained alongside development
- Testing should be implemented from the beginning
````

## File: MakerMatrix/README.md
````markdown
# MakerMatrix

## Project Overview
MakerMatrix is a Python-based API designed to help makers, hobbyists, and small organizations efficiently manage their inventory systems. Built with FastAPI, it provides a robust backend for tracking parts, organizing locations, managing categories, handling printer configurations, and generating labels. The project aims to streamline inventory workflows, reduce manual errors, and support scalable organization of maker spaces or workshops.

## Features

### Parts Management
- CRUD operations for parts
- Categorization and advanced search
- Location tracking for each part
- (Planned) Bulk operations, stock level tracking, low stock alerts, audit trail

### Location Management
- CRUD operations for locations
- Support for hierarchical (parent-child) locations
- Flexible location types
- Location path traversal and cleanup
- (Planned) Capacity tracking, utilization metrics, location history

### Category Management
- CRUD operations for categories
- Category hierarchy
- (Planned) Category statistics and reporting

### Printer & Label Management
- Basic printer configuration and management
- Label generation for parts and locations
- (Planned) Printer status monitoring, print queue, maintenance tracking
- (Planned) Custom label templates, batch printing, label preview/history

### Security & User Management
- Authentication and authorization system
- (Planned) API key management, advanced security headers, SSL/TLS, CORS
- (Planned) User management and role-based access control

### Technical Infrastructure
- SQLite database with planned migration and backup features
- Modular FastAPI architecture for scalability
- (Planned) API documentation, health checks, logging, metrics, rate limiting
- (Planned) Containerization (Docker), CI/CD, deployment automation

### Integration & Extensibility
- (Planned) Webhook support, external API integration, import/export, data sync
- (Planned) E-commerce, supplier, shipping, accounting, project management, and CAD integrations

### Testing & Quality Assurance
- Code linting, formatting, and type checking
- (Planned) Unit, integration, end-to-end, and performance tests

## Advanced Technical Insights

### Directory Structure & Responsibilities

- **api/**: Integrations with external APIs (e.g., electronics part data enrichment via EasyEDA).
- **models/**: Core data models for parts, users, labels, printers, and requests using Pydantic/SQLModel.
- **routers/**: FastAPI route definitions for all resources (parts, locations, categories, printers, authentication, users, roles, and utilities). Each router maps HTTP requests to service logic and handles validation, error responses, and pagination.
- **services/**: Business logic for each domain (parts, categories, locations, labels, printers, authentication). Services interact with repositories for data access and encapsulate validation, enrichment, and transformation.
- **repositories/**: Database operations and queries for each resource, including custom error handling and complex lookups.
- **parsers/**: Vendor-specific part data parsing and enrichment (e.g., LCSC, Mouser, BoltDepot). Supports extracting and normalizing part details from various sources using custom logic and API calls.
- **scripts/**: Setup scripts such as `setup_admin.py` for initializing default roles and admin users, useful for bootstrapping new deployments.

### Notable Implementation Details

- **Role-based Access Control**: Admin, manager, and user roles are defined with granular permissions, automatically set up on first run.
- **Extensible Part Parsing**: Pluggable parser classes allow enrichment of parts from different suppliers, with the ability to add more vendors easily.
- **Advanced Search**: The parts API supports advanced multi-field search and filtering for efficient inventory queries.
- **Label Generation**: Dynamic label sizing and printer configuration, with future support for batch printing and custom templates.
- **Error Handling**: Centralized exception handling and custom error classes provide robust and user-friendly API responses.
- **User Management**: Scripts and endpoints for user creation, password hashing, and role assignment.
- **Setup & Bootstrapping**: On startup, the database schema is created, and default roles/users are provisioned if missing.

### Planned/Advanced Features

- Bulk part operations, stock level and location capacity tracking, audit trails
- Printer status monitoring, print queue, and maintenance logs
- API key management, advanced security headers, SSL/TLS, and CORS
- API versioning, OpenAPI/Swagger docs, health checks, metrics, rate limiting
- Integration with external APIs and webhooks for synchronization and automation
- Import/export functionality and third-party (e.g., e-commerce, CAD) integrations
- Mobile support and advanced analytics

### Example API Endpoints

- `POST /add_part` - Add a new part to inventory
- `GET /get_part_counts` - Retrieve part counts
- `DELETE /delete_part` - Remove a part by ID, name, or number
- `GET /get_all_parts` - Paginated retrieval of parts
- `PUT /update_part/{part_id}` - Update part details
- `POST /login` - Authenticate user and receive token
- `POST /add_role` - Create a new user role

## Project Ideals & Vision

MakerMatrix is built on the ideals of:
- **Openness**: Open-source, transparent, and extensible for the maker community.
- **Efficiency**: Streamlining inventory and label workflows to save time and reduce errors.
- **Scalability**: Designed for both solo makers and growing organizations.
- **Security**: Multi-user authentication, role-based access, and planned advanced security features.
- **Integration**: Ready for future connections to hardware, web, and mobile interfaces, as well as third-party tools.
- **Community**: Welcoming contributions, feedback, and feature requests to evolve the platform.

## Purpose & Goals
- Provide an open-source, extensible inventory management backend for makers
- Enable efficient organization and tracking of parts and materials
- Support label printing and part identification workflows
- Facilitate secure, multi-user access with roles and permissions
- Serve as a foundation for future integration with hardware, web, and mobile interfaces

## Getting Started
1. Clone the repository
2. Install dependencies (see requirements.txt)
3. Run the FastAPI server: `python main.py` or with Uvicorn
4. Access API endpoints as documented in the routers directory

## Project Status
The project is under active development. Core CRUD features for parts, locations, categories, and printers are implemented. Many advanced features, integrations, and security enhancements are planned. See `PROJECT_STATUS.md` for detailed progress tracking.

## Contributing
Contributions, issues, and feature requests are welcome! Please open an issue or submit a pull request.

## License
This project is licensed under the MIT License.

---

For more details on current progress, features, and roadmap, see `PROJECT_STATUS.md`.
````

## File: venv310/Include/site/python3.12/greenlet/greenlet.h
````
/* -*- indent-tabs-mode: nil; tab-width: 4; -*- */

/* Greenlet object interface */

#ifndef Py_GREENLETOBJECT_H
#define Py_GREENLETOBJECT_H


#include <Python.h>

#ifdef __cplusplus
extern "C" {
#endif

/* This is deprecated and undocumented. It does not change. */
#define GREENLET_VERSION "1.0.0"

#ifndef GREENLET_MODULE
#define implementation_ptr_t void*
#endif

typedef struct _greenlet {
    PyObject_HEAD
    PyObject* weakreflist;
    PyObject* dict;
    implementation_ptr_t pimpl;
} PyGreenlet;

#define PyGreenlet_Check(op) (op && PyObject_TypeCheck(op, &PyGreenlet_Type))


/* C API functions */

/* Total number of symbols that are exported */
#define PyGreenlet_API_pointers 12

#define PyGreenlet_Type_NUM 0
#define PyExc_GreenletError_NUM 1
#define PyExc_GreenletExit_NUM 2

#define PyGreenlet_New_NUM 3
#define PyGreenlet_GetCurrent_NUM 4
#define PyGreenlet_Throw_NUM 5
#define PyGreenlet_Switch_NUM 6
#define PyGreenlet_SetParent_NUM 7

#define PyGreenlet_MAIN_NUM 8
#define PyGreenlet_STARTED_NUM 9
#define PyGreenlet_ACTIVE_NUM 10
#define PyGreenlet_GET_PARENT_NUM 11

#ifndef GREENLET_MODULE
/* This section is used by modules that uses the greenlet C API */
static void** _PyGreenlet_API = NULL;

#    define PyGreenlet_Type \
        (*(PyTypeObject*)_PyGreenlet_API[PyGreenlet_Type_NUM])

#    define PyExc_GreenletError \
        ((PyObject*)_PyGreenlet_API[PyExc_GreenletError_NUM])

#    define PyExc_GreenletExit \
        ((PyObject*)_PyGreenlet_API[PyExc_GreenletExit_NUM])

/*
 * PyGreenlet_New(PyObject *args)
 *
 * greenlet.greenlet(run, parent=None)
 */
#    define PyGreenlet_New                                        \
        (*(PyGreenlet * (*)(PyObject * run, PyGreenlet * parent)) \
             _PyGreenlet_API[PyGreenlet_New_NUM])

/*
 * PyGreenlet_GetCurrent(void)
 *
 * greenlet.getcurrent()
 */
#    define PyGreenlet_GetCurrent \
        (*(PyGreenlet * (*)(void)) _PyGreenlet_API[PyGreenlet_GetCurrent_NUM])

/*
 * PyGreenlet_Throw(
 *         PyGreenlet *greenlet,
 *         PyObject *typ,
 *         PyObject *val,
 *         PyObject *tb)
 *
 * g.throw(...)
 */
#    define PyGreenlet_Throw                 \
        (*(PyObject * (*)(PyGreenlet * self, \
                          PyObject * typ,    \
                          PyObject * val,    \
                          PyObject * tb))    \
             _PyGreenlet_API[PyGreenlet_Throw_NUM])

/*
 * PyGreenlet_Switch(PyGreenlet *greenlet, PyObject *args)
 *
 * g.switch(*args, **kwargs)
 */
#    define PyGreenlet_Switch                                              \
        (*(PyObject *                                                      \
           (*)(PyGreenlet * greenlet, PyObject * args, PyObject * kwargs)) \
             _PyGreenlet_API[PyGreenlet_Switch_NUM])

/*
 * PyGreenlet_SetParent(PyObject *greenlet, PyObject *new_parent)
 *
 * g.parent = new_parent
 */
#    define PyGreenlet_SetParent                                 \
        (*(int (*)(PyGreenlet * greenlet, PyGreenlet * nparent)) \
             _PyGreenlet_API[PyGreenlet_SetParent_NUM])

/*
 * PyGreenlet_GetParent(PyObject* greenlet)
 *
 * return greenlet.parent;
 *
 * This could return NULL even if there is no exception active.
 * If it does not return NULL, you are responsible for decrementing the
 * reference count.
 */
#     define PyGreenlet_GetParent                                    \
    (*(PyGreenlet* (*)(PyGreenlet*))                                 \
     _PyGreenlet_API[PyGreenlet_GET_PARENT_NUM])

/*
 * deprecated, undocumented alias.
 */
#     define PyGreenlet_GET_PARENT PyGreenlet_GetParent

#     define PyGreenlet_MAIN                                         \
    (*(int (*)(PyGreenlet*))                                         \
     _PyGreenlet_API[PyGreenlet_MAIN_NUM])

#     define PyGreenlet_STARTED                                      \
    (*(int (*)(PyGreenlet*))                                         \
     _PyGreenlet_API[PyGreenlet_STARTED_NUM])

#     define PyGreenlet_ACTIVE                                       \
    (*(int (*)(PyGreenlet*))                                         \
     _PyGreenlet_API[PyGreenlet_ACTIVE_NUM])




/* Macro that imports greenlet and initializes C API */
/* NOTE: This has actually moved to ``greenlet._greenlet._C_API``, but we
   keep the older definition to be sure older code that might have a copy of
   the header still works. */
#    define PyGreenlet_Import()                                               \
        {                                                                     \
            _PyGreenlet_API = (void**)PyCapsule_Import("greenlet._C_API", 0); \
        }

#endif /* GREENLET_MODULE */

#ifdef __cplusplus
}
#endif
#endif /* !Py_GREENLETOBJECT_H */
````

## File: venv310/Scripts/activate
````
# This file must be used with "source bin/activate" *from bash*
# You cannot run it directly

deactivate () {
    # reset old environment variables
    if [ -n "${_OLD_VIRTUAL_PATH:-}" ] ; then
        PATH="${_OLD_VIRTUAL_PATH:-}"
        export PATH
        unset _OLD_VIRTUAL_PATH
    fi
    if [ -n "${_OLD_VIRTUAL_PYTHONHOME:-}" ] ; then
        PYTHONHOME="${_OLD_VIRTUAL_PYTHONHOME:-}"
        export PYTHONHOME
        unset _OLD_VIRTUAL_PYTHONHOME
    fi

    # Call hash to forget past commands. Without forgetting
    # past commands the $PATH changes we made may not be respected
    hash -r 2> /dev/null

    if [ -n "${_OLD_VIRTUAL_PS1:-}" ] ; then
        PS1="${_OLD_VIRTUAL_PS1:-}"
        export PS1
        unset _OLD_VIRTUAL_PS1
    fi

    unset VIRTUAL_ENV
    unset VIRTUAL_ENV_PROMPT
    if [ ! "${1:-}" = "nondestructive" ] ; then
    # Self destruct!
        unset -f deactivate
    fi
}

# unset irrelevant variables
deactivate nondestructive

# on Windows, a path can contain colons and backslashes and has to be converted:
if [ "${OSTYPE:-}" = "cygwin" ] || [ "${OSTYPE:-}" = "msys" ] ; then
    # transform D:\path\to\venv to /d/path/to/venv on MSYS
    # and to /cygdrive/d/path/to/venv on Cygwin
    export VIRTUAL_ENV=$(cygpath "D:\Projects\Python Projects\part_inventory_server\venv310")
else
    # use the path as-is
    export VIRTUAL_ENV="D:\Projects\Python Projects\part_inventory_server\venv310"
fi

_OLD_VIRTUAL_PATH="$PATH"
PATH="$VIRTUAL_ENV/Scripts:$PATH"
export PATH

# unset PYTHONHOME if set
# this will fail if PYTHONHOME is set to the empty string (which is bad anyway)
# could use `if (set -u; : $PYTHONHOME) ;` in bash
if [ -n "${PYTHONHOME:-}" ] ; then
    _OLD_VIRTUAL_PYTHONHOME="${PYTHONHOME:-}"
    unset PYTHONHOME
fi

if [ -z "${VIRTUAL_ENV_DISABLE_PROMPT:-}" ] ; then
    _OLD_VIRTUAL_PS1="${PS1:-}"
    PS1="(venv310) ${PS1:-}"
    export PS1
    VIRTUAL_ENV_PROMPT="(venv310) "
    export VIRTUAL_ENV_PROMPT
fi

# Call hash to forget past commands. Without forgetting
# past commands the $PATH changes we made may not be respected
hash -r 2> /dev/null
````

## File: venv310/Scripts/activate.bat
````
@echo off

rem This file is UTF-8 encoded, so we need to update the current code page while executing it
for /f "tokens=2 delims=:." %%a in ('"%SystemRoot%\System32\chcp.com"') do (
    set _OLD_CODEPAGE=%%a
)
if defined _OLD_CODEPAGE (
    "%SystemRoot%\System32\chcp.com" 65001 > nul
)

set VIRTUAL_ENV=D:\Projects\Python Projects\part_inventory_server\venv310

if not defined PROMPT set PROMPT=$P$G

if defined _OLD_VIRTUAL_PROMPT set PROMPT=%_OLD_VIRTUAL_PROMPT%
if defined _OLD_VIRTUAL_PYTHONHOME set PYTHONHOME=%_OLD_VIRTUAL_PYTHONHOME%

set _OLD_VIRTUAL_PROMPT=%PROMPT%
set PROMPT=(venv310) %PROMPT%

if defined PYTHONHOME set _OLD_VIRTUAL_PYTHONHOME=%PYTHONHOME%
set PYTHONHOME=

if defined _OLD_VIRTUAL_PATH set PATH=%_OLD_VIRTUAL_PATH%
if not defined _OLD_VIRTUAL_PATH set _OLD_VIRTUAL_PATH=%PATH%

set PATH=%VIRTUAL_ENV%\Scripts;%PATH%
set VIRTUAL_ENV_PROMPT=(venv310) 

:END
if defined _OLD_CODEPAGE (
    "%SystemRoot%\System32\chcp.com" %_OLD_CODEPAGE% > nul
    set _OLD_CODEPAGE=
)
````

## File: venv310/Scripts/Activate.ps1
````powershell
<#
.Synopsis
Activate a Python virtual environment for the current PowerShell session.

.Description
Pushes the python executable for a virtual environment to the front of the
$Env:PATH environment variable and sets the prompt to signify that you are
in a Python virtual environment. Makes use of the command line switches as
well as the `pyvenv.cfg` file values present in the virtual environment.

.Parameter VenvDir
Path to the directory that contains the virtual environment to activate. The
default value for this is the parent of the directory that the Activate.ps1
script is located within.

.Parameter Prompt
The prompt prefix to display when this virtual environment is activated. By
default, this prompt is the name of the virtual environment folder (VenvDir)
surrounded by parentheses and followed by a single space (ie. '(.venv) ').

.Example
Activate.ps1
Activates the Python virtual environment that contains the Activate.ps1 script.

.Example
Activate.ps1 -Verbose
Activates the Python virtual environment that contains the Activate.ps1 script,
and shows extra information about the activation as it executes.

.Example
Activate.ps1 -VenvDir C:\Users\MyUser\Common\.venv
Activates the Python virtual environment located in the specified location.

.Example
Activate.ps1 -Prompt "MyPython"
Activates the Python virtual environment that contains the Activate.ps1 script,
and prefixes the current prompt with the specified string (surrounded in
parentheses) while the virtual environment is active.

.Notes
On Windows, it may be required to enable this Activate.ps1 script by setting the
execution policy for the user. You can do this by issuing the following PowerShell
command:

PS C:\> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

For more information on Execution Policies: 
https://go.microsoft.com/fwlink/?LinkID=135170

#>
Param(
    [Parameter(Mandatory = $false)]
    [String]
    $VenvDir,
    [Parameter(Mandatory = $false)]
    [String]
    $Prompt
)

<# Function declarations --------------------------------------------------- #>

<#
.Synopsis
Remove all shell session elements added by the Activate script, including the
addition of the virtual environment's Python executable from the beginning of
the PATH variable.

.Parameter NonDestructive
If present, do not remove this function from the global namespace for the
session.

#>
function global:deactivate ([switch]$NonDestructive) {
    # Revert to original values

    # The prior prompt:
    if (Test-Path -Path Function:_OLD_VIRTUAL_PROMPT) {
        Copy-Item -Path Function:_OLD_VIRTUAL_PROMPT -Destination Function:prompt
        Remove-Item -Path Function:_OLD_VIRTUAL_PROMPT
    }

    # The prior PYTHONHOME:
    if (Test-Path -Path Env:_OLD_VIRTUAL_PYTHONHOME) {
        Copy-Item -Path Env:_OLD_VIRTUAL_PYTHONHOME -Destination Env:PYTHONHOME
        Remove-Item -Path Env:_OLD_VIRTUAL_PYTHONHOME
    }

    # The prior PATH:
    if (Test-Path -Path Env:_OLD_VIRTUAL_PATH) {
        Copy-Item -Path Env:_OLD_VIRTUAL_PATH -Destination Env:PATH
        Remove-Item -Path Env:_OLD_VIRTUAL_PATH
    }

    # Just remove the VIRTUAL_ENV altogether:
    if (Test-Path -Path Env:VIRTUAL_ENV) {
        Remove-Item -Path env:VIRTUAL_ENV
    }

    # Just remove VIRTUAL_ENV_PROMPT altogether.
    if (Test-Path -Path Env:VIRTUAL_ENV_PROMPT) {
        Remove-Item -Path env:VIRTUAL_ENV_PROMPT
    }

    # Just remove the _PYTHON_VENV_PROMPT_PREFIX altogether:
    if (Get-Variable -Name "_PYTHON_VENV_PROMPT_PREFIX" -ErrorAction SilentlyContinue) {
        Remove-Variable -Name _PYTHON_VENV_PROMPT_PREFIX -Scope Global -Force
    }

    # Leave deactivate function in the global namespace if requested:
    if (-not $NonDestructive) {
        Remove-Item -Path function:deactivate
    }
}

<#
.Description
Get-PyVenvConfig parses the values from the pyvenv.cfg file located in the
given folder, and returns them in a map.

For each line in the pyvenv.cfg file, if that line can be parsed into exactly
two strings separated by `=` (with any amount of whitespace surrounding the =)
then it is considered a `key = value` line. The left hand string is the key,
the right hand is the value.

If the value starts with a `'` or a `"` then the first and last character is
stripped from the value before being captured.

.Parameter ConfigDir
Path to the directory that contains the `pyvenv.cfg` file.
#>
function Get-PyVenvConfig(
    [String]
    $ConfigDir
) {
    Write-Verbose "Given ConfigDir=$ConfigDir, obtain values in pyvenv.cfg"

    # Ensure the file exists, and issue a warning if it doesn't (but still allow the function to continue).
    $pyvenvConfigPath = Join-Path -Resolve -Path $ConfigDir -ChildPath 'pyvenv.cfg' -ErrorAction Continue

    # An empty map will be returned if no config file is found.
    $pyvenvConfig = @{ }

    if ($pyvenvConfigPath) {

        Write-Verbose "File exists, parse `key = value` lines"
        $pyvenvConfigContent = Get-Content -Path $pyvenvConfigPath

        $pyvenvConfigContent | ForEach-Object {
            $keyval = $PSItem -split "\s*=\s*", 2
            if ($keyval[0] -and $keyval[1]) {
                $val = $keyval[1]

                # Remove extraneous quotations around a string value.
                if ("'""".Contains($val.Substring(0, 1))) {
                    $val = $val.Substring(1, $val.Length - 2)
                }

                $pyvenvConfig[$keyval[0]] = $val
                Write-Verbose "Adding Key: '$($keyval[0])'='$val'"
            }
        }
    }
    return $pyvenvConfig
}


<# Begin Activate script --------------------------------------------------- #>

# Determine the containing directory of this script
$VenvExecPath = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvExecDir = Get-Item -Path $VenvExecPath

Write-Verbose "Activation script is located in path: '$VenvExecPath'"
Write-Verbose "VenvExecDir Fullname: '$($VenvExecDir.FullName)"
Write-Verbose "VenvExecDir Name: '$($VenvExecDir.Name)"

# Set values required in priority: CmdLine, ConfigFile, Default
# First, get the location of the virtual environment, it might not be
# VenvExecDir if specified on the command line.
if ($VenvDir) {
    Write-Verbose "VenvDir given as parameter, using '$VenvDir' to determine values"
}
else {
    Write-Verbose "VenvDir not given as a parameter, using parent directory name as VenvDir."
    $VenvDir = $VenvExecDir.Parent.FullName.TrimEnd("\\/")
    Write-Verbose "VenvDir=$VenvDir"
}

# Next, read the `pyvenv.cfg` file to determine any required value such
# as `prompt`.
$pyvenvCfg = Get-PyVenvConfig -ConfigDir $VenvDir

# Next, set the prompt from the command line, or the config file, or
# just use the name of the virtual environment folder.
if ($Prompt) {
    Write-Verbose "Prompt specified as argument, using '$Prompt'"
}
else {
    Write-Verbose "Prompt not specified as argument to script, checking pyvenv.cfg value"
    if ($pyvenvCfg -and $pyvenvCfg['prompt']) {
        Write-Verbose "  Setting based on value in pyvenv.cfg='$($pyvenvCfg['prompt'])'"
        $Prompt = $pyvenvCfg['prompt'];
    }
    else {
        Write-Verbose "  Setting prompt based on parent's directory's name. (Is the directory name passed to venv module when creating the virtual environment)"
        Write-Verbose "  Got leaf-name of $VenvDir='$(Split-Path -Path $venvDir -Leaf)'"
        $Prompt = Split-Path -Path $venvDir -Leaf
    }
}

Write-Verbose "Prompt = '$Prompt'"
Write-Verbose "VenvDir='$VenvDir'"

# Deactivate any currently active virtual environment, but leave the
# deactivate function in place.
deactivate -nondestructive

# Now set the environment variable VIRTUAL_ENV, used by many tools to determine
# that there is an activated venv.
$env:VIRTUAL_ENV = $VenvDir

if (-not $Env:VIRTUAL_ENV_DISABLE_PROMPT) {

    Write-Verbose "Setting prompt to '$Prompt'"

    # Set the prompt to include the env name
    # Make sure _OLD_VIRTUAL_PROMPT is global
    function global:_OLD_VIRTUAL_PROMPT { "" }
    Copy-Item -Path function:prompt -Destination function:_OLD_VIRTUAL_PROMPT
    New-Variable -Name _PYTHON_VENV_PROMPT_PREFIX -Description "Python virtual environment prompt prefix" -Scope Global -Option ReadOnly -Visibility Public -Value $Prompt

    function global:prompt {
        Write-Host -NoNewline -ForegroundColor Green "($_PYTHON_VENV_PROMPT_PREFIX) "
        _OLD_VIRTUAL_PROMPT
    }
    $env:VIRTUAL_ENV_PROMPT = $Prompt
}

# Clear PYTHONHOME
if (Test-Path -Path Env:PYTHONHOME) {
    Copy-Item -Path Env:PYTHONHOME -Destination Env:_OLD_VIRTUAL_PYTHONHOME
    Remove-Item -Path Env:PYTHONHOME
}

# Add the venv to the PATH
Copy-Item -Path Env:PATH -Destination Env:_OLD_VIRTUAL_PATH
$Env:PATH = "$VenvExecDir$([System.IO.Path]::PathSeparator)$Env:PATH"

# SIG # Begin signature block
# MIIvJAYJKoZIhvcNAQcCoIIvFTCCLxECAQExDzANBglghkgBZQMEAgEFADB5Bgor
# BgEEAYI3AgEEoGswaTA0BgorBgEEAYI3AgEeMCYCAwEAAAQQH8w7YFlLCE63JNLG
# KX7zUQIBAAIBAAIBAAIBAAIBADAxMA0GCWCGSAFlAwQCAQUABCBnL745ElCYk8vk
# dBtMuQhLeWJ3ZGfzKW4DHCYzAn+QB6CCE8MwggWQMIIDeKADAgECAhAFmxtXno4h
# MuI5B72nd3VcMA0GCSqGSIb3DQEBDAUAMGIxCzAJBgNVBAYTAlVTMRUwEwYDVQQK
# EwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5jb20xITAfBgNV
# BAMTGERpZ2lDZXJ0IFRydXN0ZWQgUm9vdCBHNDAeFw0xMzA4MDExMjAwMDBaFw0z
# ODAxMTUxMjAwMDBaMGIxCzAJBgNVBAYTAlVTMRUwEwYDVQQKEwxEaWdpQ2VydCBJ
# bmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5jb20xITAfBgNVBAMTGERpZ2lDZXJ0
# IFRydXN0ZWQgUm9vdCBHNDCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIB
# AL/mkHNo3rvkXUo8MCIwaTPswqclLskhPfKK2FnC4SmnPVirdprNrnsbhA3EMB/z
# G6Q4FutWxpdtHauyefLKEdLkX9YFPFIPUh/GnhWlfr6fqVcWWVVyr2iTcMKyunWZ
# anMylNEQRBAu34LzB4TmdDttceItDBvuINXJIB1jKS3O7F5OyJP4IWGbNOsFxl7s
# Wxq868nPzaw0QF+xembud8hIqGZXV59UWI4MK7dPpzDZVu7Ke13jrclPXuU15zHL
# 2pNe3I6PgNq2kZhAkHnDeMe2scS1ahg4AxCN2NQ3pC4FfYj1gj4QkXCrVYJBMtfb
# BHMqbpEBfCFM1LyuGwN1XXhm2ToxRJozQL8I11pJpMLmqaBn3aQnvKFPObURWBf3
# JFxGj2T3wWmIdph2PVldQnaHiZdpekjw4KISG2aadMreSx7nDmOu5tTvkpI6nj3c
# AORFJYm2mkQZK37AlLTSYW3rM9nF30sEAMx9HJXDj/chsrIRt7t/8tWMcCxBYKqx
# YxhElRp2Yn72gLD76GSmM9GJB+G9t+ZDpBi4pncB4Q+UDCEdslQpJYls5Q5SUUd0
# viastkF13nqsX40/ybzTQRESW+UQUOsxxcpyFiIJ33xMdT9j7CFfxCBRa2+xq4aL
# T8LWRV+dIPyhHsXAj6KxfgommfXkaS+YHS312amyHeUbAgMBAAGjQjBAMA8GA1Ud
# EwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgGGMB0GA1UdDgQWBBTs1+OC0nFdZEzf
# Lmc/57qYrhwPTzANBgkqhkiG9w0BAQwFAAOCAgEAu2HZfalsvhfEkRvDoaIAjeNk
# aA9Wz3eucPn9mkqZucl4XAwMX+TmFClWCzZJXURj4K2clhhmGyMNPXnpbWvWVPjS
# PMFDQK4dUPVS/JA7u5iZaWvHwaeoaKQn3J35J64whbn2Z006Po9ZOSJTROvIXQPK
# 7VB6fWIhCoDIc2bRoAVgX+iltKevqPdtNZx8WorWojiZ83iL9E3SIAveBO6Mm0eB
# cg3AFDLvMFkuruBx8lbkapdvklBtlo1oepqyNhR6BvIkuQkRUNcIsbiJeoQjYUIp
# 5aPNoiBB19GcZNnqJqGLFNdMGbJQQXE9P01wI4YMStyB0swylIQNCAmXHE/A7msg
# dDDS4Dk0EIUhFQEI6FUy3nFJ2SgXUE3mvk3RdazQyvtBuEOlqtPDBURPLDab4vri
# RbgjU2wGb2dVf0a1TD9uKFp5JtKkqGKX0h7i7UqLvBv9R0oN32dmfrJbQdA75PQ7
# 9ARj6e/CVABRoIoqyc54zNXqhwQYs86vSYiv85KZtrPmYQ/ShQDnUBrkG5WdGaG5
# nLGbsQAe79APT0JsyQq87kP6OnGlyE0mpTX9iV28hWIdMtKgK1TtmlfB2/oQzxm3
# i0objwG2J5VT6LaJbVu8aNQj6ItRolb58KaAoNYes7wPD1N1KarqE3fk3oyBIa0H
# EEcRrYc9B9F1vM/zZn4wggawMIIEmKADAgECAhAIrUCyYNKcTJ9ezam9k67ZMA0G
# CSqGSIb3DQEBDAUAMGIxCzAJBgNVBAYTAlVTMRUwEwYDVQQKEwxEaWdpQ2VydCBJ
# bmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5jb20xITAfBgNVBAMTGERpZ2lDZXJ0
# IFRydXN0ZWQgUm9vdCBHNDAeFw0yMTA0MjkwMDAwMDBaFw0zNjA0MjgyMzU5NTla
# MGkxCzAJBgNVBAYTAlVTMRcwFQYDVQQKEw5EaWdpQ2VydCwgSW5jLjFBMD8GA1UE
# AxM4RGlnaUNlcnQgVHJ1c3RlZCBHNCBDb2RlIFNpZ25pbmcgUlNBNDA5NiBTSEEz
# ODQgMjAyMSBDQTEwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQDVtC9C
# 0CiteLdd1TlZG7GIQvUzjOs9gZdwxbvEhSYwn6SOaNhc9es0JAfhS0/TeEP0F9ce
# 2vnS1WcaUk8OoVf8iJnBkcyBAz5NcCRks43iCH00fUyAVxJrQ5qZ8sU7H/Lvy0da
# E6ZMswEgJfMQ04uy+wjwiuCdCcBlp/qYgEk1hz1RGeiQIXhFLqGfLOEYwhrMxe6T
# SXBCMo/7xuoc82VokaJNTIIRSFJo3hC9FFdd6BgTZcV/sk+FLEikVoQ11vkunKoA
# FdE3/hoGlMJ8yOobMubKwvSnowMOdKWvObarYBLj6Na59zHh3K3kGKDYwSNHR7Oh
# D26jq22YBoMbt2pnLdK9RBqSEIGPsDsJ18ebMlrC/2pgVItJwZPt4bRc4G/rJvmM
# 1bL5OBDm6s6R9b7T+2+TYTRcvJNFKIM2KmYoX7BzzosmJQayg9Rc9hUZTO1i4F4z
# 8ujo7AqnsAMrkbI2eb73rQgedaZlzLvjSFDzd5Ea/ttQokbIYViY9XwCFjyDKK05
# huzUtw1T0PhH5nUwjewwk3YUpltLXXRhTT8SkXbev1jLchApQfDVxW0mdmgRQRNY
# mtwmKwH0iU1Z23jPgUo+QEdfyYFQc4UQIyFZYIpkVMHMIRroOBl8ZhzNeDhFMJlP
# /2NPTLuqDQhTQXxYPUez+rbsjDIJAsxsPAxWEQIDAQABo4IBWTCCAVUwEgYDVR0T
# AQH/BAgwBgEB/wIBADAdBgNVHQ4EFgQUaDfg67Y7+F8Rhvv+YXsIiGX0TkIwHwYD
# VR0jBBgwFoAU7NfjgtJxXWRM3y5nP+e6mK4cD08wDgYDVR0PAQH/BAQDAgGGMBMG
# A1UdJQQMMAoGCCsGAQUFBwMDMHcGCCsGAQUFBwEBBGswaTAkBggrBgEFBQcwAYYY
# aHR0cDovL29jc3AuZGlnaWNlcnQuY29tMEEGCCsGAQUFBzAChjVodHRwOi8vY2Fj
# ZXJ0cy5kaWdpY2VydC5jb20vRGlnaUNlcnRUcnVzdGVkUm9vdEc0LmNydDBDBgNV
# HR8EPDA6MDigNqA0hjJodHRwOi8vY3JsMy5kaWdpY2VydC5jb20vRGlnaUNlcnRU
# cnVzdGVkUm9vdEc0LmNybDAcBgNVHSAEFTATMAcGBWeBDAEDMAgGBmeBDAEEATAN
# BgkqhkiG9w0BAQwFAAOCAgEAOiNEPY0Idu6PvDqZ01bgAhql+Eg08yy25nRm95Ry
# sQDKr2wwJxMSnpBEn0v9nqN8JtU3vDpdSG2V1T9J9Ce7FoFFUP2cvbaF4HZ+N3HL
# IvdaqpDP9ZNq4+sg0dVQeYiaiorBtr2hSBh+3NiAGhEZGM1hmYFW9snjdufE5Btf
# Q/g+lP92OT2e1JnPSt0o618moZVYSNUa/tcnP/2Q0XaG3RywYFzzDaju4ImhvTnh
# OE7abrs2nfvlIVNaw8rpavGiPttDuDPITzgUkpn13c5UbdldAhQfQDN8A+KVssIh
# dXNSy0bYxDQcoqVLjc1vdjcshT8azibpGL6QB7BDf5WIIIJw8MzK7/0pNVwfiThV
# 9zeKiwmhywvpMRr/LhlcOXHhvpynCgbWJme3kuZOX956rEnPLqR0kq3bPKSchh/j
# wVYbKyP/j7XqiHtwa+aguv06P0WmxOgWkVKLQcBIhEuWTatEQOON8BUozu3xGFYH
# Ki8QxAwIZDwzj64ojDzLj4gLDb879M4ee47vtevLt/B3E+bnKD+sEq6lLyJsQfmC
# XBVmzGwOysWGw/YmMwwHS6DTBwJqakAwSEs0qFEgu60bhQjiWQ1tygVQK+pKHJ6l
# /aCnHwZ05/LWUpD9r4VIIflXO7ScA+2GRfS0YW6/aOImYIbqyK+p/pQd52MbOoZW
# eE4wggd3MIIFX6ADAgECAhAHHxQbizANJfMU6yMM0NHdMA0GCSqGSIb3DQEBCwUA
# MGkxCzAJBgNVBAYTAlVTMRcwFQYDVQQKEw5EaWdpQ2VydCwgSW5jLjFBMD8GA1UE
# AxM4RGlnaUNlcnQgVHJ1c3RlZCBHNCBDb2RlIFNpZ25pbmcgUlNBNDA5NiBTSEEz
# ODQgMjAyMSBDQTEwHhcNMjIwMTE3MDAwMDAwWhcNMjUwMTE1MjM1OTU5WjB8MQsw
# CQYDVQQGEwJVUzEPMA0GA1UECBMGT3JlZ29uMRIwEAYDVQQHEwlCZWF2ZXJ0b24x
# IzAhBgNVBAoTGlB5dGhvbiBTb2Z0d2FyZSBGb3VuZGF0aW9uMSMwIQYDVQQDExpQ
# eXRob24gU29mdHdhcmUgRm91bmRhdGlvbjCCAiIwDQYJKoZIhvcNAQEBBQADggIP
# ADCCAgoCggIBAKgc0BTT+iKbtK6f2mr9pNMUTcAJxKdsuOiSYgDFfwhjQy89koM7
# uP+QV/gwx8MzEt3c9tLJvDccVWQ8H7mVsk/K+X+IufBLCgUi0GGAZUegEAeRlSXx
# xhYScr818ma8EvGIZdiSOhqjYc4KnfgfIS4RLtZSrDFG2tN16yS8skFa3IHyvWdb
# D9PvZ4iYNAS4pjYDRjT/9uzPZ4Pan+53xZIcDgjiTwOh8VGuppxcia6a7xCyKoOA
# GjvCyQsj5223v1/Ig7Dp9mGI+nh1E3IwmyTIIuVHyK6Lqu352diDY+iCMpk9Zanm
# SjmB+GMVs+H/gOiofjjtf6oz0ki3rb7sQ8fTnonIL9dyGTJ0ZFYKeb6BLA66d2GA
# LwxZhLe5WH4Np9HcyXHACkppsE6ynYjTOd7+jN1PRJahN1oERzTzEiV6nCO1M3U1
# HbPTGyq52IMFSBM2/07WTJSbOeXjvYR7aUxK9/ZkJiacl2iZI7IWe7JKhHohqKuc
# eQNyOzxTakLcRkzynvIrk33R9YVqtB4L6wtFxhUjvDnQg16xot2KVPdfyPAWd81w
# tZADmrUtsZ9qG79x1hBdyOl4vUtVPECuyhCxaw+faVjumapPUnwo8ygflJJ74J+B
# Yxf6UuD7m8yzsfXWkdv52DjL74TxzuFTLHPyARWCSCAbzn3ZIly+qIqDAgMBAAGj
# ggIGMIICAjAfBgNVHSMEGDAWgBRoN+Drtjv4XxGG+/5hewiIZfROQjAdBgNVHQ4E
# FgQUt/1Teh2XDuUj2WW3siYWJgkZHA8wDgYDVR0PAQH/BAQDAgeAMBMGA1UdJQQM
# MAoGCCsGAQUFBwMDMIG1BgNVHR8Ega0wgaowU6BRoE+GTWh0dHA6Ly9jcmwzLmRp
# Z2ljZXJ0LmNvbS9EaWdpQ2VydFRydXN0ZWRHNENvZGVTaWduaW5nUlNBNDA5NlNI
# QTM4NDIwMjFDQTEuY3JsMFOgUaBPhk1odHRwOi8vY3JsNC5kaWdpY2VydC5jb20v
# RGlnaUNlcnRUcnVzdGVkRzRDb2RlU2lnbmluZ1JTQTQwOTZTSEEzODQyMDIxQ0Ex
# LmNybDA+BgNVHSAENzA1MDMGBmeBDAEEATApMCcGCCsGAQUFBwIBFhtodHRwOi8v
# d3d3LmRpZ2ljZXJ0LmNvbS9DUFMwgZQGCCsGAQUFBwEBBIGHMIGEMCQGCCsGAQUF
# BzABhhhodHRwOi8vb2NzcC5kaWdpY2VydC5jb20wXAYIKwYBBQUHMAKGUGh0dHA6
# Ly9jYWNlcnRzLmRpZ2ljZXJ0LmNvbS9EaWdpQ2VydFRydXN0ZWRHNENvZGVTaWdu
# aW5nUlNBNDA5NlNIQTM4NDIwMjFDQTEuY3J0MAwGA1UdEwEB/wQCMAAwDQYJKoZI
# hvcNAQELBQADggIBABxv4AeV/5ltkELHSC63fXAFYS5tadcWTiNc2rskrNLrfH1N
# s0vgSZFoQxYBFKI159E8oQQ1SKbTEubZ/B9kmHPhprHya08+VVzxC88pOEvz68nA
# 82oEM09584aILqYmj8Pj7h/kmZNzuEL7WiwFa/U1hX+XiWfLIJQsAHBla0i7QRF2
# de8/VSF0XXFa2kBQ6aiTsiLyKPNbaNtbcucaUdn6vVUS5izWOXM95BSkFSKdE45O
# q3FForNJXjBvSCpwcP36WklaHL+aHu1upIhCTUkzTHMh8b86WmjRUqbrnvdyR2yd
# I5l1OqcMBjkpPpIV6wcc+KY/RH2xvVuuoHjlUjwq2bHiNoX+W1scCpnA8YTs2d50
# jDHUgwUo+ciwpffH0Riq132NFmrH3r67VaN3TuBxjI8SIZM58WEDkbeoriDk3hxU
# 8ZWV7b8AW6oyVBGfM06UgkfMb58h+tJPrFx8VI/WLq1dTqMfZOm5cuclMnUHs2uq
# rRNtnV8UfidPBL4ZHkTcClQbCoz0UbLhkiDvIS00Dn+BBcxw/TKqVL4Oaz3bkMSs
# M46LciTeucHY9ExRVt3zy7i149sd+F4QozPqn7FrSVHXmem3r7bjyHTxOgqxRCVa
# 18Vtx7P/8bYSBeS+WHCKcliFCecspusCDSlnRUjZwyPdP0VHxaZg2unjHY3rMYIa
# tzCCGrMCAQEwfTBpMQswCQYDVQQGEwJVUzEXMBUGA1UEChMORGlnaUNlcnQsIElu
# Yy4xQTA/BgNVBAMTOERpZ2lDZXJ0IFRydXN0ZWQgRzQgQ29kZSBTaWduaW5nIFJT
# QTQwOTYgU0hBMzg0IDIwMjEgQ0ExAhAHHxQbizANJfMU6yMM0NHdMA0GCWCGSAFl
# AwQCAQUAoIHIMBkGCSqGSIb3DQEJAzEMBgorBgEEAYI3AgEEMBwGCisGAQQBgjcC
# AQsxDjAMBgorBgEEAYI3AgEVMC8GCSqGSIb3DQEJBDEiBCBnAZ6P7YvTwq0fbF62
# o7E75R0LxsW5OtyYiFESQckLhjBcBgorBgEEAYI3AgEMMU4wTKBGgEQAQgB1AGkA
# bAB0ADoAIABSAGUAbABlAGEAcwBlAF8AdgAzAC4AMQAyAC4AMgBfADIAMAAyADQA
# MAAyADAANgAuADAAMaECgAAwDQYJKoZIhvcNAQEBBQAEggIATbW6c9buReeKQQso
# g6hMn1qdYYpVw4mI50/iuRhryAKIbOF/nXFzfU2O2v7lf7eDemq47UrEagsI/fkz
# jHQCeGD49o9yUP2oWxswpBZnuo4KIVl+rd8i3bA8YwEyxcSseoiNAVJVB/x8irzu
# RXQj8bC7Cq2OG3VTyTX4m2ZGUHqZ4FdykziD771ljrl9EoJMsamH6u6nvX8D7u3D
# sX5hdLLfkO8NIca0NN6b+S0jOQk5Mds4h7XUbpre2QCn9h62TEMf+VWExSst3Wrr
# 0dZmzO76EO/4HiYqPdbvwkFjNddIwRUC/jHWr0/fWWutRPb+91M0U5L/uvaqz39/
# cteqXMzVilOqcMLdRY2i8VbEEF97xADWTjU1fg1ANEiYHOAzR1/BP9OtZPP/TDo6
# OKzZrJT6mJ07MgevqTLHSmSWZMQc+cWar8HiWSacGcY+DXhMUYaa6EdvITvKlPkE
# RO87xlQ3xmV2d2D3Vz98bU42FY7PKejRJQgClPLtW3fA7EC7o5sn8E2XgOVjLP5W
# 8IYgr0UUSJI4odUtuzXbdxjc0MUZedlX2RufM7x/OScv2CSSBMuByJ1Z4j1qQylm
# M0j/MjVyhMr4c8TH5z77Ec1HPc79dwCKTmrI9ze2mNzb7a7abG59mWmyuenIlu3r
# 1L9agonr/oNDuIpkw3GhQRMcIMahghdAMIIXPAYKKwYBBAGCNwMDATGCFywwghco
# BgkqhkiG9w0BBwKgghcZMIIXFQIBAzEPMA0GCWCGSAFlAwQCAQUAMHgGCyqGSIb3
# DQEJEAEEoGkEZzBlAgEBBglghkgBhv1sBwEwMTANBglghkgBZQMEAgEFAAQg05m0
# ZnzFt5OfLCqM3dUoLNWuyDSET+7H8CVzSSScfIcCEQD8wmvVfDaiineK4eXUaB6n
# GA8yMDI0MDIwNjIyMDg1OFqgghMJMIIGwjCCBKqgAwIBAgIQBUSv85SdCDmmv9s/
# X+VhFjANBgkqhkiG9w0BAQsFADBjMQswCQYDVQQGEwJVUzEXMBUGA1UEChMORGln
# aUNlcnQsIEluYy4xOzA5BgNVBAMTMkRpZ2lDZXJ0IFRydXN0ZWQgRzQgUlNBNDA5
# NiBTSEEyNTYgVGltZVN0YW1waW5nIENBMB4XDTIzMDcxNDAwMDAwMFoXDTM0MTAx
# MzIzNTk1OVowSDELMAkGA1UEBhMCVVMxFzAVBgNVBAoTDkRpZ2lDZXJ0LCBJbmMu
# MSAwHgYDVQQDExdEaWdpQ2VydCBUaW1lc3RhbXAgMjAyMzCCAiIwDQYJKoZIhvcN
# AQEBBQADggIPADCCAgoCggIBAKNTRYcdg45brD5UsyPgz5/X5dLnXaEOCdwvSKOX
# ejsqnGfcYhVYwamTEafNqrJq3RApih5iY2nTWJw1cb86l+uUUI8cIOrHmjsvlmbj
# aedp/lvD1isgHMGXlLSlUIHyz8sHpjBoyoNC2vx/CSSUpIIa2mq62DvKXd4ZGIX7
# ReoNYWyd/nFexAaaPPDFLnkPG2ZS48jWPl/aQ9OE9dDH9kgtXkV1lnX+3RChG4PB
# uOZSlbVH13gpOWvgeFmX40QrStWVzu8IF+qCZE3/I+PKhu60pCFkcOvV5aDaY7Mu
# 6QXuqvYk9R28mxyyt1/f8O52fTGZZUdVnUokL6wrl76f5P17cz4y7lI0+9S769Sg
# LDSb495uZBkHNwGRDxy1Uc2qTGaDiGhiu7xBG3gZbeTZD+BYQfvYsSzhUa+0rRUG
# FOpiCBPTaR58ZE2dD9/O0V6MqqtQFcmzyrzXxDtoRKOlO0L9c33u3Qr/eTQQfqZc
# ClhMAD6FaXXHg2TWdc2PEnZWpST618RrIbroHzSYLzrqawGw9/sqhux7UjipmAmh
# cbJsca8+uG+W1eEQE/5hRwqM/vC2x9XH3mwk8L9CgsqgcT2ckpMEtGlwJw1Pt7U2
# 0clfCKRwo+wK8REuZODLIivK8SgTIUlRfgZm0zu++uuRONhRB8qUt+JQofM604qD
# y0B7AgMBAAGjggGLMIIBhzAOBgNVHQ8BAf8EBAMCB4AwDAYDVR0TAQH/BAIwADAW
# BgNVHSUBAf8EDDAKBggrBgEFBQcDCDAgBgNVHSAEGTAXMAgGBmeBDAEEAjALBglg
# hkgBhv1sBwEwHwYDVR0jBBgwFoAUuhbZbU2FL3MpdpovdYxqII+eyG8wHQYDVR0O
# BBYEFKW27xPn783QZKHVVqllMaPe1eNJMFoGA1UdHwRTMFEwT6BNoEuGSWh0dHA6
# Ly9jcmwzLmRpZ2ljZXJ0LmNvbS9EaWdpQ2VydFRydXN0ZWRHNFJTQTQwOTZTSEEy
# NTZUaW1lU3RhbXBpbmdDQS5jcmwwgZAGCCsGAQUFBwEBBIGDMIGAMCQGCCsGAQUF
# BzABhhhodHRwOi8vb2NzcC5kaWdpY2VydC5jb20wWAYIKwYBBQUHMAKGTGh0dHA6
# Ly9jYWNlcnRzLmRpZ2ljZXJ0LmNvbS9EaWdpQ2VydFRydXN0ZWRHNFJTQTQwOTZT
# SEEyNTZUaW1lU3RhbXBpbmdDQS5jcnQwDQYJKoZIhvcNAQELBQADggIBAIEa1t6g
# qbWYF7xwjU+KPGic2CX/yyzkzepdIpLsjCICqbjPgKjZ5+PF7SaCinEvGN1Ott5s
# 1+FgnCvt7T1IjrhrunxdvcJhN2hJd6PrkKoS1yeF844ektrCQDifXcigLiV4JZ0q
# BXqEKZi2V3mP2yZWK7Dzp703DNiYdk9WuVLCtp04qYHnbUFcjGnRuSvExnvPnPp4
# 4pMadqJpddNQ5EQSviANnqlE0PjlSXcIWiHFtM+YlRpUurm8wWkZus8W8oM3NG6w
# QSbd3lqXTzON1I13fXVFoaVYJmoDRd7ZULVQjK9WvUzF4UbFKNOt50MAcN7MmJ4Z
# iQPq1JE3701S88lgIcRWR+3aEUuMMsOI5ljitts++V+wQtaP4xeR0arAVeOGv6wn
# LEHQmjNKqDbUuXKWfpd5OEhfysLcPTLfddY2Z1qJ+Panx+VPNTwAvb6cKmx5Adza
# ROY63jg7B145WPR8czFVoIARyxQMfq68/qTreWWqaNYiyjvrmoI1VygWy2nyMpqy
# 0tg6uLFGhmu6F/3Ed2wVbK6rr3M66ElGt9V/zLY4wNjsHPW2obhDLN9OTH0eaHDA
# dwrUAuBcYLso/zjlUlrWrBciI0707NMX+1Br/wd3H3GXREHJuEbTbDJ8WC9nR2Xl
# G3O2mflrLAZG70Ee8PBf4NvZrZCARK+AEEGKMIIGrjCCBJagAwIBAgIQBzY3tyRU
# fNhHrP0oZipeWzANBgkqhkiG9w0BAQsFADBiMQswCQYDVQQGEwJVUzEVMBMGA1UE
# ChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3d3cuZGlnaWNlcnQuY29tMSEwHwYD
# VQQDExhEaWdpQ2VydCBUcnVzdGVkIFJvb3QgRzQwHhcNMjIwMzIzMDAwMDAwWhcN
# MzcwMzIyMjM1OTU5WjBjMQswCQYDVQQGEwJVUzEXMBUGA1UEChMORGlnaUNlcnQs
# IEluYy4xOzA5BgNVBAMTMkRpZ2lDZXJ0IFRydXN0ZWQgRzQgUlNBNDA5NiBTSEEy
# NTYgVGltZVN0YW1waW5nIENBMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKC
# AgEAxoY1BkmzwT1ySVFVxyUDxPKRN6mXUaHW0oPRnkyibaCwzIP5WvYRoUQVQl+k
# iPNo+n3znIkLf50fng8zH1ATCyZzlm34V6gCff1DtITaEfFzsbPuK4CEiiIY3+va
# PcQXf6sZKz5C3GeO6lE98NZW1OcoLevTsbV15x8GZY2UKdPZ7Gnf2ZCHRgB720RB
# idx8ald68Dd5n12sy+iEZLRS8nZH92GDGd1ftFQLIWhuNyG7QKxfst5Kfc71ORJn
# 7w6lY2zkpsUdzTYNXNXmG6jBZHRAp8ByxbpOH7G1WE15/tePc5OsLDnipUjW8LAx
# E6lXKZYnLvWHpo9OdhVVJnCYJn+gGkcgQ+NDY4B7dW4nJZCYOjgRs/b2nuY7W+yB
# 3iIU2YIqx5K/oN7jPqJz+ucfWmyU8lKVEStYdEAoq3NDzt9KoRxrOMUp88qqlnNC
# aJ+2RrOdOqPVA+C/8KI8ykLcGEh/FDTP0kyr75s9/g64ZCr6dSgkQe1CvwWcZklS
# UPRR8zZJTYsg0ixXNXkrqPNFYLwjjVj33GHek/45wPmyMKVM1+mYSlg+0wOI/rOP
# 015LdhJRk8mMDDtbiiKowSYI+RQQEgN9XyO7ZONj4KbhPvbCdLI/Hgl27KtdRnXi
# YKNYCQEoAA6EVO7O6V3IXjASvUaetdN2udIOa5kM0jO0zbECAwEAAaOCAV0wggFZ
# MBIGA1UdEwEB/wQIMAYBAf8CAQAwHQYDVR0OBBYEFLoW2W1NhS9zKXaaL3WMaiCP
# nshvMB8GA1UdIwQYMBaAFOzX44LScV1kTN8uZz/nupiuHA9PMA4GA1UdDwEB/wQE
# AwIBhjATBgNVHSUEDDAKBggrBgEFBQcDCDB3BggrBgEFBQcBAQRrMGkwJAYIKwYB
# BQUHMAGGGGh0dHA6Ly9vY3NwLmRpZ2ljZXJ0LmNvbTBBBggrBgEFBQcwAoY1aHR0
# cDovL2NhY2VydHMuZGlnaWNlcnQuY29tL0RpZ2lDZXJ0VHJ1c3RlZFJvb3RHNC5j
# cnQwQwYDVR0fBDwwOjA4oDagNIYyaHR0cDovL2NybDMuZGlnaWNlcnQuY29tL0Rp
# Z2lDZXJ0VHJ1c3RlZFJvb3RHNC5jcmwwIAYDVR0gBBkwFzAIBgZngQwBBAIwCwYJ
# YIZIAYb9bAcBMA0GCSqGSIb3DQEBCwUAA4ICAQB9WY7Ak7ZvmKlEIgF+ZtbYIULh
# sBguEE0TzzBTzr8Y+8dQXeJLKftwig2qKWn8acHPHQfpPmDI2AvlXFvXbYf6hCAl
# NDFnzbYSlm/EUExiHQwIgqgWvalWzxVzjQEiJc6VaT9Hd/tydBTX/6tPiix6q4XN
# Q1/tYLaqT5Fmniye4Iqs5f2MvGQmh2ySvZ180HAKfO+ovHVPulr3qRCyXen/KFSJ
# 8NWKcXZl2szwcqMj+sAngkSumScbqyQeJsG33irr9p6xeZmBo1aGqwpFyd/EjaDn
# mPv7pp1yr8THwcFqcdnGE4AJxLafzYeHJLtPo0m5d2aR8XKc6UsCUqc3fpNTrDsd
# CEkPlM05et3/JWOZJyw9P2un8WbDQc1PtkCbISFA0LcTJM3cHXg65J6t5TRxktcm
# a+Q4c6umAU+9Pzt4rUyt+8SVe+0KXzM5h0F4ejjpnOHdI/0dKNPH+ejxmF/7K9h+
# 8kaddSweJywm228Vex4Ziza4k9Tm8heZWcpw8De/mADfIBZPJ/tgZxahZrrdVcA6
# KYawmKAr7ZVBtzrVFZgxtGIJDwq9gdkT/r+k0fNX2bwE+oLeMt8EifAAzV3C+dAj
# fwAL5HYCJtnwZXZCpimHCUcr5n8apIUP/JiW9lVUKx+A+sDyDivl1vupL0QVSucT
# Dh3bNzgaoSv27dZ8/DCCBY0wggR1oAMCAQICEA6bGI750C3n79tQ4ghAGFowDQYJ
# KoZIhvcNAQEMBQAwZTELMAkGA1UEBhMCVVMxFTATBgNVBAoTDERpZ2lDZXJ0IElu
# YzEZMBcGA1UECxMQd3d3LmRpZ2ljZXJ0LmNvbTEkMCIGA1UEAxMbRGlnaUNlcnQg
# QXNzdXJlZCBJRCBSb290IENBMB4XDTIyMDgwMTAwMDAwMFoXDTMxMTEwOTIzNTk1
# OVowYjELMAkGA1UEBhMCVVMxFTATBgNVBAoTDERpZ2lDZXJ0IEluYzEZMBcGA1UE
# CxMQd3d3LmRpZ2ljZXJ0LmNvbTEhMB8GA1UEAxMYRGlnaUNlcnQgVHJ1c3RlZCBS
# b290IEc0MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAv+aQc2jeu+Rd
# SjwwIjBpM+zCpyUuySE98orYWcLhKac9WKt2ms2uexuEDcQwH/MbpDgW61bGl20d
# q7J58soR0uRf1gU8Ug9SH8aeFaV+vp+pVxZZVXKvaJNwwrK6dZlqczKU0RBEEC7f
# gvMHhOZ0O21x4i0MG+4g1ckgHWMpLc7sXk7Ik/ghYZs06wXGXuxbGrzryc/NrDRA
# X7F6Zu53yEioZldXn1RYjgwrt0+nMNlW7sp7XeOtyU9e5TXnMcvak17cjo+A2raR
# mECQecN4x7axxLVqGDgDEI3Y1DekLgV9iPWCPhCRcKtVgkEy19sEcypukQF8IUzU
# vK4bA3VdeGbZOjFEmjNAvwjXWkmkwuapoGfdpCe8oU85tRFYF/ckXEaPZPfBaYh2
# mHY9WV1CdoeJl2l6SPDgohIbZpp0yt5LHucOY67m1O+SkjqePdwA5EUlibaaRBkr
# fsCUtNJhbesz2cXfSwQAzH0clcOP9yGyshG3u3/y1YxwLEFgqrFjGESVGnZifvaA
# sPvoZKYz0YkH4b235kOkGLimdwHhD5QMIR2yVCkliWzlDlJRR3S+Jqy2QXXeeqxf
# jT/JvNNBERJb5RBQ6zHFynIWIgnffEx1P2PsIV/EIFFrb7GrhotPwtZFX50g/KEe
# xcCPorF+CiaZ9eRpL5gdLfXZqbId5RsCAwEAAaOCATowggE2MA8GA1UdEwEB/wQF
# MAMBAf8wHQYDVR0OBBYEFOzX44LScV1kTN8uZz/nupiuHA9PMB8GA1UdIwQYMBaA
# FEXroq/0ksuCMS1Ri6enIZ3zbcgPMA4GA1UdDwEB/wQEAwIBhjB5BggrBgEFBQcB
# AQRtMGswJAYIKwYBBQUHMAGGGGh0dHA6Ly9vY3NwLmRpZ2ljZXJ0LmNvbTBDBggr
# BgEFBQcwAoY3aHR0cDovL2NhY2VydHMuZGlnaWNlcnQuY29tL0RpZ2lDZXJ0QXNz
# dXJlZElEUm9vdENBLmNydDBFBgNVHR8EPjA8MDqgOKA2hjRodHRwOi8vY3JsMy5k
# aWdpY2VydC5jb20vRGlnaUNlcnRBc3N1cmVkSURSb290Q0EuY3JsMBEGA1UdIAQK
# MAgwBgYEVR0gADANBgkqhkiG9w0BAQwFAAOCAQEAcKC/Q1xV5zhfoKN0Gz22Ftf3
# v1cHvZqsoYcs7IVeqRq7IviHGmlUIu2kiHdtvRoU9BNKei8ttzjv9P+Aufih9/Jy
# 3iS8UgPITtAq3votVs/59PesMHqai7Je1M/RQ0SbQyHrlnKhSLSZy51PpwYDE3cn
# RNTnf+hZqPC/Lwum6fI0POz3A8eHqNJMQBk1RmppVLC4oVaO7KTVPeix3P0c2PR3
# WlxUjG/voVA9/HYJaISfb8rbII01YBwCA8sgsKxYoA5AY8WYIsGyWfVVa88nq2x2
# zm8jLfR+cWojayL/ErhULSd+2DrZ8LaHlv1b0VysGMNNn3O3AamfV6peKOK5lDGC
# A3YwggNyAgEBMHcwYzELMAkGA1UEBhMCVVMxFzAVBgNVBAoTDkRpZ2lDZXJ0LCBJ
# bmMuMTswOQYDVQQDEzJEaWdpQ2VydCBUcnVzdGVkIEc0IFJTQTQwOTYgU0hBMjU2
# IFRpbWVTdGFtcGluZyBDQQIQBUSv85SdCDmmv9s/X+VhFjANBglghkgBZQMEAgEF
# AKCB0TAaBgkqhkiG9w0BCQMxDQYLKoZIhvcNAQkQAQQwHAYJKoZIhvcNAQkFMQ8X
# DTI0MDIwNjIyMDg1OFowKwYLKoZIhvcNAQkQAgwxHDAaMBgwFgQUZvArMsLCyQ+C
# Xc6qisnGTxmcz0AwLwYJKoZIhvcNAQkEMSIEINMdi4rFvW7VPP2AXVn0aK7rkofX
# zdeHGr26+9NSIEg6MDcGCyqGSIb3DQEJEAIvMSgwJjAkMCIEINL25G3tdCLM0dRA
# V2hBNm+CitpVmq4zFq9NGprUDHgoMA0GCSqGSIb3DQEBAQUABIICAEa0h9uNUeCI
# slg/9MrVGvyDPHdViMo+hEB+YgYnYy3yiMQr2BfKvKGcEK9+cbFZoW5F1wM+3Kry
# Gd+fpUCiF2MzvgxYjipgyHmHi4fMhBKF5vC8923FiwyQawZmxiPU/N9pOKEf8MHD
# ggpT91iWxHLgIX8fklieNBBbZxtGPXoyZTDaqeaJhBBJtT1FDZ7nKJbA5sp+1QQj
# nKnjpeCbAD73IgJ/ZayCGmgYwiPhY68j5+pRQt0KGp2+e1pLS9TuEbS2QNIfZEmv
# hFklZEF1P9w9U+Wr/1vnPafeNELPFTaFrELMgQL7wWCM+6uNdZQgT+2DlMWKWWFt
# kunVOD0m1SURurCEHGRi+Y8w0A22uOYnMbItMGVXbgESTwi7yDMCqrrKEkBeJXqr
# Ig8RVOmDAH2a7LPO0cUzE1Ql2oJypJH7wl8338QzVBvRYNJIJ8ISDPn80u2lFWIK
# RFwglrbMcj0b6i+g8J0dMRSMBxkg9hhS922sOLwGNUJ/pJ5IwxFBqf6pdp+WFOA8
# IQ6ynnSSDm82O6giiEL+v2iukua9VG/IKpJMccUKwal+yM4o097MjzzfjdS4oRWJ
# pMz2Wu3m0Tg4o5S09KR7zCHWqlutSriuC2nirqNE+onlbxYUx2JrXk5V+LrfNDAQ
# 0MPcQ1A5d6j7kNjY2262Nh6dU6fPNnUT
# SIG # End signature block
````

## File: venv310/Scripts/deactivate.bat
````
@echo off

if defined _OLD_VIRTUAL_PROMPT (
    set "PROMPT=%_OLD_VIRTUAL_PROMPT%"
)
set _OLD_VIRTUAL_PROMPT=

if defined _OLD_VIRTUAL_PYTHONHOME (
    set "PYTHONHOME=%_OLD_VIRTUAL_PYTHONHOME%"
    set _OLD_VIRTUAL_PYTHONHOME=
)

if defined _OLD_VIRTUAL_PATH (
    set "PATH=%_OLD_VIRTUAL_PATH%"
)

set _OLD_VIRTUAL_PATH=

set VIRTUAL_ENV=
set VIRTUAL_ENV_PROMPT=

:END
````

## File: venv310/Scripts/prichunkpng
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe
# prichunkpng
# Chunk editing tool.

"""
Make a new PNG by adding, delete, or replacing particular chunks.
"""

import argparse
import collections

# https://docs.python.org/2.7/library/io.html
import io
import re
import string
import struct
import sys
import zlib

# Local module.
import png


Chunk = collections.namedtuple("Chunk", "type content")


class ArgumentError(Exception):
    """A user problem with the command arguments."""


def process(out, args):
    """Process the PNG file args.input to the output, chunk by chunk.
    Chunks can be inserted, removed, replaced, or sometimes edited.
    Chunks are specified by their 4 byte Chunk Type;
    see https://www.w3.org/TR/2003/REC-PNG-20031110/#5Chunk-layout .
    The chunks in args.delete will be removed from the stream.
    The chunks in args.chunk will be inserted into the stream
    with their contents taken from the named files.

    Other options on the args object will create particular
    ancillary chunks.

    .gamma -> gAMA chunk
    .sigbit -> sBIT chunk

    Chunk types need not be official PNG chunks at all.
    Non-standard chunks can be created.
    """

    # Convert options to chunks in the args.chunk list
    if args.gamma:
        v = int(round(1e5 * args.gamma))
        bs = io.BytesIO(struct.pack(">I", v))
        args.chunk.insert(0, Chunk(b"gAMA", bs))
    if args.sigbit:
        v = struct.pack("%dB" % len(args.sigbit), *args.sigbit)
        bs = io.BytesIO(v)
        args.chunk.insert(0, Chunk(b"sBIT", bs))
    if args.iccprofile:
        # http://www.w3.org/TR/PNG/#11iCCP
        v = b"a color profile\x00\x00" + zlib.compress(args.iccprofile.read())
        bs = io.BytesIO(v)
        args.chunk.insert(0, Chunk(b"iCCP", bs))
    if args.transparent:
        # https://www.w3.org/TR/2003/REC-PNG-20031110/#11tRNS
        v = struct.pack(">%dH" % len(args.transparent), *args.transparent)
        bs = io.BytesIO(v)
        args.chunk.insert(0, Chunk(b"tRNS", bs))
    if args.background:
        # https://www.w3.org/TR/2003/REC-PNG-20031110/#11bKGD
        v = struct.pack(">%dH" % len(args.background), *args.background)
        bs = io.BytesIO(v)
        args.chunk.insert(0, Chunk(b"bKGD", bs))
    if args.physical:
        # https://www.w3.org/TR/PNG/#11pHYs
        numbers = re.findall(r"(\d+\.?\d*)", args.physical)
        if len(numbers) not in {1, 2}:
            raise ArgumentError("One or two numbers are required for --physical")
        xppu = float(numbers[0])
        if len(numbers) == 1:
            yppu = xppu
        else:
            yppu = float(numbers[1])

        unit_spec = 0
        if args.physical.endswith("dpi"):
            # Convert from DPI to Pixels Per Metre
            # 1 inch is 0.0254 metres
            l = 0.0254
            xppu /= l
            yppu /= l
            unit_spec = 1
        elif args.physical.endswith("ppm"):
            unit_spec = 1

        v = struct.pack("!LLB", round(xppu), round(yppu), unit_spec)
        bs = io.BytesIO(v)
        args.chunk.insert(0, Chunk(b"pHYs", bs))

    # Create:
    # - a set of chunks to delete
    # - a dict of chunks to replace
    # - a list of chunk to add

    delete = set(args.delete)
    # The set of chunks to replace are those where the specification says
    # that there should be at most one of them.
    replacing = set([b"gAMA", b"pHYs", b"sBIT", b"PLTE", b"tRNS", b"sPLT", b"IHDR"])
    replace = dict()
    add = []

    for chunk in args.chunk:
        if chunk.type in replacing:
            replace[chunk.type] = chunk
        else:
            add.append(chunk)

    input = png.Reader(file=args.input)

    return png.write_chunks(out, edit_chunks(input.chunks(), delete, replace, add))


def edit_chunks(chunks, delete, replace, add):
    """
    Iterate over chunks, yielding edited chunks.
    Subtle: the new chunks have to have their contents .read().
    """
    for type, v in chunks:
        if type in delete:
            continue
        if type in replace:
            yield type, replace[type].content.read()
            del replace[type]
            continue

        if b"IDAT" <= type <= b"IDAT" and replace:
            # If there are any chunks on the replace list by
            # the time we reach IDAT, add then all now.
            # put them all on the add list.
            for chunk in replace.values():
                yield chunk.type, chunk.content.read()
            replace = dict()

        if b"IDAT" <= type <= b"IDAT" and add:
            # We reached IDAT; add all remaining chunks now.
            for chunk in add:
                yield chunk.type, chunk.content.read()
            add = []

        yield type, v


def chunk_name(s):
    """
    Type check a chunk name option value.
    """

    # See https://www.w3.org/TR/2003/REC-PNG-20031110/#table51
    valid = len(s) == 4 and set(s) <= set(string.ascii_letters)
    if not valid:
        raise ValueError("Chunk name must be 4 ASCII letters")
    return s.encode("ascii")


def comma_list(s):
    """
    Convert s, a command separated list of whole numbers,
    into a sequence of int.
    """

    return tuple(int(v) for v in s.split(","))


def hex_color(s):
    """
    Type check and convert a hex color.
    """

    if s.startswith("#"):
        s = s[1:]
    valid = len(s) in [1, 2, 3, 4, 6, 12] and set(s) <= set(string.hexdigits)
    if not valid:
        raise ValueError("colour must be 1,2,3,4,6, or 12 hex-digits")

    # For the 4-bit RGB, expand to 8-bit, by repeating digits.
    if len(s) == 3:
        s = "".join(c + c for c in s)

    if len(s) in [1, 2, 4]:
        # Single grey value.
        return (int(s, 16),)

    if len(s) in [6, 12]:
        w = len(s) // 3
        return tuple(int(s[i : i + w], 16) for i in range(0, len(s), w))


def main(argv=None):
    if argv is None:
        argv = sys.argv

    argv = argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("--gamma", type=float, help="Gamma value for gAMA chunk")
    parser.add_argument(
        "--physical",
        type=str,
        metavar="x[,y][dpi|ppm]",
        help="specify intended pixel size or aspect ratio",
    )
    parser.add_argument(
        "--sigbit",
        type=comma_list,
        metavar="D[,D[,D[,D]]]",
        help="Number of significant bits in each channel",
    )
    parser.add_argument(
        "--iccprofile",
        metavar="file.iccp",
        type=argparse.FileType("rb"),
        help="add an ICC Profile from a file",
    )
    parser.add_argument(
        "--transparent",
        type=hex_color,
        metavar="#RRGGBB",
        help="Specify the colour that is transparent (tRNS chunk)",
    )
    parser.add_argument(
        "--background",
        type=hex_color,
        metavar="#RRGGBB",
        help="background colour for bKGD chunk",
    )
    parser.add_argument(
        "--delete",
        action="append",
        default=[],
        type=chunk_name,
        help="delete the chunk",
    )
    parser.add_argument(
        "--chunk",
        action="append",
        nargs=2,
        default=[],
        type=str,
        help="insert chunk, taking contents from file",
    )
    parser.add_argument(
        "input", nargs="?", default="-", type=png.cli_open, metavar="PNG"
    )

    args = parser.parse_args(argv)

    # Reprocess the chunk arguments, converting each pair into a Chunk.
    args.chunk = [
        Chunk(chunk_name(type), open(path, "rb")) for type, path in args.chunk
    ]

    return process(png.binary_stdout(), args)


if __name__ == "__main__":
    main()
````

## File: venv310/Scripts/pricolpng
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe

# http://www.python.org/doc/2.4.4/lib/module-itertools.html
import itertools
import sys

import png

Description = """Join PNG images in a column top-to-bottom."""


class FormatError(Exception):
    """
    Some problem with the image format.
    """


def join_col(out, l):
    """
    Join the list of images.
    All input images must be same width and
    have the same number of channels.
    They are joined top-to-bottom.
    `out` is the (open file) destination for the output image.
    `l` should be a list of open files (the input image files).
    """

    image = 0
    stream = 0

    # When the first image is read, this will be the reference width,
    # which must be the same for all images.
    width = None
    # Total height (accumulated as images are read).
    height = 0
    # Accumulated rows.
    rows = []

    for f in l:
        stream += 1
        while True:
            im = png.Reader(file=f)
            try:
                im.preamble()
            except EOFError:
                break
            image += 1

            if not width:
                width = im.width
            elif width != im.width:
                raise FormatError('Image %d in stream %d has width %d; does not match %d.' %
                  (image, stream, im.width, width))

            height += im.height
            # Various bugs here because different numbers of channels and depths go wrong.
            w, h, p, info = im.asDirect()
            rows.extend(p)

    # Alarmingly re-use the last info object.
    tinfo = dict(info)
    del tinfo['size']
    w = png.Writer(width, height, **tinfo)

    w.write(out, rows)


def main(argv):
    import argparse

    parser = argparse.ArgumentParser(description=Description)
    parser.add_argument(
        "input", nargs="*", default="-", type=png.cli_open, metavar="PNG"
    )

    args = parser.parse_args()

    return join_col(png.binary_stdout(), args.input)

if __name__ == '__main__':
    main(sys.argv)
````

## File: venv310/Scripts/priditherpng
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe

# pipdither
# Error Diffusing image dithering.
# Now with serpentine scanning.

# See http://www.efg2.com/Lab/Library/ImageProcessing/DHALF.TXT

# http://www.python.org/doc/2.4.4/lib/module-bisect.html
from bisect import bisect_left


import png


def dither(
    out,
    input,
    bitdepth=1,
    linear=False,
    defaultgamma=1.0,
    targetgamma=None,
    cutoff=0.5,  # see :cutoff:default
):
    """Dither the input PNG `inp` into an image with a smaller bit depth
    and write the result image onto `out`.  `bitdepth` specifies the bit
    depth of the new image.

    Normally the source image gamma is honoured (the image is
    converted into a linear light space before being dithered), but
    if the `linear` argument is true then the image is treated as
    being linear already: no gamma conversion is done (this is
    quicker, and if you don't care much about accuracy, it won't
    matter much).

    Images with no gamma indication (no ``gAMA`` chunk) are normally
    treated as linear (gamma = 1.0), but often it can be better
    to assume a different gamma value: For example continuous tone
    photographs intended for presentation on the web often carry
    an implicit assumption of being encoded with a gamma of about
    0.45 (because that's what you get if you just "blat the pixels"
    onto a PC framebuffer), so ``defaultgamma=0.45`` might be a
    good idea.  `defaultgamma` does not override a gamma value
    specified in the file itself: It is only used when the file
    does not specify a gamma.

    If you (pointlessly) specify both `linear` and `defaultgamma`,
    `linear` wins.

    The gamma of the output image is, by default, the same as the input
    image.  The `targetgamma` argument can be used to specify a
    different gamma for the output image.  This effectively recodes the
    image to a different gamma, dithering as we go.  The gamma specified
    is the exponent used to encode the output file (and appears in the
    output PNG's ``gAMA`` chunk); it is usually less than 1.

    """

    # Encoding is what happened when the PNG was made (and also what
    # happens when we output the PNG).  Decoding is what we do to the
    # source PNG in order to process it.

    # The dithering algorithm is not completely general; it
    # can only do bit depth reduction, not arbitrary palette changes.
    import operator

    maxval = 2 ** bitdepth - 1
    r = png.Reader(file=input)

    _, _, pixels, info = r.asDirect()
    planes = info["planes"]
    # :todo: make an Exception
    assert planes == 1
    width = info["size"][0]
    sourcemaxval = 2 ** info["bitdepth"] - 1

    if linear:
        gamma = 1
    else:
        gamma = info.get("gamma") or defaultgamma

    # Calculate an effective gamma for input and output;
    # then build tables using those.

    # `gamma` (whether it was obtained from the input file or an
    # assumed value) is the encoding gamma.
    # We need the decoding gamma, which is the reciprocal.
    decode = 1.0 / gamma

    # `targetdecode` is the assumed gamma that is going to be used
    # to decoding the target PNG.
    # Note that even though we will _encode_ the target PNG we
    # still need the decoding gamma, because
    # the table we use maps from PNG pixel value to linear light level.
    if targetgamma is None:
        targetdecode = decode
    else:
        targetdecode = 1.0 / targetgamma

    incode = build_decode_table(sourcemaxval, decode)

    # For encoding, we still build a decode table, because we
    # use it inverted (searching with bisect).
    outcode = build_decode_table(maxval, targetdecode)

    # The table used for choosing output codes.  These values represent
    # the cutoff points between two adjacent output codes.
    # The cutoff parameter can be varied between 0 and 1 to
    # preferentially choose lighter (when cutoff > 0.5) or
    # darker (when cutoff < 0.5) values.
    # :cutoff:default: The default for this used to be 0.75, but
    # testing by drj on 2021-07-30 showed that this produces
    # banding when dithering left-to-right gradients;
    # test with:
    # priforgepng grl | priditherpng | kitty icat
    choosecode = list(zip(outcode[1:], outcode))
    p = cutoff
    choosecode = [x[0] * p + x[1] * (1.0 - p) for x in choosecode]

    rows = repeat_header(pixels)
    dithered_rows = run_dither(incode, choosecode, outcode, width, rows)
    dithered_rows = remove_header(dithered_rows)

    info["bitdepth"] = bitdepth
    info["gamma"] = 1.0 / targetdecode
    w = png.Writer(**info)
    w.write(out, dithered_rows)


def build_decode_table(maxval, gamma):
    """Build a lookup table for decoding;
    table converts from pixel values to linear space.
    """

    assert maxval == int(maxval)
    assert maxval > 0

    f = 1.0 / maxval
    table = [f * v for v in range(maxval + 1)]
    if gamma != 1.0:
        table = [v ** gamma for v in table]
    return table


def run_dither(incode, choosecode, outcode, width, rows):
    """
    Run an serpentine dither.
    Using the incode and choosecode tables.
    """

    # Errors diffused downwards (into next row)
    ed = [0.0] * width
    flipped = False
    for row in rows:
        # Convert to linear...
        row = [incode[v] for v in row]
        # Add errors...
        row = [e + v for e, v in zip(ed, row)]

        if flipped:
            row = row[::-1]
        targetrow = [0] * width

        for i, v in enumerate(row):
            # `it` will be the index of the chosen target colour;
            it = bisect_left(choosecode, v)
            targetrow[i] = it
            t = outcode[it]
            # err is the error that needs distributing.
            err = v - t

            # Sierra "Filter Lite" distributes          * 2
            # as per this diagram.                    1 1
            ef = err * 0.5
            # :todo: consider making rows one wider at each end and
            # removing "if"s
            if i + 1 < width:
                row[i + 1] += ef
            ef *= 0.5
            ed[i] = ef
            if i:
                ed[i - 1] += ef

        if flipped:
            ed = ed[::-1]
            targetrow = targetrow[::-1]
        yield targetrow
        flipped = not flipped


WARMUP_ROWS = 32


def repeat_header(rows):
    """Repeat the first row, to "warm up" the error register."""
    for row in rows:
        yield row
        for _ in range(WARMUP_ROWS):
            yield row
        break
    yield from rows


def remove_header(rows):
    """Remove the same number of rows that repeat_header added."""

    for _ in range(WARMUP_ROWS):
        next(rows)
    yield from rows


def main(argv=None):
    import sys

    # https://docs.python.org/3.5/library/argparse.html
    import argparse

    parser = argparse.ArgumentParser()

    if argv is None:
        argv = sys.argv

    progname, *args = argv

    parser.add_argument("--bitdepth", type=int, default=1, help="bitdepth of output")
    parser.add_argument(
        "--cutoff",
        type=float,
        default=0.5,
        help="cutoff to select adjacent output values",
    )
    parser.add_argument(
        "--defaultgamma",
        type=float,
        default=1.0,
        help="gamma value to use when no gamma in input",
    )
    parser.add_argument("--linear", action="store_true", help="force linear input")
    parser.add_argument(
        "--targetgamma",
        type=float,
        help="gamma to use in output (target), defaults to input gamma",
    )
    parser.add_argument(
        "input", nargs="?", default="-", type=png.cli_open, metavar="PNG"
    )

    ns = parser.parse_args(args)

    return dither(png.binary_stdout(), **vars(ns))


if __name__ == "__main__":
    main()
````

## File: venv310/Scripts/priforgepng
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe
# priforgepng

"""Forge PNG image from raw computation."""

from array import array
from fractions import Fraction

import argparse
import re
import sys

import png


def gen_glr(x):
    """Gradient Left to Right"""
    return x


def gen_grl(x):
    """Gradient Right to Left"""
    return 1 - x


def gen_gtb(x, y):
    """Gradient Top to Bottom"""
    return y


def gen_gbt(x, y):
    """Gradient Bottom to Top"""
    return 1.0 - y


def gen_rtl(x, y):
    """Radial gradient, centred at Top-Left"""
    return max(1 - (float(x) ** 2 + float(y) ** 2) ** 0.5, 0.0)


def gen_rctr(x, y):
    """Radial gradient, centred at Centre"""
    return gen_rtl(float(x) - 0.5, float(y) - 0.5)


def gen_rtr(x, y):
    """Radial gradient, centred at Top-Right"""
    return gen_rtl(1.0 - float(x), y)


def gen_rbl(x, y):
    """Radial gradient, centred at Bottom-Left"""
    return gen_rtl(x, 1.0 - float(y))


def gen_rbr(x, y):
    """Radial gradient, centred at Bottom-Right"""
    return gen_rtl(1.0 - float(x), 1.0 - float(y))


def stripe(x, n):
    return int(x * n) & 1


def gen_vs2(x):
    """2 Vertical Stripes"""
    return stripe(x, 2)


def gen_vs4(x):
    """4 Vertical Stripes"""
    return stripe(x, 4)


def gen_vs10(x):
    """10 Vertical Stripes"""
    return stripe(x, 10)


def gen_hs2(x, y):
    """2 Horizontal Stripes"""
    return stripe(float(y), 2)


def gen_hs4(x, y):
    """4 Horizontal Stripes"""
    return stripe(float(y), 4)


def gen_hs10(x, y):
    """10 Horizontal Stripes"""
    return stripe(float(y), 10)


def gen_slr(x, y):
    """10 diagonal stripes, rising from Left to Right"""
    return stripe(x + y, 10)


def gen_srl(x, y):
    """10 diagonal stripes, rising from Right to Left"""
    return stripe(1 + x - y, 10)


def checker(x, y, n):
    return stripe(x, n) ^ stripe(y, n)


def gen_ck8(x, y):
    """8 by 8 checkerboard"""
    return checker(x, y, 8)


def gen_ck15(x, y):
    """15 by 15 checkerboard"""
    return checker(x, y, 15)


def gen_zero(x):
    """All zero (black)"""
    return 0


def gen_one(x):
    """All one (white)"""
    return 1


def yield_fun_rows(size, bitdepth, pattern):
    """
    Create a single channel (monochrome) test pattern.
    Yield each row in turn.
    """

    width, height = size

    maxval = 2 ** bitdepth - 1
    if maxval > 255:
        typecode = "H"
    else:
        typecode = "B"
    pfun = pattern_function(pattern)

    # The coordinates are an integer + 0.5,
    # effectively sampling each pixel at its centre.
    # This is morally better, and produces all 256 sample values
    # in a 256-pixel wide gradient.

    # We make a list of x coordinates here and re-use it,
    # because Fraction instances are slow to allocate.
    xs = [Fraction(x, 2 * width) for x in range(1, 2 * width, 2)]

    # The general case is a function in x and y,
    # but if the function only takes an x argument,
    # it's handled in a special case that is a lot faster.
    if n_args(pfun) == 2:
        for y in range(height):
            a = array(typecode)
            fy = Fraction(Fraction(y + 0.5), height)
            for fx in xs:
                a.append(int(round(maxval * pfun(fx, fy))))
            yield a
        return

    # For functions in x only, it's a _lot_ faster
    # to generate a single row and repeatedly yield it
    a = array(typecode)
    for fx in xs:
        a.append(int(round(maxval * pfun(x=fx))))
    for y in range(height):
        yield a
    return


def generate(args):
    """
    Create a PNG test image and write the file to stdout.

    `args` should be an argparse Namespace instance or similar.
    """

    size = args.size
    bitdepth = args.depth

    out = png.binary_stdout()

    for pattern in args.pattern:
        rows = yield_fun_rows(size, bitdepth, pattern)
        writer = png.Writer(
            size[0], size[1], bitdepth=bitdepth, greyscale=True, alpha=False
        )
        writer.write(out, rows)


def n_args(fun):
    """Number of arguments in fun's argument list."""
    return fun.__code__.co_argcount


def pattern_function(pattern):
    """From `pattern`, a string,
    return the function for that pattern.
    """

    lpat = pattern.lower()
    for name, fun in globals().items():
        parts = name.split("_")
        if parts[0] != "gen":
            continue
        if parts[1] == lpat:
            return fun


def patterns():
    """
    List the patterns.
    """

    for name, fun in globals().items():
        parts = name.split("_")
        if parts[0] == "gen":
            yield parts[1], fun.__doc__


def dimensions(s):
    """
    Typecheck the --size option, which should be
    one or two comma separated numbers.
    Example: "64,40".
    """

    tupl = re.findall(r"\d+", s)
    if len(tupl) not in (1, 2):
        raise ValueError("%r should be width or width,height" % s)
    if len(tupl) == 1:
        tupl *= 2
    assert len(tupl) == 2
    return list(map(int, tupl))


def main(argv=None):
    if argv is None:
        argv = sys.argv
    parser = argparse.ArgumentParser(description="Forge greyscale PNG patterns")

    parser.add_argument(
        "-l", "--list", action="store_true", help="print list of patterns and exit"
    )
    parser.add_argument(
        "-d", "--depth", default=8, type=int, metavar="N", help="N bits per pixel"
    )
    parser.add_argument(
        "-s",
        "--size",
        default=[256, 256],
        type=dimensions,
        metavar="w[,h]",
        help="width and height of the image in pixels",
    )
    parser.add_argument("pattern", nargs="*", help="name of pattern")

    args = parser.parse_args(argv[1:])

    if args.list:
        for name, doc in sorted(patterns()):
            print(name, doc, sep="\t")
        return

    if not args.pattern:
        parser.error("--list or pattern is required")
    return generate(args)


if __name__ == "__main__":
    main()
````

## File: venv310/Scripts/prigreypng
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe

# prigreypng

# Convert image to grey (L, or LA), but only if that involves no colour change.

import argparse
import array


import png


def as_grey(out, inp):
    """
    Convert image to greyscale, but only when no colour change.
    This works by using the input G channel (green) as
    the output L channel (luminance) and
    checking that every pixel is grey as we go.
    A non-grey pixel will raise an error.
    """

    r = png.Reader(file=inp)
    _, _, rows, info = r.asDirect()
    if info["greyscale"]:
        w = png.Writer(**info)
        return w.write(out, rows)

    planes = info["planes"]
    targetplanes = planes - 2
    alpha = info["alpha"]
    width, height = info["size"]
    typecode = "BH"[info["bitdepth"] > 8]

    # Values per target row
    vpr = width * targetplanes

    def iterasgrey():
        for i, row in enumerate(rows):
            row = array.array(typecode, row)
            targetrow = array.array(typecode, [0] * vpr)
            # Copy G (and possibly A) channel.
            green = row[0::planes]
            if alpha:
                targetrow[0::2] = green
                targetrow[1::2] = row[3::4]
            else:
                targetrow = green
            # Check R and B channel match.
            if green != row[0::planes] or green != row[2::planes]:
                raise ValueError("Row %i contains non-grey pixel." % i)
            yield targetrow

    info["greyscale"] = True
    del info["planes"]
    w = png.Writer(**info)
    return w.write(out, iterasgrey())


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", nargs="?", default="-", type=png.cli_open, metavar="PNG"
    )
    args = parser.parse_args()
    return as_grey(png.binary_stdout(), args.input)


if __name__ == "__main__":
    import sys

    sys.exit(main())
````

## File: venv310/Scripts/pripalpng
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe
# pripalpng


"""Convert to Palette PNG (without changing colours)"""

import argparse
import collections

# https://docs.python.org/2.7/library/io.html
import io
import string
import zlib

# Local module.
import png


def make_inverse_palette(rows, channels):
    """
    The inverse palette maps from tuple to palette index.
    """

    palette = {}

    for row in rows:
        for pixel in png.group(row, channels):
            if pixel in palette:
                continue
            palette[pixel] = len(palette)
    return palette


def palette_convert(out, inp, palette_file):
    """
    Convert PNG image in `inp` to use a palette, colour type 3,
    and write converted image to `out`.

    `palette_file` is a file descriptor for the palette to use.

    If `palette_file` is None, then `inp` is used as the palette.
    """

    if palette_file is None:
        inp, palette_file = palette_file, inp

    reader = png.Reader(file=palette_file)
    w, h, rows, info = asRGBorA8(reader)
    channels = info["planes"]
    if not inp:
        rows = list(rows)

    palette_map = make_inverse_palette(rows, channels)

    if inp:
        reader = png.Reader(file=inp)
        w, h, rows, info = asRGBorA8(reader)
        channels = info["planes"]

    # Default for colours not in palette is to use last entry.
    last = len(palette_map) - 1

    def map_pixel(p):
        return palette_map.get(p, last)

    def convert_rows():
        for row in rows:
            yield [map_pixel(p) for p in png.group(row, channels)]

    # Make a palette by sorting the pixels according to their index.
    palette = sorted(palette_map.keys(), key=palette_map.get)
    pal_info = dict(size=info["size"], palette=palette)

    w = png.Writer(**pal_info)
    w.write(out, convert_rows())


def asRGBorA8(reader):
    """
    Return (width, height, rows, info) converting to RGB,
    or RGBA if original has an alpha channel.
    """
    _, _, _, info = reader.read()
    if info["alpha"]:
        return reader.asRGBA8()
    else:
        return reader.asRGB8()


def main(argv=None):
    import sys
    import re

    if argv is None:
        argv = sys.argv

    argv = argv[1:]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--palette", type=png.cli_open)
    parser.add_argument(
        "input", nargs="?", default="-", type=png.cli_open, metavar="PNG"
    )

    args = parser.parse_args(argv)

    palette_convert(png.binary_stdout(), args.input, args.palette)


if __name__ == "__main__":
    main()
````

## File: venv310/Scripts/pripamtopng
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe

# pripamtopng
#
# Python Raster Image PAM to PNG

import array
import struct
import sys

import png

Description = """Convert NetPBM PAM/PNM format files to PNG."""


def read_pam_header(infile):
    """
    Read (the rest of a) PAM header.
    `infile` should be positioned immediately after the initial 'P7' line
    (at the beginning of the second line).
    Returns are as for `read_pnm_header`.
    """

    # Unlike PBM, PGM, and PPM, we can read the header a line at a time.
    header = dict()
    while True:
        line = infile.readline().strip()
        if line == b"ENDHDR":
            break
        if not line:
            raise EOFError("PAM ended prematurely")
        if line[0] == b"#":
            continue
        line = line.split(None, 1)
        key = line[0]
        if key not in header:
            header[key] = line[1]
        else:
            header[key] += b" " + line[1]

    required = [b"WIDTH", b"HEIGHT", b"DEPTH", b"MAXVAL"]
    required_str = b", ".join(required).decode("ascii")
    result = []
    for token in required:
        if token not in header:
            raise png.Error("PAM file must specify " + required_str)
        try:
            x = int(header[token])
        except ValueError:
            raise png.Error(required_str + " must all be valid integers")
        if x <= 0:
            raise png.Error(required_str + " must all be positive integers")
        result.append(x)

    return (b"P7",) + tuple(result)


def read_pnm_header(infile):
    """
    Read a PNM header, returning (format,width,height,depth,maxval).
    Also reads a PAM header (by using a helper function).
    `width` and `height` are in pixels.
    `depth` is the number of channels in the image;
    for PBM and PGM it is synthesized as 1, for PPM as 3;
    for PAM images it is read from the header.
    `maxval` is synthesized (as 1) for PBM images.
    """

    # Generally, see http://netpbm.sourceforge.net/doc/ppm.html
    # and http://netpbm.sourceforge.net/doc/pam.html

    # Technically 'P7' must be followed by a newline,
    # so by using rstrip() we are being liberal in what we accept.
    # I think this is acceptable.
    magic = infile.read(3).rstrip()
    if magic == b"P7":
        # PAM header parsing is completely different.
        return read_pam_header(infile)

    # Expected number of tokens in header (3 for P4, 4 for P6)
    expected = 4
    pbm = (b"P1", b"P4")
    if magic in pbm:
        expected = 3
    header = [magic]

    # We must read the rest of the header byte by byte because
    # the final whitespace character may not be a newline.
    # Of course all PNM files in the wild use a newline at this point,
    # but we are strong and so we avoid
    # the temptation to use readline.
    bs = bytearray()
    backs = bytearray()

    def next():
        if backs:
            c = bytes(backs[0:1])
            del backs[0]
        else:
            c = infile.read(1)
            if not c:
                raise png.Error("premature EOF reading PNM header")
        bs.extend(c)
        return c

    def backup():
        """Push last byte of token onto front of backs."""
        backs.insert(0, bs[-1])
        del bs[-1]

    def ignore():
        del bs[:]

    def tokens():
        ls = lexInit
        while True:
            token, ls = ls()
            if token:
                yield token

    def lexInit():
        c = next()
        # Skip comments
        if b"#" <= c <= b"#":
            while c not in b"\n\r":
                c = next()
            ignore()
            return None, lexInit
        # Skip whitespace (that precedes a token)
        if c.isspace():
            ignore()
            return None, lexInit
        if not c.isdigit():
            raise png.Error("unexpected byte %r found in header" % c)
        return None, lexNumber

    def lexNumber():
        # According to the specification it is legal to have comments
        # that appear in the middle of a token.
        # I've never seen it; and,
        # it's a bit awkward to code good lexers in Python (no goto).
        # So we break on such cases.
        c = next()
        while c.isdigit():
            c = next()
        backup()
        token = bs[:]
        ignore()
        return token, lexInit

    for token in tokens():
        # All "tokens" are decimal integers, so convert them here.
        header.append(int(token))
        if len(header) == expected:
            break

    final = next()
    if not final.isspace():
        raise png.Error("expected header to end with whitespace, not %r" % final)

    if magic in pbm:
        # synthesize a MAXVAL
        header.append(1)
    depth = (1, 3)[magic == b"P6"]
    return header[0], header[1], header[2], depth, header[3]


def convert_pnm_plain(w, infile, outfile):
    """
    Convert a plain PNM file containing raw pixel data into
    a PNG file with the parameters set in the writer object.
    Works for plain PGM formats.
    """

    # See convert_pnm_binary for the corresponding function for
    # binary PNM formats.

    rows = scan_rows_from_file_plain(infile, w.width, w.height, w.planes)
    w.write(outfile, rows)


def scan_rows_from_file_plain(infile, width, height, planes):
    """
    Generate a sequence of rows from the input file `infile`.
    The input file should be in a "Netpbm-like" plain format.
    The input file should be positioned at the beginning of the
    first value (that is, immediately after the header).
    The number of pixels to read is taken from
    the image dimensions (`width`, `height`, `planes`).

    Each row is yielded as a single sequence of values.
    """

    # Values per row
    vpr = width * planes

    values = []
    rows_output = 0

    # The core problem is that input lines (text lines) may not
    # correspond with pixel rows. We use two nested loops.
    # The outer loop reads the input one text line at a time;
    # this will contain a whole number of values, which are
    # added to the `values` list.
    # The inner loop strips the first `vpr` values from the
    # list, until there aren't enough.
    # Note we can't tell how many iterations the inner loop will
    # run for, it could be 0 (if not enough values were read to
    # make a whole pixel row) or many (if the entire image were
    # on one input line), or somewhere in between.
    # In PNM there is in general no requirement to have
    # correspondence between text lines and pixel rows.

    for inp in infile:
        values.extend(map(int, inp.split()))
        while len(values) >= vpr:
            yield values[:vpr]
            del values[:vpr]
            rows_output += 1
            if rows_output >= height:
                # Diagnostic here if there are spare values?
                return
    # Diagnostic here for early EOF?


def convert_pnm_binary(w, infile, outfile):
    """
    Convert a PNM file containing raw pixel data into
    a PNG file with the parameters set in the writer object.
    Works for (binary) PGM, PPM, and PAM formats.
    """

    rows = scan_rows_from_file(infile, w.width, w.height, w.planes, w.bitdepth)
    w.write(outfile, rows)


def scan_rows_from_file(infile, width, height, planes, bitdepth):
    """
    Generate a sequence of rows from the input file `infile`.
    The input file should be in a "Netpbm-like" binary format.
    The input file should be positioned at the beginning of the first pixel.
    The number of pixels to read is taken from
    the image dimensions (`width`, `height`, `planes`);
    the number of bytes per value is implied by `bitdepth`.
    Each row is yielded as a single sequence of values.
    """

    # Values per row
    vpr = width * planes
    # Bytes per row
    bpr = vpr
    if bitdepth > 8:
        assert bitdepth == 16
        bpr *= 2
        fmt = ">%dH" % vpr

        def line():
            return array.array("H", struct.unpack(fmt, infile.read(bpr)))

    else:

        def line():
            return array.array("B", infile.read(bpr))

    for y in range(height):
        yield line()


def parse_args(args):
    """
    Create a parser and parse the command line arguments.
    """
    from argparse import ArgumentParser

    parser = ArgumentParser(description=Description)
    version = "%(prog)s " + png.__version__
    parser.add_argument("--version", action="version", version=version)
    parser.add_argument(
        "-c",
        "--compression",
        type=int,
        metavar="level",
        help="zlib compression level (0-9)",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        type=png.cli_open,
        metavar="PAM/PNM",
        help="input PAM/PNM file to convert",
    )
    args = parser.parse_args(args)
    return args


def main(argv=None):
    if argv is None:
        argv = sys.argv

    args = parse_args(argv[1:])

    # Prepare input and output files
    infile = args.input

    # Call after parsing, so that --version and --help work.
    outfile = png.binary_stdout()

    # Encode PNM to PNG
    format, width, height, depth, maxval = read_pnm_header(infile)

    ok_formats = (b"P2", b"P5", b"P6", b"P7")
    if format not in ok_formats:
        raise NotImplementedError("file format %s not supported" % format)

    # The NetPBM depth (number of channels) completely
    # determines the PNG format.
    # Observe:
    # - L, LA, RGB, RGBA are the 4 modes supported by PNG;
    # - they correspond to 1, 2, 3, 4 channels respectively.
    # We use the number of channels in the source image to
    # determine which one we have.
    # We ignore the NetPBM image type and the PAM TUPLTYPE.
    greyscale = depth <= 2
    pamalpha = depth in (2, 4)
    supported = [2 ** x - 1 for x in range(1, 17)]
    try:
        mi = supported.index(maxval)
    except ValueError:
        raise NotImplementedError(
            "input maxval (%s) not in supported list %s" % (maxval, str(supported))
        )
    bitdepth = mi + 1
    writer = png.Writer(
        width,
        height,
        greyscale=greyscale,
        bitdepth=bitdepth,
        alpha=pamalpha,
        compression=args.compression,
    )

    plain = format in (b"P1", b"P2", b"P3")
    if plain:
        convert_pnm_plain(writer, infile, outfile)
    else:
        convert_pnm_binary(writer, infile, outfile)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except png.Error as e:
        print(e, file=sys.stderr)
        sys.exit(99)
````

## File: venv310/Scripts/priplan9topng
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe

# Imported from //depot/prj/plan9topam/master/code/plan9topam.py#4 on
# 2009-06-15.

"""Command line tool to convert from Plan 9 image format to PNG format.

Plan 9 image format description:
https://plan9.io/magic/man2html/6/image

Where possible this tool will use unbuffered read() calls,
so that when finished the file offset is exactly at the end of
the image data.
This is useful for Plan9 subfont files which place font metric
data immediately after the image.
"""

# Test materials

# asset/left.bit is a Plan 9 image file, a leftwards facing Glenda.
# Other materials have to be scrounged from the internet.
# https://plan9.io/sources/plan9/sys/games/lib/sokoban/images/cargo.bit

import array
import collections
import io

# http://www.python.org/doc/2.3.5/lib/module-itertools.html
import itertools
import os

# http://www.python.org/doc/2.3.5/lib/module-re.html
import re
import struct

# http://www.python.org/doc/2.3.5/lib/module-sys.html
import sys

# https://docs.python.org/3/library/tarfile.html
import tarfile


# https://pypi.org/project/pypng/
import png

# internal
import prix


class Error(Exception):
    """Some sort of Plan 9 image error."""


def block(s, n):
    return zip(*[iter(s)] * n)


def plan9_as_image(inp):
    """Represent a Plan 9 image file as a png.Image instance, so
    that it can be written as a PNG file.
    Works with compressed input files and may work with uncompressed files.
    """

    # Use inp.raw if available.
    # This avoids buffering and means that when the image is processed,
    # the resulting input stream is cued up exactly at the end
    # of the image.
    inp = getattr(inp, "raw", inp)

    info, blocks = plan9_open_image(inp)

    rows, infodict = plan9_image_rows(blocks, info)

    return png.Image(rows, infodict)


def plan9_open_image(inp):
    """Open a Plan9 image file (`inp` should be an already open
    file object), and return (`info`, `blocks`) pair.
    `info` should be a Plan9 5-tuple;
    `blocks` is the input, and it should yield (`row`, `data`)
    pairs (see :meth:`pixmeta`).
    """

    r = inp.read(11)
    if r == b"compressed\n":
        info, blocks = decompress(inp)
    else:
        # Since Python 3, there is a good chance that this path
        # doesn't work.
        info, blocks = glue(inp, r)

    return info, blocks


def glue(f, r):
    """Return (info, stream) pair, given `r` the initial portion of
    the metadata that has already been read from the stream `f`.
    """

    r = r + f.read(60 - len(r))
    return (meta(r), f)


def meta(r):
    """Convert 60 byte bytestring `r`, the metadata from an image file.
    Returns a 5-tuple (*chan*,*minx*,*miny*,*limx*,*limy*).
    5-tuples may settle into lists in transit.

    As per https://plan9.io/magic/man2html/6/image the metadata
    comprises 5 words separated by blanks.
    As it happens each word starts at an index that is a multiple of 12,
    but this routine does not care about that.
    """

    r = r.split()
    # :todo: raise FormatError
    if 5 != len(r):
        raise Error("Expected 5 space-separated words in metadata")
    r = [r[0]] + [int(x) for x in r[1:]]
    return r


def bitdepthof(chan):
    """Return the bitdepth for a Plan9 pixel format string."""

    maxd = 0
    for c in re.findall(rb"[a-z]\d*", chan):
        if c[0] != "x":
            maxd = max(maxd, int(c[1:]))
    return maxd


def maxvalof(chan):
    """Return the netpbm MAXVAL for a Plan9 pixel format string."""

    bitdepth = bitdepthof(chan)
    return (2 ** bitdepth) - 1


def plan9_image_rows(blocks, metadata):
    """
    Convert (uncompressed) Plan 9 image file to pair of (*rows*, *info*).
    This is intended to be used by PyPNG format.
    *info* is the image info (metadata) returned in a dictionary,
    *rows* is an iterator that yields each row in
    boxed row flat pixel format.

    `blocks`, should be an iterator of (`row`, `data`) pairs.
    """

    chan, minx, miny, limx, limy = metadata
    rows = limy - miny
    width = limx - minx
    nchans = len(re.findall(b"[a-wyz]", chan))
    alpha = b"a" in chan
    # Iverson's convention for the win!
    ncolour = nchans - alpha
    greyscale = ncolour == 1
    bitdepth = bitdepthof(chan)
    maxval = maxvalof(chan)

    # PNG style info dict.
    meta = dict(
        size=(width, rows),
        bitdepth=bitdepth,
        greyscale=greyscale,
        alpha=alpha,
        planes=nchans,
    )

    arraycode = "BH"[bitdepth > 8]

    return (
        map(
            lambda x: array.array(arraycode, itertools.chain(*x)),
            block(unpack(blocks, rows, width, chan, maxval), width),
        ),
        meta,
    )


def unpack(f, rows, width, chan, maxval):
    """Unpack `f` into pixels.
    `chan` describes the pixel format using
    the Plan9 syntax ("k8", "r8g8b8", and so on).
    Assumes the pixel format has a total channel bit depth
    that is either a multiple or a divisor of 8
    (the Plan9 image specification requires this).
    `f` should be an iterator that returns blocks of input such that
    each block contains a whole number of pixels.
    The return value is an iterator that yields each pixel as an n-tuple.
    """

    def mask(w):
        """An integer, to be used as a mask, with bottom `w` bits set to 1."""

        return (1 << w) - 1

    def deblock(f, depth, width):
        """A "packer" used to convert multiple bytes into single pixels.
        `depth` is the pixel depth in bits (>= 8), `width` is the row width in
        pixels.
        """

        w = depth // 8
        i = 0
        for block in f:
            for i in range(len(block) // w):
                p = block[w * i : w * (i + 1)]
                i += w
                # Convert little-endian p to integer x
                x = 0
                s = 1  # scale
                for j in p:
                    x += s * j
                    s <<= 8
                yield x

    def bitfunge(f, depth, width):
        """A "packer" used to convert single bytes into multiple pixels.
        Depth is the pixel depth (< 8), width is the row width in pixels.
        """

        assert 8 / depth == 8 // depth

        for block in f:
            col = 0
            for x in block:
                for j in range(8 // depth):
                    yield x >> (8 - depth)
                    col += 1
                    if col == width:
                        # A row-end forces a new byte even if
                        # we haven't consumed all of the current byte.
                        # Effectively rows are bit-padded to make
                        # a whole number of bytes.
                        col = 0
                        break
                    x <<= depth

    # number of bits in each channel
    bits = [int(d) for d in re.findall(rb"\d+", chan)]
    # colr of each channel
    # (r, g, b, k for actual colours, and
    # a, m, x for alpha, map-index, and unused)
    colr = re.findall(b"[a-z]", chan)

    depth = sum(bits)

    # Select a "packer" that either:
    # - gathers multiple bytes into a single pixel (for depth >= 8); or,
    # - splits bytes into several pixels (for depth < 8).
    if depth >= 8:
        assert depth % 8 == 0
        packer = deblock
    else:
        assert 8 % depth == 0
        packer = bitfunge

    for x in packer(f, depth, width):
        # x is the pixel as an unsigned integer
        o = []
        # This is a bit yucky.
        # Extract each channel from the _most_ significant part of x.
        for b, col in zip(bits, colr):
            v = (x >> (depth - b)) & mask(b)
            x <<= b
            if col != "x":
                # scale to maxval
                v = v * float(maxval) / mask(b)
                v = int(v + 0.5)
                o.append(v)
        yield o


def decompress(f):
    """Decompress a Plan 9 image file.
    The input `f` should be a binary file object that
    is already cued past the initial 'compressed\n' string.
    The return result is (`info`, `blocks`);
    `info` is a 5-tuple of the Plan 9 image metadata;
    `blocks` is an iterator that yields a (row, data) pair
    for each block of data.
    """

    r = meta(f.read(60))
    return r, decomprest(f, r[4])


def decomprest(f, rows):
    """Iterator that decompresses the rest of a file once the metadata
    have been consumed."""

    row = 0
    while row < rows:
        row, o = deblock(f)
        yield o


def deblock(f):
    """Decompress a single block from a compressed Plan 9 image file.
    Each block starts with 2 decimal strings of 12 bytes each.
    Yields a sequence of (row, data) pairs where
    `row` is the total number of rows processed
    (according to the file format) and
    `data` is the decompressed data for this block.
    """

    row = int(f.read(12))
    size = int(f.read(12))
    if not (0 <= size <= 6000):
        raise Error("block has invalid size; not a Plan 9 image file?")

    # Since each block is at most 6000 bytes we may as well read it all in
    # one go.
    d = f.read(size)
    i = 0
    o = []

    while i < size:
        x = d[i]
        i += 1
        if x & 0x80:
            x = (x & 0x7F) + 1
            lit = d[i : i + x]
            i += x
            o.extend(lit)
            continue
        # x's high-order bit is 0
        length = (x >> 2) + 3
        # Offset is made from bottom 2 bits of x and 8 bits of next byte.
        #     MSByte                                 LSByte
        #   +---------------------+-------------------------+
        #   | - - - - - - | x1 x0 | d7 d6 d5 d4 d3 d2 d1 d0 |
        #   +-----------------------------------------------+
        # Had to discover by inspection which way round the bits go,
        # because https://plan9.io/magic/man2html/6/image doesn't say.
        # that x's 2 bits are most significant.
        offset = (x & 3) << 8
        offset |= d[i]
        i += 1
        # Note: complement operator neatly maps (0 to 1023) to (-1 to
        # -1024).  Adding len(o) gives a (non-negative) offset into o from
        # which to start indexing.
        offset = ~offset + len(o)
        if offset < 0:
            raise Error(
                "byte offset indexes off the begininning of "
                "the output buffer; not a Plan 9 image file?"
            )
        for j in range(length):
            o.append(o[offset + j])
    return row, bytes(o)


FontChar = collections.namedtuple("FontChar", "x top bottom left width")


def font_copy(inp, image, out, control):
    """
    Convert a Plan 9 font (`inp`, `image`) to a series of PNG images,
    and write them out as a tar file to the file object `out`.
    Write a text control file out to the file object `control`.

    Each valid glyph in the font becomes a single PNG image;
    the output is a tar file of all the images.

    A Plan 9 font consists of a Plan 9 image immediately
    followed by font data.
    The image for the font should be the `image` argument,
    the file containing the rest of the font data should be the
    file object `inp` which should be cued up to the start of
    the font data that immediately follows the image.

    https://plan9.io/magic/man2html/6/font
    """

    # The format is a little unusual, and isn't completely
    # clearly documented.
    # Each 6-byte structure (see FontChar above) defines
    # a rectangular region of the image that is used for each
    # glyph.
    # The source image region that is used may be strictly
    # smaller than the rectangle for the target glyph.
    # This seems like a micro-optimisation.
    # For each glyph,
    # rows above `top` and below `bottom` will not be copied
    # from the source (they can be assumed to be blank).
    # No space is saved in the source image, since the rows must
    # be present.
    # `x` is always non-decreasing, so the glyphs appear strictly
    # left-to-image in the source image.
    # The x of the next glyph is used to
    # infer the width of the source rectangle.
    # `top` and `bottom` give the y-coordinate of the top- and
    # bottom- sides of the rectangle in both source and targets.
    # `left` is the x-coordinate of the left-side of the
    # rectangle in the target glyph. (equivalently, the amount
    # of padding that should be added on the left).
    # `width` is the advance-width of the glyph; by convention
    # it is 0 for an undefined glyph.

    name = getattr(inp, "name", "*subfont*name*not*supplied*")

    header = inp.read(36)
    n, height, ascent = [int(x) for x in header.split()]
    print("baseline", name, ascent, file=control, sep=",")

    chs = []
    for i in range(n + 1):
        bs = inp.read(6)
        ch = FontChar(*struct.unpack("<HBBBB", bs))
        chs.append(ch)

    tar = tarfile.open(mode="w|", fileobj=out)

    # Start at 0, increment for every image output
    # (recall that not every input glyph has an output image)
    output_index = 0
    for i in range(n):
        ch = chs[i]
        if ch.width == 0:
            continue

        print("png", "index", output_index, "glyph", name, i, file=control, sep=",")

        info = dict(image.info, size=(ch.width, height))
        target = new_image(info)

        source_width = chs[i + 1].x - ch.x
        rect = ((ch.left, ch.top), (ch.left + source_width, ch.bottom))
        image_draw(target, rect, image, (ch.x, ch.top))

        # :todo: add source, glyph, and baseline data here (as a
        # private tag?)
        o = io.BytesIO()
        target.write(o)
        binary_size = o.tell()
        o.seek(0)

        tarinfo = tar.gettarinfo(arcname="%s/glyph%d.png" % (name, i), fileobj=inp)
        tarinfo.size = binary_size
        tar.addfile(tarinfo, fileobj=o)

        output_index += 1

    tar.close()


def new_image(info):
    """Return a fresh png.Image instance."""

    width, height = info["size"]
    vpr = width * info["planes"]
    row = lambda: [0] * vpr
    rows = [row() for _ in range(height)]
    return png.Image(rows, info)


def image_draw(target, rect, source, point):
    """The point `point` in the source image is aligned with the
    top-left of rect in the target image, and then the rectangle
    in target is replaced with the pixels from `source`.

    This routine assumes that both source and target can have
    their rows objects indexed (not streamed).
    """

    # :todo: there is no attempt to do clipping or channel or
    # colour conversion. But maybe later?

    if target.info["planes"] != source.info["planes"]:
        raise NotImplementedError(
            "source and target must have the same number of planes"
        )

    if target.info["bitdepth"] != source.info["bitdepth"]:
        raise NotImplementedError("source and target must have the same bitdepth")

    tl, br = rect
    left, top = tl
    right, bottom = br
    height = bottom - top

    planes = source.info["planes"]

    vpr = (right - left) * planes
    source_left, source_top = point

    source_l = source_left * planes
    source_r = source_l + vpr

    target_l = left * planes
    target_r = target_l + vpr

    for y in range(height):
        row = source.rows[y + source_top]
        row = row[source_l:source_r]
        target.rows[top + y][target_l:target_r] = row


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Convert Plan9 image to PNG")
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        type=png.cli_open,
        metavar="image",
        help="image file in Plan 9 format",
    )
    parser.add_argument(
        "--control",
        default=os.path.devnull,
        type=argparse.FileType("w"),
        metavar="ControlCSV",
        help="(when using --font) write a control CSV file to named file",
    )
    parser.add_argument(
        "--font",
        action="store_true",
        help="process as Plan 9 subfont: output a tar file of PNGs",
    )

    args = parser.parse_args()

    image = plan9_as_image(args.input)
    image.stream()

    if not args.font:
        image.write(png.binary_stdout())
    else:
        font_copy(args.input, image, png.binary_stdout(), args.control)


if __name__ == "__main__":
    sys.exit(main())
````

## File: venv310/Scripts/pripnglsch
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe
# pripnglsch
# PNG List Chunks

import png


def list_chunks(out, inp):
    r = png.Reader(file=inp)
    for t, v in r.chunks():
        add = ""
        if len(v) <= 28:
            add = " " + v.hex()
        else:
            add = " " + v[:26].hex() + "..."
        t = t.decode("ascii")
        print("%s %10d%s" % (t, len(v), add), file=out)


def main(argv=None):
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input", nargs="?", default="-", type=png.cli_open, metavar="PNG"
    )
    args = parser.parse_args()
    return list_chunks(sys.stdout, args.input)


if __name__ == "__main__":
    main()
````

## File: venv310/Scripts/pripngtopam
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe

import struct

import png


def write_pnm(file, plain, rows, meta):
    """
    Write a Netpbm PNM (or PAM) file.
    *file* output file object;
    *plain* (a bool) true if writing plain format (not possible for PAM);
    *rows* an iterator for the rows;
    *meta* the info dictionary.
    """

    meta = dict(meta)
    meta["maxval"] = 2 ** meta["bitdepth"] - 1
    meta["width"], meta["height"] = meta["size"]

    # Number of planes determines both image formats:
    # 1 : L to PGM
    # 2 : LA to PAM
    # 3 : RGB to PPM
    # 4 : RGBA to PAM
    planes = meta["planes"]

    # Assume inputs are from a PNG file.
    assert planes in (1, 2, 3, 4)
    if planes in (1, 3):
        if 1 == planes:
            # PGM
            # Even if maxval is 1 we use PGM instead of PBM,
            # to avoid converting data.
            magic = "P5"
            if plain:
                magic = "P2"
        else:
            # PPM
            magic = "P6"
            if plain:
                magic = "P3"
        header = "{magic} {width:d} {height:d} {maxval:d}\n".format(magic=magic, **meta)
    if planes in (2, 4):
        # PAM
        # See http://netpbm.sourceforge.net/doc/pam.html
        if plain:
            raise Exception("PAM (%d-plane) does not support plain format" % planes)
        if 2 == planes:
            tupltype = "GRAYSCALE_ALPHA"
        else:
            tupltype = "RGB_ALPHA"
        header = (
            "P7\nWIDTH {width:d}\nHEIGHT {height:d}\n"
            "DEPTH {planes:d}\nMAXVAL {maxval:d}\n"
            "TUPLTYPE {tupltype}\nENDHDR\n".format(tupltype=tupltype, **meta)
        )
    file.write(header.encode("ascii"))

    # Values per row
    vpr = planes * meta["width"]

    if plain:
        for row in rows:
            row_b = b" ".join([b"%d" % v for v in row])
            file.write(row_b)
            file.write(b"\n")
    else:
        # format for struct.pack
        fmt = ">%d" % vpr
        if meta["maxval"] > 0xFF:
            fmt = fmt + "H"
        else:
            fmt = fmt + "B"
        for row in rows:
            file.write(struct.pack(fmt, *row))

    file.flush()


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Convert PNG to PAM")
    parser.add_argument("--plain", action="store_true")
    parser.add_argument(
        "input", nargs="?", default="-", type=png.cli_open, metavar="PNG"
    )

    args = parser.parse_args()

    # Encode PNG to PNM (or PAM)
    image = png.Reader(file=args.input)
    _, _, rows, info = image.asDirect()
    write_pnm(png.binary_stdout(), args.plain, rows, info)


if __name__ == "__main__":
    import sys

    sys.exit(main())
````

## File: venv310/Scripts/prirowpng
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe

# http://www.python.org/doc/2.4.4/lib/module-itertools.html
import itertools
import sys

import png

Description = """Join PNG images in a row left-to-right."""


class FormatError(Exception):
    """
    Some problem with the image format.
    """


def join_row(out, l):
    """
    Concatenate the list of images.
    All input images must be same height and
    have the same number of channels.
    They are concatenated left-to-right.
    `out` is the (open file) destination for the output image.
    `l` should be a list of open files (the input image files).
    """

    l = [png.Reader(file=f) for f in l]

    # Ewgh, side effects.
    for r in l:
        r.preamble()

    # The reference height; from the first image.
    height = l[0].height
    # The total target width
    width = 0
    for i,r in enumerate(l):
        if r.height != height:
            raise FormatError('Image %d, height %d, does not match %d.' %
              (i, r.height, height))
        width += r.width

    # Various bugs here because different numbers of channels and depths go wrong.
    pixel, info = zip(*[r.asDirect()[2:4] for r in l])
    tinfo = dict(info[0])
    del tinfo['size']
    w = png.Writer(width, height, **tinfo)

    def iter_all_rows():
        for row in zip(*pixel):
            # `row` is a sequence that has one row from each input image.
            # list() is required here to hasten the lazy row building;
            # not sure if that's a bug in PyPNG or not.
            yield list(itertools.chain(*row))
    w.write(out, iter_all_rows())

def main(argv):
    import argparse

    parser = argparse.ArgumentParser(description=Description)
    parser.add_argument(
        "input", nargs="*", default="-", type=png.cli_open, metavar="PNG"
    )

    args = parser.parse_args()

    return join_row(png.binary_stdout(), args.input)

if __name__ == '__main__':
    main(sys.argv)
````

## File: venv310/Scripts/priweavepng
````
#!D:\Projects\Python Projects\part_inventory_server\venv310\Scripts\python.exe

# priweavepng
# Weave selected channels from input PNG files into
# a multi-channel output PNG.

import collections
import re

from array import array

import png

"""
priweavepng file1.png [file2.png ...]

The `priweavepng` tool combines channels from the input images and
weaves a selection of those channels into an output image.

Conceptually an intermediate image is formed consisting of
all channels of all input images in the order given on the command line
and in the order of each channel in its image.
Then from 1 to 4 channels are selected and
an image is output with those channels.
The limit on the number of selected channels is
imposed by the PNG image format.

The `-c n` option selects channel `n`.
Further channels can be selected either by repeating the `-c` option,
or using a comma separated list.
For example `-c 3,2,1` will select channels 3, 2, and 1 in that order;
if the input is an RGB PNG, this will swop the Red and Blue channels.
The order is significant, the order in which the options are given is
the order of the output channels.
It is permissible, and sometimes useful
(for example, grey to colour expansion, see below),
to repeat the same channel.

If no `-c` option is used the default is
to select all of the input channels, up to the first 4.

`priweavepng` does not care about the meaning of the channels
and treats them as a matrix of values.

The numer of output channels determines the colour mode of the PNG file:
L (1-channel, Grey), LA (2-channel, Grey+Alpha),
RGB (3-channel, Red+Green+Blue), RGBA (4-channel, Red+Green+Blue+Alpha).

The `priweavepng` tool can be used for a variety of
channel building, swopping, and extraction effects:

Combine 3 grayscale images into RGB colour:
    priweavepng grey1.png grey2.png grey3.png

Swop Red and Blue channels in colour image:
    priweavepng -c 3 -c 2 -c 1 rgb.png

Extract Green channel as a greyscale image:
    priweavepng -c 2 rgb.png

Convert a greyscale image to a colour image (all grey):
    priweavepng -c 1 -c 1 -c 1 grey.png

Add alpha mask from a separate (greyscale) image:
    priweavepng rgb.png grey.png

Extract alpha mask into a separate (greyscale) image:
    priweavepng -c 4 rgba.png

Steal alpha mask from second file and add to first.
Note that the intermediate image in this example has 7 channels:
    priweavepng -c 1 -c 2 -c 3 -c 7 rgb.png rgba.png

Take Green channel from 3 successive colour images to make a new RGB image:
    priweavepng -c 2 -c 5 -c 8 rgb1.png rgb2.png rgb3.png

"""

Image = collections.namedtuple("Image", "rows info")

# For each channel in the intermediate raster,
# model:
# - image: the input image (0-based);
# - i: the channel index within that image (0-based);
# - bitdepth: the bitdepth of this channel.
Channel = collections.namedtuple("Channel", "image i bitdepth")


class Error(Exception):
    pass


def weave(out, args):
    """Stack the input PNG files and extract channels
    into a single output PNG.
    """

    paths = args.input

    if len(paths) < 1:
        raise Error("Required input is missing.")

    # List of Image instances
    images = []
    # Channel map. Maps from channel number (starting from 1)
    # to an (image_index, channel_index) pair.
    channel_map = dict()
    channel = 1

    for image_index, path in enumerate(paths):
        inp = png.cli_open(path)
        rows, info = png.Reader(file=inp).asDirect()[2:]
        rows = list(rows)
        image = Image(rows, info)
        images.append(image)
        # A later version of PyPNG may intelligently support
        # PNG files with heterogenous bitdepths.
        # For now, assumes bitdepth of all channels in image
        # is the same.
        channel_bitdepth = (image.info["bitdepth"],) * image.info["planes"]
        for i in range(image.info["planes"]):
            channel_map[channel + i] = Channel(image_index, i, channel_bitdepth[i])
        channel += image.info["planes"]

    assert channel - 1 == sum(image.info["planes"] for image in images)

    # If no channels, select up to first 4 as default.
    if not args.channel:
        args.channel = range(1, channel)[:4]

    out_channels = len(args.channel)
    if not (0 < out_channels <= 4):
        raise Error("Too many channels selected (must be 1 to 4)")
    alpha = out_channels in (2, 4)
    greyscale = out_channels in (1, 2)

    bitdepth = tuple(image.info["bitdepth"] for image in images)
    arraytype = "BH"[max(bitdepth) > 8]

    size = [image.info["size"] for image in images]
    # Currently, fail unless all images same size.
    if len(set(size)) > 1:
        raise NotImplementedError("Cannot cope when sizes differ - sorry!")
    size = size[0]

    # Values per row, of output image
    vpr = out_channels * size[0]

    def weave_row_iter():
        """
        Yield each woven row in turn.
        """
        # The zip call creates an iterator that yields
        # a tuple with each element containing the next row
        # for each of the input images.
        for row_tuple in zip(*(image.rows for image in images)):
            # output row
            row = array(arraytype, [0] * vpr)
            # for each output channel select correct input channel
            for out_channel_i, selection in enumerate(args.channel):
                channel = channel_map[selection]
                # incoming row (make it an array)
                irow = array(arraytype, row_tuple[channel.image])
                n = images[channel.image].info["planes"]
                row[out_channel_i::out_channels] = irow[channel.i :: n]
            yield row

    w = png.Writer(
        size[0],
        size[1],
        greyscale=greyscale,
        alpha=alpha,
        bitdepth=bitdepth,
        interlace=args.interlace,
    )
    w.write(out, weave_row_iter())


def comma_list(s):
    """
    Type and return a list of integers.
    """

    return [int(c) for c in re.findall(r"\d+", s)]


def main(argv=None):
    import argparse
    import itertools
    import sys

    if argv is None:
        argv = sys.argv
    argv = argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--channel",
        action="append",
        type=comma_list,
        help="list of channels to extract",
    )
    parser.add_argument("--interlace", action="store_true", help="write interlaced PNG")
    parser.add_argument("input", nargs="+")
    args = parser.parse_args(argv)

    if args.channel:
        args.channel = list(itertools.chain(*args.channel))

    return weave(png.binary_stdout(), args)


if __name__ == "__main__":
    main()
````

## File: venv310/share/man/man1/qr.1
````
.\" Manpage for qr
.TH QR 1 "6 Feb 2023" "7.4.2" "Python QR tool"
.SH NAME
qr \- script to create QR codes at the command line
.SH SYNOPSIS
qr [\-\-help] [\-\-factory=FACTORY] [\-\-optimize=OPTIMIZE] [\-\-error\-correction=LEVEL] [data]
.SH DESCRIPTION
This script uses the python qrcode module. It can take data from stdin or from the commandline and generate a QR code.
Normally it will output the QR code as ascii art to the terminal. If the output is piped to a file, it will output the image (default type of PNG).
.SH OPTIONS
.PP
\fB\ \-h, \-\-help\fR
.RS 4
Show a help message.
.RE

.PP
\fB\ \-\-factory=FACTORY\fR
.RS 4
Full python path to the image factory class to create the
image with. You can use the following shortcuts to the
built-in image factory classes: pil (default), png (
default if pillow is not installed), svg, svg-fragment,
svg-path.
.RE

.PP
\fB\ \-\-optimize=OPTIMIZE\fR
.RS 4
Optimize the data by looking for chunks of at least this
many characters that could use a more efficient encoding
method. Use 0 to turn off chunk optimization.
.RE

.PP
\fB\ \-\-error\-correction=LEVEL\fR
.RS 4
The error correction level to use. Choices are L (7%),
M (15%, default), Q (25%), and H (30%).
.RE

.PP
\fB\ data\fR
.RS 4
The data from which the QR code will be generated.
.RE

.SH SEE ALSO
https://github.com/lincolnloop/python-qrcode/
````

## File: venv310/pyvenv.cfg
````
home = C:\Python312
include-system-site-packages = false
version = 3.12.2
executable = C:\Python312\python.exe
command = C:\Python312\python.exe -m venv D:\Projects\Python Projects\part_inventory_server\venv310
````

## File: .gitignore
````
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class
*.pyc
# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
#  Usually these files are written by a python script from a template
#  before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
#   For a library or package, you might want to ignore these files since the code is
#   intended to run in multiple environments; otherwise, check them in:
# .python-version

# pipenv
#   Ignore the virtual environment directories created by pipenv
pipenv/
pipenv-*

# PEP 582; used by e.g. github.com/David-OConnor/pyflow
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# PyCharm
#  JetBrains specific template is maintained in a separate JetBrains.gitignore that can
#  be found at https://github.com/github/gitignore/blob/main/Global/JetBrains.gitignore
#  and can be added to the global gitignore or merged into this file.  For a more nuclear
#  option (not recommended) you can uncomment the following to ignore the entire idea folder.
# .idea/

# Virtual Environment
venv/
env/
ENV/
.env

# IDE
.idea/
.vscode/
*.swp
*.swo
.DS_Store

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# Logs
*.log

# Database
*.sqlite3
*.sqlite3-journal

# Generated files
*.png
*.jpg
*.jpeg
*.gif
*.bmp

# Backup files
*.backup
*.bak
*~

# Temporary files
*.tmp
*.temp
assert
command
env.txt
ql-refactor-printer
makers_matrix.db
````

## File: part_inventory.json
````json
{"parts": {"1": {"part_id": "cf1e3283-8d4f-4457-b827-1dad73b4697f", "part_number": "hfuif", "part_name": "gddh", "quantity": 8585, "description": "xbbcnc", "supplier": "gcjnc", "location": {"id": "0adeb588-52a3-4b2b-b068-22ba12791666", "name": "desk", "description": "my desk", "parent_id": null}, "image_url": null, "additional_properties": {}, "categories": null}, "2": {"part_id": "152d7a0f-faab-491a-8a62-1ddd8a4a73f1", "part_number": "hxhf", "part_name": null, "quantity": 6899, "description": "fhuf", "supplier": "cnnc", "location": null, "image_url": null, "additional_properties": {}, "categories": null}, "3": {"part_id": "7e80ac1b-9059-4315-b285-fa730d3a1cd5", "part_number": "vnncvm", "part_name": "gjjfj", "quantity": 506, "description": "", "supplier": "nc nc", "location": {"id": "0adeb588-52a3-4b2b-b068-22ba12791666", "name": "desk", "description": "my desk", "parent_id": null}, "image_url": null, "additional_properties": {}, "categories": null}}, "locations": {"1": {"id": "c5584c3f-3eb6-48d6-a9db-dc0b64d2ef3b", "name": "Office", "description": "Main office space", "parent_id": null}, "2": {"id": "12345", "name": "Desk", "description": "Office desk", "parent_id": "c5584c3f-3eb6-48d6-a9db-dc0b64d2ef3b"}, "3": {"id": "318988bf-5534-4e74-8dee-0cdbe61edc47", "name": "Chair", "description": "Office chair", "parent_id": "c5584c3f-3eb6-48d6-a9db-dc0b64d2ef3b"}, "4": {"id": "2211224", "name": "Bottom Drawer", "description": "Bottom Drawer in Desk", "parent_id": "12345"}, "5": {"id": "1809a757-59b3-4880-99a3-77fba48d1f2d", "name": "Pencil Box", "description": "Pencil Box in Bottom Drawer in Desk", "parent_id": "2211224"}}}
````

## File: printer_config.json
````json
{
  "model": "QL-800",
  "backend": "network",
  "printer_identifier": "tcp://192.168.1.71",
  "dpi": 300,
  "scaling_factor": 1.1
}
````

## File: project_status.md
````markdown
# Project Status Updates

## 2024-03-21
- Refactored exception handling into a dedicated module for better organization
- Fixed database initialization by properly implementing FastAPI lifespan
- Improved error handling consistency across all routes
- Fixed failing tests related to category management
- Added proper database table creation on application startup

## Testing and Quality Assurance Status
- Unit Tests: ✅ Comprehensive test suite for all major components
- Integration Tests: ✅ Present but some failing due to database connection issues
- Test Coverage: ⚠️ 54% overall coverage
  - High coverage (>90%) in core modules
  - Low coverage in lib/ and parsers/ directories
- Error Handling: ⚠️ Most cases handled but some inconsistencies in status codes
- Code Quality: ⚠️ Well-organized but some deprecation warnings to address

### Next Steps
1. Fix database connection issues in integration tests
2. Address error handling inconsistencies (500 vs 404/409)
3. Add tests for lib/ and parsers/ directories
4. Update deprecated code (Pydantic V2, PIL.ANTIALIAS)
5. Improve printer service test reliability
````

## File: pyproject.toml
````toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "MakerMatrix"
version = "0.1.0"
description = "A part inventory management system with label printing capabilities"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.68.0",
    "uvicorn>=0.15.0",
    "sqlmodel>=0.0.8",
    "pydantic>=2.0.0",
    "python-multipart>=0.0.5",
    "brother_ql>=0.9.0",
    "pillow>=9.0.0",
    "qrcode>=7.3",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "python-dotenv>=0.19.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.18.0",
    "pytest-cov>=4.0.0",
    "requests>=2.31.0",
    "httpx>=0.24.0"

]

[tool.pytest.ini_options]
markers = [
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
]
````

## File: pytest.ini
````
[pytest]
markers =
    integration: marks tests as integration tests (deselect with '-m "not integration"') 
addopts = -m "not integration"
testpaths =
    MakerMatrix/tests
    MakerMatrix/integration_tests
````

## File: README.md
````markdown
# Part Inventory Server

This server provides a RESTful API for managing an inventory of parts.  It allows you to create, read, update, and delete part records.

## Getting Started

### Prerequisites

* Python 3.7+
* A database supported by SQLAlchemy (e.g., PostgreSQL, MySQL, SQLite)

### Installation

1. Clone the repository:

   ```bash
   git clone <repository_url>
   ```

2. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   ```

3. Activate the virtual environment:

   ```bash
   source .venv/bin/activate  # On Linux/macOS
   .venv\Scripts\activate  # On Windows
   ```

4. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Configure the database connection:

   * Create a `.env` file in the root directory of the project.
   * Add the following environment variables, replacing the placeholders with your database credentials:

     ```
     DATABASE_URL=dialect+driver://username:password@host:port/database
     ```

     For example, for a PostgreSQL database:

     ```
     DATABASE_URL=postgresql://user:password@localhost:5432/part_inventory
     ```

     Or for an SQLite database:

     ```
     DATABASE_URL=sqlite:///part_inventory.db
     ```


### Running the Server

1. Start the server:

   ```bash
   python -m MakerMatrix.main
   ```

   This will start the server on port 57891.

## Authentication

The API uses JWT (JSON Web Token) authentication. Most endpoints require authentication.

### Default Admin User

When the application starts for the first time, a default admin user is created with the following credentials:

- **Username**: admin
- **Password**: Admin123!

You should change this password after the first login.

### Using the Swagger UI

1. Go to the Swagger UI at `http://localhost:57891/docs`
2. Click the "Authorize" button at the top right
3. Enter the admin credentials (or your user credentials)
4. Click "Authorize" to log in
5. Now you can use all the authenticated endpoints

### Authentication Endpoints

- **POST /auth/login**: Log in with username and password to get an access token (form-based, used by Swagger UI)
- **POST /auth/mobile-login**: Log in with username and password to get an access token (JSON-based, ideal for mobile apps)
- **POST /auth/refresh**: Refresh an expired access token
- **POST /auth/logout**: Log out (invalidate the current token)
- **POST /users/register**: Register a new user (admin only)

### Mobile Application Integration

For mobile applications (like an iPhone app), use the `/auth/mobile-login` endpoint:

```json
POST /auth/mobile-login
Content-Type: application/json

{
  "username": "admin",
  "password": "Admin123!"
}
```

Response:

```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

Then use the token in subsequent requests:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Role-Based Access Control

The API uses role-based access control with the following default roles:

- **admin**: Full access to all endpoints
- **manager**: Read, write, and update access
- **user**: Read-only access

## API Endpoints

The following endpoints are available:

* **GET /parts**: Retrieve all parts.
* **GET /parts/{part_id}**: Retrieve a specific part by ID.
* **POST /parts**: Create a new part.
* **PUT /parts/{part_id}**: Update an existing part.
* **DELETE /parts/{part_id}**: Delete a part.


## Data Model

The part data model includes the following fields:

* **id (int)**: Unique identifier for the part.
* **name (str)**: Name of the part.
* **description (str, optional)**: Description of the part.
* **quantity (int)**: Quantity of the part in stock.

## Example Usage

### Creating a new part:

```bash
curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" -d '{"name": "Example Part", "description": "A test part", "quantity": 10}' http://localhost:57891/parts
```

### Retrieving all parts:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:57891/parts
```

### Updating a part:

```bash
curl -X PUT -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" -d '{"name": "Updated Part", "quantity": 5}' http://localhost:57891/parts/1
```

### Deleting a part:

```bash
curl -X DELETE -H "Authorization: Bearer YOUR_TOKEN" http://localhost:57891/parts/1
```
````

## File: requirements-dev.txt
````
httpx>=0.27.2
pytest==7.4.3
pytest-asyncio==0.21.1
passlib>=1.7.4
python-jose[cryptography]>=3.3.0
# Removed bcrypt, now using pbkdf2_sha256 via passlib only
````

## File: requirements.txt
````
# Development dependencies
pytest==7.4.3
pytest-asyncio==0.21.1
requests==2.32.3
websockets==13.1
beautifulsoup4==4.12.2
mouser==0.1.5

# Specific version pins for production dependencies
fastapi==0.115.2
uvicorn==0.27.1
python-multipart==0.0.19
pydantic==2.11.0a2
pillow==10.2.0
qrcode==7.4.2
starlette==0.40.0
brother_ql-inventree==1.3
sqlmodel==0.0.22
SQLAlchemy==2.0.36
passlib>=1.7.4
python-jose[cryptography]>=3.3.0

# Removed bcrypt, now using pbkdf2_sha256 via passlib only
````
