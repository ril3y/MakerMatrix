from typing import Optional, Dict, Any, List, Union
from pydantic import model_validator, field_validator, BaseModel, ConfigDict
from sqlalchemy import create_engine, ForeignKey, String, or_, cast
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
