"""
backend/services/ban_advisor.py — Motor de recomendación de ban.

Responde: "¿Qué debería banear según mi propio historial?"

Fórmula ban_score (0-100):
    50% peso en WR (cuánto pierdo → más urgente)
    25% peso en muestra (más partidas = más confianza)
    15% peso en spike de muertes
    10% peso en caída de CS

Sin OP.GG. Sin meta. Solo tu historial.
"""

from __future__ import annotations

import math

from .matchup_models import MatchupRecord, BanRecommendation
from backend.config.constants import ROBUST_MATCHUP_GAMES


def _normalize(val: float, min_val: float, max_val: float) -> float:
    """Normaliza val al rango [0, 1] dentro de [min_val, max_val]."""
    rng = max_val - min_val
    if rng == 0:
        return 0.0
    return max(0.0, min(1.0, (val - min_val) / rng))


def recommend_ban(
    matchups: list[MatchupRecord],
) -> BanRecommendation | None:
    """
    Elige el ban más recomendado a partir de los matchups calificados.

    Parámetros
    ----------
    matchups : lista de MatchupRecord ya filtrada por muestra mínima

    Retorna
    -------
    BanRecommendation o None si no hay datos suficientes.
    """
    if not matchups:
        return None

    scored: list[tuple[float, MatchupRecord]] = []

    for r in matchups:
        # Componente 1: WR negativa (invertida: más bajo WR → más urgente)
        loss_rate  = 1.0 - r.winrate
        wr_score   = loss_rate  # 0-1

        # Componente 2: tamaño de muestra (más partidas → más confianza)
        sample_score = min(1.0, r.games / ROBUST_MATCHUP_GAMES)

        # Componente 3: spike de muertes (capped a 50%)
        deaths_spike = max(0.0, r.deaths_delta_pct)
        deaths_score = min(1.0, deaths_spike / 50.0)

        # Componente 4: caída de CS (capped a 30%)
        cs_drop  = max(0.0, -r.cs_delta_pct)
        cs_score = min(1.0, cs_drop / 30.0)

        ban_score = (
            0.50 * wr_score
            + 0.25 * sample_score
            + 0.15 * deaths_score
            + 0.10 * cs_score
        ) * 100.0

        scored.append((ban_score, r))

    if not scored:
        return None

    # Elegir el de mayor ban_score
    best_score, best = max(scored, key=lambda t: t[0])

    reasons = _build_reasons(best)
    confidence = "low" if best.games < 4 else ("medium" if best.games < ROBUST_MATCHUP_GAMES else "high")

    return BanRecommendation(
        enemy      = best.enemy,
        games      = best.games,
        winrate    = best.winrate,
        ban_score  = round(best_score, 1),
        reasons    = reasons,
        confidence = confidence,
    )


def _build_reasons(r: MatchupRecord) -> list[str]:
    """Genera razones data-driven para el ban recomendado."""
    reasons: list[str] = []

    # 1. WR principal
    reasons.append(
        f"Solo ganas el {r.winrate:.0%} de tus {r.games} partidas contra {r.enemy}."
    )

    # 2. Muertes
    if r.deaths_delta_pct >= 15:
        reasons.append(
            f"Mueres {r.deaths_delta_pct:.0f}% más ({r.avg_deaths:.1f} muertes/partida "
            f"vs {r.overall_avg_deaths:.1f} de media)."
        )

    # 3. CS
    if r.cs_delta_pct <= -10:
        reasons.append(
            f"Tu farm cae {abs(r.cs_delta_pct):.0f}% "
            f"({r.avg_cs_min:.1f} CS/min vs {r.overall_avg_cs_min:.1f} de media)."
        )

    return reasons[:3]  # máximo 3 razones
