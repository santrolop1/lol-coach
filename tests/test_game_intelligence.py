"""
Tests del Sprint GI-1 — Game Intelligence Platform Foundation.

Verifica:
- Imports correctos sin dependencias circulares
- Los modelos se instancian
- ChampionRegistry funciona (sin perfiles: lista vacía)
- KnowledgeAPI inicia correctamente
- GameIntelligencePlatform inicia y build() funciona sin perfiles
- Sin romper ningún test existente
"""

import pytest


# ── Imports ───────────────────────────────────────────────────────────────────

def test_platform_importable():
    from backend.game_intelligence.platform import GameIntelligencePlatform
    assert GameIntelligencePlatform is not None


def test_models_importable():
    from backend.game_intelligence.models import (
        ChampionProfile, MatchupProfile, WaveStrategy, MacroPattern,
        ItemDefinition, ItemBuild, RunePage, LearningRoadmap, LearningLevel,
        GraduationCriteria, Drill, ActiveDrill, EnrichedReview, CoachExplanation,
        PlayerModel, KnowledgeSource, VideoReference, PatchVersion, Confidence,
    )
    assert ChampionProfile is not None
    assert MatchupProfile is not None


def test_registries_importable():
    from backend.game_intelligence.registries import (
        BaseRegistry, ChampionRegistry, KnowledgeAPI, knowledge,
    )
    assert knowledge is not None


def test_no_circular_imports():
    """Si este test pasa, no hay imports circulares."""
    import backend.game_intelligence
    import backend.game_intelligence.models
    import backend.game_intelligence.registries
    import backend.game_intelligence.platform


# ── Modelos ───────────────────────────────────────────────────────────────────

def test_champion_profile_creation():
    from backend.game_intelligence.models import ChampionProfile

    profile = ChampionProfile(
        champion="tryndamere",
        display_name="Tryndamere",
        roles=["TOP"],
        difficulty="medium",
        patch_version="14.12",
        identity="Guerrero cuerpo a cuerpo escalado que domina el split push tardío.",
        playstyle="scaling",
        scaling="late",
    )
    assert profile.champion == "tryndamere"
    assert "TOP" in profile.roles
    assert profile.combos == []


def test_matchup_profile_creation():
    from backend.game_intelligence.models import MatchupProfile

    matchup = MatchupProfile(
        champion="tryndamere",
        enemy="darius",
        role="TOP",
        patch_version="14.12",
        difficulty="hard",
        summary="Darius te gana en intercambios cortos; tú ganas el split tardío.",
        early_game="Evitar intercambios con stack de Darius.",
        mid_game="Pushear y rotar si Darius está en el mapa.",
        late_game="Split push permanente — no te puede matar con R activa.",
    )
    assert matchup.champion == "tryndamere"
    assert matchup.enemy == "darius"
    assert matchup.difficulty == "hard"


def test_wave_strategy_creation():
    from backend.game_intelligence.models import WaveStrategy, WaveTechnique

    strategy = WaveStrategy(
        id="freeze",
        name="Freeze",
        technique=WaveTechnique.FREEZE,
        description="Mantener la oleada cerca de tu torre.",
        when_to_use="Cuando tienes ventaja de lane y quieres negar CS al enemigo.",
        when_not_to_use="Cuando tienes un dive amenazante o necesitas empujar.",
        why="Niega CS y fuerza al enemigo a sobreextenderse.",
    )
    assert strategy.technique == WaveTechnique.FREEZE
    assert strategy.drill_id is None


def test_learning_roadmap_creation():
    from backend.game_intelligence.models import LearningRoadmap, LearningLevel, GraduationCriteria

    criteria = GraduationCriteria(
        id="deaths_under_5",
        description="Morir menos de 5 veces en 4 de 5 partidas",
        evaluation_mode="auto",
        metric_key="deaths",
        threshold=5.0,
    )
    level = LearningLevel(
        level=1,
        name="Fundamentos",
        description="Sobrevivir en lane y llegar a late game.",
        graduation_criteria=[criteria],
        drill_ids=["deaths_lt_threshold"],
        estimated_games=15,
    )
    roadmap = LearningRoadmap(
        id="tryndamere_top_v1",
        champion="tryndamere",
        role="TOP",
        levels=[level],
    )
    assert roadmap.champion == "tryndamere"
    assert len(roadmap.levels) == 1
    assert roadmap.levels[0].level == 1


def test_drill_creation():
    from backend.game_intelligence.models import Drill, DrillCategory, DrillEvaluationMode

    drill = Drill(
        id="deaths_lt_threshold",
        name="Controlar muertes",
        category=DrillCategory.MECHANICAL,
        description="Morir menos del umbral definido por tus propios percentiles.",
        why="Las muertes son el mayor indicador de pérdida en lane.",
        how_measured="Promedio de muertes < p25 de tus propias partidas en 4/5 juegos.",
        evaluation_mode=DrillEvaluationMode.AUTO,
        metric_key="deaths",
        threshold_type="less_than",
        threshold_source="p25",
    )
    assert drill.category == DrillCategory.MECHANICAL
    assert drill.evaluation_mode == DrillEvaluationMode.AUTO


def test_patch_version_comparison():
    from backend.game_intelligence.models import PatchVersion

    old = PatchVersion(14, 10)
    new = PatchVersion(14, 12)
    assert old.is_older_than(new, versions=2)
    assert not new.is_older_than(old, versions=2)
    assert old.full == "14.10"


