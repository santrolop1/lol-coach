"""
backend/services/review_models.py — Modelos de datos para Post Game Review.

Toda la información se deriva de partidas reales del jugador.
Sin benchmarks externos. Sin datos inventados.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MatchComparison:
    """Compara una métrica de la partida actual contra el historial del campeón."""
    label:       str    # "Muertes", "CS/min", etc.
    current:     float  # valor de esta partida
    avg:         float  # promedio histórico del campeón (o rol si <MIN)
    unit:        str    # "muertes/partida", "CS/min", etc.
    verdict:     str    # "Mejor de lo normal" | "Peor de lo normal" | "Normal"
    delta_pct:   float  # % de diferencia (positivo = mejor para el jugador)


@dataclass
class PostGameReview:
    """Revisión post-partida completa y accionable."""
    match_id:    str
    champion:    str
    result:      str           # "WIN" | "LOSS"
    score:       float | None  # scorer_v2 overall_score de esta partida

    # Clasificación de la partida
    rating:      str           # "Excelente" | "Buena" | "Normal" | "Mala" | "Muy mala"
    rating_color: str          # color CSS hex para el rating

    # Contexto histórico del score
    score_avg:   float | None  # promedio de las últimas N partidas del campeón
    score_delta: float | None  # score_actual - score_avg

    # Motor de fortalezas / errores
    strengths:   list[str] = field(default_factory=list)   # máx 3
    mistakes:    list[str] = field(default_factory=list)    # máx 3

    # Foco para la próxima partida (1 único objetivo)
    focus:       str | None = None

    # Comparaciones métricas
    comparisons: list[MatchComparison] = field(default_factory=list)

    # Integración Champion Coach
    champion_problem: str | None = None    # problema recurrente detectado
    pattern_repeated: bool = False         # si el error de hoy ya fue detectado antes

    # Integración Matchup Intelligence
    matchup_context: str | None = None    # texto sobre el rival de esta partida

    # Errores repetidos en historial reciente
    repeated_mistakes: list[str] = field(default_factory=list)

    # Confianza del análisis
    confidence: str = "low"   # "low" | "medium" | "high"
