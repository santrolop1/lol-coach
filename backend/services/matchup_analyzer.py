"""
backend/services/matchup_analyzer.py — Motor de análisis de matchups.

Agrupa partidas enriquecidas por (mi campeón, enemigo) o solo por enemigo,
calcula métricas win/loss/WR/score/deaths/cs/damage, detecta patrones,
y devuelve un MatchupResult completo.

Sin mocks, sin datos inventados. Todo derivado del historial real.
"""

from __future__ import annotations

import statistics
from collections import defaultdict

from backend.config.constants import MIN_MATCHUP_GAMES, ROBUST_MATCHUP_GAMES
from .matchup_models import MatchupRecord, MatchupPattern, MatchupResult
from .ban_advisor import recommend_ban
from .matchup_repository import enrich_with_enemy, get_raw_coverage

# ── Umbrales de patrón ────────────────────────────────────────────────────────
_DEATHS_SPIKE_PCT  = 20.0   # +20% muertes vs promedio → patrón
_CS_DROP_PCT       = 15.0   # -15% CS/min vs promedio → patrón
_DAMAGE_DROP_PCT   = 15.0   # -15% daño/min vs promedio → patrón

_DEATHS_CRITICAL   = 35.0   # +35% → crítico
_CS_CRITICAL       = 25.0
_DAMAGE_CRITICAL   = 25.0

_MIN_PATTERN_GAMES = 3      # mínimo de partidas contra ese campeón para detectar patrón


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _cs_pm(m: dict) -> float | None:
    cs  = _safe_float(m.get("cs"))
    dur = _safe_float(m.get("duration_sec"))
    if cs is not None and dur and dur > 60:
        return cs / (dur / 60.0)
    return None


def _dmg_pm(m: dict) -> float | None:
    dmg = _safe_float(m.get("damage"))
    dur = _safe_float(m.get("duration_sec"))
    if dmg is not None and dur and dur > 60:
        return dmg / (dur / 60.0)
    return None


def _mean_or_zero(vals: list[float]) -> float:
    return statistics.mean(vals) if vals else 0.0


def _trend_from_scores(scores: list[float]) -> str:
    """Tendencia basada en la mitad más reciente vs antigua."""
    if len(scores) < 4:
        return "insufficient"
    mid   = len(scores) // 2
    # scores[0] es la más reciente (orden desc); scores[-1] la más antigua
    recent = statistics.mean(scores[:mid])
    older  = statistics.mean(scores[mid:])
    diff   = recent - older
    if diff > 3:
        return "improving"
    if diff < -3:
        return "declining"
    return "stable"


def _confidence(games: int) -> str:
    if games < MIN_MATCHUP_GAMES:
        return "low"
    if games < ROBUST_MATCHUP_GAMES:
        return "medium"
    return "high"


# ── Aggregator ────────────────────────────────────────────────────────────────

