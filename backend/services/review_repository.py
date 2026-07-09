"""
backend/services/review_repository.py — Acceso a datos de partidas para Post Game Review.

Lee directamente del historial de partidas (list[dict]) pasado desde la UI.
No tiene acceso directo a SQLite ni a la Riot API — consume datos ya parseados.
"""

from __future__ import annotations

import statistics

from backend.config.constants import MIN_CHAMPION_GAMES


_MIN_HISTORY = 3   # mínimas partidas previas para comparaciones fiables


def _safe(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _cs_pm(m: dict) -> float | None:
    cs  = _safe(m.get("cs"))
    dur = _safe(m.get("duration_sec"))
    if cs is not None and dur and dur > 60:
        return cs / (dur / 60.0)
    return None


def _dmg_pm(m: dict) -> float | None:
    dmg = _safe(m.get("damage"))
    dur = _safe(m.get("duration_sec"))
    if dmg is not None and dur and dur > 60:
        return dmg / (dur / 60.0)
    return None


def _mean(vals: list) -> float | None:
    clean = [v for v in vals if v is not None]
    return statistics.mean(clean) if clean else None


def get_champion_history(
    champion: str,
    history: list[dict],
) -> list[dict]:
    """Devuelve partidas del campeón indicado, más recientes primero."""
    return [m for m in history if m.get("champion") == champion]


def get_champion_averages(
    champion: str,
    history: list[dict],
    exclude_match_id: str | None = None,
) -> dict:
    """
    Calcula promedios del campeón excluyendo opcionalmente la partida actual.

    Retorna dict con claves: deaths, cs_pm, damage_pm, kp, score, games.
    Valores pueden ser None si no hay datos suficientes.
    """
    champ_matches = [
        m for m in history
        if m.get("champion") == champion
        and (exclude_match_id is None or m.get("match_id") != exclude_match_id)
    ]

    if len(champ_matches) < _MIN_HISTORY:
        return {
            "deaths":    None,
            "cs_pm":     None,
            "damage_pm": None,
            "kp":        None,
            "score":     None,
            "games":     len(champ_matches),
        }

    deaths    = _mean([_safe(m.get("deaths"))             for m in champ_matches])
    cs_pm     = _mean([_cs_pm(m)                          for m in champ_matches])
    damage_pm = _mean([_dmg_pm(m)                         for m in champ_matches])
    kp        = _mean([_safe(m.get("kill_participation"))  for m in champ_matches])
    score     = _mean([_safe(m.get("overall_score"))       for m in champ_matches])

    return {
        "deaths":    deaths,
        "cs_pm":     cs_pm,
        "damage_pm": damage_pm,
        "kp":        kp,
        "score":     score,
        "games":     len(champ_matches),
    }


def get_recent_scores(
    champion: str,
    history: list[dict],
    n: int = 10,
    exclude_match_id: str | None = None,
) -> list[float]:
    """Últimos N scores del campeón (más reciente primero)."""
    champ_matches = [
        m for m in history
        if m.get("champion") == champion
        and (exclude_match_id is None or m.get("match_id") != exclude_match_id)
    ]
    scores = []
    for m in champ_matches[:n]:
        s = _safe(m.get("overall_score"))
        if s is not None:
            scores.append(s)
    return scores


def get_recent_deaths(
    champion: str,
    history: list[dict],
    n: int = 5,
    exclude_match_id: str | None = None,
) -> list[float]:
    """Últimas N muertes del campeón (más reciente primero)."""
    champ_matches = [
        m for m in history
        if m.get("champion") == champion
        and (exclude_match_id is None or m.get("match_id") != exclude_match_id)
    ]
    result = []
    for m in champ_matches[:n]:
        d = _safe(m.get("deaths"))
        if d is not None:
            result.append(d)
    return result


def get_matchup_winrate(
    enemy_champion: str,
    history: list[dict],
) -> tuple[float | None, int]:
    """
    Calcula WR histórico del jugador contra un campeón específico.

    Usa el campo 'enemy_champion' si está disponible (enriquecido por matchup_repository).
    Retorna (winrate, games). winrate es None si games < 2.
    """
    matchup_games = [
        m for m in history
        if m.get("enemy_champion") == enemy_champion
    ]
    if len(matchup_games) < 2:
        return None, len(matchup_games)
    wins = sum(1 for m in matchup_games if m.get("result") == "WIN")
    return wins / len(matchup_games), len(matchup_games)
