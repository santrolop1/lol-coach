"""
Tests de GI-3 — Champion Intelligence MVP.

Cubre:
  - Auto-descubrimiento de Tryndamere (profile + matchups)
  - ChampionValidator (validación profunda con referencias cruzadas)
  - CoverageReport (completitud del perfil)
  - ChampionIntelligenceEngine (con y sin perfil, confianza, análisis)
  - Integración: KnowledgeAPI → engine → ChampionAnalysis
"""

import pytest
from backend.game_intelligence.registries import (
    ChampionRegistry,
    KnowledgeAPI,
    ChampionValidator,
    CoverageReport,
    build_coverage_report,
)
from backend.game_intelligence.engines.champion.engine import ChampionIntelligenceEngine
from backend.game_intelligence.models.analysis import ChampionAnalysis, LiveCoachHints, DetectedMistake
from backend.game_intelligence.models.champion import ChampionProfile


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def registry():
    return ChampionRegistry()

@pytest.fixture(scope="module")
def knowledge():
    return KnowledgeAPI()

@pytest.fixture(scope="module")
def engine(knowledge):
    return ChampionIntelligenceEngine(knowledge)

@pytest.fixture(scope="module")
def tryndamere_profile(registry):
    return registry.get("tryndamere")

@pytest.fixture
def matches_few():
    """3 partidas — confianza 'insufficient' (< 5)."""
    return [
        {"win": True,  "deaths": 3, "kills": 5, "assists": 2,
         "cs_per_min": 7.0, "damage_per_min": 500, "kill_participation": 0.6,
         "vision_score": 10, "gold_per_min": 350},
        {"win": False, "deaths": 6, "kills": 2, "assists": 1,
         "cs_per_min": 5.5, "damage_per_min": 400, "kill_participation": 0.4,
         "vision_score": 8, "gold_per_min": 300},
        {"win": True,  "deaths": 2, "kills": 8, "assists": 3,
         "cs_per_min": 8.0, "damage_per_min": 600, "kill_participation": 0.7,
         "vision_score": 12, "gold_per_min": 380},
    ]

@pytest.fixture
def matches_medium():
    """10 partidas — confianza 'low' (5-14)."""
    base = [
        {"win": True,  "deaths": 2, "kills": 7, "assists": 3,
         "cs_per_min": 7.5, "damage_per_min": 550, "kill_participation": 0.65,
         "vision_score": 11, "gold_per_min": 370},
        {"win": False, "deaths": 7, "kills": 2, "assists": 1,
         "cs_per_min": 4.5, "damage_per_min": 350, "kill_participation": 0.35,
         "vision_score": 7, "gold_per_min": 290},
    ]
    return base * 5  # 10 partidas

@pytest.fixture
def matches_high():
    """35 partidas — confianza 'high' (>= 30)."""
    base = {
        "win": True, "deaths": 3, "kills": 5, "assists": 2,
        "cs_per_min": 6.8, "damage_per_min": 480, "kill_participation": 0.55,
        "vision_score": 10, "gold_per_min": 340,
    }
    return [base.copy() for _ in range(35)]

@pytest.fixture
def matches_bad_stats():
    """Partidas con estadísticas malas — muchas muertes, poco CS."""
    return [
        {"win": False, "deaths": 8, "kills": 1, "assists": 0,
         "cs_per_min": 3.5, "damage_per_min": 200, "kill_participation": 0.2,
         "vision_score": 5, "gold_per_min": 220},
    ] * 10


# ── Auto-descubrimiento ───────────────────────────────────────────────────────

class TestAutoDiscovery:

    def test_tryndamere_is_available(self, registry):
        available = registry.list_available()
        assert "tryndamere" in available

    def test_tryndamere_profile_loads(self, tryndamere_profile):
        assert tryndamere_profile is not None
        assert isinstance(tryndamere_profile, ChampionProfile)

    def test_tryndamere_basic_identity(self, tryndamere_profile):
        p = tryndamere_profile
        assert p.champion == "tryndamere"
        assert p.display_name == "Tryndamere"
        assert "TOP" in p.roles
        assert p.patch_version == "14.12"
        assert p.playstyle == "scaling"
        assert p.scaling == "late"
        assert len(p.identity) > 20

    def test_tryndamere_exists(self, registry):
        assert registry.exists("tryndamere") is True

    def test_tryndamere_case_insensitive(self, registry):
        assert registry.get("Tryndamere") is not None
        assert registry.get("TRYNDAMERE") is not None

    def test_unknown_champion_returns_none(self, registry):
        assert registry.get("unknownchampxyz") is None

    def test_unknown_champion_exists_false(self, registry):
        assert registry.exists("unknownchampxyz") is False

    def test_registry_cache(self, registry):
        # Segundo get debe ser del cache
        first = registry.get("tryndamere")
        second = registry.get("tryndamere")
        assert first is second


