"""
GET /draft — Estado actual del draft (snapshot).

Para updates en tiempo real usa el WebSocket /ws/draft.
"""

from __future__ import annotations

import dataclasses

from fastapi import APIRouter

from backend.viewmodels.draft_vm import build_draft
from backend.api.schemas.draft import DraftResponse

router = APIRouter()

# Cache compartido para el mapa de campeones (evita re-fetch en cada request)
_champ_map_cache: dict = {}
_cpa_cache: dict = {}


@router.get("/draft", response_model=DraftResponse, tags=["Draft"])
def get_draft() -> DraftResponse:
    """
    Devuelve el estado actual del draft leyendo el LCU.

    - Si el cliente de LoL no está abierto: `lcu_connected=false`
    - Si está en Champ Select: incluye `session`, `advice`, `champion_pool`
    - Para tiempo real usa `/ws/draft`
    """
    vm = build_draft(
        champion_map_cache=_champ_map_cache,
        cpa_cache=_cpa_cache,
    )

    if vm.champion_map:
        _champ_map_cache.update(vm.champion_map)

    return DraftResponse(
        lcu_connected=  vm.lcu_connected,
        phase=          vm.phase,
        phase_label=    vm.phase_label,
        role=           vm.role,
        role_supported= vm.role_supported,
        session=        _serialize_session(vm.session) if vm.session else None,
        advice=         _serialize_advice(vm.advice) if vm.advice else None,
        champion_pool=  _serialize_cpa(vm.champion_pool) if vm.champion_pool else None,
    )


def _serialize_session(session) -> dict:
    try:
        return dataclasses.asdict(session)
    except Exception:
        return {}


def _serialize_advice(advice) -> dict:
    try:
        return dataclasses.asdict(advice)
    except Exception:
        return {}


def _serialize_cpa(cpa) -> dict:
    try:
        return dataclasses.asdict(cpa)
    except Exception:
        return {}
