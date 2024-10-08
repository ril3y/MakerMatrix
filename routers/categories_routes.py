from typing import Optional

from fastapi import APIRouter, HTTPException

from models.category_model import CategoryModel
from services.category_service import CategoryService

router = APIRouter()


@router.get("/all_categories/")
async def get_all_categories():
    categories = CategoryService.get_all_categories()
    return {"categories": categories}


@router.post("/add_category/")
async def add_category(category_data: CategoryModel):
    try:
        response = CategoryService.add_category(category_data)

        return response
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
async def remove_category(id: Optional[str] = None, name: Optional[str] = None) -> dict:
    # Validate that at least one parameter is provided
    if not id and not name:
        raise HTTPException(status_code=400, detail="Either category ID or name must be provided")

    # Call the service based on the provided parameter
    try:
        success, identifier = CategoryService.remove_category(id=id, name=name)
        if success:
            return {"message": f"Category with {identifier} removed successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Category with {identifier} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/remove_all_categories/")
async def remove_all_categories():
    response = CategoryService.delete_all_categories()
    return response
