import importlib.util
import os
import sys
import uuid
import json
import threading
import time
import base64

from asyncio import Queue, create_task, sleep
from lib.Connection import Connection
from fastapi.staticfiles import StaticFiles
from lib.part_inventory import PartInventory
import uvicorn
from threading import Thread, Lock
from lib.job_manager import JobManager
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.responses import HTMLResponse

app = FastAPI()
parsers = []
queue = Queue()

websocket_info = {}

# Create TinyDB Doc Store
db = PartInventory('part_inventory.json')

sys.path.append("./parsers")
active_websockets = {}

websocket_info_lock = Lock()
job_manager = JobManager()


# Updated update_websocket_info function with thread-safe access
def update_websocket_info(client_id, status):
    with websocket_info_lock:
        websocket_info[client_id] = {'status': status}


class ParserMeta:
    def parse(self, data: str):
        pass


class QRParser(ParserMeta):
    def parse(self, data: str):
        print(f"QR Code: {data}")


class BarcodeParser(ParserMeta):
    def parse(self, data: str):
        print(f"Barcode: {data}")


def load_parsers():
    parsers = []
    parser_dir = './parsers/'
    for filename in os.listdir(parser_dir):
        full_path = os.path.join(parser_dir, filename)
        if os.path.isfile(full_path) and filename.endswith('.py') and not filename.startswith(
                '__') and filename != "parser.py":
            module_name = filename[:-3]
            module_path = full_path

            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and 'Parser' in str(attr.__bases__):
                    parsers.append(attr())

    return parsers


async def heartbeat(websocket: WebSocket):
    while True:
        try:
            await websocket.send_text("heartbeat")
            await sleep(5)  # send a heartbeat every 10 seconds
        except Exception as e:
            print(f"Error sending heartbeat: {e}")
            break  # If error occurs, break the loop


async def broadcast(message: str):
    for client_id, connection in active_websockets.items():
        try:
            await connection.websocket.send_text(message)
        except Exception as e:
            print(f"Error sending message to client {client_id}: {e}")


async def update_database(data):
    await db.add_part(data)


@app.put("/update_quantity/")
async def update_part_quantity(manufacturer_pn: str, new_quantity: int):
    # Call the update_quantity method from the PartInventory class
    db.update_quantity(manufacturer_pn, new_quantity)
    return {"message": f"Quantity updated for part with manufacturer part number {manufacturer_pn} to {new_quantity}"}


@app.put("/decrement_count/")
async def decrement_count(manufacturer_pn: str, by: int = 1):
    # Call the update_quantity method from the PartInventory class
    db.decrement_count(manufacturer_pn, by)
    return {"message": f"Quantity decremented by {by} for part with manufacturer part number {manufacturer_pn}"}


# Define the process_queue function without the infinite loop
async def process_queue():
    loaded_parsers = load_parsers()
    data, client_id = await queue.get()

    if data is not None:
        data = bytes.fromhex(data)

        for parser in loaded_parsers:
            if parser.check(data):
                # This data matches the parser signature
                parser.process(data)
                await update_database(parser)
                # Send processed data back to the client
                if client_id in active_websockets:
                    connection = active_websockets[client_id]
                    await connection.websocket.send_text(str(parser.toJson()))


# Create a separate function to handle new data reception
async def handle_new_data(new_data, client_id):
    loaded_parsers = load_parsers()

    for parser in loaded_parsers:
        if parser.matches(new_data):
            parser.parse(new_data)
            parser.enrich()

            # Send the enriched data to the client and wait for a response
            if len(parser.required_inputs) != 0:
                # We have inputs we need to resolve before we can put this into the database.
                required_data = parser.format_required_data(part_number=parser.part.part_number,
                                                            requirements=parser.required_inputs, clientId=client_id)
                job_manager.create_job(parser, client_id)

                await send_data_to_client(client_id, required_data)
                # Wait for the user's input from the phone app
                user_input = await receive_input_from_client(client_id)

                # Validate and process user input
                if parser.validate(user_input):
                    # Add part to the database

                    return_message = db.add_part(parser)
                    if return_message['event'] == 'part_added':
                        await send_data_to_client(client_id, data=parser.to_json(return_message))
                    elif return_message['event'] == 'question':

                        await send_data_to_client(client_id, data=parser.to_json(return_message))
                        user_response = await receive_input_from_client(client_id)
                        if user_response:
                            db.add_part(parser, overwrite=True)


