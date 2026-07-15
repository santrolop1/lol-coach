"""
backend/services/matchup_repository.py — Extrae matchup data de los JSONs raw cacheados.

NO modifica parser.py, db.py ni riot_api.py.
Lee únicamente los archivos data/raw/match_*.json ya almacenados por riot_api.
Cruza esa información con los dicts de partida que vienen de db.get_matches().

Mapeo de rol → teamPosition (Riot API):
    ADC  → "BOTTOM"
    TOP  → "TOP"
"""

from __future__ import annotations

import json
from pathlib import Path

import _paths

# Directorio donde riot_api cachea los JSONs — sincronizado con riot_api.py
_RAW_DIR = _paths.get_cache_dir()

_ROLE_TO_POSITION: dict[str, str] = {
    "ADC": "BOTTOM",
    "TOP": "TOP",
}


def _load_raw(match_id: str) -> dict | None:
    """Carga el JSON cacheado de una partida. Devuelve None si no existe."""
    path = _RAW_DIR / f"match_{match_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _find_lane_opponent(participants: list[dict], puuid: str, position: str) -> str | None:
    """
    Encuentra el nombre del campeón rival de carril.

    Lógica:
    1. Encuentra el teamId del jugador.
    2. Busca un participante con la misma teamPosition y diferente teamId.
    """
    player = next((p for p in participants if p.get("puuid") == puuid), None)
    if player is None:
        return None

    player_team = player.get("teamId")
    player_pos  = player.get("teamPosition", "")

    if player_pos != position:
        return None

    opponent = next(
        (
            p for p in participants
            if p.get("teamPosition") == position
            and p.get("teamId") != player_team
        ),
        None,
    )
    return opponent.get("championName") if opponent else None


def enrich_with_enemy(
    matches: list[dict],
    role: str,
) -> list[dict]:
    """
    Añade el campo `enemy_champion` a cada partida del historial.

    Partidas para las que no existe JSON raw (o el rival no puede identificarse)
    se devuelven sin el campo `enemy_champion` — el llamador debe filtrarlas.

    Parámetros
    ----------
    matches : lista de dicts de partida (de db.get_matches())
    role    : "ADC" | "TOP"

    Retorna
    -------
    Lista de dicts, con `enemy_champion` añadido donde fue posible.
    """
    position = _ROLE_TO_POSITION.get(role)
    if position is None:
        return []

    enriched: list[dict] = []
    for m in matches:
        match_id = m.get("match_id", "")
        puuid    = m.get("puuid", "")

        raw = _load_raw(match_id)
        if raw is None:
            # JSON no cacheado — se incluye sin enemy_champion
            enriched.append(m)
            continue

        participants = raw.get("info", {}).get("participants", [])
        enemy = _find_lane_opponent(participants, puuid, position)

        result = dict(m)
        if enemy:
            result["enemy_champion"] = enemy
        enriched.append(result)

    return enriched


def get_raw_coverage(matches: list[dict]) -> int:
    """Cuántas partidas tienen JSON raw disponible."""
    return sum(
        1 for m in matches
        if (_RAW_DIR / f"match_{m.get('match_id','')}.json").exists()
    )
