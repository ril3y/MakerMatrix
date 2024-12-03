from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status

from MakerMatrix.models.models import PartModel
from MakerMatrix.repositories.custom_exceptions import PartAlreadyExistsError, ResourceNotFoundError
from MakerMatrix.schemas.part_create import PartCreate, PartUpdate
from MakerMatrix.schemas.part_response import PartResponse
from MakerMatrix.schemas.response import ResponseSchema
from MakerMatrix.services.category_service import CategoryService
from MakerMatrix.services.part_service import PartService

from MakerMatrix.models.models import PartModel, UpdateQuantityRequest, GenericPartQuery
from MakerMatrix.services.part_service import PartService

router = APIRouter()

import logging

logger = logging.getLogger(__name__)

@router.post("/add_part", response_model=ResponseSchema[PartResponse])
async def add_part(part: PartCreate) -> ResponseSchema[PartResponse]:
    try:
        # Process to add part
        response = PartService.add_part(part.model_dump(), part.category_names)

        if response and response.get("status") == "part exists":
            raise PartAlreadyExistsError(
                part_name=part.part_name,
                part_data=response.get("data")
            )

        # noinspection PyArgumentList
        return ResponseSchema(


            status=response["status"],
            message=response["message"],
            data=PartResponse.model_validate(response["data"])
        )

    except PartAlreadyExistsError as exc:
        raise exc
    except Exception as e:
        logger.error(f"Failed to add part: {e}")
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

        # if response is None:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail=f"get_part had a error not found"
        #     )

        # If the part is found, return it
        # noinspection PyArgumentList
        # noinspection PyArgumentList
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
