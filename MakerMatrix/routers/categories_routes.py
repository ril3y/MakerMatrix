from typing import Optional

from fastapi import APIRouter, HTTPException

from MakerMatrix.models.category_model import CategoryModel
from MakerMatrix.repositories.custom_exceptions import ResourceNotFoundError
from MakerMatrix.schemas.part_response import CategoryResponse
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.category_service import CategoryService

router = APIRouter()


@router.get("/get_all_categories/")
async def get_all_categories():
    response = CategoryService.get_all_categories()
    if response:
        return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=response["data"])
    


@router.post("/add_category/")
async def add_category(category_data: CategoryModel):
    try:
        response = CategoryService.add_category(category_data)
        if response:
            return ResponseSchema(
            status=response["status"],
            message=response["message"],
            data=CategoryResponse.model_validate(response["data"])) 
        else:    
            raise ResourceNotFoundError(
                status="error",
                message="f{Error: Category with name {category_data.name} not found",
                data=None)
                
     
            
             
    
    except ResourceNotFoundError as rnfe:
        raise rnfe
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add category: {str(e)}")


@router.put("/update_category/{category_id}")
async def update_category(category_id: str, category_data: CategoryModel):
    # Ensure the ID in the path matches the ID in the payload if provided
    if category_data.id and category_data.id != category_id:
        raise HTTPException(status_code=400, detail="Category ID in the path and payload must match")

    # Set the ID from the path into the model (if not already set)
    category_data.id = category_id

    response = CategoryService.update_category(category_data)
    if response["status"] == "success":
        return response
    else:
        raise HTTPException(status_code=404, detail=response["message"])


@router.get("/get_category")
async def get_category(category_id: Optional[str] = None, name: Optional[str] = None):
    try:
        # Validate that either category_id or name is provided
        if not category_id and not name:
            raise HTTPException(status_code=400, detail="Either 'category_id' or 'name' must be provided")

        # Call the service to get the category
        category_data = CategoryService.get_category(category_id=category_id, name=name)
        if category_data:
            return {"status": "success", "data": category_data}
        else:
            raise HTTPException(status_code=404, detail="Category not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/remove_category")
async def remove_category(id: Optional[str] = None, name: Optional[str] = None)  -> ResponseSchema[CategoryResponse]:
    # Validate that at least one parameter is provided
    if not id and not name:
        raise HTTPException(status_code=400, detail="Either category ID or name must be provided")

    # Call the service based on the provided parameter
    try:
        response = CategoryService.remove_category(id=id, name=name)
        if response["status"] == "removed":
            return ResponseSchema(
                status=response["status"],
                message=response["message"],
                data=CategoryResponse.model_validate(response["data"])
            )
        else:
            raise HTTPException(status_code=404, detail=f"Category with {id} not found")
    
    except ResourceNotFoundError as rnfe:
        raise rnfe
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



@router.delete("/delete_all_categories")
async def delete_all_categories() -> ResponseSchema[CategoryResponse]:

    try:
        response = CategoryService.delete_all_categories()
        if response["status"] == "success":
            return ResponseSchema(
                status=response["status"],
                message=response["message"],
                data=CategoryResponse.model_validate(response["data"])
            )
    
    except ResourceNotFoundError as rnfe:
        raise rnfe
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))