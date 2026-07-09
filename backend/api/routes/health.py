"""
GET /health — Estado del sistema.

Verifica: DB, LCU, Riot API configurada, última sync.
"""

from __future__ import annotations

from fastapi import APIRouter

import db
import lcu.client as lcu_client
from backend.api.schemas.settings import HealthResponse
from backend.services.sync_service import get_last_sync

router = APIRouter()

VERSION = "E-2.0.0"


@router.get("/health", response_model=HealthResponse, tags=["Sistema"])
def get_health() -> HealthResponse:
    """
    Verifica el estado de todos los subsistemas.

    - **db**: acceso a SQLite
    - **lcu**: League Client detectado en lockfile
    - **riot_api**: API Key configurada
    - **last_sync**: timestamp de la última sincronización
    """

    # DB
    try:
        db.get_config("__health_check__")
        db_status = "ok"
    except Exception:
        db_status = "error"

    # LCU
    try:
        creds = lcu_client.read_credentials()
        lcu_status = "connected" if creds is not None else "disconnected"
    except Exception:
        lcu_status = "disconnected"

    # Riot API
    api_key = db.get_config("api_key")
    riot_status = "configured" if api_key else "not_configured"

    # Última sync
    last = get_last_sync()
    last_sync_str = last.isoformat() if last else None

    overall = "ok" if db_status == "ok" else "error"

    return HealthResponse(
        status=overall,
        version=VERSION,
        db=db_status,
        lcu=lcu_status,
        riot_api=riot_status,
        last_sync=last_sync_str,
    )
