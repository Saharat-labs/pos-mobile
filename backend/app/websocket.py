"""WebSocket manager สำหรับ real-time sync notifications."""

import json
from typing import Set, Dict
from fastapi import WebSocket


class ConnectionManager:
    """จัดการ WebSocket connections — broadcast เมื่อมีข้อมูลเปลี่ยน."""

    def __init__(self):
        self.active: Set[WebSocket] = set()
        # group ตาม device_id เพื่อ broadcast เฉพาะกลุ่ม
        self.rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, room: str = "default"):
        await ws.accept()
        self.active.add(ws)
        self.rooms.setdefault(room, set()).add(ws)

    def disconnect(self, ws: WebSocket, room: str = "default"):
        self.active.discard(ws)
        if room in self.rooms:
            self.rooms[room].discard(ws)
            if not self.rooms[room]:
                del self.rooms[room]

    async def broadcast(self, message: dict, room: str = None):
        """ส่ง message ไปทุก connection (หรือเฉพาะ room)."""
        data = json.dumps(message, ensure_ascii=False)
        targets = self.rooms.get(room, set()) if room else self.active
        dead = set()
        for ws in targets:
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        # เก็บกวาด connection ที่ตายแล้ว
        for ws in dead:
            self.active.discard(ws)
            for r in self.rooms.values():
                r.discard(ws)


# Singleton
manager = ConnectionManager()


async def notify_data_change(entity: str, action: str, detail: dict = None):
    """เรียกจาก service หลังเปลี่ยนข้อมูล — broadcast ผ่าน WebSocket."""
    await manager.broadcast({
        "type": "data_change",
        "entity": entity,    # products, sales, purchases, ...
        "action": action,    # create, update, delete
        "detail": detail or {},
    })
