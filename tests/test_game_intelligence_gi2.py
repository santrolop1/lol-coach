"""
Tests del Sprint GI-2 — Knowledge Foundation.

Verifica:
- Todos los registries cargan correctamente
- Cache funciona (warm / invalidate / reload)
- Validación detecta errores correctamente
- Búsqueda por key devuelve el objeto esperado
- IDs inexistentes devuelven None
- list_available() devuelve la lista correcta
- KnowledgeAPI tiene todos los dominios GI-2
- warm_all() carga todos los dominios
- Sin imports circulares
- Sin regresiones de GI-1
"""

import pytest


# ── Imports GI-2 ─────────────────────────────────────────────────────────────

def test_gi2_all_registries_importable():
    from backend.game_intelligence.registries import (
        WaveRegistry, MacroRegistry, ItemRegistry,
        RuneRegistry, ObjectiveRegistry, VisionRegistry,
    )
    assert WaveRegistry is not None
    assert MacroRegistry is not None
    assert ItemRegistry is not None
    assert RuneRegistry is not None
    assert ObjectiveRegistry is not None
    assert VisionRegistry is not None


def test_gi2_new_models_importable():
    from backend.game_intelligence.models import (
        ObjectiveDefinition, ObjectiveTiming, ObjectivePriority,
        ObjectiveType, DragonType, Priority,
        WardSpot, VisionPattern, WardType, VisionZone, VisionPurpose,
    )
    assert ObjectiveDefinition is not None
    assert WardSpot is not None


def test_gi2_no_circular_imports():
    import backend.game_intelligence.registries.wave_registry
    import backend.game_intelligence.registries.macro_registry
    import backend.game_intelligence.registries.item_registry
    import backend.game_intelligence.registries.rune_registry
    import backend.game_intelligence.registries.objective_registry
    import backend.game_intelligence.registries.vision_registry
    import backend.game_intelligence.knowledge.wave.strategies
    import backend.game_intelligence.knowledge.macro.patterns
    import backend.game_intelligence.knowledge.macro.win_conditions
    import backend.game_intelligence.knowledge.items.definitions
    import backend.game_intelligence.knowledge.items.builds
    import backend.game_intelligence.knowledge.runes.trees
    import backend.game_intelligence.knowledge.runes.pages
    import backend.game_intelligence.knowledge.objectives.definitions
    import backend.game_intelligence.knowledge.vision.ward_spots
    import backend.game_intelligence.knowledge.vision.patterns


# ── BaseRegistry: invalidate_cache / reload ───────────────────────────────────

def test_base_registry_invalidate_cache():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    reg.warm_cache()
    assert len(reg._cache) > 0
    reg.invalidate_cache()
    assert len(reg._cache) == 0


def test_base_registry_reload():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    result = reg.reload()
    assert result["loaded"] > 0
    assert result["errors"] == 0


# ── WaveRegistry ──────────────────────────────────────────────────────────────

def test_wave_registry_list_available():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    available = reg.list_available()
    assert "freeze" in available
    assert "slow_push" in available
    assert "fast_push" in available
    assert "bounce" in available
    assert "crash" in available
    assert "reset" in available
    assert len(available) == 6


def test_wave_registry_get_freeze():
    from backend.game_intelligence.registries import WaveRegistry
    from backend.game_intelligence.models import WaveTechnique

    reg = WaveRegistry()
    strategy = reg.get("freeze")
    assert strategy is not None
    assert strategy.id == "freeze"
    assert strategy.technique == WaveTechnique.FREEZE
    assert len(strategy.steps) > 0
    assert len(strategy.common_mistakes) > 0


def test_wave_registry_get_all_strategies():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    for sid in reg.list_available():
        s = reg.get(sid)
        assert s is not None, f"WaveStrategy '{sid}' devolvió None"
        assert s.id == sid


def test_wave_registry_get_nonexistent():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    result = reg.get("tecnica_que_no_existe_xyz")
    assert result is None


def test_wave_registry_exists():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    assert reg.exists("freeze") is True
    assert reg.exists("no_existe") is False


def test_wave_registry_cache_hit():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    s1 = reg.get("freeze")
    s2 = reg.get("freeze")
    assert s1 is s2  # mismo objeto del cache


def test_wave_registry_warm_cache():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    result = reg.warm_cache()
    assert result["loaded"] == 6
    assert result["errors"] == 0


def test_wave_registry_validate_valid():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    strategy = reg.get("freeze")
    errors = reg.validate(strategy)
    assert errors == []


