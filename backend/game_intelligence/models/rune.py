"""Entidades del Rune Intelligence."""

from __future__ import annotations
from dataclasses import dataclass, field
from .common import KnowledgeSource


@dataclass
class RuneTree:
    id: str                           # "precision", "domination", "sorcery", "resolve", "inspiration"
    name: str
    description: str
    playstyle: str                    # cuándo elegir este árbol


@dataclass
class RunePage:
    id: str                           # "standard_trynd", "vs_poke_trynd"
    name: str
    primary_tree: str
    primary_keystone: str
    primary_slots: list[str] = field(default_factory=list)    # 3 runas secundarias del árbol
    secondary_tree: str = ""
    secondary_slots: list[str] = field(default_factory=list)  # 2 runas del árbol secundario
    shards: list[str] = field(default_factory=list)           # [offense, flex, defense]
    when_to_use: str = ""
    description: str = ""
    patch_version: str = ""
    sources: list[KnowledgeSource] = field(default_factory=list)


@dataclass
class RuneSetup:
    """Configuración de runas para un campeón en un contexto específico."""
    id: str
    name: str
    page_id: str                      # referencia a RunePage en RuneRegistry
    context: str                      # "standard" | "vs_poke" | "vs_all_in"
    when_to_use: str = ""
