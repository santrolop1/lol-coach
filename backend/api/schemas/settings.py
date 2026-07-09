"""Schemas Pydantic para la pantalla de Configuración."""

from __future__ import annotations
from pydantic import BaseModel


class SettingsResponse(BaseModel):
    is_configured: bool
    puuid:         str | None
    platform:      str | None
    platform_name: str | None
    riot_id:       str | None
    tag:           str | None
    level:         int | None
    rank:          str | None
    tier:          str | None
    lp:            int | None


# ── API Key Management ─────────────────────────────────────────────────────────

class ApiKeyStatusResponse(BaseModel):
    configured:   bool
    status:       str           # "active" | "expiring_soon" | "expired" | "not_configured"
    status_label: str           # texto en español
    masked_key:   str | None    # RGAPI-****..****ABCD
    saved_at:     str | None    # ISO 8601 UTC
    hours_old:    float | None  # horas desde que se guardó


class ApiKeySaveRequest(BaseModel):
    api_key: str


class ApiKeySaveResponse(BaseModel):
    success:     bool
    message:     str
    status:      str            # "active" | "expired" | "invalid"
    masked_key:  str | None


# ── Cuenta ────────────────────────────────────────────────────────────────────

class AccountChangeRequest(BaseModel):
    game_name: str
    tag_line:  str
    platform:  str


class AccountChangeResponse(BaseModel):
    success:  bool
    message:  str
    riot_id:  str
    tag:      str
    level:    int
    rank:     str


class HealthResponse(BaseModel):
    status:    str          # "ok" | "degraded" | "error"
    version:   str
    db:        str          # "ok" | "error"
    lcu:       str          # "connected" | "disconnected"
    riot_api:  str          # "configured" | "not_configured"
    last_sync: str | None
