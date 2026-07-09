"""Entidades del Vision Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .common import KnowledgeSource


class WardType(str, Enum):
    STEALTH    = "stealth"       # Ward invisible estándar
    CONTROL    = "control"       # Control Ward (Pink)
    TOTEM      = "totem"         # Totem trinket
    FARSIGHT   = "farsight"      # Farsight Alteration


class VisionZone(str, Enum):
    RIVER_TOP    = "river_top"
    RIVER_BOT    = "river_bot"
    BARON_PIT    = "baron_pit"
    DRAGON_PIT   = "dragon_pit"
    TOP_JUNGLE   = "top_jungle"
    BOT_JUNGLE   = "bot_jungle"
    MID_LANE     = "mid_lane"
    TOP_SIDE     = "top_side"
    BOT_SIDE     = "bot_side"
    ENEMY_JUNGLE = "enemy_jungle"


class VisionPurpose(str, Enum):
    OBJECTIVE  = "objective"     # visión para asegurar/contestar objetivo
    DEFENSIVE  = "defensive"     # visión para evitar ganks
    OFFENSIVE  = "offensive"     # visión en jungla enemiga
    TRACKING   = "tracking"      # seguimiento del jungler enemigo


@dataclass
class WardSpot:
    id: str
    name: str
    zone: VisionZone
    ward_type: WardType
    purpose: VisionPurpose
    description: str
    when_to_use: str
    map_position: str = ""       # descripción de la posición en el mapa
    timing_minutes: list[float] = field(default_factory=list)  # minutos clave
    requires_deep_entry: bool = False
    role_priority: list[str] = field(default_factory=list)  # roles que deben hacerlo
    tips: list[str] = field(default_factory=list)
    sources: list[KnowledgeSource] = field(default_factory=list)


@dataclass
class VisionPattern:
    id: str
    name: str
    purpose: VisionPurpose
    phase: str                   # "early" | "mid" | "late" | "objective"
    description: str
    ward_spot_ids: list[str] = field(default_factory=list)   # WardSpot IDs incluidos
    steps: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)
    sources: list[KnowledgeSource] = field(default_factory=list)
