"""WebSocket route — เปิด connection สำหรับ real-time sync."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, room: str = "default"):
    """WebSocket endpoint สำหรับรับ notification Real-time.

    เชื่อมต่อ: ws://localhost:8000/api/v1/ws?room=default
    รับ message: {"type": "data_change", "entity": "products", "action": "create"}
    """
    await manager.connect(ws, room)
    try:
        while True:
            # รอรับ message จาก client (เช่น ping หรือ subscribe)
            data = await ws.receive_text()
            # Echo กลับเพื่อรักษา connection
            if data == "ping":
                await ws.send_text('{"type": "pong"}')
    except WebSocketDisconnect:
        manager.disconnect(ws, room)