def test_wave_registry_validate_invalid():
    from backend.game_intelligence.registries import WaveRegistry
    from backend.game_intelligence.models import WaveStrategy, WaveTechnique

    reg = WaveRegistry()
    bad = WaveStrategy(
        id="",                    # ← inválido
        name="",                  # ← inválido
        technique=WaveTechnique.FREEZE,
        description="",           # ← inválido
        when_to_use="",
        when_not_to_use="",
        why="",                   # ← inválido
    )
    errors = reg.validate(bad)
    assert len(errors) >= 4


def test_wave_registry_reload():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    reg.warm_cache()
    result = reg.reload()
    assert result["loaded"] == 6


# ── MacroRegistry ─────────────────────────────────────────────────────────────

def test_macro_registry_list_available():
    from backend.game_intelligence.registries import MacroRegistry

    reg = MacroRegistry()
    patterns = reg.list_available()
    assert "split_push" in patterns
    assert "rotation" in patterns
    assert "recall_timing" in patterns
    assert len(patterns) >= 7


def test_macro_registry_get_split_push():
    from backend.game_intelligence.registries import MacroRegistry

    reg = MacroRegistry()
    pattern = reg.get("split_push")
    assert pattern is not None
    assert pattern.id == "split_push"
    assert len(pattern.steps) > 0
    assert pattern.anti_pattern


def test_macro_registry_get_nonexistent():
    from backend.game_intelligence.registries import MacroRegistry

    reg = MacroRegistry()
    assert reg.get("patron_inexistente_xyz") is None


def test_macro_registry_win_conditions():
    from backend.game_intelligence.registries import MacroRegistry

    reg = MacroRegistry()
    wc_ids = reg.list_win_conditions()
    assert "split_and_win" in wc_ids
    assert "teamfight_and_win" in wc_ids
    assert len(wc_ids) >= 3


def test_macro_registry_get_win_condition():
    from backend.game_intelligence.registries import MacroRegistry

    reg = MacroRegistry()
    wc = reg.get_win_condition("split_and_win")
    assert wc is not None
    assert wc.id == "split_and_win"
    assert len(wc.macro_steps) > 0
    assert len(wc.failure_modes) > 0


def test_macro_registry_validate_valid_pattern():
    from backend.game_intelligence.registries import MacroRegistry

    reg = MacroRegistry()
    pattern = reg.get("split_push")
    errors = reg.validate(pattern)
    assert errors == []


def test_macro_registry_warm_cache():
    from backend.game_intelligence.registries import MacroRegistry

    reg = MacroRegistry()
    result = reg.warm_cache()
    assert result["loaded"] >= 10  # 7+ patrones + 4 win conditions
    assert result["errors"] == 0


# ── ItemRegistry ──────────────────────────────────────────────────────────────

def test_item_registry_list_available():
    from backend.game_intelligence.registries import ItemRegistry

    reg = ItemRegistry()
    items = reg.list_available()
    assert "trinity_force" in items
    assert "phantom_dancer" in items
    assert "plated_steelcaps" in items
    assert len(items) >= 15


def test_item_registry_get_trinity_force():
    from backend.game_intelligence.registries import ItemRegistry

    reg = ItemRegistry()
    item = reg.get("trinity_force")
    assert item is not None
    assert item.id == "trinity_force"
    assert item.cost > 0
    assert item.when_to_buy


def test_item_registry_get_nonexistent():
    from backend.game_intelligence.registries import ItemRegistry

    reg = ItemRegistry()
    assert reg.get("item_que_no_existe_xyz") is None


def test_item_registry_builds():
    from backend.game_intelligence.registries import ItemRegistry

    reg = ItemRegistry()
    builds = reg.list_builds()
    assert "tryndamere_standard_crit" in builds
    assert len(builds) >= 3


def test_item_registry_get_build():
    from backend.game_intelligence.registries import ItemRegistry

    reg = ItemRegistry()
    build = reg.get_build("tryndamere_standard_crit")
    assert build is not None
    assert build.id == "tryndamere_standard_crit"
    assert len(build.core) >= 3


def test_item_registry_validate_valid():
    from backend.game_intelligence.registries import ItemRegistry

    reg = ItemRegistry()
    item = reg.get("trinity_force")
    errors = reg.validate(item)
    assert errors == []


