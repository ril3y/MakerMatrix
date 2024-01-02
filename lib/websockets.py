import json
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from lib.connection import Connection
from asyncio import sleep, create_task
from database import DatabaseManager
import queue
from threading import Lock
from parser_manager import ParserManager
import json
import uuid
from fastapi import WebSocket
from lib.connection import Connection
from asyncio import sleep, Queue
from lib.database import DatabaseManager
from lib.parser_manager import ParserManager
from threading import Lock

class WebSocketManager:
    _instance = None
    _instance_lock = Lock()

    def __init__(self, db_manager: DatabaseManager):
        if WebSocketManager._instance is not None:
            raise Exception("This class is a singleton! Use 'get_instance()' to get its instance.")

        self.active_websockets = {}
        self.db_manager = db_manager
        self.parser_manager = ParserManager()
        self.queue = Queue()

    @classmethod
    def get_instance(cls, db_manager: DatabaseManager):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(db_manager)
        return cls._instance

    @classmethod
    def add_to_queue(cls, item):
        if cls._instance is not None:
            cls._instance.queue.put(item)
        else:
            raise Exception("WebSocketManager instance is not initialized.")

    # Define the process_queue function without the infinite loop
    async def process_queue(self):
        while True:
            data, client_id = await self.queue.get()
            if data is not None:
                data = bytes.fromhex(data)
                for parser in self.parser_manager.get_parser_instances():
                    if parser.check(data):
                        parser.process(data)
                        await self.db_manager.update_database(parser)
                        if client_id in self.active_websockets:
                            connection = self.active_websockets[client_id]
                            await connection.websocket.send_text(str(parser.toJson()))

    async def heartbeat(self, websocket: WebSocket):
        while True:
            try:
                await websocket.send_text("heartbeat")
                print("Sending heartbeat")
                await sleep(5)  # Adjust the interval as needed
            except WebSocketDisconnect:
                break

    async def broadcast(self, message: str):
        for client_id, connection in self.active_websockets.items():
            try:
                await connection.websocket.send_text(message)
            except Exception as e:
                print(f"Error sending message to client {client_id}: {e}")

    async def process_and_add_part(self, parser, client_id):
        """
        Processes and adds a part to the database. It handles required inputs, validates user responses,
        and manages the overwrite scenario when a part already exists in the database.

        Args:
            parser: The parser object containing part data and required inputs.
            client_id: The identifier of the client making the request.

        The method operates in a loop to continuously process data until all required inputs are fulfilled
        and the part is successfully added or updated in the database.
        """

        while True:
            # Check if there are required inputs yet to be fulfilled
            if len(parser.required_inputs) != 0:
                # Format required data for client response
                required_data = parser.format_required_data(part_number=parser.part.part_number,
                                                            requirements=parser.required_inputs, clientId=client_id)

                # Send required data to the client
                await self.send_data_to_client(client_id, required_data)

                # Receive input from the client
                user_input = await self.receive_input_from_client(client_id)

                # Validate user input; if invalid, continue the loop to request input again
                if not parser.validate(user_input):
                    continue

            # Attempt to add the part to the database
            return_message = await self.db_manager.add_part(parser)

            # Handle scenario where a part already exists (indicated by 'question' event)
            if return_message['event'] == 'question':
                # Send the question to the client
                await self.send_data_to_client(client_id, parser.to_json(return_message))

                # Wait for user response to the question
                user_response = await self.receive_input_from_client(client_id)
                user_response_data = json.loads(user_response)['data']

                # Check user's response
                if user_response_data == "yes":
                    # If 'yes', overwrite the part in the database and check the response
                    overwrite_response = await self.db_manager.add_part(parser, overwrite=True)

                    # If the response event is not 'question', assume success and exit the loop
                    if overwrite_response.get('event') != 'question':
                        await self.send_data_to_client(client_id, parser.to_json(overwrite_response))
                        break
                elif user_response_data == "no":
                    # If user responds with 'no', exit the loop without overwriting
                    break
            else:
                # If there's no 'question' event, part addition is successful; exit the loop
                await self.send_data_to_client(client_id,parser.to_json(return_message))
                break

    async def handle_new_data(self, new_data, client_id):
        parser = self.parser_manager.parse_data(new_data)
        if parser is not None:
            parser.enrich()
            await self.process_and_add_part(parser, client_id)

    async def receive_input_from_client(self, client_id):
        if client_id in self.active_websockets:
            connection = self.active_websockets[client_id]
            try:
                response = await connection.websocket.receive_text()
                print(f"Response from user_input {response}")
                return response
            except Exception as e:
                print(f"Error receiving input from client {client_id}: {e}")
                return None
        else:
            print(f"No active WebSocket connection for client {client_id}")
            return None

    async def send_data_to_client(self, client_id, data):
        if client_id in self.active_websockets:
            connection = self.active_websockets[client_id]
            try:
                await connection.websocket.send_text(data)
                print(f"Data sent to client {client_id}.")
            except Exception as e:
                print(f"Error sending data to client {client_id}: {e}")
        else:
            print(f"No active connection found for client {client_id}.")

