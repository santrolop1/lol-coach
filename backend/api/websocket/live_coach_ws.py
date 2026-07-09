"""
backend/api/websocket/live_coach_ws.py — WebSocket /ws/live-coach

Envía el estado del overlay cada TICK_INTERVAL segundos.
El overlay React se suscribe aquí y re-renderiza con cada mensaje.

Protocolo:
  → cliente conecta
  ← servidor envía JSON (OverlayState.to_dict()) cada N segundos
  → cliente puede enviar {"action": "set_champion", "champion": "tryndamere", "role": "TOP"}
  ← servidor confirma con {"ok": true}

No hay lógica de negocio aquí — solo serialización y timing.
"""

from __future__ import annotations
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger("lol_coach.ws.live_coach")

_TICK_INTERVAL = 2.0        # segundos entre actualizaciones en juego
_IDLE_INTERVAL = 5.0        # cuando no hay partida activa


@router.websocket("/ws/live-coach")
async def live_coach_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("Live Coach WebSocket conectado")

    from backend.api.routes.live_coach import get_coach
    coach = get_coach()

    try:
        while True:
            # Tick + snapshot
            coach.tick()
            state = coach.get_state()
            await websocket.send_json(state.to_dict())

            # Mensajes entrantes del cliente (no bloquean)
            try:
                msg_text = await asyncio.wait_for(
                    websocket.receive_text(), timeout=0.05
                )
                await _handle_client_message(msg_text, coach, websocket)
            except asyncio.TimeoutError:
                pass

            interval = _TICK_INTERVAL if state.session.active else _IDLE_INTERVAL
            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info("Live Coach WebSocket desconectado")
    except Exception as exc:
        logger.error("Error en Live Coach WebSocket: %s", exc, exc_info=True)


async def _handle_client_message(
    msg_text: str,
    coach,
    websocket: WebSocket,
) -> None:
    try:
        msg = json.loads(msg_text)
        action = msg.get("action")

        if action == "set_champion":
            champion = msg.get("champion", "")
            role = msg.get("role", "TOP")
            if champion:
                coach.set_champion(champion, role)
                await websocket.send_json({"ok": True, "action": action})

        elif action == "reset":
            coach.reset()
            await websocket.send_json({"ok": True, "action": action})

        elif action == "ping":
            await websocket.send_json({"pong": True})

    except (json.JSONDecodeError, Exception) as exc:
        logger.warning("Mensaje de cliente inválido: %s", exc)
