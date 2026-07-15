"""
telemetry.py — Estadísticas anónimas opt-in para el aprendizaje colectivo.

Complementa a analytics.py (que es SOLO local): este módulo, únicamente si
el usuario dio consentimiento explícito, envía resúmenes ANÓNIMOS al
backend de conocimiento (server/) para mejorar los umbrales globales.

Principios de diseño
────────────────────
1. LISTA BLANCA, nunca lista negra: los payloads se construyen campo a
   campo desde cero. Es imposible que se filtre un campo no previsto
   (puuid, riot_id, api_key, correo, nombre del PC) porque nunca se copia
   el dict original.
2. Sin identidad real: `install_id` es un UUID4 aleatorio generado
   localmente, sin relación con la cuenta de Riot. El match_id de Riot
   NO se envía (permitiría cruzar con la API de Riot y desanonimizar);
   se envía un hash SHA-256 salteado con el install_id, útil solo para
   dedup en el servidor.
3. Elo con granularidad gruesa: solo el tier (GOLD), nunca división ni LP.
4. Nunca bloquear la UI: el envío corre en un hilo daemon con timeout;
   la cola vive en SQLite (db.telemetry_queue) y sobrevive reinicios.
   Sin internet → backoff exponencial y reintento automático.
5. Sin dependencias del servidor: solo usa `requests` (ya en requirements).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

import requests

import db
from version import __version__

# ── Configuración ─────────────────────────────────────────────────────────────

# URL del backend. Prioridad: variable de entorno → config local → None.
# Sin URL configurada la cola se llena igualmente (hasta el cap) pero no se
# intenta ningún envío — no hay servidor desplegado todavía.
_ENV_URL_KEY    = "LOLCOACH_TELEMETRY_URL"
_CONFIG_URL_KEY = "telemetry_server_url"

_CONSENT_KEY    = "telemetry_consent"     # "yes" | "no" | (ausente = no preguntado)
_INSTALL_ID_KEY = "telemetry_install_id"

_SCHEMA_VERSION = 1
_BATCH_SIZE     = 50
_HTTP_TIMEOUT   = 5.0   # segundos — el hilo nunca queda colgado

_flush_lock = threading.Lock()


# ── Consentimiento ────────────────────────────────────────────────────────────

def consent_status() -> Optional[str]:
    """'yes' | 'no' | None (todavía no se preguntó)."""
    return db.get_config(_CONSENT_KEY)


def set_consent(enabled: bool) -> None:
    db.save_config(_CONSENT_KEY, "yes" if enabled else "no")


def is_enabled() -> bool:
    return consent_status() == "yes"


def get_server_url() -> Optional[str]:
    url = os.environ.get(_ENV_URL_KEY) or db.get_config(_CONFIG_URL_KEY)
    return url.rstrip("/") if url else None


def get_install_id() -> str:
    """UUID aleatorio por instalación. No deriva de ningún dato de Riot."""
    install_id = db.get_config(_INSTALL_ID_KEY)
    if not install_id:
        install_id = uuid.uuid4().hex
        db.save_config(_INSTALL_ID_KEY, install_id)
    return install_id


# ── Anonimización ─────────────────────────────────────────────────────────────

def _match_hash(match_id: str) -> str:
    """
    Hash irreversible del match_id salteado con el install_id.
    Sirve para dedup en el servidor sin exponer el ID real de Riot
    (que permitiría recuperar los Riot IDs de los 10 participantes).
    """
    return hashlib.sha256(f"{get_install_id()}:{match_id}".encode()).hexdigest()[:24]


def _elo_tier() -> str:
    """Tier grueso del jugador (GOLD, PLATINUM...). Nunca división ni LP."""
    puuid = db.get_config("puuid")
    if puuid:
        player = db.get_player(puuid)
        tier = (player or {}).get("tier") or ""
        if tier:
            return tier.upper()
    return "UNRANKED"


def _per_min(value, duration_sec) -> Optional[float]:
    if value is None or not duration_sec or duration_sec <= 0:
        return None
    return round(float(value) / (duration_sec / 60.0), 2)


def build_match_summary(match: dict, match_score) -> dict:
    """
    Resumen anónimo de UNA partida. Construido por lista blanca:
    ningún campo del dict original se copia sin pasar por aquí.

    `match_score`: scorer_v2.MatchScore de esa partida (o None).
    """
    dur = match.get("duration_sec")
    return {
        "schema_version": _SCHEMA_VERSION,
        "client_version": __version__,
        "install_id":     get_install_id(),
        "match_hash":     _match_hash(match.get("match_id", "")),
        "patch":          match.get("game_version"),      # "15.13" | None (partidas antiguas)
        "role":           match.get("role"),
        "champion":       match.get("champion"),
        "elo_tier":       _elo_tier(),
        "result":         match.get("result"),
        "duration_sec":   dur,
        "surrender":      bool(match.get("game_ended_surrender")),
        "overall_score":  match_score.overall_score if match_score else None,
        "dimensions": (
            {d.name: d.score for d in match_score.dimensions if d.score is not None}
            if match_score else {}
        ),
        "stats": {
            "kills":              match.get("kills"),
            "deaths":             match.get("deaths"),
            "assists":            match.get("assists"),
            "cs_per_min":         _per_min(match.get("cs"), dur),
            "gold_per_min":       _per_min(match.get("gold_earned"), dur),
            "damage_per_min":     _per_min(match.get("damage"), dur),
            "kill_participation": match.get("kill_participation"),
            "team_damage_pct":    match.get("team_damage_pct"),
            "cs_at_10":           match.get("cs_at_10"),
            "vision_score":       match.get("vision_score"),
        },
        # Builds / runas / hechizos: el parser aún no los captura (ver
        # informe del sprint). El esquema del servidor ya los acepta como
        # opcionales para cuando el cliente los envíe.
        "loadout": None,
    }


def build_coaching_summary(role: str, coaching_result, score_result) -> dict:
    """
    Resumen anónimo del diagnóstico de coaching (agregado sobre N partidas).
    Envía claves de problemas y nombres de fortalezas — nunca los textos
    con datos del jugador.
    """
    return {
        "schema_version":   _SCHEMA_VERSION,
        "client_version":   __version__,
        "install_id":       get_install_id(),
        "role":             role,
        "elo_tier":         _elo_tier(),
        "confidence_level": coaching_result.confidence_level,
        "sample_size":      coaching_result.sample_size,
        "primary_problem":  coaching_result.primary_problem,
        "improvements":     list(coaching_result.improvements or []),
        "strengths":        [s.name for s in (coaching_result.strengths or [])],
        "overall_score":    score_result.overall_score,
        "consistency":      score_result.consistency_score,
        "trend":            score_result.trend,
    }


def build_champion_summary(role: str, champion_stats, classification: str) -> dict:
    """Resumen anónimo del rendimiento agregado con un campeón."""
    return {
        "schema_version": _SCHEMA_VERSION,
        "client_version": __version__,
        "install_id":     get_install_id(),
        "role":           role,
        "elo_tier":       _elo_tier(),
        "champion":       champion_stats.champion,
        "games":          champion_stats.games,
        "wins":           champion_stats.wins,
        "avg_score":      round(champion_stats.avg_score, 1),
        "classification": classification,
    }


# ── Encolado (con dedup persistente) ──────────────────────────────────────────

def enqueue_match_summaries(puuid: str) -> int:
    """
    Encola los resúmenes de partidas soportadas que aún no estén en la cola.
    Se llama tras descargar partidas. Devuelve cuántos se encolaron.
    No hace nada sin consentimiento.
    """
    if not is_enabled():
        return 0

    import scorer_v2  # import local: evita ciclo db → telemetry → scorer

    queued = 0
    all_matches = db.get_matches(puuid, limit=200)
    for role in scorer_v2.SUPPORTED_ROLES:
        role_matches = [m for m in all_matches if m.get("role") == role]
        if not role_matches:
            continue
        for m in role_matches:
            dedup = f"match:{_match_hash(m['match_id'])}"
            ms = scorer_v2.score_match(m, role_matches)
            if db.telemetry_enqueue("match", dedup, build_match_summary(m, ms)):
                queued += 1
    return queued


def enqueue_coaching_summary(role: str, coaching_result, score_result) -> bool:
    """Encola el diagnóstico del día (máximo uno por rol y día)."""
    if not is_enabled():
        return False
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dedup = f"session:{role}:{today}"
    return db.telemetry_enqueue(
        "session", dedup, build_coaching_summary(role, coaching_result, score_result)
    )


def enqueue_champion_summaries(role: str, cpa) -> int:
    """Encola stats por campeón del pool (máximo una por campeón/rol/día)."""
    if not is_enabled():
        return 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    trap_names = {t.champion for t in cpa.classification.trap}
    queued = 0
    for cs in cpa.champions:
        clf = "TRAP" if cs.champion in trap_names else "SOLID"
        if cpa.classification.main and cpa.classification.main.champion == cs.champion:
            clf = "MAIN"
        elif cpa.classification.carry and cpa.classification.carry.champion == cs.champion:
            clf = "CARRY"
        elif cpa.classification.comfort and cpa.classification.comfort.champion == cs.champion:
            clf = "COMFORT"
        dedup = f"champion:{role}:{cs.champion}:{today}"
        if db.telemetry_enqueue("champion", dedup, build_champion_summary(role, cs, clf)):
            queued += 1
    return queued


# ── Envío en segundo plano ────────────────────────────────────────────────────

def flush_async() -> None:
    """
    Lanza el envío de la cola en un hilo daemon. Retorna inmediatamente:
    NUNCA bloquea la UI. Sin consentimiento o sin URL de servidor, no-op.
    """
    if not is_enabled() or not get_server_url():
        return
    threading.Thread(target=_flush, daemon=True, name="telemetry-flush").start()


def _flush() -> None:
    """
    Envía los elementos pendientes agrupados por tipo, en lotes.
    Un solo flush a la vez (lock no bloqueante). Cualquier fallo de red
    marca el lote para reintento con backoff — jamás propaga excepción.
    """
    if not _flush_lock.acquire(blocking=False):
        return
    try:
        url = get_server_url()
        if not url or not is_enabled():
            return

        pending = db.telemetry_pending(limit=_BATCH_SIZE * 3)
        by_kind: dict[str, list[dict]] = {}
        for item in pending:
            by_kind.setdefault(item["kind"], []).append(item)

        for kind, items in by_kind.items():
            for i in range(0, len(items), _BATCH_SIZE):
                batch = items[i:i + _BATCH_SIZE]
                ids = [it["id"] for it in batch]
                try:
                    resp = requests.post(
                        f"{url}/telemetry/{kind}",
                        json={"items": [it["payload"] for it in batch]},
                        timeout=_HTTP_TIMEOUT,
                    )
                    if resp.status_code in (200, 201, 202):
                        db.telemetry_mark_sent(ids)
                    elif 400 <= resp.status_code < 500:
                        # Rechazo permanente (payload inválido): no reintentar
                        # para siempre — se marca sent para sacarlo de la cola.
                        db.telemetry_mark_sent(ids)
                    else:
                        db.telemetry_mark_failed(ids)
                except requests.exceptions.RequestException:
                    db.telemetry_mark_failed(ids)
    except Exception:
        # Telemetría jamás debe romper la app por ningún motivo.
        pass
    finally:
        _flush_lock.release()