# ── Abilities ─────────────────────────────────────────────────────────────────

class TestTryndamereAbilities:

    def test_all_abilities_present(self, tryndamere_profile):
        keys = set(tryndamere_profile.abilities.keys())
        assert keys == {"P", "Q", "W", "E", "R"}

    def test_abilities_have_name_and_description(self, tryndamere_profile):
        for key, ability in tryndamere_profile.abilities.items():
            assert ability.name, f"Ability {key} sin nombre"
            assert ability.description, f"Ability {key} sin descripción"

    def test_r_has_cooldowns(self, tryndamere_profile):
        r = tryndamere_profile.abilities["R"]
        assert r.cooldowns == [110.0, 100.0, 90.0]

    def test_q_has_cooldowns(self, tryndamere_profile):
        q = tryndamere_profile.abilities["Q"]
        assert len(q.cooldowns) == 5

    def test_r_has_tips(self, tryndamere_profile):
        r = tryndamere_profile.abilities["R"]
        assert len(r.tips) > 0

    def test_r_has_common_mistakes(self, tryndamere_profile):
        r = tryndamere_profile.abilities["R"]
        assert len(r.common_mistakes) > 0


# ── Combos y Power Spikes ─────────────────────────────────────────────────────

class TestTryndamereCombosAndSpikes:

    def test_has_combos(self, tryndamere_profile):
        assert len(tryndamere_profile.combos) >= 3

    def test_combo_ids_unique(self, tryndamere_profile):
        ids = [c.id for c in tryndamere_profile.combos]
        assert len(ids) == len(set(ids))

    def test_all_in_r_combo_exists(self, tryndamere_profile):
        ids = [c.id for c in tryndamere_profile.combos]
        assert "all_in_r" in ids

    def test_has_power_spikes(self, tryndamere_profile):
        assert len(tryndamere_profile.power_spikes) >= 2

    def test_level_6_spike_exists(self, tryndamere_profile):
        ids = [s.id for s in tryndamere_profile.power_spikes]
        assert "level_6" in ids

    def test_power_spike_ids_unique(self, tryndamere_profile):
        ids = [s.id for s in tryndamere_profile.power_spikes]
        assert len(ids) == len(set(ids))

    def test_animation_cancels(self, tryndamere_profile):
        assert len(tryndamere_profile.animation_cancels) >= 1


# ── Configs ───────────────────────────────────────────────────────────────────

class TestTryndamereConfigs:

    def test_macro_config_split_push(self, tryndamere_profile):
        mc = tryndamere_profile.macro_config
        assert "split_push" in mc.primary_pattern_ids
        assert "split_and_win" in mc.win_condition_ids

    def test_wave_config_has_techniques(self, tryndamere_profile):
        wc = tryndamere_profile.wave_config
        assert len(wc.preferred_technique_ids) >= 2
        assert "crash" in wc.preferred_technique_ids

    def test_build_config_standard(self, tryndamere_profile):
        bc = tryndamere_profile.build_config
        assert bc.standard_build_id == "tryndamere_standard_crit"
        assert bc.vs_tanks_build_id == "tryndamere_vs_tanks"

    def test_rune_config_standard(self, tryndamere_profile):
        rc = tryndamere_profile.rune_config
        assert rc.standard_page_id == "lethal_tempo_crit"

    def test_learning_roadmap_id(self, tryndamere_profile):
        assert tryndamere_profile.learning_roadmap_id == "tryndamere_top_v1"


# ── Matchups ──────────────────────────────────────────────────────────────────

class TestMatchups:

    def test_tryndamere_matchups_list(self, registry):
        matchups = registry.list_matchups("tryndamere")
        assert "darius" in matchups
        assert "teemo" in matchups
        assert "garen" in matchups

    def test_darius_matchup_loads(self, registry):
        m = registry.get_matchup("tryndamere", "darius", "TOP")
        assert m is not None
        assert m.champion == "tryndamere"
        assert m.enemy == "darius"
        assert m.difficulty == "hard"

    def test_teemo_matchup_loads(self, registry):
        m = registry.get_matchup("tryndamere", "teemo", "TOP")
        assert m is not None
        assert m.difficulty == "hard"

    def test_garen_matchup_loads(self, registry):
        m = registry.get_matchup("tryndamere", "garen", "TOP")
        assert m is not None
        assert m.difficulty == "medium"

    def test_unknown_matchup_returns_none(self, registry):
        m = registry.get_matchup("tryndamere", "unknownchampxyz", "TOP")
        assert m is None

    def test_matchup_exists(self, registry):
        assert registry.matchup_exists("tryndamere", "darius") is True
        assert registry.matchup_exists("tryndamere", "unknownxyz") is False

    def test_matchup_cache(self, registry):
        first = registry.get_matchup("tryndamere", "darius", "TOP")
        second = registry.get_matchup("tryndamere", "darius", "TOP")
        assert first is second