def test_item_registry_validate_invalid():
    from backend.game_intelligence.registries import ItemRegistry
    from backend.game_intelligence.models.item import ItemDefinition

    reg = ItemRegistry()
    bad = ItemDefinition(id="", name="", cost=0, description="", when_to_buy="")
    errors = reg.validate(bad)
    assert len(errors) >= 3


def test_item_registry_warm_cache():
    from backend.game_intelligence.registries import ItemRegistry

    reg = ItemRegistry()
    result = reg.warm_cache()
    assert result["loaded"] >= 18  # 15+ items + 3+ builds
    assert result["errors"] == 0


# ── RuneRegistry ──────────────────────────────────────────────────────────────

def test_rune_registry_list_trees():
    from backend.game_intelligence.registries import RuneRegistry

    reg = RuneRegistry()
    trees = reg.list_trees()
    assert "precision" in trees
    assert "domination" in trees
    assert "resolve" in trees
    assert "sorcery" in trees
    assert "inspiration" in trees
    assert len(trees) == 5


def test_rune_registry_get_tree():
    from backend.game_intelligence.registries import RuneRegistry

    reg = RuneRegistry()
    tree = reg.get_tree("precision")
    assert tree is not None
    assert tree.id == "precision"
    assert tree.description


def test_rune_registry_list_pages():
    from backend.game_intelligence.registries import RuneRegistry

    reg = RuneRegistry()
    pages = reg.list_available()
    assert "conqueror_standard" in pages
    assert "lethal_tempo_crit" in pages
    assert len(pages) >= 6


def test_rune_registry_get_page():
    from backend.game_intelligence.registries import RuneRegistry

    reg = RuneRegistry()
    page = reg.get("conqueror_standard")
    assert page is not None
    assert page.primary_keystone == "conqueror"
    assert len(page.primary_slots) == 3


def test_rune_registry_pages_by_keystone():
    from backend.game_intelligence.registries import RuneRegistry

    reg = RuneRegistry()
    pages = reg.pages_by_keystone("grasp_of_the_undying")
    assert len(pages) >= 2
    for p in pages:
        assert p.primary_keystone == "grasp_of_the_undying"


def test_rune_registry_validate_valid():
    from backend.game_intelligence.registries import RuneRegistry

    reg = RuneRegistry()
    page = reg.get("conqueror_standard")
    errors = reg.validate(page)
    assert errors == []


def test_rune_registry_warm_cache():
    from backend.game_intelligence.registries import RuneRegistry

    reg = RuneRegistry()
    result = reg.warm_cache()
    assert result["loaded"] >= 13  # 5 trees + 8 pages
    assert result["errors"] == 0


# ── ObjectiveRegistry ─────────────────────────────────────────────────────────

def test_objective_registry_list_available():
    from backend.game_intelligence.registries import ObjectiveRegistry

    reg = ObjectiveRegistry()
    ids = reg.list_available()
    assert "baron" in ids
    assert "herald" in ids
    assert "dragon_soul" in ids
    assert len(ids) >= 4


def test_objective_registry_get_baron():
    from backend.game_intelligence.registries import ObjectiveRegistry
    from backend.game_intelligence.models import ObjectiveType, Priority

    reg = ObjectiveRegistry()
    baron = reg.get("baron")
    assert baron is not None
    assert baron.type == ObjectiveType.BARON
    assert baron.priority == Priority.CRITICAL
    assert baron.timing.spawn_minutes == 20.0
    assert len(baron.requirements) > 0
    assert len(baron.tips) > 0


def test_objective_registry_by_type():
    from backend.game_intelligence.registries import ObjectiveRegistry
    from backend.game_intelligence.models import ObjectiveType

    reg = ObjectiveRegistry()
    towers = reg.by_type(ObjectiveType.TOWER)
    assert len(towers) >= 1
    for t in towers:
        assert t.type == ObjectiveType.TOWER


def test_objective_registry_by_priority():
    from backend.game_intelligence.registries import ObjectiveRegistry
    from backend.game_intelligence.models import Priority

    reg = ObjectiveRegistry()
    critical = reg.by_priority(Priority.CRITICAL)
    assert len(critical) >= 2  # baron + dragon_soul
    for obj in critical:
        assert obj.priority == Priority.CRITICAL


def test_objective_registry_validate_valid():
    from backend.game_intelligence.registries import ObjectiveRegistry

    reg = ObjectiveRegistry()
    baron = reg.get("baron")
    errors = reg.validate(baron)
    assert errors == []


