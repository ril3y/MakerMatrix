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
