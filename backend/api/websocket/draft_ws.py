"""
backend/api/websocket/draft_ws.py — WebSocket /ws/draft

Envía el estado del draft cada 750ms mientras hay clientes conectados.
El estado viene del DraftViewModel — sin lógica aquí.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.api.websocket.manager import manager
from backend.viewmodels.draft_vm import build_draft

router = APIRouter()
logger = logging.getLogger("lol_coach.ws.draft")

# Intervalo de refresh durante Champ Select
_CHAMP_SELECT_INTERVAL = 0.75
_IDLE_INTERVAL         = 2.0

# Cache compartido por proceso para el mapa de campeones
_champ_map_cache: dict = {}
_cpa_cache:       dict = {}


@router.websocket("/ws/draft")
async def draft_websocket(ws: WebSocket) -> None:
    """
    Stream del estado del draft en tiempo real.

    Envía JSON cada 750ms durante Champ Select, cada 2s en otras fases.

    Formato del mensaje:
    ```json
    {
        "lcu_connected": true,
        "phase": "ChampSelect",
        "phase_label": "Champ Select",
        "role": "ADC",
        "role_supported": true,
        "session": {...},
        "advice": {...},
        "champion_pool": {...}
    }
    ```
    """
    await manager.connect(ws)
    logger.info("Cliente draft conectado")

    try:
        while True:
            vm = build_draft(
                champion_map_cache=_champ_map_cache,
                cpa_cache=_cpa_cache,
            )

            if vm.champion_map:
                _champ_map_cache.update(vm.champion_map)

            payload = _serialize_vm(vm)
            await ws.send_json(payload)

            interval = _CHAMP_SELECT_INTERVAL if vm.phase == "ChampSelect" else _IDLE_INTERVAL
            await asyncio.sleep(interval)

    except WebSocketDisconnect:
        logger.info("Cliente draft desconectado")
    except Exception as e:
        logger.error("Error en WebSocket draft: %s", e)
    finally:
        manager.disconnect(ws)


def _serialize_vm(vm) -> dict:
    """Convierte DraftViewModel a dict JSON-serializable."""
    def _try_asdict(obj) -> dict | None:
        if obj is None:
            return None
        try:
            return dataclasses.asdict(obj)
        except Exception:
            return {}

    return {
        "lcu_connected":  vm.lcu_connected,
        "phase":          vm.phase,
        "phase_label":    vm.phase_label,
        "role":           vm.role,
        "role_supported": vm.role_supported,
        "session":        _try_asdict(vm.session),
        "advice":         _try_asdict(vm.advice),
        "champion_pool":  _try_asdict(vm.champion_pool),
    }
