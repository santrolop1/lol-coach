"""Entidades del Coach Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class ExperienceTier(str, Enum):
    BEGINNER     = "beginner"      # ≤50 partidas totales
    INTERMEDIATE = "intermediate"  # 50-300
    ADVANCED     = "advanced"      # 300-1000
    EXPERT       = "expert"        # 1000+


@dataclass
class PlayerModel:
    """Modelo del jugador para adaptar las explicaciones del Coach."""
    puuid: str
    total_games: int
    experience_tier: ExperienceTier = ExperienceTier.INTERMEDIATE
    persistent_patterns: list[str] = field(default_factory=list)  # patrones sin mejorar >3 sesiones
    mastered_concepts: list[str] = field(default_factory=list)     # drills completados
    prefers_short: bool = False
    likely_tilted: bool = False
    on_win_streak: bool = False


@dataclass
class CoachExplanation:
    """Output del Coach Intelligence Engine. Texto adaptado al nivel del jugador."""
    title: str
    headline: str                  # Una oración directa
    explanation: str               # Adaptada al experience_tier
    why_it_matters: str
    how_to_fix: str
    drill_suggestion: str | None = None
    repeated_note: str | None = None   # "Ya detectamos esto hace 20 partidas"
    tone: str = "direct"           # "encouraging"|"direct"|"concise"|"data_only"
