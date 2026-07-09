"""Entidades del Learning Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class GraduationCriteria:
    id: str
    description: str
    evaluation_mode: str              # "auto" | "manual"
    metric_key: str | None = None     # campo de la tabla match si es auto
    threshold: float | None = None
    window_games: int = 5             # evaluar sobre cuántas partidas
    required_successes: int = 4       # de las window_games, cuántas deben cumplir


@dataclass
class LearningLevel:
    level: int                        # 1-10
    name: str                         # "Fundamentos", "Intermedio", "Avanzado", "Maestría"
    description: str
    focus_areas: list[str] = field(default_factory=list)   # "wave", "trading", "macro"
    prerequisite_level: int | None = None
    graduation_criteria: list[GraduationCriteria] = field(default_factory=list)
    drill_ids: list[str] = field(default_factory=list)
    estimated_games: int = 20


@dataclass
class LearningRoadmap:
    id: str                           # "tryndamere_top_v1"
    champion: str
    role: str
    levels: list[LearningLevel] = field(default_factory=list)
    total_estimated_games: int = 0
    notes: str | None = None
    patch_version: str = ""


@dataclass
class LearningState:
    """Estado persistido de aprendizaje de un jugador en un campeón específico."""
    champion: str
    role: str
    current_level: int = 1
    completed_drill_ids: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)  # drills completados con timestamps
    phase_graduation_eligible: bool = False
    last_updated: str = ""
