"""Entidades de dominio del Champion Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field
from .common import KnowledgeSource, VideoReference


@dataclass
class AbilityInfo:
    key: str                              # "Q" | "W" | "E" | "R" | "P"
    name: str
    description: str                      # Mecánica relevante, no lore
    tips: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    cancel_windows: list[str] = field(default_factory=list)
    cooldowns: list[float] = field(default_factory=list)   # por nivel [1-5]
    cost: str | None = None
    max_rank_priority: int = 1            # 1=subir primero, 2=segundo, 3=tercero
    source: KnowledgeSource | None = None


@dataclass
class Combo:
    id: str                               # slug único: "all_in_6", "quick_trade_early"
    name: str
    sequence: list[str]                   # ["Flash", "R", "Q", "AA", "E"]
    description: str
    when_to_use: str
    difficulty: str                       # "basic" | "intermediate" | "advanced"
    timing_notes: str | None = None
    video: VideoReference | None = None
    source: KnowledgeSource | None = None


@dataclass
class AnimationCancel:
    id: str
    name: str
    sequence: list[str]                   # ["AA", "Q-cancel", "AA"]
    description: str
    difficulty: str                       # "basic" | "intermediate" | "advanced"
    practice_drill_id: str | None = None  # drill que trabaja este cancel
    video: VideoReference | None = None


@dataclass
class PowerSpike:
    id: str                               # "level_6", "first_item", "full_build"
    timing: str                           # descripción legible
    description: str
    action: str                           # qué hacer cuando llega el spike
    window_minutes: tuple[float, float] | None = None
    enemy_spike_context: str | None = None


@dataclass
class ChampionMacroConfig:
    """Referencias a MacroRegistry por ID. NO duplica el contenido."""
    primary_pattern_ids: list[str] = field(default_factory=list)
    win_condition_ids: list[str] = field(default_factory=list)
    split_push_priority: str = "conditional"   # "always"|"conditional"|"rarely"|"never"
    teamfight_role: str = "frontline"           # "frontline"|"flanker"|"peeler"|"backline"


@dataclass
class ChampionWaveConfig:
    """Referencias a WaveRegistry por ID. NO duplica el contenido."""
    preferred_technique_ids: list[str] = field(default_factory=list)
    level_2_crash: bool = False
    recall_setup_technique_id: str | None = None


@dataclass
class ChampionBuildConfig:
    """Referencias a ItemRegistry por ID. NO duplica el contenido."""
    standard_build_id: str = ""
    vs_tanks_build_id: str | None = None
    vs_poke_build_id: str | None = None
    vs_burst_build_id: str | None = None
    starter_id: str = ""
    boots_options: list[str] = field(default_factory=list)


@dataclass
class ChampionRuneConfig:
    """Referencias a RuneRegistry por ID. NO duplica el contenido."""
    standard_page_id: str = ""
    vs_poke_page_id: str | None = None
    vs_all_in_page_id: str | None = None


@dataclass
class ChampionProfile:
    # Identidad
    champion: str                         # slug normalizado: "tryndamere"
    display_name: str                     # nombre de pantalla: "Tryndamere"
    roles: list[str]                      # ["TOP"] | ["TOP", "MID"]
    difficulty: str                       # "low" | "medium" | "high" | "extreme"
    patch_version: str                    # "14.12"
    identity: str                         # Una oración: qué tipo de campeón es
    playstyle: str                        # "early_dominant"|"scaling"|"flex"
    scaling: str                          # "early"|"mid"|"late"|"all_game"

    # Fortalezas y debilidades
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)

    # Habilidades y mecánicas (datos propios del campeón)
    abilities: dict[str, AbilityInfo] = field(default_factory=dict)
    ability_order: list[str] = field(default_factory=list)   # ["Q", "E", "W"]
    combos: list[Combo] = field(default_factory=list)
    animation_cancels: list[AnimationCancel] = field(default_factory=list)
    power_spikes: list[PowerSpike] = field(default_factory=list)

    # Referencias a conocimiento global (no duplica)
    macro_config: ChampionMacroConfig = field(default_factory=ChampionMacroConfig)
    wave_config: ChampionWaveConfig = field(default_factory=ChampionWaveConfig)
    build_config: ChampionBuildConfig = field(default_factory=ChampionBuildConfig)
    rune_config: ChampionRuneConfig = field(default_factory=ChampionRuneConfig)

    # Conocimiento editorial propio
    common_mistakes: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)

    # Ruta de aprendizaje
    learning_roadmap_id: str = ""         # referencia al LearningRoadmap

    # Metadatos
    sources: list[KnowledgeSource] = field(default_factory=list)
    last_updated: str = ""