def test_patch_version_parse():
    from backend.game_intelligence.models import PatchVersion

    v = PatchVersion.parse("14.12")
    assert v.major == 14
    assert v.minor == 12


# ── ChampionRegistry ──────────────────────────────────────────────────────────

def test_champion_registry_no_profiles():
    """Sin perfiles creados, list_available devuelve lista vacía."""
    from backend.game_intelligence.registries import ChampionRegistry

    reg = ChampionRegistry()
    available = reg.list_available()
    assert isinstance(available, list)


def test_champion_registry_get_nonexistent():
    from backend.game_intelligence.registries import ChampionRegistry

    reg = ChampionRegistry()
    result = reg.get("champion_que_no_existe_xyz")
    assert result is None


def test_champion_registry_exists_nonexistent():
    from backend.game_intelligence.registries import ChampionRegistry

    reg = ChampionRegistry()
    assert not reg.exists("champion_que_no_existe_xyz")


def test_champion_registry_matchup_nonexistent():
    from backend.game_intelligence.registries import ChampionRegistry

    reg = ChampionRegistry()
    result = reg.get_matchup("tryndamere", "enemigo_que_no_existe_xyz", "TOP")
    assert result is None


def test_champion_registry_validate_valid_profile():
    from backend.game_intelligence.registries import ChampionRegistry
    from backend.game_intelligence.models import ChampionProfile

    reg = ChampionRegistry()
    profile = ChampionProfile(
        champion="tryndamere",
        display_name="Tryndamere",
        roles=["TOP"],
        difficulty="medium",
        patch_version="14.12",
        identity="Split pusher.",
        playstyle="scaling",
        scaling="late",
    )
    errors = reg.validate(profile)
    assert errors == []


def test_champion_registry_validate_invalid_profile():
    from backend.game_intelligence.registries import ChampionRegistry
    from backend.game_intelligence.models import ChampionProfile

    reg = ChampionRegistry()
    # Perfil con campos vacíos
    profile = ChampionProfile(
        champion="",          # ← inválido
        display_name="",      # ← inválido
        roles=[],             # ← inválido
        difficulty="medium",
        patch_version="",     # ← inválido
        identity="",          # ← inválido
        playstyle="scaling",
        scaling="late",
    )
    errors = reg.validate(profile)
    assert len(errors) > 0


# ── KnowledgeAPI ──────────────────────────────────────────────────────────────

def test_knowledge_api_initializes():
    from backend.game_intelligence.registries import KnowledgeAPI

    api = KnowledgeAPI()
    assert api.champion is not None


def test_knowledge_api_singleton():
    from backend.game_intelligence.registries import knowledge

    assert knowledge is not None
    assert knowledge.champion is not None


def test_knowledge_api_warm_all():
    from backend.game_intelligence.registries import KnowledgeAPI

    api = KnowledgeAPI()
    result = api.warm_all()
    assert "champion" in result
    assert "loaded" in result["champion"]


# ── GameIntelligencePlatform ──────────────────────────────────────────────────

def test_platform_initializes():
    from backend.game_intelligence.platform import GameIntelligencePlatform

    platform = GameIntelligencePlatform()
    assert platform is not None
    assert platform.knowledge is not None


def test_platform_build_no_profile():
    """build() con campeón sin perfil devuelve contexto con has_profile=False."""
    from backend.game_intelligence.platform import GameIntelligencePlatform

    platform = GameIntelligencePlatform()
    ctx = platform.build("campeon_sin_perfil_xyz", "TOP")

    assert ctx.champion == "campeon_sin_perfil_xyz"
    assert ctx.role == "TOP"
    assert ctx.has_profile is False
    assert ctx.profile is None


def test_platform_build_with_enemy_no_matchup():
    from backend.game_intelligence.platform import GameIntelligencePlatform

    platform = GameIntelligencePlatform()
    ctx = platform.build("tryndamere", "TOP", enemy="enemigo_sin_matchup_xyz")

    assert ctx.has_matchup_profile is False
    assert ctx.matchup_profile is None


def test_platform_available_champions():
    from backend.game_intelligence.platform import GameIntelligencePlatform

    platform = GameIntelligencePlatform()
    champs = platform.available_champions()
    assert isinstance(champs, list)


def test_platform_warm():
    from backend.game_intelligence.platform import GameIntelligencePlatform

    platform = GameIntelligencePlatform()
    result = platform.warm()
    assert isinstance(result, dict)


def test_platform_review_returns_none_in_gi1():
    from backend.game_intelligence.platform import GameIntelligencePlatform

    platform = GameIntelligencePlatform()
    result = platform.review("tryndamere", "TOP", match={})
    assert result is None


def test_platform_learning_returns_none_in_gi1():
    from backend.game_intelligence.platform import GameIntelligencePlatform

    platform = GameIntelligencePlatform()
    result = platform.learning("tryndamere", "TOP", puuid="test-puuid")
    assert result is None


def test_platform_training_returns_none_in_gi1():
    from backend.game_intelligence.platform import GameIntelligencePlatform

    platform = GameIntelligencePlatform()
    result = platform.training("tryndamere", "TOP", puuid="test-puuid")
    assert result is None
