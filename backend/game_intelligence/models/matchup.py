"""Entidades del Matchup Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field
from .common import KnowledgeSource, VideoReference


@dataclass
class TradeWindow:
    id: str
    timing: str                    # "pre_6" | "level_6" | "first_item_spike"
    condition: str                 # "cuando su W está en cooldown"
    action: str
    expected_outcome: str          # "ventaja" | "intercambio favorable" | "kill"
    risk: str                      # "low" | "medium" | "high"
    video: VideoReference | None = None


@dataclass
class DangerWindow:
    id: str
    timing: str
    reason: str
    survival_tip: str


@dataclass
class MatchupWavePlan:
    phase: str                     # "early" | "mid" | "late"
    technique: str                 # ID de WaveRegistry: "freeze" | "slow_push" | etc.
    reasoning: str
    steps: list[str] = field(default_factory=list)


@dataclass
class MatchupItemPriority:
    item: str
    reason: str
    timing: str                    # "first_item" | "second_item" | "component"


@dataclass
class MatchupProfile:
    # Identidad del matchup
    champion: str                  # slug: "tryndamere"
    enemy: str                     # slug: "darius"
    role: str                      # "TOP"
    patch_version: str

    # Clasificación
    difficulty: str                # "easy" | "medium" | "hard" | "extreme"
    summary: str                   # Una oración: dinámica central

    # Fases del juego
    early_game: str
    mid_game: str
    late_game: str

    # Power spikes
    our_spikes: list[str] = field(default_factory=list)
    enemy_spikes: list[str] = field(default_factory=list)

    # Trading
    kill_windows: list[TradeWindow] = field(default_factory=list)
    danger_windows: list[DangerWindow] = field(default_factory=list)
    trading_style: str = "situational"  # "short_trades"|"extended"|"poke_only"|"avoid"

    # Wave
    wave_plan: list[MatchupWavePlan] = field(default_factory=list)
    recall_plan: str = ""

    # Items y runas
    item_priority: list[MatchupItemPriority] = field(default_factory=list)
    rune_adjustments: list[str] = field(default_factory=list)

    # Conocimiento editorial
    tips: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)

    # Drills específicos de este matchup
    drill_ids: list[str] = field(default_factory=list)

    sources: list[KnowledgeSource] = field(default_factory=list)
    last_updated: str = ""
