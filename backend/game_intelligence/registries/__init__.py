"""APIs internas de acceso al conocimiento de la Game Intelligence Platform."""

from .base import BaseRegistry
from .champion_registry import ChampionRegistry
from .wave_registry import WaveRegistry
from .macro_registry import MacroRegistry
from .item_registry import ItemRegistry
from .rune_registry import RuneRegistry
from .objective_registry import ObjectiveRegistry
from .vision_registry import VisionRegistry
from .registry_facade import KnowledgeAPI, knowledge
from .validator import ChampionValidator
from .coverage import CoverageReport, build_coverage_report

__all__ = [
    "BaseRegistry",
    "ChampionRegistry",
    "WaveRegistry",
    "MacroRegistry",
    "ItemRegistry",
    "RuneRegistry",
    "ObjectiveRegistry",
    "VisionRegistry",
    "KnowledgeAPI",
    "knowledge",
    "ChampionValidator",
    "CoverageReport",
    "build_coverage_report",
]