def test_objective_registry_validate_invalid():
    from backend.game_intelligence.registries import ObjectiveRegistry
    from backend.game_intelligence.models import ObjectiveDefinition, ObjectiveType, Priority

    reg = ObjectiveRegistry()
    bad = ObjectiveDefinition(
        id="",
        name="",
        type=ObjectiveType.BARON,
        priority=Priority.CRITICAL,
        description="",
        reward="",
    )
    errors = reg.validate(bad)
    assert len(errors) >= 3


def test_objective_registry_warm_cache():
    from backend.game_intelligence.registries import ObjectiveRegistry

    reg = ObjectiveRegistry()
    result = reg.warm_cache()
    assert result["loaded"] >= 4
    assert result["errors"] == 0


# ── VisionRegistry ────────────────────────────────────────────────────────────

def test_vision_registry_list_spots():
    from backend.game_intelligence.registries import VisionRegistry

    reg = VisionRegistry()
    spots = reg.list_available()
    assert "baron_entrance_top" in spots
    assert "dragon_entrance_bot" in spots
    assert "river_top_tribrush" in spots
    assert len(spots) >= 7


def test_vision_registry_get_spot():
    from backend.game_intelligence.registries import VisionRegistry
    from backend.game_intelligence.models import VisionZone, VisionPurpose, WardType

    reg = VisionRegistry()
    spot = reg.get("baron_entrance_top")
    assert spot is not None
    assert spot.zone == VisionZone.BARON_PIT
    assert spot.purpose == VisionPurpose.OBJECTIVE
    assert spot.ward_type == WardType.STEALTH
    assert len(spot.timing_minutes) > 0


def test_vision_registry_list_patterns():
    from backend.game_intelligence.registries import VisionRegistry

    reg = VisionRegistry()
    patterns = reg.list_patterns()
    assert "pre_objective_control" in patterns
    assert "early_lane_defense" in patterns
    assert len(patterns) >= 2


def test_vision_registry_get_pattern():
    from backend.game_intelligence.registries import VisionRegistry

    reg = VisionRegistry()
    pattern = reg.get_pattern("pre_objective_control")
    assert pattern is not None
    assert len(pattern.steps) > 0
    assert len(pattern.ward_spot_ids) > 0


def test_vision_registry_spots_by_zone():
    from backend.game_intelligence.registries import VisionRegistry
    from backend.game_intelligence.models import VisionZone

    reg = VisionRegistry()
    baron_spots = reg.spots_by_zone(VisionZone.BARON_PIT)
    assert len(baron_spots) >= 2
    for s in baron_spots:
        assert s.zone == VisionZone.BARON_PIT


def test_vision_registry_spots_by_purpose():
    from backend.game_intelligence.registries import VisionRegistry
    from backend.game_intelligence.models import VisionPurpose

    reg = VisionRegistry()
    defensive = reg.spots_by_purpose(VisionPurpose.DEFENSIVE)
    assert len(defensive) >= 3
    for s in defensive:
        assert s.purpose == VisionPurpose.DEFENSIVE


def test_vision_registry_validate_valid():
    from backend.game_intelligence.registries import VisionRegistry

    reg = VisionRegistry()
    spot = reg.get("baron_entrance_top")
    errors = reg.validate(spot)
    assert errors == []


def test_vision_registry_warm_cache():
    from backend.game_intelligence.registries import VisionRegistry

    reg = VisionRegistry()
    result = reg.warm_cache()
    assert result["loaded"] >= 10  # 7+ spots + 3 patrones
    assert result["errors"] == 0


# ── KnowledgeAPI GI-2 ────────────────────────────────────────────────────────

def test_knowledge_api_has_all_gi2_registries():
    from backend.game_intelligence.registries import KnowledgeAPI

    api = KnowledgeAPI()
    assert hasattr(api, "champion")
    assert hasattr(api, "wave")
    assert hasattr(api, "macro")
    assert hasattr(api, "item")
    assert hasattr(api, "rune")
    assert hasattr(api, "objective")
    assert hasattr(api, "vision")


def test_knowledge_api_wave_access():
    from backend.game_intelligence.registries import KnowledgeAPI

    api = KnowledgeAPI()
    freeze = api.wave.get("freeze")
    assert freeze is not None
    assert freeze.id == "freeze"


def test_knowledge_api_macro_access():
    from backend.game_intelligence.registries import KnowledgeAPI

    api = KnowledgeAPI()
    pattern = api.macro.get("split_push")
    assert pattern is not None


