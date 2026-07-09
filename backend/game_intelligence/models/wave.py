"""Entidades del Wave Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .common import KnowledgeSource, VideoReference


class WaveTechnique(str, Enum):
    FREEZE    = "freeze"
    SLOW_PUSH = "slow_push"
    FAST_PUSH = "fast_push"
    BOUNCE    = "bounce"
    CRASH     = "crash"
    RESET     = "reset"


class WaveState(str, Enum):
    FROZEN        = "frozen"          # oleada congelada cerca de tu torre
    SLOW_PUSHING  = "slow_pushing"    # oleada creciendo lentamente hacia enemigo
    FAST_PUSHING  = "fast_pushing"    # oleada empujada fuerte
    BOUNCING      = "bouncing"        # oleada volviendo hacia el jugador
    CRASHED       = "crashed"         # oleada reventada en la torre enemiga
    EQUILIBRIUM   = "equilibrium"     # oleadas equilibradas en el centro


@dataclass
class WaveStrategy:
    id: str                           # slug: "freeze", "slow_push", etc.
    name: str
    technique: WaveTechnique
    description: str
    when_to_use: str
    when_not_to_use: str
    why: str
    steps: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)
    difficulty: str = "basic"         # "basic" | "intermediate" | "advanced"
    drill_id: str | None = None
    video: VideoReference | None = None
    sources: list[KnowledgeSource] = field(default_factory=list)
