from pydantic import BaseModel, root_validator, Field, ValidationError


class LabelData(BaseModel):
    part_number: str = Field(None, description="The part number")
    part_name: str = Field(None, description="The part name")

    @root_validator(pre=True)
    def check_at_least_one(cls, values):
        part_number = values.get('part_number')
        part_name = values.get('part_name')

        # Raise an error if neither part_number nor part_name is provided
        if not part_number and not part_name:
            raise ValueError('At least one of part_number or part_name must be provided.')

        return values

    class Config:
        schema_extra = {
            "example": {
                "part_number": "c1591",
                "part_name": "cl10b104kb8nnnc"
            }
        }
