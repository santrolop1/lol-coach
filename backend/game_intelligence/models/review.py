"""Entidades del Review Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ReviewComparison:
    metric: str
    label: str
    value_now: float
    value_avg: float | None
    unit: str = ""
    verdict: str = "neutral"          # "better" | "worse" | "neutral"


@dataclass
class ProfileNote:
    """Cruce entre lo que ocurrió en la partida y lo que dice el perfil del campeón."""
    topic: str                        # "trading" | "wave" | "ult_usage"
    profile_says: str                 # qué recomienda el perfil
    what_happened: str                # qué hizo el jugador
    severity: str = "info"           # "critical" | "warning" | "info" | "positive"


@dataclass
class MatchupNote:
    """Cruce entre lo que ocurrió y lo que dice el MatchupProfile."""
    topic: str
    matchup_says: str
    what_happened: str
    severity: str = "info"


@dataclass
class EnrichedReview:
    """Review post-partida enriquecida con contexto de la plataforma."""
    champion: str
    result: str                       # "WIN" | "LOSS"
    match_id: str

    # Score
    score_now: float | None = None
    score_avg: float | None = None
    score_delta: float | None = None
    rating: str = "Okay"              # "Excellent"|"Good"|"Okay"|"Poor"
    rating_color: str = "#9CA3AF"

    # Análisis
    comparisons: list[ReviewComparison] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)

    # Contexto enriquecido (solo si hay perfil/matchup)
    profile_notes: list[ProfileNote] = field(default_factory=list)
    matchup_notes: list[MatchupNote] = field(default_factory=list)

    # Patrones
    repeated_mistakes: list[str] = field(default_factory=list)
    pattern_broken: str | None = None  # si rompió un patrón negativo

    # Foco
    focus: str = ""
    drill_recommendation: str | None = None

    confidence: str = "preliminary"
