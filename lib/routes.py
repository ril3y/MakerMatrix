import threading
import json
import threading
import uuid
from asyncio import create_task

from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
from starlette.responses import FileResponse

from lib.connection import Connection
from database import DatabaseManager

# Import necessary modules and classes
from lib.part_inventory import PartInventory
from parser_manager import ParserManager
from lib.websockets import WebSocketManager
from lib.database import DatabaseManager
# Initialize or import the PartInventory instance (adjust this according to your project setup)
db = PartInventory('part_inventory.json')

# Global variables (update or import these as per your actual project setup)
active_websockets = {}
websocket_info = {}
websocket_info_lock = threading.Lock()



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
