"""Entidades del Macro Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field
from .common import KnowledgeSource, VideoReference


@dataclass
class MacroPattern:
    id: str                           # "split_push", "rotation", "tempo", "recall"
    name: str
    phase: str                        # "early" | "mid" | "late" | "all"
    description: str
    when_to_apply: str
    steps: list[str] = field(default_factory=list)
    anti_pattern: str = ""            # el error opuesto más común
    common_mistakes: list[str] = field(default_factory=list)
    applies_to_roles: list[str] = field(default_factory=list)  # vacío = todos
    drill_id: str | None = None
    video: VideoReference | None = None
    sources: list[KnowledgeSource] = field(default_factory=list)


@dataclass
class WinCondition:
    id: str                           # "split_and_win", "teamfight_and_win", "siege"
    name: str
    description: str
    required_conditions: list[str] = field(default_factory=list)
    champion_archetypes: list[str] = field(default_factory=list)
    macro_steps: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    sources: list[KnowledgeSource] = field(default_factory=list)
