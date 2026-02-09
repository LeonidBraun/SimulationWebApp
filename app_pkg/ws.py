import asyncio
from typing import Dict
from fastapi import APIRouter, WebSocket, status
from starlette.websockets import WebSocketDisconnect

ws_router = APIRouter()


class UserConnectionManager:
    """
    Manages one WebSocket per user session.
    Each WebSocket has a dedicated queue and sender task.
    Messages are multiplexed by type (chart_update, file_update, notification, etc.)
    """

    def __init__(self):
        self.user_queues: Dict[str, Dict[WebSocket, asyncio.Queue]] = (
            {}
        )  # user_id -> {ws -> queue}
        self.ws_to_user: Dict[WebSocket, str] = {}  # ws -> user_id
        self.tasks: Dict[WebSocket, asyncio.Task] = {}  # ws -> sender_task
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        q: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            if user_id not in self.user_queues:
                self.user_queues[user_id] = {}
            self.user_queues[user_id][websocket] = q
            self.ws_to_user[websocket] = user_id
            self.tasks[websocket] = asyncio.create_task(self._sender(websocket, q))

    async def _sender(self, websocket: WebSocket, queue: asyncio.Queue):
        """Dedicated task: pops messages from queue and sends to websocket"""
        try:
            while True:
                msg = await queue.get()
                await websocket.send_json(msg)
        except Exception as e:
            print(f"Send failed: {e}")
        finally:
            await self.disconnect(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            user_id = self.ws_to_user.pop(websocket, None)
            if user_id:
                self.user_queues[user_id].pop(websocket, None)
                if not self.user_queues[user_id]:
                    del self.user_queues[user_id]
            task = self.tasks.pop(websocket, None)
            if task:
                task.cancel()

    async def broadcast_to_user(self, user_id: str, msg):
        """Broadcast to all connections for a specific user"""
        async with self._lock:
            if user_id in self.user_queues:
                for q in list(self.user_queues[user_id].values()):
                    try:
                        q.put_nowait(msg)
                    except asyncio.QueueFull:
                        pass

    async def disconnect_user(self, user_id: str):
        """Disconnect all websockets for a specific user (e.g., on logout)"""
        async with self._lock:
            if user_id in self.user_queues:
                websockets = list(self.user_queues[user_id].keys())
                for ws in websockets:
                    await ws.close(code=status.WS_1008_POLICY_VIOLATION)
                del self.user_queues[user_id]
                for ws in websockets:
                    self.ws_to_user.pop(ws, None)
                    task = self.tasks.pop(ws, None)
                    if task:
                        task.cancel()


manager = UserConnectionManager()


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint that validates user from session middleware.
    Re-validates session every 30 seconds to detect logout/credential changes.
    """
    user_id = None
    try:
        user_id = websocket.session.get("user_id")
    except Exception:
        user_id = None

    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket, user_id)

    # Create a re-validation task that checks session every 30 seconds
    async def validate_session_periodically():
        while True:
            try:
                await asyncio.sleep(30)
                # Re-check if session is still valid
                current_user = websocket.session.get("user_id")
                if current_user != user_id:
                    # User changed or logged out - close connection
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    break
            except Exception:
                break

    validation_task = asyncio.create_task(validate_session_periodically())

    try:
        while True:
            # Keep-alive: listen for client messages; if client closes, this will raise
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(websocket)
    finally:
        validation_task.cancel()
        try:
            await validation_task
        except asyncio.CancelledError:
            pass