def _aggregate_by_enemy(
    enriched: list[dict],
    overall: dict,
) -> list[MatchupRecord]:
    """
    Agrupa por `enemy_champion` (sin importar qué campeón jugó el jugador).
    Devuelve MatchupRecords para todos los enemigos con datos.
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for m in enriched:
        enemy = m.get("enemy_champion")
        if enemy:
            groups[enemy].append(m)

    records: list[MatchupRecord] = []
    for enemy, matches in groups.items():
        if len(matches) < 1:
            continue

        wins   = sum(1 for m in matches if m.get("result") == "WIN")
        losses = len(matches) - wins

        deaths_vals = [_safe_float(m.get("deaths")) for m in matches]
        deaths_vals = [v for v in deaths_vals if v is not None]

        cs_vals  = [_cs_pm(m)  for m in matches]
        cs_vals  = [v for v in cs_vals  if v is not None]
        dmg_vals = [_dmg_pm(m) for m in matches]
        dmg_vals = [v for v in dmg_vals if v is not None]

        # Scores no siempre disponibles en el dict de partida
        score_vals: list[float] = []
        for m in matches:
            s = _safe_float(m.get("overall_score"))
            if s is not None:
                score_vals.append(s)

        records.append(MatchupRecord(
            champion       = "ALL",
            enemy          = enemy,
            role           = overall["role"],
            games          = len(matches),
            wins           = wins,
            losses         = losses,
            winrate        = wins / len(matches),
            avg_score      = statistics.mean(score_vals) if score_vals else None,
            avg_deaths     = _mean_or_zero(deaths_vals),
            avg_cs_min     = _mean_or_zero(cs_vals),
            avg_damage_min = _mean_or_zero(dmg_vals),
            trend          = _trend_from_scores(score_vals),
            confidence     = _confidence(len(matches)),
            overall_avg_deaths    = overall["avg_deaths"],
            overall_avg_cs_min    = overall["avg_cs_min"],
            overall_avg_damage_min= overall["avg_damage_min"],
        ))

    return records


# ── Pattern detector ──────────────────────────────────────────────────────────

def _detect_patterns(
    records: list[MatchupRecord],
) -> list[MatchupPattern]:
    patterns: list[MatchupPattern] = []

    for r in records:
        if r.games < _MIN_PATTERN_GAMES:
            continue

        # Muertes
        delta = r.deaths_delta_pct
        if delta >= _DEATHS_SPIKE_PCT:
            severity = "critical" if delta >= _DEATHS_CRITICAL else "warning"
            patterns.append(MatchupPattern(
                enemy        = r.enemy,
                pattern_type = "deaths_spike",
                description  = (
                    f"Tus muertes aumentan {delta:.0f}% contra {r.enemy} "
                    f"({r.avg_deaths:.1f} vs {r.overall_avg_deaths:.1f} promedio)."
                ),
                severity = severity,
            ))

        # CS/min
        cs_delta = r.cs_delta_pct
        if cs_delta <= -_CS_DROP_PCT:
            severity = "critical" if cs_delta <= -_CS_CRITICAL else "warning"
            patterns.append(MatchupPattern(
                enemy        = r.enemy,
                pattern_type = "cs_drop",
                description  = (
                    f"Tu CS/min cae {abs(cs_delta):.0f}% contra {r.enemy} "
                    f"({r.avg_cs_min:.1f} vs {r.overall_avg_cs_min:.1f} promedio)."
                ),
                severity = severity,
            ))

        # Daño
        dmg_delta = r.damage_delta_pct
        if dmg_delta <= -_DAMAGE_DROP_PCT and r.avg_damage_min > 0:
            severity = "critical" if dmg_delta <= -_DAMAGE_CRITICAL else "warning"
            patterns.append(MatchupPattern(
                enemy        = r.enemy,
                pattern_type = "damage_drop",
                description  = (
                    f"Tu daño/min cae {abs(dmg_delta):.0f}% contra {r.enemy} "
                    f"({r.avg_damage_min:.0f} vs {r.overall_avg_damage_min:.0f} promedio)."
                ),
                severity = severity,
            ))

    # Ordenar: críticos primero, luego por magnitud
    patterns.sort(key=lambda p: (0 if p.severity == "critical" else 1, p.enemy))
    return patterns


# ── Motor principal ───────────────────────────────────────────────────────────

def analyze_matchups(
    matches: list[dict],
    role: str,
) -> MatchupResult:
    """
    Analiza los matchups del jugador usando el historial y los JSONs raw.

    Parámetros
    ----------
    matches : partidas filtradas por rol (de db.get_matches() o match_resolver)
    role    : "ADC" | "TOP"

    Retorna
    -------
    MatchupResult completo.
    """
    total = len(matches)
    raw_coverage = get_raw_coverage(matches)

    if total == 0:
        return MatchupResult(
            role=role, all_matchups=[], best=[], worst=[],
            ban=None, patterns=[], raw_coverage=0, total_matches=0,
        )

    # Enriquecer con enemy_champion
    enriched = enrich_with_enemy(matches, role)

    # Promedios globales (base para comparar patrones)
    all_deaths = [_safe_float(m.get("deaths")) for m in matches]
    all_deaths = [v for v in all_deaths if v is not None]
    all_cs     = [_cs_pm(m)  for m in matches]; all_cs  = [v for v in all_cs  if v is not None]
    all_dmg    = [_dmg_pm(m) for m in matches]; all_dmg = [v for v in all_dmg if v is not None]

    overall = {
        "role":           role,
        "avg_deaths":     _mean_or_zero(all_deaths),
        "avg_cs_min":     _mean_or_zero(all_cs),
        "avg_damage_min": _mean_or_zero(all_dmg),
    }

    # Agregar por enemigo
    all_records = _aggregate_by_enemy(enriched, overall)

    # Filtrar por muestra mínima para best/worst
    qualified = [r for r in all_records if r.games >= MIN_MATCHUP_GAMES]

    best  = sorted(qualified, key=lambda r: (-r.winrate, -r.games))[:5]
    worst = sorted(qualified, key=lambda r: (r.winrate, -r.games))[:5]

    # Patrones (sobre todos los registros con ≥ MIN_PATTERN_GAMES)
    patterns = _detect_patterns(all_records)

    # Ban advisor
    ban = recommend_ban(qualified) if qualified else None

    return MatchupResult(
        role          = role,
        all_matchups  = sorted(all_records, key=lambda r: -r.games),
        best          = best,
        worst         = worst,
        ban           = ban,
        patterns      = patterns[:5],   # máximo 5 patrones
        raw_coverage  = raw_coverage,
        total_matches = total,
    )
