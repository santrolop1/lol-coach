"""Entidades del Training Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class DrillCategory(str, Enum):
    MECHANICAL  = "mechanical"
    COMBO       = "combo"
    ANIMATION   = "animation"
    WAVE        = "wave"
    TRADING     = "trading"
    MACRO       = "macro"
    SPLIT_PUSH  = "split_push"
    OBJECTIVE   = "objective"
    TEAMFIGHT   = "teamfight"
    MATCHUP     = "matchup"
    VISION      = "vision"
    RESOURCE    = "resource"


class DrillEvaluationMode(str, Enum):
    AUTO       = "auto"       # evaluación automática desde métrica de la tabla match
    SEMI_AUTO  = "semi_auto"  # combinación de métricas
    MANUAL     = "manual"     # el jugador confirma manualmente


@dataclass
class Drill:
    id: str
    name: str
    category: DrillCategory
    description: str
    why: str
    how_measured: str                 # explicación legible para el jugador
    evaluation_mode: DrillEvaluationMode = DrillEvaluationMode.AUTO
    metric_key: str | None = None     # campo de la tabla match (si auto/semi_auto)
    threshold_type: str | None = None # "less_than" | "greater_than"
    threshold_source: str | None = None  # "fixed"|"p25"|"p50"|"p75"|"win_avg"|"profile"
    threshold_fixed: float | None = None
    target_games: int = 5
    required_success: int = 4
    expected_gain: str = ""
    unlocks: list[str] = field(default_factory=list)  # drill_ids que este desbloquea
    difficulty: float = 0.5           # 0-1, usado en priority algorithm


@dataclass
class ActiveDrill:
    """Estado de un drill en progreso para un jugador en un campeón concreto."""
    drill: Drill
    champion: str
    role: str
    started_at: str                   # ISO — solo evalúa partidas posteriores
    threshold_computed: float | None = None  # valor real calculado al crear
    success_count: int = 0
    games_checked: int = 0
    dots: list[dict] = field(default_factory=list)  # {"game_i", "success", "value"}
    status: str = "active"            # "active" | "completed" | "failed"


@dataclass
class DrillResult:
    drill_id: str
    champion: str
    role: str
    completed_at: str
    success_count: int
    games_checked: int
    impact: float | None = None       # score_after - score_before
