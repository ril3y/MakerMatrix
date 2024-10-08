
from typing import Dict

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import ValidationError
from starlette.responses import JSONResponse

from models.part_model import PartModel, UpdateQuantityRequest, GenericPartQuery
from services.part_service import PartService

router = APIRouter()

@router.put("/decrement_count/")
async def decrement_count(generic_part_query: GenericPartQuery):
    try:
        part, part_field, previous_quantity = PartService.decrement_count_service(generic_part_query)
        return {
            "message": f"Quantity decremented from {previous_quantity} to {part['quantity']} part {part[part_field]}",
            "previous_quantity": previous_quantity,
            "new_quantity": part['quantity']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update_quantity/")
def update_part_quantity(update_request: UpdateQuantityRequest):
    try:
        part_updated = PartService.update_quantity_service(
            new_quantity=update_request.new_quantity,
            part_id=update_request.part_id,
            part_number=update_request.part_number,
            manufacturer_pn=update_request.manufacturer_pn

        )

        if part_updated:
            return {"message": f"Quantity updated to {update_request.new_quantity}"}
        else:
            raise HTTPException(status_code=404, detail="Part not found")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@router.get("/all_parts/")
async def get_all_parts():
    try:
        parts = PartService.get_all_parts()
        return parts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_part_by_part_number/")
async def get_part_by_part_number(part_number) -> PartModel:
    try:
        part = PartService.get_part_by_pn(part_number)
        return part
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_parts/")
async def get_parts(page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1)):
    try:
        parts = PartService.get_all_parts_paginated(page=page, page_size=page_size)
        total_count = PartService.get_total_parts_count()
        return {"parts": parts, "page": page, "page_size": page_size, "total": total_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_part_by_id/{part_id}")
async def get_part_by_id(part_id: str):
    try:
        part = PartService.get_part_by_id(part_id)
        if part:
            return part
        else:
            # Raise the 404 HTTPException directly
            raise HTTPException(status_code=404, detail=f"Part ID {part_id} not found")
    except HTTPException as http_exc:
        # Re-raise HTTPException (such as the 404) without catching it
        raise http_exc
    except Exception as e:
        # Catch other generic exceptions and raise a 500 error
        raise HTTPException(status_code=500, detail=str(e))


# @router.get("/get_part_by_details/{part_details}")
# async def get_part_by_details(part_details: str):
#     try:
#         part = await PartService.get_part_by_details(part_details)
#         if part:
#             return part
#         else:
#             raise HTTPException(status_code=404, detail=f"Part Details {part_details} not found")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))



@router.get("/get_parts/")
async def get_parts(page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1)):
    try:
        result = PartService.get_parts_paginated(page, page_size)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return JSONResponse(
            content=result,
            status_code=200
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear_parts")
def clear_all_parts():
    try:
        PartService.part_repo.clear_all_parts()
        return {"status": "success", "message": "All parts have been cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add_part")
async def add_part(part: PartModel, overwrite: bool = False) -> Dict:
    try:
        response = PartService.add_part(part, overwrite)

        # Check if the response asks for confirmation
        if response.get("status") == "part exists":
            return {
                "status": "pending_confirmation",
                "message": response.get("message"),
                "data": response["data"]
            }

        # Return success response if the part was added
        return {
            "status": "success",
            "message": "Part added successfully",
            "data": response["data"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete_part/{part_id}")
async def delete_part(part_id: str):
    try:
        deleted_part = PartService.part_repo.delete_part(part_id)
        if deleted_part:
            return {"message": "Part deleted successfully", "deleted_part_id": part_id}
        else:
            # Properly raise the 404 error if no part was found
            raise HTTPException(status_code=404, detail="Part not found")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-parts/")
async def search_parts(criteria: Dict[str, str]):
    try:
        if not criteria:
            raise HTTPException(status_code=400, detail="Search criteria are required")
        results = PartService.dynamic_search(criteria)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