# ── Validator ─────────────────────────────────────────────────────────────────

class TestChampionValidator:

    @pytest.fixture(scope="class")
    def validator(self, knowledge):
        return ChampionValidator(knowledge)

    def test_tryndamere_profile_is_valid(self, validator, tryndamere_profile):
        errors = validator.validate_full(tryndamere_profile)
        assert errors == [], f"Errores inesperados: {errors}"

    def test_missing_champion_slug(self, validator, tryndamere_profile):
        import copy
        bad = copy.copy(tryndamere_profile)
        bad.champion = ""
        errors = validator.validate_full(bad)
        assert any("champion" in e for e in errors)

    def test_missing_ability(self, validator, tryndamere_profile):
        import copy
        bad = copy.copy(tryndamere_profile)
        abilities = dict(tryndamere_profile.abilities)
        del abilities["R"]
        bad.abilities = abilities
        errors = validator.validate_full(bad)
        assert any("'R'" in e for e in errors)

    def test_invalid_build_id(self, validator, tryndamere_profile):
        import copy
        from backend.game_intelligence.models.champion import ChampionBuildConfig
        bad = copy.copy(tryndamere_profile)
        bad.build_config = ChampionBuildConfig(standard_build_id="nonexistent_build_xyz")
        errors = validator.validate_full(bad)
        assert any("standard_build_id" in e for e in errors)

    def test_invalid_rune_page_id(self, validator, tryndamere_profile):
        import copy
        from backend.game_intelligence.models.champion import ChampionRuneConfig
        bad = copy.copy(tryndamere_profile)
        bad.rune_config = ChampionRuneConfig(standard_page_id="nonexistent_page_xyz")
        errors = validator.validate_full(bad)
        assert any("standard_page_id" in e for e in errors)

    def test_invalid_wave_technique(self, validator, tryndamere_profile):
        import copy
        from backend.game_intelligence.models.champion import ChampionWaveConfig
        bad = copy.copy(tryndamere_profile)
        bad.wave_config = ChampionWaveConfig(preferred_technique_ids=["nonexistent_wave"])
        errors = validator.validate_full(bad)
        assert any("wave_config" in e for e in errors)

    def test_invalid_macro_pattern(self, validator, tryndamere_profile):
        import copy
        from backend.game_intelligence.models.champion import ChampionMacroConfig
        bad = copy.copy(tryndamere_profile)
        bad.macro_config = ChampionMacroConfig(
            primary_pattern_ids=["nonexistent_pattern"],
            win_condition_ids=["split_and_win"],
        )
        errors = validator.validate_full(bad)
        assert any("macro_config" in e for e in errors)

    def test_duplicate_combo_id(self, validator, tryndamere_profile):
        import copy
        from backend.game_intelligence.models.champion import Combo
        bad = copy.copy(tryndamere_profile)
        dup_combo = Combo(
            id="basic_trade",  # ID duplicado del perfil
            name="Duplicado",
            sequence=["AA"],
            description="desc",
            when_to_use="siempre",
            difficulty="basic",
        )
        bad.combos = list(tryndamere_profile.combos) + [dup_combo]
        errors = validator.validate_full(bad)
        assert any("duplicado" in e.lower() for e in errors)

    def test_no_combos(self, validator, tryndamere_profile):
        import copy
        bad = copy.copy(tryndamere_profile)
        bad.combos = []
        errors = validator.validate_full(bad)
        assert any("combos" in e for e in errors)


# ── Coverage ──────────────────────────────────────────────────────────────────

