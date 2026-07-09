"""
GET    /settings               — Configuración actual del usuario.
POST   /settings/sync          — Fuerza una sincronización inmediata.
GET    /settings/api-key/status — Estado de la API key (sin devolver la key).
POST   /settings/api-key       — Guarda y valida la API key.
DELETE /settings/api-key       — Elimina la API key.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

import db
from riot_api import RiotClient, RiotAPIError, RiotNotFoundError
from backend.viewmodels.settings_vm import build_settings
from backend.api.schemas.settings import (
    SettingsResponse,
    ApiKeyStatusResponse,
    ApiKeySaveRequest,
    ApiKeySaveResponse,
    AccountChangeRequest,
    AccountChangeResponse,
)
from backend.services.sync_service import sync_matches, SyncResult
from backend.services.setup_service import resolve_riot_account, save_account, detect_account_from_lcu

router = APIRouter()

# Edad (horas) a partir de la cual la key se considera "próxima a expirar"
_EXPIRING_SOON_HOURS = 20.0

_RGAPI_RE = re.compile(r'^RGAPI-[0-9a-f\-]{8,}$', re.IGNORECASE)


def _mask_key(key: str) -> str:
    """Devuelve RGAPI-********************XXXX (últimos 4 visibles)."""
    if len(key) <= 4:
        return '****'
    return f"RGAPI-{'*' * 20}{key[-4:]}"


def _hours_old(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        saved = datetime.fromisoformat(iso)
        if saved.tzinfo is None:
            saved = saved.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - saved
        return delta.total_seconds() / 3600
    except ValueError:
        return None


# ── Endpoints existentes ───────────────────────────────────────────────────────

@router.get("/settings", response_model=SettingsResponse, tags=["Configuración"])
def get_settings() -> SettingsResponse:
    """Devuelve la configuración actual: cuenta, plataforma, estado."""
    vm = build_settings()
    return SettingsResponse(
        is_configured= vm.is_configured,
        puuid=         vm.puuid,
        platform=      vm.platform,
        platform_name= vm.platform_name,
        riot_id=       vm.riot_id,
        tag=           vm.tag,
        level=         vm.level,
        rank=          vm.rank,
        tier=          vm.tier,
        lp=            vm.lp,
    )


@router.post("/settings/detect-from-lcu", tags=["Configuración"])
def detect_from_lcu() -> dict:
    """Detecta la cuenta logeada en el cliente de League y la sincroniza automáticamente."""
    return detect_account_from_lcu()


@router.post("/settings/account", response_model=AccountChangeResponse, tags=["Configuración"])
def change_account(body: AccountChangeRequest) -> AccountChangeResponse:
    """Reconfigura el Riot ID activo (cambio de cuenta) y resincroniza el perfil."""
    api_key = db.get_config("api_key")
    if not api_key:
        raise HTTPException(
            status_code=422,
            detail="No hay una Riot API key configurada. Configurala antes de cambiar de cuenta."
        )

    try:
        profile = resolve_riot_account(
            api_key=api_key,
            platform=body.platform,
            game_name=body.game_name,
            tag_line=body.tag_line,
        )
    except RiotNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró esa cuenta de Riot.")
    except RiotAPIError as e:
        raise HTTPException(status_code=502, detail=f"Error consultando Riot API: {e}")

    save_account(
        api_key=api_key,
        platform=body.platform,
        game_name=body.game_name,
        tag_line=body.tag_line,
        profile=profile,
    )

    return AccountChangeResponse(
        success=True,
        message="Cuenta actualizada correctamente.",
        riot_id=profile["riot_id"],
        tag=profile["tag"],
        level=profile["level"],
        rank=profile["rank"],
    )


@router.post("/settings/sync", tags=["Configuración"])
def trigger_sync() -> dict:
    """Fuerza una sincronización inmediata de partidas con Riot API."""
    result: SyncResult = sync_matches()
    return {
        "status":    result.status,
        "saved":     result.saved,
        "skipped":   result.skipped,
        "new_found": result.new_found,
        "error_msg": result.error_msg,
        "synced_at": result.synced_at.isoformat() if result.synced_at else None,
    }


# ── API Key management ─────────────────────────────────────────────────────────

@router.get("/settings/api-key/status", response_model=ApiKeyStatusResponse, tags=["Configuración"])
def get_api_key_status() -> ApiKeyStatusResponse:
    """Estado de la API key. Nunca devuelve la key completa."""
    raw_key  = db.get_config("api_key")
    saved_at = db.get_config("api_key_saved_at")
    hours    = _hours_old(saved_at)

    if not raw_key:
        return ApiKeyStatusResponse(
            configured=False,
            status="not_configured",
            status_label="No configurada",
            masked_key=None,
            saved_at=saved_at,
            hours_old=None,
        )

    expired_flag = db.get_config("api_key_expired")
    if expired_flag == "1":
        status, label = "expired", "Expirada"
    elif hours is not None and hours >= _EXPIRING_SOON_HOURS:
        status, label = "expiring_soon", "Próxima a expirar"
    else:
        status, label = "active", "Activa"

    return ApiKeyStatusResponse(
        configured=True,
        status=status,
        status_label=label,
        masked_key=_mask_key(raw_key),
        saved_at=saved_at,
        hours_old=round(hours, 1) if hours is not None else None,
    )


@router.post("/settings/api-key", response_model=ApiKeySaveResponse, tags=["Configuración"])
def save_api_key(body: ApiKeySaveRequest) -> ApiKeySaveResponse:
    """Guarda y valida la Riot API key. Lanza 401 si es inválida."""
    key = body.api_key.strip()

    if not _RGAPI_RE.match(key):
        raise HTTPException(
            status_code=422,
            detail="Formato inválido. La key debe comenzar con RGAPI- seguido de caracteres hexadecimales."
        )

    platform = db.get_config("platform") or "la1"
    try:
        client = RiotClient(api_key=key, platform=platform)
        valid  = client.validate_key()
    except (RiotAPIError, Exception):
        valid = False

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="La API key es inválida o ha expirado. Genera una nueva en developer.riotgames.com"
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    db.save_config("api_key",          key)
    db.save_config("api_key_saved_at", now_iso)
    db.delete_config("api_key_expired")

    return ApiKeySaveResponse(
        success=True,
        message="Riot API configurada correctamente.",
        status="active",
        masked_key=_mask_key(key),
    )


@router.delete("/settings/api-key", tags=["Configuración"])
def delete_api_key() -> dict:
    """Elimina la Riot API key guardada."""
    db.delete_config("api_key")
    db.delete_config("api_key_saved_at")
    db.delete_config("api_key_expired")
    return {"success": True, "message": "API key eliminada."}
