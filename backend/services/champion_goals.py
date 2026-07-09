"""
backend/services/champion_goals.py — Generación de objetivos específicos por campeón.

El objetivo se deriva del mayor gap win/loss del jugador con ese campeón.
Target = promedio del jugador en sus victorias con ese mismo campeón.
Sin benchmarks externos. Sin valores inventados.
"""

from __future__ import annotations

from .champion_models import ChampionAnalysis, ChampionGoal

# Peso de cada métrica para priorizar el objetivo (mayor = más urgente)
_METRIC_WEIGHTS = {
    "deaths":  20,
    "cs_pm":   15,
    "damage":  10,
    "kp":      12,
}

_MIN_SPLIT = 2  # mínimo de wins Y losses para generar objetivo


def generate_goal(analysis: ChampionAnalysis) -> ChampionGoal | None:
    """
    Genera el objetivo más impactante para el campeón analizado.

    Requiere al menos MIN_SPLIT victorias y derrotas.
    Retorna None si no hay datos suficientes para un objetivo significativo.
    """
    if analysis.wins < _MIN_SPLIT or analysis.losses < _MIN_SPLIT:
        return None

    candidates: list[tuple[float, str]] = []

    # ── Deaths ────────────────────────────────────────────────────────────────
    deaths_gap = analysis.deaths_win_loss_delta_pct
    if deaths_gap >= 15:
        score = deaths_gap * _METRIC_WEIGHTS["deaths"] / 100
        candidates.append((score, "deaths"))

    # ── CS/min ────────────────────────────────────────────────────────────────
    cs_gap = abs(analysis.cs_win_loss_delta_pct)
    if analysis.cs_win_loss_delta_pct <= -10:
        score = cs_gap * _METRIC_WEIGHTS["cs_pm"] / 100
        candidates.append((score, "cs_pm"))

    # ── Damage ────────────────────────────────────────────────────────────────
    dmg_gap = abs(analysis.damage_win_loss_delta_pct)
    if analysis.damage_win_loss_delta_pct <= -15 and analysis.win_avg_damage_min > 0:
        score = dmg_gap * _METRIC_WEIGHTS["damage"] / 100
        candidates.append((score, "damage"))

    # ── KP ────────────────────────────────────────────────────────────────────
    kp_gap = abs(analysis.kp_win_loss_delta_pct)
    if analysis.kp_win_loss_delta_pct <= -12 and analysis.win_avg_kp > 0:
        score = kp_gap * _METRIC_WEIGHTS["kp"] / 100
        candidates.append((score, "kp"))

    if not candidates:
        return None

    _, best_metric = max(candidates, key=lambda t: t[0])
    return _build_goal(best_metric, analysis)


def _build_goal(metric: str, a: ChampionAnalysis) -> ChampionGoal | None:
    name = a.champion_name

    if metric == "deaths":
        current = a.avg_deaths
        target  = a.win_avg_deaths
        if target >= current:
            return None
        return ChampionGoal(
            metric_key  = "deaths",
            title       = f"Reducir muertes con {name}",
            description = (
                f"Objetivo: {target:.1f} muertes/partida. "
                f"Situación actual: {current:.1f} muertes/partida."
            ),
            current     = current,
            target      = target,
            unit        = "muertes/partida",
            impact_desc = (
                f"Igualas tu nivel de victorias con {name} "
                f"({a.wins} partidas, {a.winrate:.0%} WR actual)."
            ),
        )

    if metric == "cs_pm":
        current = a.avg_cs_min
        target  = a.win_avg_cs_min
        if target <= current:
            return None
        return ChampionGoal(
            metric_key  = "cs_pm",
            title       = f"Mejorar farm con {name}",
            description = (
                f"Objetivo: {target:.1f} CS/min. "
                f"Situación actual: {current:.1f} CS/min."
            ),
            current     = current,
            target      = target,
            unit        = "CS/min",
            impact_desc = (
                f"Tu farm en victorias con {name} es "
                f"{a.win_avg_cs_min:.1f} CS/min — ese es tu nivel real."
            ),
        )

    if metric == "damage":
        current = a.avg_damage_min
        target  = a.win_avg_damage_min
        if target <= current:
            return None
        return ChampionGoal(
            metric_key  = "damage",
            title       = f"Subir daño con {name}",
            description = (
                f"Objetivo: {target:.0f} daño/min. "
                f"Situación actual: {current:.0f} daño/min."
            ),
            current     = current,
            target      = target,
            unit        = "daño/min",
            impact_desc = (
                f"En victorias con {name} produces "
                f"{a.win_avg_damage_min:.0f} daño/min — "
                f"replicar ese nivel en derrotas es tu objetivo."
            ),
        )

    if metric == "kp":
        current = a.avg_kp
        target  = a.win_avg_kp
        if target <= current:
            return None
        return ChampionGoal(
            metric_key  = "kp",
            title       = f"Aumentar participación con {name}",
            description = (
                f"Objetivo: {target:.0%} participación. "
                f"Situación actual: {current:.0%}."
            ),
            current     = current,
            target      = target,
            unit        = "% KP",
            impact_desc = (
                f"Tu participación en victorias con {name} "
                f"es {a.win_avg_kp:.0%} — ese es tu nivel cuando el equipo gana."
            ),
        )

    return None
