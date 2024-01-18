import threading
import json
import threading
import uuid
from asyncio import create_task
from fastapi import FastAPI, HTTPException, Request
from typing import Optional
from fastapi import UploadFile, File
import os, shutil
from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from starlette.responses import FileResponse
from lib.connection import Connection
from database import DatabaseManager
from lib.part_inventory import PartInventory
from parser_manager import ParserManager
from lib.websockets import WebSocketManager
from lib.database import DatabaseManager
from lib.part_inventory import PartInventory
from pydantic import BaseModel, root_validator, ValidationError
from pydantic import BaseModel
from typing import List
import datetime

# Initialize or import the PartInventory instance (adjust this according to your project setup)
db = PartInventory('part_inventory.json')

# Global variables (update or import these as per your actual project setup)
active_websockets = {}
websocket_info = {}
websocket_info_lock = threading.Lock()


class LocationModel(BaseModel):
    id: Optional[str]  # Use Optional to make id field not required
    name: Optional[str]
    description: Optional[str]
    parent_id: Optional[str] = None  # Also make parent_id not required


class PartModel(BaseModel):
    part_number: Optional[str] = None
    part_name: Optional[str] = None
    quantity: Optional[int]
    description: Optional[str] = None
    supplier: Optional[str] = None  # Also make parent_id not required
    location: Optional[LocationModel] = None

    @root_validator
    def check_part_details(cls, values):
        part_number, part_name = values.get('part_number'), values.get('part_name')
        if part_number is None and part_name is None:
            raise ValueError('Either part_number or part_name must be provided')
        return values

    def to_json(self):
        return json.dumps(self.dict(), default=str)



def setup_routes(app: FastAPI):
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

    @app.get("/clear_parts")
    async def clear_all_parts():
        db.clear_all_parts()
        return {"status": "success", "message": "All parts have been cleared."}

    @app.get("/get_part/{part_number}")
    async def get_part_by_part_number(part_number: str):
        part = db.get_part_by_part_number(part_number)
        if part:
            return JSONResponse(content=part, status_code=200)
        else:
            return JSONResponse(content={"error": "Part not found"}, status_code=404)

    @app.get("/get_all_locations/")
    async def get_all_locations():
        db_manager = DatabaseManager.get_instance()
        locations = db_manager.get_all_locations()
        return JSONResponse(content={"locations": locations}, status_code=200)

    @app.get("/get_location_details/{location_id}")
    async def get_location_details(location_id: int):
        db_manager = DatabaseManager.get_instance()
        location = await db_manager.get_location_details(location_id)
        if location:
            return JSONResponse(content=location, status_code=200)
        else:
            return JSONResponse(content={"error": "Location not found"}, status_code=404)

    @app.put("/edit_location/{location_id}")
    async def edit_location(location_id: int, name: str = None, description: str = None, parent_id: int = None):
        db_manager = DatabaseManager.get_instance()
        updated_location = await db_manager.edit_location(location_id, name, description, parent_id)
        if updated_location:
            return {"message": "Location updated", "location": updated_location}
        else:
            return JSONResponse(content={"error": "Error updating location"}, status_code=400)

    @app.get("/clear_locations/")
    async def clear_locations():
        db_manager = DatabaseManager.get_instance()
        db.location_table.truncate()  # This clears all records in the locations table
        return {"message": "All locations cleared"}

    @app.post("/add_location/")
    async def add_location(location: LocationModel):
        db_manager = DatabaseManager.get_instance()

        # Add the new location to the database
        added_location = await db_manager.add_location(location.dict())

        # Return a success message with the added location data
        # return JSONResponse(content={"error": "Error updating location"}, status_code=400)
        if "error" in added_location:
            res = JSONResponse(content=added_location, status_code=409)
        else:
            res = JSONResponse(content=added_location, status_code=200)
        return res

    @app.get("/get_location/{location_id}")
    async def get_location(location_id: int):
        db_manager = DatabaseManager.get_instance()
        location = await db_manager.get_location(location_id)

        if location:
            return location
        else:
            return JSONResponse(content={"error": "Location not found"}, status_code=404)

    @app.get("/get_image/{image_id}")
    async def get_image(image_id: str):
        file_path = f"uploaded_images/{image_id}"
        if os.path.exists(file_path):
            return FileResponse(file_path)
        else:
            raise HTTPException(status_code=404, detail="Image not found")

    @app.post("/add_part")
    async def add_part(request: Request):
        try:
            json_data = await request.json()
            part = PartModel(**json_data)
            # Process and save part
            db_manager = DatabaseManager.get_instance('part_inventory.json')
            return_message = await db_manager.add_part(part, overwrite=False)
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

    @app.delete("/delete_location/{location_id}")
    async def delete_location(location_id: int):
        db_manager = DatabaseManager.get_instance()
        # Delete the location and its children
        deleted_location = await db_manager.delete_location(location_id)
        if deleted_location:
            return {"message": "Location deleted", "location": deleted_location}
        else:
            return JSONResponse(content={"error": "Error deleting location"}, status_code=400)

    @app.get("/search/{query}")
    async def search(query: str):
        search_results = db.search_parts(query)
        suggestions = db.get_suggestions(query)
        return {"search_results": search_results, "suggestions": suggestions}

    # Define a route to serve the index.html file
    @app.get("/")
    async def serve_index_html():
        return FileResponse("static/part_inventory_ui/build/index.html")

    @app.on_event("startup")
    async def startup_event():
        # Initialize DatabaseManager
        db_manager = DatabaseManager.get_instance('part_inventory.json')

        # Initialize WebSocketManager with the DatabaseManager instance
        ws_manager = WebSocketManager.get_instance(db_manager)

        # Start processing the queue
        create_task(ws_manager.process_queue())

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
                        await ws_manager.handle_new_data(data, client_id)  # Correct if handle_new_data is async
                    else:
                        data = message.get("bytes")
                        if data is not None:
                            print(f"Received byte data: {data}")
                            ws_manager.queue.put((data, client_id))  # Correct, as put is not awaited


        except Exception as e:
            print(f"Error in websocket: {e}")

        finally:
            # Clean up on disconnection
            if client_id in ws_manager.active_websockets:
                del ws_manager.active_websockets[client_id]
                await ws_manager.broadcast(json.dumps({"action": "disconnect", "clientId": client_id}))
            print(f"Client {client_id} disconnected")