def test_knowledge_api_item_access():
    from backend.game_intelligence.registries import KnowledgeAPI

    api = KnowledgeAPI()
    item = api.item.get("trinity_force")
    assert item is not None
    assert item.cost > 0


def test_knowledge_api_rune_access():
    from backend.game_intelligence.registries import KnowledgeAPI

    api = KnowledgeAPI()
    page = api.rune.get("conqueror_standard")
    assert page is not None


def test_knowledge_api_objective_access():
    from backend.game_intelligence.registries import KnowledgeAPI

    api = KnowledgeAPI()
    baron = api.objective.get("baron")
    assert baron is not None


def test_knowledge_api_vision_access():
    from backend.game_intelligence.registries import KnowledgeAPI

    api = KnowledgeAPI()
    spot = api.vision.get("pixel_bush_bot")
    assert spot is not None


def test_knowledge_api_warm_all_gi2():
    from backend.game_intelligence.registries import KnowledgeAPI

    api = KnowledgeAPI()
    result = api.warm_all()

    expected_domains = ["champion", "wave", "macro", "item", "rune", "objective", "vision"]
    for domain in expected_domains:
        assert domain in result, f"'{domain}' no está en warm_all()"
        assert "loaded" in result[domain], f"'{domain}' no tiene clave 'loaded'"
        assert result[domain]["errors"] == 0, f"'{domain}' tiene errores: {result[domain]}"

    assert result["wave"]["loaded"] == 6
    assert result["macro"]["loaded"] >= 10
    assert result["item"]["loaded"] >= 18
    assert result["rune"]["loaded"] >= 13
    assert result["objective"]["loaded"] >= 4
    assert result["vision"]["loaded"] >= 10


def test_knowledge_api_singleton_has_gi2():
    from backend.game_intelligence.registries import knowledge

    assert hasattr(knowledge, "wave")
    assert hasattr(knowledge, "macro")
    assert hasattr(knowledge, "item")
    assert hasattr(knowledge, "rune")
    assert hasattr(knowledge, "objective")
    assert hasattr(knowledge, "vision")
    # Verificar que el singleton sirve datos reales
    assert knowledge.wave.get("crash") is not None
    assert knowledge.objective.get("baron") is not None


# ── Datos de conocimiento ─────────────────────────────────────────────────────

def test_wave_strategy_has_complete_data():
    from backend.game_intelligence.registries import WaveRegistry

    reg = WaveRegistry()
    for sid in reg.list_available():
        s = reg.get(sid)
        assert s.id, f"'{sid}' sin id"
        assert s.name, f"'{sid}' sin name"
        assert s.description, f"'{sid}' sin description"
        assert s.when_to_use, f"'{sid}' sin when_to_use"
        assert s.when_not_to_use, f"'{sid}' sin when_not_to_use"
        assert s.why, f"'{sid}' sin why"


def test_macro_patterns_have_roles():
    from backend.game_intelligence.registries import MacroRegistry

    reg = MacroRegistry()
    for pid in reg.list_available():
        p = reg.get(pid)
        assert len(p.applies_to_roles) > 0, f"'{pid}' sin applies_to_roles"


def test_items_have_positive_cost():
    from backend.game_intelligence.registries import ItemRegistry

    reg = ItemRegistry()
    for iid in reg.list_available():
        item = reg.get(iid)
        assert item.cost > 0, f"'{iid}' tiene cost <= 0"


def test_rune_pages_have_primary_keystone():
    from backend.game_intelligence.registries import RuneRegistry

    reg = RuneRegistry()
    for pid in reg.list_available():
        page = reg.get(pid)
        assert page.primary_keystone, f"'{pid}' sin primary_keystone"
        assert page.when_to_use, f"'{pid}' sin when_to_use"


def test_objectives_have_timing():
    from backend.game_intelligence.registries import ObjectiveRegistry

    reg = ObjectiveRegistry()
    baron = reg.get("baron")
    assert baron.timing.spawn_minutes == 20.0
    assert baron.timing.respawn_minutes == 6.0
    assert baron.timing.ideal_attempt_window


def test_vision_spots_have_timing():
    from backend.game_intelligence.registries import VisionRegistry

    reg = VisionRegistry()
    for sid in reg.list_available():
        spot = reg.get(sid)
        assert len(spot.timing_minutes) > 0, f"'{sid}' sin timing_minutes"
        assert len(spot.role_priority) > 0, f"'{sid}' sin role_priority"
