from fastapi import WebSocket
from asyncio import create_task


class Connection:
    def __init__(self, client_id: str, websocket: WebSocket):
        self.client_id = client_id
        self.websocket = websocket
        self.heartbeat_task = None

    def start_heartbeat(self, heartbeat_coroutine):
        self.heartbeat_task = create_task(heartbeat_coroutine)

    def stop_heartbeat(self):
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
