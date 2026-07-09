"""Entidades del Item Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field
from .common import KnowledgeSource


@dataclass
class ItemDefinition:
    id: str                           # slug: "trinity_force", "stridebreaker"
    name: str
    cost: int
    description: str                  # qué hace en términos de juego
    stats: list[str] = field(default_factory=list)
    when_to_buy: str = ""
    synergies: list[str] = field(default_factory=list)   # IDs de items que combinan bien
    countered_by: list[str] = field(default_factory=list)
    patch_version: str = ""
    sources: list[KnowledgeSource] = field(default_factory=list)


@dataclass
class ItemBuild:
    id: str                           # "standard_trynd", "vs_tanks_trynd"
    name: str
    description: str
    when_to_use: str
    starter: list[str] = field(default_factory=list)
    core: list[str] = field(default_factory=list)         # Los 2-3 items principales
    situational: list[str] = field(default_factory=list)
    boots_options: list[str] = field(default_factory=list)
    stat_priority: list[str] = field(default_factory=list)
    patch_version: str = ""
    sources: list[KnowledgeSource] = field(default_factory=list)


@dataclass
class BuildPath:
    """Camino de construcción de un item (componentes en orden)."""
    item_id: str
    components: list[str] = field(default_factory=list)  # IDs en orden de compra
    first_back_gold: int = 0          # oro mínimo para la primera recall óptima
    notes: str = ""
