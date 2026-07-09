"""
backend/knowledge/models.py — Estructuras de datos del Knowledge Engine.

Solo dataclasses. Sin lógica.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Goal:
    """Objetivo activo o completado del jugador."""
    id:                str
    metric_key:        str
    metric_label:      str
    target_value:      float
    target_str:        str           # "< 4 muertes" | "> 7.0 CS/min"
    higher_is_better:  bool
    check_window:      int           # nº de partidas para evaluar el objetivo
    status:            str           # "active" | "completed" | "skipped"
    created_at:        str           # ISO date
    completed_at:      str | None
    progress_count:    int           # partidas que cumplen el objetivo
    total_count:       int
    pct:               float


@dataclass
class Pattern:
    """Patrón detectado automáticamente en el historial del jugador."""
    id:          str
    category:    str   # "champion" | "death" | "trend" | "habit" | "pool"
    title:       str
    description: str
    evidence:    str   # "En 7 de las últimas 10 partidas..."
    confidence:  float # 0-1
    actionable:  str   # qué hacer al respecto


@dataclass
class Insight:
    """Observación específica, accionable y con evidencia."""
    rank:       int
    text:       str   # oración completa
    evidence:   str
    category:   str   # "positive" | "negative" | "neutral"
    confidence: float


@dataclass
class Recommendation:
    """Recomendación priorizada con todas las dimensiones de evaluación."""
    rank:        int
    title:       str
    body:        str
    why:         str
    impact:      str   # "Alto" | "Medio"
    impact_pct:  int   # 0-100 (impacto relativo)
    confidence:  float # 0-1
    difficulty:  str   # "Baja" | "Media" | "Alta"
    goal_str:    str   # objetivo asociado
    metric_key:  str | None


@dataclass
class SessionMatch:
    """Datos de una partida dentro de la sesión actual."""
    match_id:     str
    champion:     str
    role:         str
    is_win:       bool
    kda:          str
    overall_score: float | None
    best_dim:     str | None
    worst_dim:    str | None


@dataclass
class SessionSummary:
    """Resumen de la sesión de juego actual (últimas 4 horas)."""
    has_session:   bool
    total_games:   int   = 0
    wins:          int   = 0
    losses:        int   = 0
    avg_score:     float | None = None
    best_aspect:   str | None   = None
    worst_aspect:  str | None   = None
    goal_progress: str | None   = None   # "3 / 5 completado"
    tip:           str | None   = None
    session_label: str          = ""     # "Hace 2h" | "Hoy"
    matches:       list[SessionMatch] = field(default_factory=list)


@dataclass
class MemoryEntry:
    """Entrada en la memoria histórica de objetivos."""
    goal_title:   str
    status:       str          # "active" | "completed" | "skipped"
    created_at:   str
    completed_at: str | None
    metric_key:   str


@dataclass
class KnowledgeViewModel:
    has_data:       bool
    role:           str = ""
    total_matches:  int = 0

    session:        SessionSummary      = field(default_factory=lambda: SessionSummary(has_session=False))
    active_goal:    Goal | None         = None
    memory:         list[MemoryEntry]   = field(default_factory=list)
    patterns:       list[Pattern]       = field(default_factory=list)
    insights:       list[Insight]       = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)

    confidence:       str = "insufficient"   # overall
    games_needed_msg: str | None = None
