"""
KnowledgeAPI — Punto de acceso único a todo el conocimiento de la plataforma.

Los motores importan KnowledgeAPI o el singleton `knowledge`.
Nunca importan knowledge/ directamente.

Uso:
    from backend.game_intelligence.registries import knowledge

    strategy = knowledge.wave.get("freeze")
    pattern  = knowledge.macro.get("split_push")
    profile  = knowledge.champion.get("tryndamere")
    matchup  = knowledge.champion.get_matchup("tryndamere", "darius", "TOP")
"""

from __future__ import annotations
import logging

from .champion_registry import ChampionRegistry
from .wave_registry import WaveRegistry
from .macro_registry import MacroRegistry
from .item_registry import ItemRegistry
from .rune_registry import RuneRegistry
from .objective_registry import ObjectiveRegistry
from .vision_registry import VisionRegistry

logger = logging.getLogger(__name__)


class KnowledgeAPI:
    """
    Facade unificado de todos los registries.

    GI-1: ChampionRegistry
    GI-2: Wave, Macro, Item, Rune, Objective, Vision
    """

    def __init__(self) -> None:
        self.champion  = ChampionRegistry()
        self.wave      = WaveRegistry()
        self.macro     = MacroRegistry()
        self.item      = ItemRegistry()
        self.rune      = RuneRegistry()
        self.objective = ObjectiveRegistry()
        self.vision    = VisionRegistry()
        # self.patch   = PatchRegistry()   ← GI-7

    def warm_all(self) -> dict[str, dict[str, int]]:
        """Calienta todos los caches disponibles. Llamar al iniciar la app."""
        results: dict[str, dict[str, int]] = {}
        results["champion"]  = self.champion.warm_cache()
        results["wave"]      = self.wave.warm_cache()
        results["macro"]     = self.macro.warm_cache()
        results["item"]      = self.item.warm_cache()
        results["rune"]      = self.rune.warm_cache()
        results["objective"] = self.objective.warm_cache()
        results["vision"]    = self.vision.warm_cache()
        logger.info("KnowledgeAPI warm_all: %s", results)
        return results

    def staleness_summary(self) -> dict[str, list[str]]:
        """
        Devuelve campeones cuyos perfiles podrían estar desactualizados.
        Implementación completa en GI-7 con PatchRegistry.
        """
        return {}


# Singleton de la aplicación
knowledge = KnowledgeAPI()
