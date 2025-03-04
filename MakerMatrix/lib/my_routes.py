import json
import os
import shutil
import threading
import uuid
from asyncio import create_task
from typing import Dict

import qrcode
from fastapi import FastAPI, WebSocket, Body
from fastapi import HTTPException, Request, Query
from fastapi import UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.responses import FileResponse

from MakerMatrix.lib.connection import Connection
from MakerMatrix.lib.database import DatabaseManager
from MakerMatrix.lib import LabelData
from MakerMatrix.lib import PartModel
from MakerMatrix.lib.part_inventory import PartInventory
from MakerMatrix.lib.websockets import WebSocketManager
from MakerMatrix.lib import LocationModel
from MakerMatrix.lib.parser_manager import ParserManager
from MakerMatrix.lib.printer_brother import Printer
from MakerMatrix.lib import printer_config_model

# Initialize or import the PartInventory instance (adjust this according to your project setup)
db = PartInventory('part_inventory.json')

# Global variables (update or import these as per your actual project setup)
active_websockets = {}
websocket_info = {}
websocket_info_lock = threading.Lock()


def setup_routes(app: FastAPI, printer: Printer):
    # Define route functions

    @app.put("/update_quantity/")
    async def update_part_quantity(manufacturer_pn: str, new_quantity: int):
        db.update_quantity(manufacturer_pn, new_quantity)
        return {
            "message": f"Quantity updated for part with manufacturer part number {manufacturer_pn} to {new_quantity}"}

    @app.put("/decrement_count/")
    async def decrement_count(manufacturer_pn: str, by: int = 1):
        db.decrement_count(manufacturer_pn, by)
        return {"message": f"Quantity decremented by {by} for part with manufacturer part number {manufacturer_pn}"}

    @app.get("/all_parts/")
    async def get_all_parts():
        parts = db.get_all_parts()
        return JSONResponse(content=parts, status_code=200)

    @app.get("/get_parts/")
    async def get_parts(page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1)):
        parts = db.get_all_parts_paginated(page=page,
                                           page_size=page_size)
        return JSONResponse(
            content={"parts": parts, "page": page, "page_size": page_size, "total": db.get_total_parts_count()},
            status_code=200)

    @app.delete("/clear_parts")
    async def clear_all_parts():
        db.clear_all_parts()
        return {"status": "success", "message": "All parts have been cleared."}

    @app.get("/get_part_by_id/{part_id}")
    async def get_part_by_id(part_id: str):
        part = await db.get_part_by_part_id(part_id)
        if part:
            return JSONResponse(content=part, status_code=200)
        else:
            return JSONResponse(content={"error": f"Part ID {part_id} not found"}, status_code=404)

    @app.get("/get_part_by_name/{part_name}")
    async def get_part_by_id(part_name: str):
        part = await db.get_part_by_part_name(part_name)
        if part:
            return JSONResponse(content=part, status_code=200)
        else:
            return JSONResponse(content={"error": f"Part name {part_name} not found"}, status_code=404)

    @app.get("/get_part_by_number/{part_number}")
    async def get_part_by_part_number(part_number: str):
        part = db.get_part_by_part_number(part_number)
        if part:
            return JSONResponse(content=part, status_code=200)
        else:
            return JSONResponse(content={"error": f"Part number {part_number} not found"}, status_code=404)

    @app.get("/get_part_by_details")
    async def get_part_by_details(part_id: str = None, part_name: str = None, part_number: str = None):
        if not part_id and not part_name and not part_number:
            raise HTTPException(status_code=400,
                                detail="At least one of part_id, part_name, or part_number must be provided.")

        part = None

        # Attempt to find the part by part_id first
        if part_id:
            part = await db.get_part_by_part_id(part_id)

        # If not found by part_id, try part_name
        if not part and part_name:
            part = await db.get_part_by_part_name(part_name)

        # If not found by part_name, try part_number
        if not part and part_number:
            part = await db.get_part_by_part_number(part_number)

        if part:
            return JSONResponse(content=part, status_code=200)
        else:
            return JSONResponse(content={"error": "Part not found with the provided details"}, status_code=404)



    @app.get("/preview-delete/{location_id}")
    async def preview_delete(location_id: str):
        # Fetch the number of parts affected by the deletion
        affected_parts = await db.get_parts_effected_locations(location_id)
        affected_parts_count = len(affected_parts)

        # Fetch the child locations affected by the deletion
        child_locations = await db.get_location_hierarchy(location_id)
        affected_children_count = len(child_locations)

        return {
            "location_id": location_id,
            "affected_parts_count": affected_parts_count,
            "affected_children_count": affected_children_count
        }

    @app.get("/get_location_path/{location_id}")
    async def get_location_path(location_id: str):
        """
        Retrieves the path from a specific location to the root.

        :param location_id: The ID of the specific location.
        :return: A list of locations forming the path from the specified location to the root.
        """
        path = await db.get_location_path(location_id)
        if path:
            return JSONResponse(content={"path": path}, status_code=200)
        else:
            return JSONResponse(content={"error": "Location path not found"}, status_code=404)

    @app.get("/get_all_locations/")
    async def get_all_locations():
        # db_manager = DatabaseManager.get_instance()
        locations = db.get_all_locations()
        return JSONResponse(content={"locations": locations}, status_code=200)

    @app.get("/get_counts")
    async def get_counts():
        """
        Returns all counts for parts, locations, and categories
        """
        # db_manager = DatabaseManager.get_instance()
        try:
            parts = db.get_all_parts()
            locations = db.get_all_locations()
            categories = db.get_all_categories()

            parts_count = len(parts)
            locations_count = len(locations)
            categories_count = len(categories)
            return JSONResponse(
                content={"parts": parts_count, "locations": locations_count, "categories": categories_count},
                status_code=200)
        except Exception as e:
            print(f"Error getting counts: {e}")
            return JSONResponse(content={"error": "An error occurred while fetching counts"}, status_code=500)

    @app.get("/get_location_details/{location_id}")
    async def get_location_details(location_id: str):
        location = await db.get_location_hierarchy(location_id)
        if location:
            return JSONResponse(content=location, status_code=200)
        else:
            return JSONResponse(content={"error": "Location not found"}, status_code=404)

    @app.put("/edit_location/{location_id}")
    async def edit_location(location_id: str, name: str = None, description: str = None, parent_id: int = None):
        # db_manager = DatabaseManager.get_instance()
        updated_location = await db.edit_location(location_id, name, description, parent_id)
        if updated_location:
            return {"message": "Location updated", "location": updated_location}
        else:
            return JSONResponse(content={"error": "Error updating location"}, status_code=400)

    @app.get("/clear_locations/")
    async def clear_locations():
        # db_manager = DatabaseManager.get_instance()
        db.location_table.truncate()  # This clears all records in the locations table
        return {"message": "All locations cleared"}

    @app.post("/add_location/")
    async def add_location(location: LocationModel):
        # db_manager = DatabaseManager.get_instance()

        # Add the new location to the database
        added_location = await db.add_location(location.dict())

        # Return a success message with the added location data
        # return JSONResponse(content={"error": "Error updating location"}, status_code=400)
        if "error" in added_location:
            res = JSONResponse(content=added_location, status_code=409)
        else:
            res = JSONResponse(content=added_location, status_code=200)
        return res

    @app.get("/get_location/{location_id}")
    async def get_location(location_id: str):
        location = await db.get_location(location_id)

        if location:
            return location
        else:
            return JSONResponse(content={"error": "Location not found"}, status_code=404)

    @app.get("/get_image/{image_id}/")
    async def get_image(image_id: str):
        file_path = f"uploaded_images/{image_id}"
        if os.path.exists(file_path):
            return FileResponse(file_path)
        else:
            raise HTTPException(status_code=404, detail="Image not found")

    @app.delete("/delete_part/{part_id}")
    async def delete_part(part_id: str):
        try:
            # Assuming db_manager is used to handle database operations
            # and `delete_part` is a method that deletes a part by ID
            part_exists = await db.get_part_by_part_id(part_id)  # Check if the part exists
            if not part_exists:
                raise HTTPException(status_code=404, detail="Part not found")

            # Delete part using the database manager
            delete_message = await db.delete_part(part_id)
            return {"message": delete_message}

        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail="An error occurred while deleting the part")

    @app.post("/add_part")
    async def add_part(request: Request):
        try:
            json_data = await request.json()
            part = PartModel(**json_data)
            # Process and save part
            # db_manager = DatabaseManager.get_instance('part_inventory.json')
            return_message = await db.add_part(part, overwrite=False)
            return return_message
        except ValidationError as e:
            # Log e.errors() to see the detailed validation errors
            print(e)
            raise HTTPException(status_code=422, detail=str(e.errors()))
        except Exception as e:
            print(e)

    @app.post("/upload_image/")
    async def upload_image(file: UploadFile = File(...)):
        file_extension = os.path.splitext(file.filename)[1]
        image_id = str(uuid.uuid4())
        file_path = f"uploaded_images/{image_id}{file_extension}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {"image_id": image_id}

    @app.put("/update_location/{location_id}")
    async def update_location(location_id: int, location: LocationModel):
        db_manager = DatabaseManager.get_instance()
        # Update the location with the provided data
        updated_location = await db_manager.update_location(location_id, location.dict())
        if updated_location:
            return {"message": "Location updated", "location": updated_location}
        else:
            return JSONResponse(content={"error": "Error updating location"}, status_code=400)

    @app.delete("/cleanup-locations")
    async def cleanup_locations():
        # Step 1: Find all locations
        all_locations = db.get_all_locations()

        # Create a set of all valid location IDs
        valid_ids = {loc.get('id') for loc in all_locations}

        # Step 2: Identify invalid locations
        invalid_locations = [
            loc for loc in all_locations
            if loc.get('parent_id') and loc.get('parent_id') not in valid_ids
        ]

        # Recursive function to delete a location and its descendants
        async def delete_location_and_descendants(location_id):
            # Delete all child locations
            for loc in all_locations:
                if loc.get('parent_id') == location_id:
                    delete_location_and_descendants(loc.get('id'))

            # Delete the location itself
            await db.delete_location(location_id)

        # Step 3: Delete invalid locations and their descendants
        for loc in invalid_locations:
            await delete_location_and_descendants(loc.get('id'))

        return {"message": "Cleanup completed", "deleted_locations_count": len(invalid_locations)}

    @app.delete("/delete_location/{location_id}")
    async def delete_location(location_id: str):
        # Query and get all child locations
        child_locations = await db.get_location_hierarchy(location_id)

        # Iterate and delete each child location
        for child_location in child_locations:
            await db.delete_location(child_location['id'])  # Assuming each child has an 'id' attribute

        # Finally, delete the specified location
        deleted_location = await db.delete_location(location_id)

        if deleted_location:
            return {
                "message": "Location and its children deleted successfully",
                "deleted_location": location_id,
                "deleted_children_count": len(child_locations)
            }
        else:
            raise HTTPException(status_code=400, detail="Error deleting location")

    @app.delete("/delete_part/{part_id}")
    async def delete_location(part_id: str):

        # Finally, delete the specified location
        deleted_part = db.delete_parts(part_id)

        if deleted_part:
            return {
                "message": "Part deleted successfully",
                "deleted_partid": part_id,
            }
        else:
            raise HTTPException(status_code=400, detail="Error deleting location")

    @app.post("/search-parts/")
    async def search_parts(criteria: Dict[str, str] = Body(...)):
        if not criteria:
            raise HTTPException(status_code=400, detail="Search criteria are required")
        results = db.dynamic_search(criteria)
        return results

    @app.get("/search/{query}")
    async def search(query: str, search_type: str ):
        """
        Perform a search based on the query and type.
        :param query: The search query string.
        :param search_type: The type of search (e.g., 'name', 'number').
        :return: A JSON response with search results and suggestions.
        """

        valid_search_types = ["name", "number", "value", "id"]

        if search_type in valid_search_types:
            search_results = db.search_parts(query, search_type)
            suggestions = db.get_suggestions(query, search_type)
            print(f"Returned Suggestions: {suggestions}")
            return {"search_results": search_results, "suggestions": suggestions}
        else:
            return HTTPException(status_code=500, detail="invalid search type")

    # Define a route to serve the index.html file
    @app.get("/")
    async def serve_index_html():
        return FileResponse("static/part_inventory_ui/build/index.html")

    # @app.on_event("startup")
    # async def startup_event():
    #     # Initialize DatabaseManager
    #     db_manager = DatabaseManager.get_instance('part_inventory.json')
    #
    #     # Initialize WebSocketManager with the DatabaseManager instance
    #     ws_manager = WebSocketManager.get_instance(db_manager)
    #
    #     # Start processing the queue
    #     create_task(ws_manager.process_queue())

    @app.get("/all_categories/")
    async def get_all_categories():
        categories = db.get_all_categories()
        return JSONResponse(content={"categories": categories}, status_code=200)

    async def process_queue(self):
        data, client_id = await self.queue.get()

        if data is not None:
            data = bytes.fromhex(data)

            for parser in ParserManager.get_parser_instances():
                if parser.check(data):
                    # This data matches the parser signature
                    parser.process(data)
                    await DatabaseManager.get_instance()
                    # Send processed data back to the client
                    if client_id in active_websockets:
                        connection = active_websockets[client_id]
                        await connection.websocket.send_text(str(parser.toJson()))

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):

        client_id = str(uuid.uuid4())
        await websocket.accept()

        # Initialize DatabaseManager
        db_manager = DatabaseManager.get_instance('part_inventory.json')

        # Get the WebSocketManager instance with the DatabaseManager instance
        ws_manager = WebSocketManager.get_instance(db_manager)

        # Add a new WebSocket connection and start the heartbeat
        connection = Connection(client_id, websocket)
        ws_manager.active_websockets[client_id] = connection
        create_task(ws_manager.heartbeat(websocket))

        # Notify about new connection
        await ws_manager.broadcast(json.dumps({"action": "connect", "clientId": client_id}))

        try:
            while True:
                message = await websocket.receive()
                message_type = message["type"]

                if message_type == "websocket.receive":
                    data = message.get("text")
                    if data is not None:
                        print(f"Received text data: {data}")
                        await ws_manager.handle_new_data(data, client_id)
                    else:
                        data = message.get("bytes")
                        if data is not None:
                            print(f"Received byte data: {data}")
                            ws_manager.queue.put((data, client_id))


        except Exception as e:
            print(f"Error in websocket: {e}")

        finally:
            # Clean up on disconnection
            if client_id in ws_manager.active_websockets:
                del ws_manager.active_websockets[client_id]
                await ws_manager.broadcast(json.dumps({"action": "disconnect", "clientId": client_id}))
            print(f"Client {client_id} disconnected")

    @app.post("/add_category/")
    async def add_category(category_name: str):
        db.add_category(category_name)
        return {"message": f"Category {category_name} added successfully"}

    @app.delete("/remove_category/{category_id}")
    async def remove_category(category_id: str):
        db.remove_category(category_id)
        return {"message": f"Category with id {category_id} removed successfully"}

    @app.delete("/remove_all_categories/")
    async def remove_category():
        documents_deleted_count = db.delete_all_categories()
        return {"message": f"Removed {documents_deleted_count} categories successfully"}

    @app.put("/update_category/{category_id}")
    async def update_category(category_id: str, new_name: str):
        db.update_category(category_id, new_name)
        return {"message": f"Category with id {category_id} updated successfully to {new_name}"}

    @app.put("/update_part/{part_id}")
    async def update_part(part_id: str, updated_part: PartModel):
        success = db.update_part(part_id, updated_part.dict())
        if success:
            return {"message": f"Part with id {part_id} updated successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Part with id {part_id} not found")

    # @app.post("/printer/print_qr")
    # async def print_qr_code(label_data: LabelData):
    #     # Access the part_name and part_number from the request body
    #     part_number = label_data.part_number
    #     part_name = label_data.part_name
    #
    #     # Lookup logic based on the provided values
    #     _part = None
    #     if part_number:
    #         _part = await db.get_part_by_part_number(part_number)
    #     if not _part and part_name:
    #         _part = await db.get_part_by_part_name(part_name)
    #
    #     if not _part:
    #         raise HTTPException(status_code=404, detail="Part not found")
    #
    #     # Generate and print the QR code
    #     qr_img = qrcode.make(f'{{"name": "{_part["part_name"]}", "number": "{_part["part_number"]}"}}')
    #     # Call the printer function to print the QR code
    #     response = printer.print_qr_from_memory(qr_img)
    #
    #     if response:
    #         return {"message": "QR code printed successfully"}
    #     else:
    #         raise HTTPException(status_code=500, detail="Failed to print QR code")

    @app.post("/printer/config")
    async def configure_printer(config: printer_config_model.PrinterConfig):
        printer.set_backend(config.backend)
        printer.set_printer_identifier(config.printer_identifier)
        printer.save_config()  # Save the configuration
        return {"message": "Printer configuration updated and saved."}

    # Route to load printer configuration
    @app.get("/printer/load_config")
    async def load_printer_config():
        try:
            printer.load_config()
            return {"message": "Printer configuration loaded."}
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Config file not found.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