async def receive_input_from_client(client_id):
    """
    Wait for and return the user's input from the client identified by client_id.
    """
    if client_id in active_websockets:
        connection = active_websockets[client_id]
        try:
            # Wait for a message from the client. This will pause execution here
            # until a message is received.
            response = await connection.websocket.receive_text()
            print(f"Response from user_input {response}")
            return response  # Return the received input
        except Exception as e:
            print(f"Error receiving input from client {client_id}: {e}")
            return None
    else:
        print(f"No active WebSocket connection for client {client_id}")
        return None


# Serve static files from the "build/static" directory
app.mount("/static", StaticFiles(directory="static/part_inventory_ui/build/static"), name="static")


# Define a route to serve the index.html file
@app.get("/")
async def serve_index_html():
    return FileResponse("static/part_inventory_ui/build/index.html")


@app.on_event("startup")
async def startup_event():
    create_task(process_queue())


@app.get("/all_parts/")
async def get_all_parts():
    try:

        parts = db.get_all_parts()
        return JSONResponse(content=parts, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/clear_parts")
async def clear_all_parts():
    try:
        db.clear_all_parts()
        return {"status": "success", "message": "All parts have been cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_part/{part_number}")
async def get_part_by_part_number(part_number: str):
    try:
        part = db.get_part_by_part_number(part_number)
        if part:
            return JSONResponse(content=part, status_code=200)
        else:
            return JSONResponse(content={"error": "Part not found"}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/search/{query}")
async def search(query: str):
    try:
        search_results = db.search_parts(query)
        suggestions = db.get_suggestions(query)
        return {"search_results": search_results, "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def send_data_to_client(client_id, data):
    """
    Sends data to a specific WebSocket client.

    :param client_id: The unique identifier for the client's WebSocket connection.
    :param data: The data to be sent to the client. Should be in JSON format.
    """
    # Check if the client_id exists in the active_websockets
    if client_id in active_websockets:
        connection = active_websockets[client_id]
        try:
            # Send the data to the client
            await connection.websocket.send_text(data)
            print(f"Data sent to client {client_id}.")
        except Exception as e:
            print(f"Error sending data to client {client_id}: {e}")
    else:
        print(f"No active connection found for client {client_id}.")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = str(uuid.uuid4())
    await websocket.accept()

    connection = Connection(client_id, websocket)
    connection.start_heartbeat(heartbeat(websocket))

    active_websockets[client_id] = connection
    update_websocket_info(client_id, 'Connected')
    await broadcast(json.dumps({"action": "connect", "clientId": client_id}))

    try:
        while True:
            message = await websocket.receive()
            message_type = message["type"]

            if message_type == "websocket.receive":
                data = message.get("text")
                print(f"Received text data: {data}")
                if data is not None:
                    await handle_new_data(data, client_id)
                else:
                    data = message.get("bytes")
                    if data is not None:
                        print(f"Received byte data: {data}")
                        await queue.put((data, client_id))

    except Exception as e:
        print(f"Error in websocket: {e}")

    finally:
        if client_id in active_websockets:
            active_websockets[client_id].stop_heartbeat()
            del active_websockets[client_id]
            update_websocket_info(client_id, 'Disconnected')
            await broadcast(json.dumps({"action": "disconnect", "clientId": client_id}))
        print(f"Client {client_id} disconnected")


if __name__ == "__main__":
    # Start the FastAPI server
    uvicorn.run(app, host='0.0.0.0', port=57891)
