"""Entidades del Objective Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .common import KnowledgeSource


class ObjectiveType(str, Enum):
    BARON        = "baron"
    DRAGON       = "dragon"
    HERALD       = "herald"
    TOWER        = "tower"
    INHIBITOR    = "inhibitor"
    NEXUS        = "nexus"


class DragonType(str, Enum):
    INFERNAL  = "infernal"
    MOUNTAIN  = "mountain"
    OCEAN     = "ocean"
    CLOUD     = "cloud"
    HEXTECH   = "hextech"
    CHEMTECH  = "chemtech"
    ELDER     = "elder"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    SITUATIONAL = "situational"


@dataclass
class ObjectiveTiming:
    spawn_minutes: float | None = None      # minuto de spawn inicial
    respawn_minutes: float | None = None    # tiempo de respawn
    ideal_attempt_window: str = ""          # descripción del momento ideal
    warning: str = ""                       # cuándo NO intentarlo


@dataclass
class ObjectiveDefinition:
    id: str                                 # "baron", "dragon_infernal", "herald"
    name: str
    type: ObjectiveType
    priority: Priority
    description: str
    reward: str                             # qué da al equipo
    timing: ObjectiveTiming = field(default_factory=ObjectiveTiming)
    requirements: list[str] = field(default_factory=list)    # condiciones para intentarlo
    risks: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    team_composition_notes: str = ""
    role_responsibility: dict[str, str] = field(default_factory=dict)  # {role: responsabilidad}
    sources: list[KnowledgeSource] = field(default_factory=list)


@dataclass
class ObjectivePriority:
    """Priorización de objetivos en un momento del juego."""
    phase: str                              # "early" | "mid" | "late"
    ordered_objectives: list[str]           # IDs en orden de prioridad
    context: str                            # cuándo aplica esta priorización
    exceptions: list[str] = field(default_factory=list)
