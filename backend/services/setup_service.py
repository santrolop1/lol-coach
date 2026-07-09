"""
backend/services/setup_service.py — Lógica de setup inicial y validación de cuenta.

Centraliza: verificación de estado, validación de API Key, resolución de
cuenta Riot y descarga de partidas iniciales.
Las páginas de UI no deben llamar a RiotClient directamente para setup.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Callable

import db
from riot_api import RiotClient, RiotAPIError, RiotNotFoundError
from parser import parse_match
import lcu.client as lcu_client


# ── Estado ───────────────────────────────────────────────────────────────────

def is_setup_complete() -> bool:
    """
    True cuando la app está lista para usarse.
    Verifica estado real: no confía en un flag boolean único.
    """
    return all([
        db.get_config("api_key"),
        db.get_config("game_name"),
        db.get_config("tag_line"),
        db.get_config("platform"),
        db.get_config("puuid"),
        count_matches() > 0,
    ])


def count_matches(role: str | None = None) -> int:
    """Total de partidas guardadas en DB, opcionalmente filtradas por rol."""
    try:
        conn = sqlite3.connect("data/lol_coach.db")
        if role:
            n = conn.execute(
                "SELECT COUNT(*) FROM match WHERE role = ?", (role,)
            ).fetchone()[0]
        else:
            n = conn.execute("SELECT COUNT(*) FROM match").fetchone()[0]
        conn.close()
        return n
    except Exception:
        return 0


def last_sync_date() -> str | None:
    """Fecha de la partida más reciente en DB (formato YYYY-MM-DD) o None."""
    try:
        conn = sqlite3.connect("data/lol_coach.db")
        row  = conn.execute(
            "SELECT played_at FROM match ORDER BY played_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row[0][:10] if row and row[0] else None
    except Exception:
        return None


# ── Validación de API Key ─────────────────────────────────────────────────────

def validate_api_key(api_key: str, platform: str = "la1") -> bool:
    """
    True si la API Key responde OK. False si es inválida.
    Raises RiotAPIError en errores de red.
    """
    client = RiotClient(api_key.strip(), platform)
    return client.validate_key()


# ── Resolución de cuenta ─────────────────────────────────────────────────────

def resolve_riot_account(
    api_key: str,
    platform: str,
    game_name: str,
    tag_line: str,
) -> dict:
    """
    Verifica el Riot ID y retorna el perfil completo del jugador.

    Raises
    ------
    RiotNotFoundError — cuenta no encontrada
    RiotAPIError      — error de API o red
    """
    client   = RiotClient(api_key.strip(), platform)
    account  = client.get_account(game_name.strip(), tag_line.strip().lstrip("#"))
    summoner = client.get_summoner(account["puuid"])
    leagues  = client.get_league_by_puuid(account["puuid"])

    solo = next((e for e in leagues if e.get("queueType") == "RANKED_SOLO_5x5"), None)
    rank_str = "Sin rango"
    tier_str = ""
    lp = wins = losses = 0
    if solo:
        tier_str = solo.get("tier", "")
        rank_str = f"{tier_str} {solo.get('rank', '')}".strip()
        lp       = solo.get("leaguePoints", 0)
        wins     = solo.get("wins", 0)
        losses   = solo.get("losses", 0)

    return {
        "puuid":   account["puuid"],
        "riot_id": account.get("gameName", game_name.strip()),
        "tag":     account.get("tagLine", tag_line.strip().lstrip("#")),
        "level":   summoner.get("summonerLevel", 0),
        "rank":    rank_str,
        "tier":    tier_str,
        "lp":      lp,
        "wins":    wins,
        "losses":  losses,
    }


def save_account(
    api_key: str,
    platform: str,
    game_name: str,
    tag_line: str,
    profile: dict,
) -> None:
    """Persiste la configuración y el perfil del jugador en DB."""
    db.save_config("api_key",   api_key.strip())
    db.save_config("game_name", game_name.strip())
    db.save_config("tag_line",  tag_line.strip().lstrip("#"))
    db.save_config("platform",  platform)
    db.save_config("puuid",     profile["puuid"])
    db.save_player({**profile, "updated_at": datetime.now(timezone.utc).isoformat()})


# ── Auto-detección de cuenta desde LCU ───────────────────────────────────────

def detect_account_from_lcu() -> dict:
    """
    Lee el jugador actualmente logueado en el cliente de League y, si es
    distinto al configurado, actualiza la cuenta automáticamente.

    Retorna dict con:
      status: "updated" | "already_synced" | "lcu_offline" | "no_api_key" | "error"
      riot_id, tag, level, rank (solo cuando status == "updated")
      message: texto legible
    """
    api_key = db.get_config("api_key")
    if not api_key:
        return {"status": "no_api_key", "message": "No hay Riot API key configurada."}

    creds = lcu_client.read_credentials()
    if creds is None:
        return {"status": "lcu_offline", "message": "Cliente de League no detectado."}

    summoner = lcu_client.get_current_summoner(creds)
    if not summoner:
        return {"status": "lcu_offline", "message": "No se pudo leer el invocador del cliente."}

    lcu_puuid   = summoner.get("puuid", "")
    lcu_game    = summoner.get("gameName") or summoner.get("displayName", "")
    lcu_tag     = summoner.get("tagLine") or summoner.get("gameTag", "")
    platform    = db.get_config("platform") or "la1"

    if not lcu_puuid:
        return {"status": "error", "message": "El cliente no devolvió un PUUID válido."}

    configured_puuid = db.get_config("puuid") or ""
    if lcu_puuid == configured_puuid:
        return {"status": "already_synced", "message": "La cuenta ya está sincronizada."}

    # Cuenta cambió — resolver perfil completo vía Riot API
    try:
        profile = resolve_riot_account(
            api_key=api_key,
            platform=platform,
            game_name=lcu_game,
            tag_line=lcu_tag,
        )
    except (RiotNotFoundError, RiotAPIError, Exception) as e:
        return {"status": "error", "message": f"No se pudo resolver la cuenta: {e}"}

    save_account(
        api_key=api_key,
        platform=platform,
        game_name=lcu_game,
        tag_line=lcu_tag,
        profile=profile,
    )

    return {
        "status":  "updated",
        "message": f"Cuenta actualizada a {profile['riot_id']}#{profile['tag']}",
        "riot_id": profile["riot_id"],
        "tag":     profile["tag"],
        "level":   profile["level"],
        "rank":    profile["rank"],
    }


# ── Descarga de partidas ──────────────────────────────────────────────────────

def download_matches(
    puuid: str,
    api_key: str,
    platform: str,
    count: int = 20,
    queue: int = 420,
    on_progress: Callable[[int, int], None] | None = None,
) -> dict:
    """
    Descarga y guarda partidas desde Riot API.

    Parámetros
    ----------
    on_progress : callback(done, total) llamado tras procesar cada partida.

    Retorna
    -------
    {"saved": int, "skipped": int, "errors": int, "total_new": int,
     "already_saved": int}

    Raises
    ------
    RiotAPIError si no se pueden obtener los IDs de partidas.
    """
    client    = RiotClient(api_key, platform)
    match_ids = client.get_match_ids(puuid, count=count, queue=queue)
    new_ids   = [mid for mid in match_ids if not db.match_exists(mid)]

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
        except Exception:
            errors += 1

        if on_progress:
            on_progress(i + 1, len(new_ids) or 1)

    return {
        "saved":         saved,
        "skipped":       skipped,
        "errors":        errors,
        "total_new":     len(new_ids),
        "already_saved": len(match_ids) - len(new_ids),
    }