class TestCoverageReport:

    def test_tryndamere_coverage(self, registry, knowledge):
        validator = ChampionValidator(knowledge)
        report = build_coverage_report("tryndamere", registry, validator)
        assert report.champion == "tryndamere"
        assert report.has_profile is True
        assert report.has_all_abilities is True
        assert report.has_combos is True
        assert report.has_power_spikes is True
        assert report.has_build_config is True
        assert report.has_rune_config is True
        assert report.has_wave_config is True
        assert report.has_macro_config is True
        assert report.has_learning_roadmap is True
        assert report.has_strengths is True
        assert report.has_weaknesses is True
        assert report.has_common_mistakes is True
        assert report.has_tips is True

    def test_tryndamere_overall_pct_high(self, registry):
        report = build_coverage_report("tryndamere", registry)
        # Tryndamere es el Gold Standard — debe tener >= 90%
        assert report.overall_pct >= 90.0, f"Solo {report.overall_pct}% de cobertura"

    def test_tryndamere_matchups_count(self, registry):
        report = build_coverage_report("tryndamere", registry)
        assert report.matchups_count >= 3

    def test_tryndamere_animation_cancels(self, registry):
        report = build_coverage_report("tryndamere", registry)
        assert report.animation_cancels_count >= 1

    def test_tryndamere_no_validation_errors(self, registry, knowledge):
        validator = ChampionValidator(knowledge)
        report = build_coverage_report("tryndamere", registry, validator)
        assert report.validation_errors == [], f"Errores: {report.validation_errors}"

    def test_unknown_champion_coverage_zero(self, registry):
        report = build_coverage_report("unknownchampxyz", registry)
        assert report.has_profile is False
        assert report.overall_pct == 0.0

    def test_coverage_report_recomputes_pct_on_init(self):
        # overall_pct se calcula en __post_init__
        r = CoverageReport(champion="test", has_profile=False)
        assert r.overall_pct == 0.0

        r2 = CoverageReport(
            champion="test",
            has_profile=True,
            has_all_abilities=True,
            has_combos=True,
            has_power_spikes=True,
            has_build_config=True,
            has_rune_config=True,
        )
        assert r2.overall_pct > 0.0


# ── ChampionIntelligenceEngine ────────────────────────────────────────────────

