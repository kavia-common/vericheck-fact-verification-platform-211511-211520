from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

router = APIRouter(tags=["stream"], include_in_schema=True)


class ConnectionManager:
    """Simple WS connection manager with broadcast support."""

    def __init__(self) -> None:
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        # Send JSON to all connected clients; ignore failures
        for ws in list(self.active):
            try:
                if ws.application_state == WebSocketState.CONNECTED:
                    await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


ws_manager = ConnectionManager()


@router.websocket("/api/v1/stream")
async def stream_endpoint(websocket: WebSocket):
    """WebSocket stream endpoint to broadcast claim processing events.

    Security: expects standard FastAPI header "Authorization: Bearer <token>" in the WS query headers.
    The handler performs an auth handshake before admitting connection.

    Messages broadcast:
    - claim_created
    - claim_updated
    - sources_fetched
    - score_updated
    - job_completed
    - job_failed
    """
    # Manual auth handshake using HTTP headers
    # Starlette exposes headers on websocket at connection time
    auth = websocket.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        await websocket.close(code=4401)
        return
    token = auth.split(" ", 1)[1]
    # Reuse security decode to validate
    from src.core.security import decode_token

    try:
        decode_token(token)
    except Exception:
        await websocket.close(code=4401)
        return

    await ws_manager.connect(websocket)
    try:
        while True:
            # We don't expect client messages, but keep alive by receiving
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
