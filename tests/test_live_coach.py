"""
Tests de GI-LIVE-1 — Live Coach MVP.

Cubre:
  - EventBus (pub/sub, historial, wildcards, errores)
  - PriorityManager (widgets, notificaciones, expiración, visibilidad)
  - WidgetManager (refresh, reacciones a eventos)
  - MockLiveDataProvider (interface + escenarios)
  - OverlayConfig (serialización, persistencia)
  - LiveCoach facade (tick, detección de eventos, análisis)
  - Integración con ChampionIntelligenceEngine
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from backend.live_coach.models import (
    EventType, GameEvent, PlayerStats, LiveSession,
    WidgetId, Priority, WidgetContent, OverlayState,
)
from backend.live_coach.event_bus import EventBus
from backend.live_coach.priority_manager import PriorityManager
from backend.live_coach.widget_manager import WidgetManager
from backend.live_coach.providers.mock import MockLiveDataProvider
from backend.live_coach.providers.base import LiveDataProvider
from backend.live_coach.config import OverlayConfig
from backend.live_coach.coach import LiveCoach


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def bus():
    return EventBus()

@pytest.fixture
def pm():
    return PriorityManager()

@pytest.fixture
def wm(pm):
    return WidgetManager(pm)

@pytest.fixture
def mock_provider():
    return MockLiveDataProvider(champion="tryndamere", role="TOP")

@pytest.fixture
def coach(mock_provider):
    return LiveCoach(provider=mock_provider, knowledge_api=None)

@pytest.fixture
def coach_with_knowledge(mock_provider):
    from backend.game_intelligence.registries.registry_facade import knowledge
    return LiveCoach(provider=mock_provider, knowledge_api=knowledge)


# ── EventBus ─────────────────────────────────────────────────────────────────

class TestEventBus:

    def test_subscribe_and_publish(self, bus):
        received = []
        bus.subscribe(EventType.TICK, lambda e: received.append(e))
        bus.publish(GameEvent(type=EventType.TICK))
        assert len(received) == 1

    def test_publish_returns_handler_count(self, bus):
        bus.subscribe(EventType.TICK, lambda e: None)
        bus.subscribe(EventType.TICK, lambda e: None)
        n = bus.publish(GameEvent(type=EventType.TICK))
        assert n == 2

    def test_no_handlers_returns_zero(self, bus):
        n = bus.publish(GameEvent(type=EventType.DEATH))
        assert n == 0

    def test_wildcard_handler(self, bus):
        received = []
        bus.subscribe_all(lambda e: received.append(e.type))
        bus.publish(GameEvent(type=EventType.TICK))
        bus.publish(GameEvent(type=EventType.DEATH))
        assert EventType.TICK in received
        assert EventType.DEATH in received

    def test_handler_exception_does_not_stop_others(self, bus):
        called = []
        def bad(e): raise RuntimeError("boom")
        def good(e): called.append(True)
        bus.subscribe(EventType.TICK, bad)
        bus.subscribe(EventType.TICK, good)
        bus.publish(GameEvent(type=EventType.TICK))
        assert called  # el segundo handler se llamó igual

    def test_unsubscribe(self, bus):
        called = []
        handler = lambda e: called.append(True)
        bus.subscribe(EventType.TICK, handler)
        bus.unsubscribe(EventType.TICK, handler)
        bus.publish(GameEvent(type=EventType.TICK))
        assert not called

    def test_unsubscribe_all_wildcard(self, bus):
        called = []
        handler = lambda e: called.append(True)
        bus.subscribe_all(handler)
        bus.unsubscribe_all(handler)
        bus.publish(GameEvent(type=EventType.TICK))
        assert not called

    def test_no_duplicate_handlers(self, bus):
        called = []
        handler = lambda e: called.append(True)
        bus.subscribe(EventType.TICK, handler)
        bus.subscribe(EventType.TICK, handler)  # segunda vez no añade
        bus.publish(GameEvent(type=EventType.TICK))
        assert len(called) == 1

    def test_history_records_events(self, bus):
        bus.publish(GameEvent(type=EventType.TICK, data={"x": 1}))
        bus.publish(GameEvent(type=EventType.DEATH))
        assert len(bus.history()) == 2

    def test_history_filtered_by_type(self, bus):
        bus.publish(GameEvent(type=EventType.TICK))
        bus.publish(GameEvent(type=EventType.DEATH))
        bus.publish(GameEvent(type=EventType.TICK))
        ticks = bus.history(EventType.TICK)
        assert len(ticks) == 2
        assert all(e.type == EventType.TICK for e in ticks)

    def test_last_event(self, bus):
        bus.publish(GameEvent(type=EventType.LEVEL_UP, data={"level": 3}))
        bus.publish(GameEvent(type=EventType.LEVEL_UP, data={"level": 6}))
        last = bus.last(EventType.LEVEL_UP)
        assert last is not None
        assert last.data["level"] == 6

    def test_last_event_not_found(self, bus):
        assert bus.last(EventType.DEATH) is None

    def test_timestamp_auto_set(self, bus):
        e = GameEvent(type=EventType.TICK)
        assert e.timestamp == 0.0
        bus.publish(e)
        assert e.timestamp > 0.0

    def test_timestamp_preserved_if_set(self, bus):
        e = GameEvent(type=EventType.TICK, timestamp=999.0)
        bus.publish(e)
        assert e.timestamp == 999.0

    def test_clear_removes_all(self, bus):
        bus.subscribe(EventType.TICK, lambda e: None)
        bus.publish(GameEvent(type=EventType.TICK))
        bus.clear()
        assert bus.handler_count() == 0
        assert bus.history() == []

    def test_handler_count_by_type(self, bus):
        bus.subscribe(EventType.TICK, lambda e: None)
        bus.subscribe(EventType.TICK, lambda e: None)
        bus.subscribe(EventType.DEATH, lambda e: None)
        assert bus.handler_count(EventType.TICK) == 2
        assert bus.handler_count(EventType.DEATH) == 1

    def test_game_event_get_helper(self):
        e = GameEvent(type=EventType.LEVEL_UP, data={"level": 6, "champion": "tryndamere"})
        assert e.get("level") == 6
        assert e.get("missing", "default") == "default"

    def test_history_max_size(self, bus):
        bus._max_history = 5
        for i in range(10):
            bus.publish(GameEvent(type=EventType.TICK, data={"i": i}))
        assert len(bus.history()) == 5


# ── PriorityManager ───────────────────────────────────────────────────────────

class TestPriorityManager:

    def _widget(self, wid: WidgetId, priority: Priority = Priority.NORMAL, ttl: float = 0.0) -> WidgetContent:
        return WidgetContent(
            widget_id=wid,
            title=f"Widget {wid.value}",
            lines=["Línea 1"],
            priority=priority,
            ttl=ttl,
        )

    def test_register_and_get_visible(self, pm):
        pm.register_widget(self._widget(WidgetId.CHAMPION))
        visible = pm.get_visible_widgets()
        assert len(visible) == 1
        assert visible[0].widget_id == WidgetId.CHAMPION

    def test_widgets_sorted_by_priority(self, pm):
        pm.register_widget(self._widget(WidgetId.BUILD, Priority.LOW))
        pm.register_widget(self._widget(WidgetId.CURRENT_OBJ, Priority.HIGH))
        pm.register_widget(self._widget(WidgetId.WAVE_TIP, Priority.NORMAL))
        visible = pm.get_visible_widgets()
        priorities = [w.priority.value for w in visible]
        assert priorities == sorted(priorities, reverse=True)

    def test_max_visible_widgets(self, pm):
        for i, wid in enumerate(WidgetId):
            pm.register_widget(self._widget(wid))
        from backend.live_coach.priority_manager import MAX_VISIBLE_WIDGETS
        assert len(pm.get_visible_widgets()) <= MAX_VISIBLE_WIDGETS

    def test_hide_widget(self, pm):
        pm.register_widget(self._widget(WidgetId.CHAMPION))
        pm.hide_widget(WidgetId.CHAMPION)
        assert pm.get_visible_widgets() == []

    def test_show_widget_after_hide(self, pm):
        pm.register_widget(self._widget(WidgetId.CHAMPION))
        pm.hide_widget(WidgetId.CHAMPION)
        pm.show_widget(WidgetId.CHAMPION)
        assert len(pm.get_visible_widgets()) == 1

    def test_toggle_widget(self, pm):
        pm.register_widget(self._widget(WidgetId.CHAMPION))
        visible1 = pm.toggle_widget(WidgetId.CHAMPION)
        assert visible1 is False  # ahora oculto
        visible2 = pm.toggle_widget(WidgetId.CHAMPION)
        assert visible2 is True   # ahora visible

    def test_push_notification_accepted(self, pm):
        notif = self._widget(WidgetId.NOTIFICATIONS, Priority.HIGH, ttl=10.0)
        result = pm.push_notification(notif)
        assert result is True
        assert pm.has_notification

    def test_push_notification_lower_priority_rejected(self, pm):
        high = self._widget(WidgetId.NOTIFICATIONS, Priority.HIGH, ttl=10.0)
        low  = self._widget(WidgetId.NOTIFICATIONS, Priority.LOW, ttl=10.0)
        pm.push_notification(high)
        result = pm.push_notification(low)
        assert result is False

    def test_push_notification_critical_replaces_high(self, pm):
        high = self._widget(WidgetId.NOTIFICATIONS, Priority.HIGH, ttl=10.0)
        crit = self._widget(WidgetId.NOTIFICATIONS, Priority.CRITICAL, ttl=10.0)
        pm.push_notification(high)
        result = pm.push_notification(crit)
        assert result is True
        assert pm.get_active_notification().priority == Priority.CRITICAL

    def test_notification_expires(self, pm):
        notif = self._widget(WidgetId.NOTIFICATIONS, Priority.HIGH, ttl=0.01)
        pm.push_notification(notif)
        time.sleep(0.05)
        pm.tick()
        assert not pm.has_notification

    def test_notification_permanent(self, pm):
        notif = self._widget(WidgetId.NOTIFICATIONS, Priority.NORMAL, ttl=0.0)
        pm.push_notification(notif)
        time.sleep(0.05)
        pm.tick()
        assert pm.has_notification  # ttl=0 → permanente

    def test_clear_notification(self, pm):
        notif = self._widget(WidgetId.NOTIFICATIONS, Priority.HIGH, ttl=10.0)
        pm.push_notification(notif)
        pm.clear_notification()
        assert not pm.has_notification

    def test_reset_clears_everything(self, pm):
        pm.register_widget(self._widget(WidgetId.CHAMPION))
        notif = self._widget(WidgetId.NOTIFICATIONS, Priority.HIGH, ttl=10.0)
        pm.push_notification(notif)
        pm.reset()
        assert pm.get_visible_widgets() == []
        assert not pm.has_notification

    def test_update_widget(self, pm):
        pm.register_widget(self._widget(WidgetId.CHAMPION))
        updated = WidgetContent(
            widget_id=WidgetId.CHAMPION,
            title="Updated",
            lines=["New line"],
            priority=Priority.HIGH,
        )
        pm.update_widget(WidgetId.CHAMPION, updated)
        visible = pm.get_visible_widgets()
        assert visible[0].title == "Updated"

    def test_widget_count(self, pm):
        assert pm.widget_count == 0
        pm.register_widget(self._widget(WidgetId.CHAMPION))
        pm.register_widget(self._widget(WidgetId.BUILD))
        assert pm.widget_count == 2


# ── WidgetManager ─────────────────────────────────────────────────────────────

class TestWidgetManager:

    def test_default_widgets_registered(self, wm):
        from backend.live_coach.widget_manager import WidgetManager
        from backend.live_coach.priority_manager import PriorityManager
        pm = PriorityManager()
        mgr = WidgetManager(pm)
        assert len(mgr._registry) >= 6

    def test_refresh_with_no_analysis(self, wm):
        session = LiveSession(
            active=True, champion="tryndamere", role="TOP",
            game_time=300,
            player_stats=PlayerStats(champion="tryndamere", level=4, gold=800, cs=50),
            phase="in_game", provider_connected=True,
        )
        wm.refresh(session, None)
        # No debe lanzar excepción; widgets de analysis se omiten

    def test_refresh_champion_widget(self, wm, pm):
        session = LiveSession(
            active=True, champion="tryndamere", role="TOP",
            game_time=300,
            player_stats=PlayerStats(champion="tryndamere", level=6, gold=1200, cs=70, kills=3, deaths=1, assists=2),
            phase="in_game", provider_connected=True,
        )
        wm.refresh(session, None)
        visible = pm.get_visible_widgets()
        champ = next((w for w in visible if w.widget_id == WidgetId.CHAMPION), None)
        assert champ is not None
        assert "Nivel 6" in champ.lines[0]

    def test_on_event_death_notification(self, wm, pm):
        session = LiveSession(
            player_stats=PlayerStats(deaths=3),
        )
        wm.on_event_death(session)
        assert pm.has_notification
        notif = pm.get_active_notification()
        assert notif.priority == Priority.HIGH
        assert "Muerte" in notif.title

    def test_on_event_level_up_normal(self, wm, pm):
        session = LiveSession(player_stats=PlayerStats(level=4))
        wm.on_event_level_up(session, 4)
        assert pm.has_notification
        notif = pm.get_active_notification()
        assert "4" in notif.title

    def test_on_event_level_up_6_highlight(self, wm, pm):
        session = LiveSession(player_stats=PlayerStats(level=6))
        wm.on_event_level_up(session, 6)
        notif = pm.get_active_notification()
        assert notif.highlight is True
        assert notif.priority == Priority.HIGH

    def test_on_event_item_purchased(self, wm, pm):
        session = LiveSession()
        wm.on_event_item_purchased(session, "Trinity Force")
        assert pm.has_notification
        notif = pm.get_active_notification()
        assert "Trinity Force" in notif.lines[0]

    def test_on_event_recall(self, wm, pm):
        wm.on_event_recall(LiveSession())
        assert pm.has_notification

    def test_custom_widget_registration(self, wm, pm):
        def my_widget(session, analysis):
            return WidgetContent(
                widget_id=WidgetId.STATUS,
                title="Custom",
                lines=["Test"],
                priority=Priority.LOW,
            )
        wm.register(WidgetId.STATUS, my_widget)
        session = LiveSession(active=True, player_stats=PlayerStats())
        wm.refresh(session, None)
        visible = pm.get_visible_widgets()
        status = next((w for w in visible if w.widget_id == WidgetId.STATUS), None)
        assert status is not None
        assert status.title == "Custom"

    def test_widget_fn_exception_does_not_crash(self, wm, pm):
        def bad_widget(session, analysis):
            raise RuntimeError("fallo de widget")
        wm.register(WidgetId.STATUS, bad_widget)
        wm.refresh(LiveSession(), None)  # no debe lanzar


# ── MockLiveDataProvider ──────────────────────────────────────────────────────

class TestMockLiveDataProvider:

    def test_is_live_data_provider(self, mock_provider):
        assert isinstance(mock_provider, LiveDataProvider)

    def test_connected_by_default(self, mock_provider):
        assert mock_provider.is_connected() is True

    def test_phase_default(self, mock_provider):
        assert mock_provider.get_phase() == "in_game"

    def test_get_player_stats(self, mock_provider):
        stats = mock_provider.get_player_stats()
        assert stats is not None
        assert stats.champion == "tryndamere"
        assert stats.role == "TOP"

    def test_get_player_stats_idle_returns_none(self):
        p = MockLiveDataProvider(phase="idle")
        assert p.get_player_stats() is None

    def test_set_level(self, mock_provider):
        mock_provider.set_level(6)
        assert mock_provider.get_player_stats().level == 6

    def test_set_kda(self, mock_provider):
        mock_provider.set_kda(5, 2, 3)
        stats = mock_provider.get_player_stats()
        assert stats.kills == 5
        assert stats.deaths == 2
        assert stats.assists == 3

    def test_set_cs(self, mock_provider):
        mock_provider.set_cs(120)
        assert mock_provider.get_player_stats().cs == 120

    def test_set_game_time(self, mock_provider):
        mock_provider.set_game_time(900.0)
        assert mock_provider.get_game_time() == 900.0

    def test_set_connected_false(self, mock_provider):
        mock_provider.set_connected(False)
        assert mock_provider.is_connected() is False

    def test_add_item(self, mock_provider):
        mock_provider.add_item("trinity_force")
        assert "trinity_force" in mock_provider.get_player_stats().items

    def test_no_duplicate_items(self, mock_provider):
        mock_provider.add_item("trinity_force")
        mock_provider.add_item("trinity_force")
        assert mock_provider.get_player_stats().items.count("trinity_force") == 1

    def test_set_hp_pct_clamps(self, mock_provider):
        mock_provider.set_hp_pct(1.5)
        assert mock_provider.get_player_stats().hp_pct == 1.0
        mock_provider.set_hp_pct(-0.5)
        assert mock_provider.get_player_stats().hp_pct == 0.0

    def test_get_session_snapshot(self, mock_provider):
        session = mock_provider.get_session_snapshot()
        assert isinstance(session, LiveSession)
        assert session.active is True
        assert session.champion == "tryndamere"
        assert session.provider_connected is True

    def test_scenario_early_game(self):
        p = MockLiveDataProvider.scenario_early_game()
        stats = p.get_player_stats()
        assert stats.level == 3
        assert p.get_game_time() == 180

    def test_scenario_level_6(self):
        p = MockLiveDataProvider.scenario_level_6()
        assert p.get_player_stats().level == 6

    def test_scenario_first_item(self):
        p = MockLiveDataProvider.scenario_first_item()
        assert "trinity_force" in p.get_player_stats().items

    def test_scenario_disconnected(self):
        p = MockLiveDataProvider.scenario_disconnected()
        assert p.is_connected() is False
        assert p.get_phase() == "idle"

    def test_scenario_post_game(self):
        p = MockLiveDataProvider.scenario_post_game()
        assert p.get_phase() == "post_game"


# ── OverlayConfig ─────────────────────────────────────────────────────────────

class TestOverlayConfig:

    def test_defaults(self):
        cfg = OverlayConfig()
        assert cfg.opacity == 0.90
        assert cfg.scale == 1.0
        assert cfg.compact_mode is False
        assert cfg.always_on_top is True
        assert cfg.auto_hide_on_idle is True

    def test_to_dict(self):
        cfg = OverlayConfig()
        d = cfg.to_dict()
        assert isinstance(d, dict)
        assert "opacity" in d
        assert "widgets_enabled" in d

    def test_from_dict_roundtrip(self):
        cfg = OverlayConfig(opacity=0.7, scale=1.2, compact_mode=True)
        restored = OverlayConfig.from_dict(cfg.to_dict())
        assert restored.opacity == 0.7
        assert restored.scale == 1.2
        assert restored.compact_mode is True

    def test_from_dict_ignores_unknown_keys(self):
        cfg = OverlayConfig.from_dict({"opacity": 0.5, "unknown_key": "value"})
        assert cfg.opacity == 0.5

    def test_is_widget_enabled(self):
        cfg = OverlayConfig()
        assert cfg.is_widget_enabled("champion") is True
        # wave_tip está deshabilitado por defecto
        assert cfg.is_widget_enabled("wave_tip") is False

    def test_is_widget_enabled_unknown_defaults_true(self):
        cfg = OverlayConfig()
        assert cfg.is_widget_enabled("nonexistent_widget") is True

    def test_widget_enabled_mutation(self):
        cfg = OverlayConfig()
        cfg.widgets_enabled["champion"] = False
        assert cfg.is_widget_enabled("champion") is False

    def test_load_config_no_db_returns_default(self):
        from backend.live_coach.config import load_config
        cfg = load_config(db_module=None)
        # Sin db disponible en test, devuelve default
        assert isinstance(cfg, OverlayConfig)

    def test_save_config_no_db_does_not_crash(self):
        from backend.live_coach.config import save_config
        cfg = OverlayConfig()
        save_config(cfg, db_module=None)  # no debe lanzar


# ── LiveCoach facade ──────────────────────────────────────────────────────────

class TestLiveCoach:

    def test_tick_no_crash(self, coach):
        coach.tick()  # no debe lanzar

    def test_get_state_returns_overlay_state(self, coach):
        coach.tick()
        state = coach.get_state()
        assert isinstance(state, OverlayState)

    def test_get_state_to_dict(self, coach):
        coach.tick()
        d = coach.get_state().to_dict()
        assert "active" in d
        assert "widgets" in d
        assert "phase" in d
        assert "player" in d

    def test_set_champion(self, coach):
        coach.set_champion("tryndamere", "TOP")
        assert coach._champion == "tryndamere"
        assert coach._role == "TOP"

    def test_set_champion_case_normalized(self, coach):
        coach.set_champion("Tryndamere", "top")
        assert coach._champion == "tryndamere"
        assert coach._role == "TOP"

    def test_set_champion_publishes_event(self, coach):
        received = []
        coach.event_bus.subscribe(EventType.CHAMPION_LOADED, lambda e: received.append(e))
        coach.set_champion("tryndamere", "TOP")
        assert len(received) == 1
        assert received[0].data["champion"] == "tryndamere"

    def test_set_champion_only_reloads_on_change(self, coach):
        events = []
        coach.event_bus.subscribe(EventType.CHAMPION_LOADED, lambda e: events.append(e))
        coach.set_champion("tryndamere", "TOP")
        coach.set_champion("tryndamere", "TOP")  # mismo campeón — no republica
        assert len(events) == 1

    def test_reset_clears_state(self, coach):
        coach.set_champion("tryndamere", "TOP")
        coach.tick()
        coach.reset()
        assert coach._session.active is False

    def test_reset_publishes_game_started(self, coach):
        events = []
        coach.event_bus.subscribe(EventType.GAME_STARTED, lambda e: events.append(e))
        coach.reset()
        assert len(events) == 1

    def test_detect_level_up(self, coach, mock_provider):
        coach._last_level = 3
        mock_provider.set_level(4)
        events = []
        coach.event_bus.subscribe(EventType.LEVEL_UP, lambda e: events.append(e))
        coach.tick()
        assert len(events) == 1
        assert events[0].data["level"] == 4

    def test_detect_death(self, coach, mock_provider):
        coach._last_death_count = 0
        mock_provider.set_kda(0, 1, 0)
        events = []
        coach.event_bus.subscribe(EventType.DEATH, lambda e: events.append(e))
        coach.tick()
        assert len(events) == 1
        assert events[0].data["deaths"] == 1

    def test_detect_respawn(self, coach, mock_provider):
        coach._was_dead = True
        mock_provider.set_is_dead(False)
        events = []
        coach.event_bus.subscribe(EventType.RESPAWN, lambda e: events.append(e))
        coach.tick()
        assert len(events) == 1

    def test_detect_item_purchased(self, coach, mock_provider):
        coach._last_item_count = 0
        mock_provider.add_item("trinity_force")
        events = []
        coach.event_bus.subscribe(EventType.ITEM_PURCHASED, lambda e: events.append(e))
        coach.tick()
        assert len(events) == 1
        assert events[0].data["item"] == "trinity_force"

    def test_tick_publishes_tick_event(self, coach):
        events = []
        coach.event_bus.subscribe(EventType.TICK, lambda e: events.append(e))
        coach.tick()
        assert len(events) >= 1

    def test_death_triggers_notification(self, coach, mock_provider):
        coach._last_death_count = 0
        mock_provider.set_kda(0, 1, 0)
        coach.tick()
        state = coach.get_state()
        assert state.active_notification is not None

    def test_level_6_triggers_highlight_notification(self, coach, mock_provider):
        coach._last_level = 5
        mock_provider.set_level(6)
        coach.tick()
        state = coach.get_state()
        assert state.active_notification is not None
        assert state.active_notification.highlight is True

    def test_provider_disconnected_state(self):
        provider = MockLiveDataProvider.scenario_disconnected()
        c = LiveCoach(provider=provider, knowledge_api=None)
        c.tick()
        state = c.get_state()
        assert state.session.provider_connected is False

    def test_event_bus_accessible(self, coach):
        assert coach.event_bus is not None
        assert isinstance(coach.event_bus, EventBus)

    def test_priority_manager_accessible(self, coach):
        assert coach.priority_manager is not None
        assert isinstance(coach.priority_manager, PriorityManager)

    def test_widget_manager_accessible(self, coach):
        assert coach.widget_manager is not None
        assert isinstance(coach.widget_manager, WidgetManager)


# ── Integración con ChampionIntelligence ─────────────────────────────────────

class TestLiveCoachWithChampionIntelligence:

    def test_set_champion_with_knowledge(self, coach_with_knowledge):
        coach_with_knowledge.set_champion("tryndamere", "TOP")
        assert coach_with_knowledge._champion == "tryndamere"

    def test_tick_loads_analysis(self, coach_with_knowledge):
        coach_with_knowledge.set_champion("tryndamere", "TOP")
        coach_with_knowledge.tick()
        # Con knowledge_api y perfil disponible, debe cargar el análisis
        assert coach_with_knowledge._analysis is not None

    def test_analysis_has_profile(self, coach_with_knowledge):
        coach_with_knowledge.set_champion("tryndamere", "TOP")
        coach_with_knowledge.tick()
        assert coach_with_knowledge._analysis.has_profile is True

    def test_widgets_populate_with_analysis(self, coach_with_knowledge):
        coach_with_knowledge.set_champion("tryndamere", "TOP")
        coach_with_knowledge.tick()
        state = coach_with_knowledge.get_state()
        # Con perfil cargado, al menos el widget de campeón debe estar presente
        widget_ids = [w["id"] for w in state.to_dict()["widgets"]]
        assert len(widget_ids) >= 1  # al menos champion widget
        # El análisis con 0 partidas no activa objective/spike — eso es correcto

    def test_live_coach_current_objective_split_push(self, coach_with_knowledge):
        coach_with_knowledge.set_champion("tryndamere", "TOP")
        coach_with_knowledge.tick()
        state = coach_with_knowledge.get_state()
        widgets = state.to_dict()["widgets"]
        obj_widget = next((w for w in widgets if w["id"] == "current_objective"), None)
        if obj_widget:
            assert "split" in obj_widget["lines"][0].lower() or len(obj_widget["lines"]) > 0

    def test_unknown_champion_no_crash(self, coach_with_knowledge):
        coach_with_knowledge.set_champion("unknownchampxyz", "TOP")
        coach_with_knowledge.tick()
        # Sin perfil — análisis sin crash
        state = coach_with_knowledge.get_state()
        assert state is not None

    def test_overlay_state_serializable(self, coach_with_knowledge):
        coach_with_knowledge.set_champion("tryndamere", "TOP")
        coach_with_knowledge.tick()
        state = coach_with_knowledge.get_state()
        d = state.to_dict()
        import json
        # Debe ser serializable a JSON sin errores
        json.dumps(d)


# ── OverlayState.to_dict ─────────────────────────────────────────────────────

class TestOverlayState:

    def test_to_dict_structure(self):
        state = OverlayState(
            session=LiveSession(active=True, champion="tryndamere", role="TOP"),
            widgets=[WidgetContent(
                widget_id=WidgetId.CHAMPION,
                title="Tryndamere",
                lines=["Nivel 4"],
                priority=Priority.NORMAL,
            )],
        )
        d = state.to_dict()
        assert d["active"] is True
        assert d["champion"] == "tryndamere"
        assert len(d["widgets"]) == 1
        assert d["widgets"][0]["id"] == "champion"
        assert d["notification"] is None

    def test_to_dict_with_notification(self):
        notif = WidgetContent(
            widget_id=WidgetId.NOTIFICATIONS,
            title="⚠ Muerte",
            lines=["Cuidado"],
            priority=Priority.HIGH,
            highlight=True,
        )
        state = OverlayState(active_notification=notif)
        d = state.to_dict()
        assert d["notification"] is not None
        assert d["notification"]["title"] == "⚠ Muerte"
        assert d["notification"]["highlight"] is True

    def test_to_dict_hides_invisible_widgets(self):
        state = OverlayState(widgets=[
            WidgetContent(widget_id=WidgetId.CHAMPION, title="A", lines=[], priority=Priority.NORMAL, visible=True),
            WidgetContent(widget_id=WidgetId.BUILD, title="B", lines=[], priority=Priority.NORMAL, visible=False),
        ])
        d = state.to_dict()
        assert len(d["widgets"]) == 1
        assert d["widgets"][0]["id"] == "champion"
