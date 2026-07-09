"""Entidades de dominio de la Game Intelligence Platform."""

from .common import KnowledgeSource, VideoReference, PatchVersion, Confidence, SourceType
from .champion import (
    ChampionProfile, AbilityInfo, Combo, AnimationCancel, PowerSpike,
    ChampionMacroConfig, ChampionWaveConfig, ChampionBuildConfig, ChampionRuneConfig,
)
from .matchup import MatchupProfile, TradeWindow, DangerWindow, MatchupWavePlan, MatchupItemPriority
from .wave import WaveStrategy, WaveState, WaveTechnique
from .macro import MacroPattern, WinCondition
from .item import ItemDefinition, ItemBuild, BuildPath
from .rune import RuneTree, RunePage, RuneSetup
from .learning import LearningRoadmap, LearningLevel, GraduationCriteria, LearningState
from .training import Drill, DrillCategory, ActiveDrill, DrillResult, DrillEvaluationMode
from .review import EnrichedReview, ProfileNote, MatchupNote, ReviewComparison
from .coaching import CoachExplanation, PlayerModel, ExperienceTier
from .objective import ObjectiveDefinition, ObjectiveTiming, ObjectivePriority, ObjectiveType, DragonType, Priority
from .vision import WardSpot, VisionPattern, WardType, VisionZone, VisionPurpose
from .analysis import ChampionAnalysis, LiveCoachHints, DetectedMistake

__all__ = [
    # common
    "KnowledgeSource", "VideoReference", "PatchVersion", "Confidence", "SourceType",
    # champion
    "ChampionProfile", "AbilityInfo", "Combo", "AnimationCancel", "PowerSpike",
    "ChampionMacroConfig", "ChampionWaveConfig", "ChampionBuildConfig", "ChampionRuneConfig",
    # matchup
    "MatchupProfile", "TradeWindow", "DangerWindow", "MatchupWavePlan", "MatchupItemPriority",
    # wave
    "WaveStrategy", "WaveState", "WaveTechnique",
    # macro
    "MacroPattern", "WinCondition",
    # item
    "ItemDefinition", "ItemBuild", "BuildPath",
    # rune
    "RuneTree", "RunePage", "RuneSetup",
    # learning
    "LearningRoadmap", "LearningLevel", "GraduationCriteria", "LearningState",
    # training
    "Drill", "DrillCategory", "ActiveDrill", "DrillResult", "DrillEvaluationMode",
    # review
    "EnrichedReview", "ProfileNote", "MatchupNote", "ReviewComparison",
    # coaching
    "CoachExplanation", "PlayerModel", "ExperienceTier",
    # objective
    "ObjectiveDefinition", "ObjectiveTiming", "ObjectivePriority",
    "ObjectiveType", "DragonType", "Priority",
    # vision
    "WardSpot", "VisionPattern", "WardType", "VisionZone", "VisionPurpose",
    # analysis
    "ChampionAnalysis", "LiveCoachHints", "DetectedMistake",
]
