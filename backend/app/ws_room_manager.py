from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


class CaseRoomManager:
    """In-memory fan-out for a case_id room (prototype; scale-out needs Redis/SSE gateway)."""

    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = {}

    def _ensure_room(self, case_id: str) -> set[WebSocket]:
        room = self._rooms.get(case_id)
        if room is None:
            room = set()
            self._rooms[case_id] = room
        return room

    async def connect(self, case_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._ensure_room(case_id).add(websocket)

    def disconnect(self, case_id: str, websocket: WebSocket) -> None:
        room = self._rooms.get(case_id)
        if not room:
            return
        room.discard(websocket)
        if not room:
            del self._rooms[case_id]

    async def broadcast_json(self, case_id: str, message: dict[str, Any], *, exclude: WebSocket | None = None) -> None:
        room = self._rooms.get(case_id)
        if not room:
            return
        text = json.dumps(message, default=str)
        dead: list[WebSocket] = []
        for ws in room:
            if ws is exclude:
                continue
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            room.discard(ws)


case_room_manager = CaseRoomManager()
