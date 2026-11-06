import json
from typing import Any, Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        if not self._connections:
            return
        message = json.dumps({"type": event_type, "payload": payload}, default=str)
        stale: list[WebSocket] = []
        for connection in list(self._connections):
            try:
                await connection.send_text(message)
            except Exception:
                stale.append(connection)
        for conn in stale:
            self._connections.discard(conn)

    @property
    def active_count(self) -> int:
        return len(self._connections)


ws_manager = ConnectionManager()