class TestChampionIntelligenceEngine:

    def test_no_matches_returns_analysis(self, engine):
        result = engine.analyze("tryndamere", "TOP", [])
        assert isinstance(result, ChampionAnalysis)
        assert result.confidence == "insufficient"
        assert result.games_analyzed == 0

    def test_no_matches_has_profile_flag(self, engine):
        result = engine.analyze("tryndamere", "TOP", [])
        assert result.has_profile is True

    def test_no_matches_unknown_champion(self, engine):
        result = engine.analyze("unknownchampxyz", "TOP", [])
        assert result.has_profile is False

    def test_few_matches_confidence_insufficient(self, engine, matches_few):
        result = engine.analyze("tryndamere", "TOP", matches_few)
        # 3 partidas < 5 → insufficient
        assert result.confidence == "insufficient"

    def test_medium_matches_confidence_low(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        assert result.confidence == "low"

    def test_high_matches_confidence_high(self, engine, matches_high):
        result = engine.analyze("tryndamere", "TOP", matches_high)
        assert result.confidence == "high"

    def test_analysis_has_profile_true(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        assert result.has_profile is True

    def test_analysis_champion_and_role(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        assert result.champion == "tryndamere"
        assert result.role == "TOP"

    def test_analysis_has_wave_priorities(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        assert len(result.wave_priorities) > 0
        assert "crash" in result.wave_priorities

    def test_analysis_has_macro_priorities(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        assert "split_push" in result.macro_priorities

    def test_analysis_has_build_recommendation(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        assert result.build_recommendation == "tryndamere_standard_crit"

    def test_analysis_has_rune_recommendation(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        assert result.rune_recommendation == "lethal_tempo_crit"

    def test_analysis_has_power_spikes(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        assert len(result.power_spikes) >= 2

    def test_analysis_games_analyzed(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        assert result.games_analyzed == 10

    def test_live_coach_hints(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        lc = result.live_coach
        assert isinstance(lc, LiveCoachHints)
        assert lc.current_objective != ""
        assert lc.recommended_build_id == "tryndamere_standard_crit"
        assert lc.recommended_rune_page_id == "lethal_tempo_crit"

    def test_live_coach_split_push_objective(self, engine, matches_medium):
        result = engine.analyze("tryndamere", "TOP", matches_medium)
        assert "split" in result.live_coach.current_objective.lower()

    def test_detect_mistakes_bad_stats(self, engine, matches_bad_stats):
        result = engine.analyze("tryndamere", "TOP", matches_bad_stats)
        assert len(result.detected_mistakes) > 0
        # Con 8 muertes promedio y 3.5 CS/min debería detectar ambos problemas
        severities = [m.severity for m in result.detected_mistakes]
        assert "high" in severities

    def test_detect_deaths_mistake(self, engine, matches_bad_stats):
        result = engine.analyze("tryndamere", "TOP", matches_bad_stats)
        texts = [m.mistake_text.lower() for m in result.detected_mistakes]
        # Debe detectar deaths issue (8 muertes avg > 5)
        assert any("morir" in t or "muerte" in t or "muertes" in t for t in texts)

    def test_detect_cs_mistake(self, engine, matches_bad_stats):
        result = engine.analyze("tryndamere", "TOP", matches_bad_stats)
        texts = [m.mistake_text.lower() for m in result.detected_mistakes]
        # Debe detectar CS bajo (3.5 < 5.0)
        assert any("cs" in t for t in texts)

    def test_focus_areas_populated(self, engine, matches_bad_stats):
        result = engine.analyze("tryndamere", "TOP", matches_bad_stats)
        assert len(result.focus_areas) > 0

    def test_max_mistakes_limit(self, engine, matches_bad_stats):
        result = engine.analyze("tryndamere", "TOP", matches_bad_stats)
        assert len(result.detected_mistakes) <= 5

    def test_no_profile_champion(self, engine, matches_medium):
        result = engine.analyze("unknownchampxyz", "TOP", matches_medium)
        assert result.has_profile is False
        assert result.champion == "unknownchampxyz"
        # Sin perfil: focus básico por stats
        assert isinstance(result.focus_areas, list)

    def test_case_insensitive_champion(self, engine, matches_medium):
        r1 = engine.analyze("Tryndamere", "TOP", matches_medium)
        r2 = engine.analyze("TRYNDAMERE", "TOP", matches_medium)
        assert r1.has_profile is True
        assert r2.has_profile is True

    def test_winrate_positive_strengths(self, engine, matches_high):
        # matches_high todos son wins → winrate 100% → strengths realizadas
        result = engine.analyze("tryndamere", "TOP", matches_high)
        assert len(result.strengths_realized) > 0


# ── Integración KnowledgeAPI ──────────────────────────────────────────────────

class TestKnowledgeAPIIntegration:

    def test_knowledge_champion_registry_works(self, knowledge):
        profile = knowledge.champion.get("tryndamere")
        assert profile is not None

    def test_knowledge_wave_registry_referenced_by_profile(self, knowledge, tryndamere_profile):
        for tech_id in tryndamere_profile.wave_config.preferred_technique_ids:
            wave = knowledge.wave.get(tech_id)
            assert wave is not None, f"Técnica '{tech_id}' no encontrada en WaveRegistry"

    def test_knowledge_macro_patterns_referenced_by_profile(self, knowledge, tryndamere_profile):
        for pattern_id in tryndamere_profile.macro_config.primary_pattern_ids:
            pattern = knowledge.macro.get(pattern_id)
            assert pattern is not None, f"Patrón '{pattern_id}' no encontrado en MacroRegistry"

    def test_knowledge_win_condition_referenced_by_profile(self, knowledge, tryndamere_profile):
        for wc_id in tryndamere_profile.macro_config.win_condition_ids:
            wc = knowledge.macro.get_win_condition(wc_id)
            assert wc is not None, f"Win condition '{wc_id}' no encontrada en MacroRegistry"

    def test_knowledge_build_referenced_by_profile(self, knowledge, tryndamere_profile):
        build = knowledge.item.get_build(tryndamere_profile.build_config.standard_build_id)
        assert build is not None

    def test_knowledge_rune_page_referenced_by_profile(self, knowledge, tryndamere_profile):
        page = knowledge.rune.get(tryndamere_profile.rune_config.standard_page_id)
        assert page is not None

    def test_warm_all_includes_champion(self, knowledge):
        result = knowledge.warm_all()
        assert "champion" in result


# ── Modelos de análisis ───────────────────────────────────────────────────────

class TestAnalysisModels:

    def test_champion_analysis_defaults(self):
        a = ChampionAnalysis(champion="tryndamere", role="TOP")
        assert a.has_profile is False
        assert a.confidence == "insufficient"
        assert a.games_analyzed == 0
        assert a.detected_mistakes == []
        assert a.focus_areas == []
        assert a.power_spikes == []

    def test_live_coach_hints_defaults(self):
        lc = LiveCoachHints()
        assert lc.current_objective == ""
        assert lc.next_power_spike is None
        assert lc.reminders == []

    def test_detected_mistake_severity(self):
        dm = DetectedMistake(mistake_text="test", severity="high", games_observed=5)
        assert dm.severity == "high"
        assert dm.games_observed == 5

    def test_detected_mistake_defaults(self):
        dm = DetectedMistake(mistake_text="test")
        assert dm.severity == "medium"
        assert dm.games_observed == 0
        assert dm.evidence == ""
