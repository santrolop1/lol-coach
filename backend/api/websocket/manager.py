"""
backend/api/websocket/manager.py — Gestor de conexiones WebSocket activas.

Mantiene la lista de clientes conectados y permite broadcast.
Thread-safe para uso con asyncio.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger("lol_coach.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self._active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._active.append(ws)
        logger.info("WS conectado. Clientes activos: %d", len(self._active))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._active:
            self._active.remove(ws)
        logger.info("WS desconectado. Clientes activos: %d", len(self._active))

    async def broadcast(self, data: dict) -> None:
        """Envía datos a todos los clientes conectados. Desconecta los caídos."""
        dead: list[WebSocket] = []
        for ws in list(self._active):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def count(self) -> int:
        return len(self._active)


# Instancia global (singleton por proceso)
manager = ConnectionManager()
