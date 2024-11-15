from typing import Optional, Dict, Any, List, Union

from pydantic import model_validator, field_validator, BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload
from sqlmodel import SQLModel, Field, Relationship, select
import uuid
from pydantic import Field as PydanticField

from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy.dialects.sqlite import JSON
import uuid


# Association table to link PartModel and CategoryModel
class PartCategoryLink(SQLModel, table=True):
    part_id: str = Field(foreign_key="partmodel.id", primary_key=True)
    category_id: str = Field(foreign_key="categorymodel.id", primary_key=True)


# CategoryModel
class CategoryModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    parent_id: Optional[str] = Field(default=None, foreign_key="categorymodel.id")

    # Define the parent relationship with remote_side to avoid conflict
    parent: Optional["CategoryModel"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "CategoryModel.id"}
    )
    children: List["CategoryModel"] = Relationship(back_populates="parent")

    parts: List["PartModel"] = Relationship(back_populates="categories", link_model=PartCategoryLink)


# LocationModel
class LocationModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: Optional[str] = Field(index=True)
    description: Optional[str] = None
    parent_id: Optional[str] = Field(default=None, foreign_key="locationmodel.id")
    location_type: str = Field(default="standard")

    # Define the parent-child relationships for LocationModel
    parent: Optional["LocationModel"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "LocationModel.id"}
    )
    children: List["LocationModel"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    parts: List["PartModel"] = Relationship(back_populates="location")


# PartModel
class PartModel(SQLModel, table=True):
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    part_name: str = Field(index=True, unique=True)
    description: Optional[str] = None

    categories: List["CategoryModel"] = Relationship(back_populates="parts", link_model=PartCategoryLink)

    part_number: Optional[str] = Field(index=True)
    part_name: Optional[str] = Field(index=True)
    quantity: Optional[int]
    supplier: Optional[str] = None
    location_id: Optional[str] = Field(default=None, foreign_key="locationmodel.id")

    location: Optional["LocationModel"] = Relationship(
        back_populates="parts",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    image_url: Optional[str] = None
    additional_properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    # Example for setting eager loading by default
    categories: List["CategoryModel"] = Relationship(
        back_populates="parts",
        link_model=PartCategoryLink,
        sa_relationship_kwargs={"lazy": "selectin"}  # `selectin` eager loads with a separate query.
    )

    class Config:
        arbitrary_types_allowed = True

        # Custom serialization function
    def to_dict(self) -> Dict[str, Any]:
        """ Custom serialization method for PartModel """
        part_dict = self.dict()
        # Convert the related categories to a list of dictionaries or names
        part_dict['categories'] = [
            {"id": category.id, "name": category.name, "description": category.description}
            for category in self.categories
        ]
        return part_dict


    @model_validator(mode='before')
    def check_unique_part_name(cls, values):
        from MakerMatrix.services.part_service import PartService
        part_name = values.get("part_name")
        part_id = values.get("id")  # Assuming this is the ID field in PartModel

        if part_name:
            # Check if there is any part with the same name, excluding the current part by ID
            if not PartService.is_part_name_unique(part_name, part_id):
                raise ValueError(f"The part name '{part_name}' already exists.")

        return values




# Additional models for operations
class UpdateQuantityRequest(SQLModel):
    part_id: Optional[str] = None
    part_number: Optional[str] = None
    manufacturer_pn: Optional[str] = None
    new_quantity: int

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

    @classmethod
    def check_at_least_one_identifier(cls, values):
        part_id = values.get('part_id')
        part_number = values.get('part_number')
        manufacturer_pn = values.get('manufacturer_pn')

        if not part_id and not part_number and not manufacturer_pn:
            raise ValueError("At least one of part_id, part_number, or manufacturer_pn must be provided.")
        return values


# Create an engine for SQLite
sqlite_file_name = "makers_matrix.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)


# Create tables if they don't exist
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
