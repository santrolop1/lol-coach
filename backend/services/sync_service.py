"""
backend/services/sync_service.py — Sincronización automática incremental.

Detecta partidas nuevas en Riot API, descarga solo las faltantes y
registra el timestamp de la última sync para controlar el intervalo.

NO descarga toda la historia en cada llamada.
SOLO descarga lo que falta desde la última partida guardada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import db
from riot_api import RiotClient, RiotAPIError
from parser import parse_match

# Mínimo de minutos entre syncs automáticas (evita abusar de la API)
SYNC_INTERVAL_MINUTES: int = 15

# Partidas a consultar en cada check (ranked solo)
_SYNC_FETCH_COUNT: int = 20


# ── Resultado ──────────────────────────────────────────────────────────────────

@dataclass
class SyncResult:
    status:    str            # "ok" | "no_new" | "error" | "rate_limited" | "no_credentials"
    saved:     int            # partidas guardadas en esta sync
    skipped:   int            # otras colas / ya existentes
    new_found: int            # IDs nuevos encontrados en Riot
    error_msg: str | None
    synced_at: datetime | None


# ── Tiempo y estado ────────────────────────────────────────────────────────────

def get_last_sync() -> datetime | None:
    """Última sync exitosa registrada en DB (UTC)."""
    raw = db.get_config("last_sync_time")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def minutes_since_last_sync() -> float:
    """Minutos desde la última sync. Devuelve inf si nunca sincronizó."""
    last = get_last_sync()
    if last is None:
        return float("inf")
    now = datetime.now(timezone.utc)
    return (now - last).total_seconds() / 60


def should_sync() -> bool:
    """True si han pasado más de SYNC_INTERVAL_MINUTES desde la última sync."""
    return minutes_since_last_sync() > SYNC_INTERVAL_MINUTES


def sync_status_label() -> str:
    """Texto breve del estado de sync para el sidebar."""
    last = get_last_sync()
    if last is None:
        return "Sin sincronizar"
    secs = int((datetime.now(timezone.utc) - last).total_seconds())
    if secs < 60:
        return "Sincronizado ahora"
    if secs < 3600:
        return f"Hace {secs // 60} min"
    if secs < 86400:
        return f"Hace {secs // 3600} h"
    return f"Hace {secs // 86400} días"


# ── Cache ──────────────────────────────────────────────────────────────────────

def invalidate_caches(session_state: dict) -> None:
    """
    Elimina del session_state todas las cachés de análisis derivadas
    (Champion Pool Analysis, champion map) que dependen del historial.
    Al recalcular, los valores reflejan las partidas nuevas.
    """
    stale = [k for k in session_state if k.startswith(("cpa_", "champ_map_", "champ_"))]
    for k in stale:
        del session_state[k]


# ── Sync principal ─────────────────────────────────────────────────────────────

def sync_matches(
    on_progress: Callable[[int, int], None] | None = None,
) -> SyncResult:
    """
    Descarga solo partidas que no existen en la DB.

    Proceso
    -------
    1. Lee credenciales de DB (api_key, puuid, platform).
    2. Obtiene los últimos _SYNC_FETCH_COUNT match IDs de Riot (ranked).
    3. Filtra los que ya están guardados (db.match_exists).
    4. Descarga y guarda solo los nuevos.
    5. Actualiza last_sync_time en config.

    Parámetros
    ----------
    on_progress : callback(done, total) llamado tras cada partida procesada.

    Retorna
    -------
    SyncResult con status y contadores.
    """
    api_key  = db.get_config("api_key")
    platform = db.get_config("platform") or "la1"
    puuid    = db.get_config("puuid")

    if not api_key or not puuid:
        return SyncResult(
            status="no_credentials", saved=0, skipped=0,
            new_found=0, error_msg=None, synced_at=None,
        )

    client = RiotClient(api_key, platform)

    # ── Obtener IDs recientes ──────────────────────────────────────────────────
    try:
        recent_ids = client.get_match_ids(puuid, count=_SYNC_FETCH_COUNT, queue=420)
    except RiotAPIError as e:
        err = str(e)
        status = "rate_limited" if "429" in err or "rate" in err.lower() else "error"
        return SyncResult(
            status=status, saved=0, skipped=0,
            new_found=0, error_msg=err, synced_at=None,
        )

    # ── Filtrar solo los nuevos ────────────────────────────────────────────────
    new_ids = [mid for mid in recent_ids if not db.match_exists(mid)]

    if not new_ids:
        _mark_synced()
        return SyncResult(
            status="no_new", saved=0, skipped=0,
            new_found=0, error_msg=None, synced_at=datetime.now(timezone.utc),
        )

    # ── Descargar solo los faltantes ───────────────────────────────────────────
    saved = skipped = errors = 0

    for i, match_id in enumerate(new_ids):
        try:
            match_json = client.get_match(match_id)
            match_data = parse_match(match_json, puuid)

            if match_data is None:
                skipped += 1
            elif match_data.role == "OTHER":
                db.save_match(match_data.to_dict())
                skipped += 1
            else:
                db.save_match(match_data.to_dict())
                saved += 1

        except RiotAPIError as e:
            if "429" in str(e) or "rate" in str(e).lower():
                # Rate limit en descarga: abortar y guardar lo que tenemos
                _mark_synced()
                return SyncResult(
                    status="rate_limited",
                    saved=saved, skipped=skipped,
                    new_found=len(new_ids),
                    error_msg="Rate limit alcanzado. Usando datos locales.",
                    synced_at=datetime.now(timezone.utc),
                )
            errors += 1
        except (KeyError, ValueError):
            errors += 1

        if on_progress:
            on_progress(i + 1, len(new_ids))

    _mark_synced()

    final_status = "ok" if saved > 0 else "no_new"
    err_str = f"{errors} con error" if errors else None

    return SyncResult(
        status=final_status,
        saved=saved, skipped=skipped,
        new_found=len(new_ids),
        error_msg=err_str,
        synced_at=datetime.now(timezone.utc),
    )


# ── Internos ───────────────────────────────────────────────────────────────────

def _mark_synced() -> None:
    db.save_config("last_sync_time", datetime.now(timezone.utc).isoformat())
