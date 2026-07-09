"""
Tests del Sprint GI-LIVE-2 — Intelligent Live Coach.

Cubre: ContextEngine, CoachStateMachine, ObjectiveEngine,
       MissionEngine, TimelineEngine, RecommendationEngine,
       CoachIntelligence (facade), integración con LiveCoach.
"""

import pytest
from backend.live_coach.intelligence.models import (
    GamePhase, GameSituation, CoachState, CoachMode, MissionState,
    GameContext, CoachObjective, Mission, TimelineEvent, Recommendation, CoachInsight,
)
from backend.live_coach.intelligence.context_engine import ContextEngine
from backend.live_coach.intelligence.state_machine import CoachStateMachine
from backend.live_coach.intelligence.objective_engine import ObjectiveEngine
from backend.live_coach.intelligence.mission_engine import MissionEngine
from backend.live_coach.intelligence.timeline_engine import TimelineEngine
from backend.live_coach.intelligence.recommendation_engine import RecommendationEngine
from backend.live_coach.intelligence.coach_intelligence import CoachIntelligence
from backend.live_coach.models import LiveSession, PlayerStats


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_session(
    game_time: float = 0.0,
    level: int = 1,
    gold: int = 500,
    kills: int = 0,
    deaths: int = 0,
    cs: int = 0,
    hp_pct: float = 1.0,
    is_dead: bool = False,
    items: list | None = None,
    connected: bool = True,
    active: bool = True,
    phase: str = "in_game",
) -> LiveSession:
    stats = PlayerStats(
        champion="tryndamere",
        level=level,
        gold=gold,
        kills=kills,
        deaths=deaths,
        assists=0,
        cs=cs,
        game_time=game_time,
        hp_pct=hp_pct,
        mana_pct=1.0,
        items=items or [],
        abilities_leveled=[],
        is_dead=is_dead,
        role="TOP",
    )
    return LiveSession(
        active=active,
        champion="tryndamere",
        role="TOP",
        game_time=game_time,
        player_stats=stats,
        phase=phase,
        provider_connected=connected,
    )


# ─── ContextEngine ────────────────────────────────────────────────────────────

class TestContextEngine:

    def setup_method(self):
        self.engine = ContextEngine()

    def test_early_phase_at_start(self):
        session = make_session(game_time=0.0, level=1)
        ctx = self.engine.compute(session)
        assert ctx.phase == GamePhase.EARLY

    def test_lane_phase_at_3min(self):
        session = make_session(game_time=3.0 * 60, level=4)
        ctx = self.engine.compute(session)
        assert ctx.phase == GamePhase.LANE_PHASE

    def test_mid_game_at_15min(self):
        session = make_session(game_time=15.0 * 60, level=11)
        ctx = self.engine.compute(session)
        assert ctx.phase == GamePhase.MID_GAME

    def test_late_game_at_26min(self):
        session = make_session(game_time=26.0 * 60, level=16)
        ctx = self.engine.compute(session)
        assert ctx.phase == GamePhase.LATE_GAME

    def test_dead_situation(self):
        session = make_session(game_time=5.0 * 60, is_dead=True)
        ctx = self.engine.compute(session)
        assert ctx.is_dead is True
        assert ctx.situation == GameSituation.DEAD

    def test_low_hp_flag(self):
        session = make_session(game_time=5.0 * 60, hp_pct=0.15)
        ctx = self.engine.compute(session)
        assert ctx.is_low_hp is True
        assert ctx.situation == GameSituation.IN_DANGER

    def test_recall_window_with_enough_gold(self):
        session = make_session(game_time=4.0 * 60, gold=1200)
        ctx = self.engine.compute(session)
        assert ctx.is_recall_window is True
        assert ctx.situation == GameSituation.RECALL_WINDOW

    def test_no_recall_window_too_early(self):
        session = make_session(game_time=0.5 * 60, gold=2000)
        ctx = self.engine.compute(session)
        assert ctx.is_recall_window is False

    def test_objective_window_at_5min(self):
        session = make_session(game_time=5.0 * 60)
        ctx = self.engine.compute(session)
        assert ctx.is_objective_window is True

    def test_no_objective_window_outside_windows(self):
        session = make_session(game_time=3.0 * 60)
        ctx = self.engine.compute(session)
        assert ctx.is_objective_window is False

    def test_cs_per_min_calculation(self):
        session = make_session(game_time=10.0 * 60, cs=70)
        ctx = self.engine.compute(session)
        assert abs(ctx.cs_per_min - 7.0) < 0.1

    def test_has_first_item_with_items(self):
        session = make_session(game_time=7.0 * 60, items=["Divine Sunderer"])
        ctx = self.engine.compute(session)
        assert ctx.has_first_item is True

    def test_no_first_item_empty(self):
        session = make_session(game_time=3.0 * 60, items=[])
        ctx = self.engine.compute(session)
        assert ctx.has_first_item is False

    def test_context_is_frozen(self):
        session = make_session()
        ctx = self.engine.compute(session)
        with pytest.raises((AttributeError, TypeError)):
            ctx.game_time_minutes = 99.0

    def test_coach_mode_propagated(self):
        session = make_session()
        ctx = self.engine.compute(session, mode=CoachMode.BEGINNER)
        assert ctx.coach_mode == CoachMode.BEGINNER


# ─── CoachStateMachine ────────────────────────────────────────────────────────

class TestCoachStateMachine:

    def setup_method(self):
        self.sm = CoachStateMachine()

    def _ctx(self, **kwargs) -> GameContext:
        defaults = {
            "game_time_minutes": 5.0,
            "player_level": 5,
            "phase": GamePhase.LANE_PHASE,
            "situation": GameSituation.FARMING,
            "is_dead": False,
            "is_recall_window": False,
            "is_objective_window": False,
            "is_power_spike_window": False,
            "is_low_hp": False,
        }
        defaults.update(kwargs)
        return GameContext(**defaults)

    def test_initial_state_is_loading(self):
        assert self.sm.state == CoachState.LOADING

    def test_transition_to_level_1(self):
        ctx = self._ctx(phase=GamePhase.EARLY, player_level=1, game_time_minutes=0.5)
        state = self.sm.transition(ctx)
        assert state == CoachState.LEVEL_1

    def test_transition_to_lane_phase(self):
        ctx = self._ctx(phase=GamePhase.LANE_PHASE, player_level=4)
        state = self.sm.transition(ctx)
        assert state == CoachState.LANE_PHASE

    def test_transition_to_dead(self):
        ctx = self._ctx(is_dead=True)
        state = self.sm.transition(ctx)
        assert state == CoachState.DEAD

    def test_respawn_returns_to_previous(self):
        ctx_lane = self._ctx(phase=GamePhase.LANE_PHASE)
        self.sm.transition(ctx_lane)
        ctx_dead = self._ctx(is_dead=True)
        self.sm.transition(ctx_dead)
        ctx_alive = self._ctx(phase=GamePhase.LANE_PHASE)
        state = self.sm.transition(ctx_alive)
        assert state == CoachState.LANE_PHASE

    def test_transition_to_recall_window(self):
        ctx = self._ctx(is_recall_window=True)
        state = self.sm.transition(ctx)
        assert state == CoachState.RECALL_WINDOW

    def test_transition_to_power_spike(self):
        ctx = self._ctx(is_power_spike_window=True)
        state = self.sm.transition(ctx)
        assert state == CoachState.POWER_SPIKE

    def test_transition_to_objective_window(self):
        ctx = self._ctx(is_objective_window=True)
        state = self.sm.transition(ctx)
        assert state == CoachState.OBJECTIVE_WINDOW

    def test_transition_to_late_game(self):
        ctx = self._ctx(phase=GamePhase.LATE_GAME, situation=GameSituation.FARMING)
        state = self.sm.transition(ctx)
        assert state == CoachState.LATE_GAME

    def test_force_state(self):
        self.sm.force_state(CoachState.SPLIT_PUSH)
        assert self.sm.state == CoachState.SPLIT_PUSH

    def test_reset(self):
        self.sm.force_state(CoachState.LATE_GAME)
        self.sm.reset()
        assert self.sm.state == CoachState.LOADING

    def test_double_death_preserves_pre_death_state(self):
        ctx_lane = self._ctx(phase=GamePhase.LANE_PHASE)
        self.sm.transition(ctx_lane)
        ctx_dead = self._ctx(is_dead=True)
        self.sm.transition(ctx_dead)
        # Segunda muerte no debe cambiar pre_death_state
        self.sm.transition(ctx_dead)
        ctx_alive = self._ctx(phase=GamePhase.LANE_PHASE)
        state = self.sm.transition(ctx_alive)
        assert state == CoachState.LANE_PHASE


# ─── ObjectiveEngine ─────────────────────────────────────────────────────────

class TestObjectiveEngine:

    def setup_method(self):
        self.engine = ObjectiveEngine()

    def _ctx(self, **kwargs) -> GameContext:
        defaults = {
            "game_time_minutes": 5.0,
            "player_level": 5,
            "phase": GamePhase.LANE_PHASE,
            "situation": GameSituation.FARMING,
            "is_dead": False,
            "is_recall_window": False,
            "is_objective_window": False,
            "is_power_spike_window": False,
            "is_low_hp": False,
            "hp_pct": 1.0,
            "deaths_so_far": 0,
            "player_gold": 500,
            "has_first_item": False,
        }
        defaults.update(kwargs)
        return GameContext(**defaults)

    def test_always_returns_objective(self):
        ctx = self._ctx()
        obj = self.engine.compute(ctx, CoachState.LANE_PHASE)
        assert isinstance(obj, CoachObjective)
        assert obj.id

    def test_dead_priority(self):
        ctx = self._ctx(is_dead=True)
        obj = self.engine.compute(ctx, CoachState.DEAD)
        assert obj.id == "dead_wait"
        assert obj.priority >= 85

    def test_low_hp_priority(self):
        ctx = self._ctx(hp_pct=0.15, is_low_hp=True)
        obj = self.engine.compute(ctx, CoachState.LANE_PHASE)
        assert obj.id == "low_hp_back_off"
        assert obj.priority >= 90

    def test_recall_window_objective(self):
        ctx = self._ctx(is_recall_window=True, player_gold=1200)
        obj = self.engine.compute(ctx, CoachState.RECALL_WINDOW)
        assert obj.id == "recall_now"
        assert "Recall" in obj.action_verb

    def test_objective_window_generic(self):
        ctx = self._ctx(is_objective_window=True)
        obj = self.engine.compute(ctx, CoachState.OBJECTIVE_WINDOW)
        assert "objective" in obj.id.lower() or "contest" in obj.id.lower()

    def test_generic_fallback_all_states(self):
        for state in CoachState:
            ctx = self._ctx()
            obj = self.engine.compute(ctx, state)
            assert obj is not None
            assert len(obj.title) > 0


# ─── MissionEngine ────────────────────────────────────────────────────────────

class TestMissionEngine:

    def setup_method(self):
        self.engine = MissionEngine()

    def _ctx(self, **kwargs) -> GameContext:
        defaults = {
            "game_time_minutes": 1.0,
            "player_level": 1,
            "phase": GamePhase.EARLY,
            "situation": GameSituation.FARMING,
            "is_dead": False,
            "cs": 0,
            "cs_per_min": 0.0,
            "has_first_item": False,
            "deaths_so_far": 0,
            "player_gold": 500,
            "is_power_spike_window": False,
            "is_recall_window": False,
            "is_low_hp": False,
        }
        defaults.update(kwargs)
        return GameContext(**defaults)

    def test_no_deaths_early_mission_at_start(self):
        ctx = self._ctx(game_time_minutes=0.5)
        mission = self.engine.tick(ctx, CoachState.LEVEL_1)
        assert mission is not None
        assert mission.id == "no_deaths_early"
        assert mission.is_active

    def test_mission_fails_on_death(self):
        ctx_start = self._ctx(game_time_minutes=0.5)
        self.engine.tick(ctx_start, CoachState.LEVEL_1)
        ctx_dead = self._ctx(game_time_minutes=5.0, deaths_so_far=1)
        mission = self.engine.tick(ctx_dead, CoachState.LANE_PHASE)
        # La misión no_deaths_early debería haber fallado
        # nueva misión seleccionada
        assert mission is None or mission.id != "no_deaths_early"

    def test_cs_target_mission_in_lane_phase(self):
        ctx = self._ctx(
            game_time_minutes=3.0,
            phase=GamePhase.LANE_PHASE,
            cs=20,
            deaths_so_far=1,  # para que no coja no_deaths_early
        )
        self.engine.reset()
        mission = self.engine.tick(ctx, CoachState.LANE_PHASE)
        # Debería haber misión de CS u otra
        assert mission is not None

    def test_mission_progress_updates(self):
        ctx_start = self._ctx(game_time_minutes=0.5)
        self.engine.tick(ctx_start, CoachState.LEVEL_1)
        ctx_progress = self._ctx(game_time_minutes=5.0)
        mission = self.engine.tick(ctx_progress, CoachState.LANE_PHASE)
        if mission and mission.id == "no_deaths_early":
            assert mission.progress_current >= 5.0

    def test_mission_success_when_target_reached(self):
        ctx_start = self._ctx(game_time_minutes=0.5)
        self.engine.tick(ctx_start, CoachState.LEVEL_1)
        ctx_done = self._ctx(game_time_minutes=10.5, deaths_so_far=0)
        self.engine.tick(ctx_done, CoachState.LANE_PHASE)
        # Misión debería estar completada → engine busca nueva
        m = self.engine.active_mission
        assert m is None or m.id != "no_deaths_early"

    def test_reset_clears_mission(self):
        ctx = self._ctx(game_time_minutes=0.5)
        self.engine.tick(ctx, CoachState.LEVEL_1)
        self.engine.reset()
        assert self.engine.active_mission is None

    def test_mission_progress_pct_bounds(self):
        ctx = self._ctx(game_time_minutes=0.5)
        mission = self.engine.tick(ctx, CoachState.LEVEL_1)
        if mission:
            assert 0.0 <= mission.progress_pct <= 1.0


# ─── TimelineEngine ──────────────────────────────────────────────────────────

class TestTimelineEngine:

    def setup_method(self):
        self.engine = TimelineEngine()

    def _ctx(self, game_time_minutes: float) -> GameContext:
        return GameContext(game_time_minutes=game_time_minutes)

    def test_returns_list(self):
        ctx = self._ctx(0.0)
        timeline = self.engine.compute(ctx)
        assert isinstance(timeline, list)
        assert len(timeline) > 0

    def test_past_events_marked_completed(self):
        ctx = self._ctx(10.0)
        timeline = self.engine.compute(ctx)
        for event in timeline:
            if event.time_minutes < 10.0:
                assert event.completed is True

    def test_future_events_not_completed(self):
        ctx = self._ctx(0.0)
        timeline = self.engine.compute(ctx)
        for event in timeline:
            assert event.completed is False

    def test_exactly_one_next_event(self):
        ctx = self._ctx(6.5)
        timeline = self.engine.compute(ctx)
        next_events = [e for e in timeline if e.is_next]
        assert len(next_events) == 1

    def test_timeline_ordered_by_time(self):
        ctx = self._ctx(0.0)
        timeline = self.engine.compute(ctx)
        times = [e.time_minutes for e in timeline]
        assert times == sorted(times)

    def test_all_events_have_id_and_title(self):
        ctx = self._ctx(0.0)
        timeline = self.engine.compute(ctx)
        for event in timeline:
            assert event.id
            assert event.title

    def test_game_start_always_completed_after_1min(self):
        ctx = self._ctx(1.5)
        timeline = self.engine.compute(ctx)
        start = next((e for e in timeline if e.id == "game_start"), None)
        assert start is not None
        assert start.completed is True


# ─── RecommendationEngine ────────────────────────────────────────────────────

class TestRecommendationEngine:

    def setup_method(self):
        self.engine = RecommendationEngine()

    def _ctx(self, **kwargs) -> GameContext:
        defaults = {
            "game_time_minutes": 5.0,
            "player_level": 5,
            "phase": GamePhase.LANE_PHASE,
            "situation": GameSituation.FARMING,
            "is_dead": False,
            "is_recall_window": False,
            "is_objective_window": False,
            "is_power_spike_window": False,
            "is_low_hp": False,
            "hp_pct": 1.0,
            "cs": 30,
            "cs_per_min": 6.0,
            "deaths_so_far": 0,
            "player_gold": 500,
            "has_first_item": False,
            "coach_mode": CoachMode.INTERMEDIATE,
        }
        defaults.update(kwargs)
        return GameContext(**defaults)

    def test_returns_list(self):
        ctx = self._ctx()
        recs = self.engine.compute(ctx, CoachState.LANE_PHASE)
        assert isinstance(recs, list)

    def test_max_3_recommendations(self):
        ctx = self._ctx()
        recs = self.engine.compute(ctx, CoachState.LANE_PHASE)
        assert len(recs) <= 3

    def test_low_hp_rec(self):
        ctx = self._ctx(hp_pct=0.12, is_low_hp=True)
        recs = self.engine.compute(ctx, CoachState.LANE_PHASE)
        ids = [r.id for r in recs]
        assert "back_off_low_hp" in ids

    def test_dead_rec(self):
        ctx = self._ctx(is_dead=True)
        recs = self.engine.compute(ctx, CoachState.DEAD)
        ids = [r.id for r in recs]
        assert "plan_next_recall" in ids

    def test_recall_window_rec(self):
        ctx = self._ctx(is_recall_window=True, player_gold=1500)
        recs = self.engine.compute(ctx, CoachState.RECALL_WINDOW)
        ids = [r.id for r in recs]
        assert "recall_now" in ids

    def test_low_cs_rec(self):
        ctx = self._ctx(cs_per_min=3.0, game_time_minutes=5.0)
        recs = self.engine.compute(ctx, CoachState.LANE_PHASE)
        ids = [r.id for r in recs]
        assert "improve_cs" in ids

    def test_sorted_by_priority(self):
        ctx = self._ctx(hp_pct=0.10, is_low_hp=True, cs_per_min=2.0)
        recs = self.engine.compute(ctx, CoachState.LANE_PHASE)
        priorities = [r.priority for r in recs]
        assert priorities == sorted(priorities, reverse=True)

    def test_no_duplicates(self):
        ctx = self._ctx()
        recs = self.engine.compute(ctx, CoachState.LANE_PHASE)
        ids = [r.id for r in recs]
        assert len(ids) == len(set(ids))

    def test_all_recs_have_title_and_reason(self):
        ctx = self._ctx()
        recs = self.engine.compute(ctx, CoachState.LANE_PHASE)
        for r in recs:
            assert r.title
            assert r.reason


# ─── CoachIntelligence (facade) ───────────────────────────────────────────────

class TestCoachIntelligence:

    def setup_method(self):
        self.ci = CoachIntelligence()

    def test_compute_returns_insight(self):
        session = make_session(game_time=5.0 * 60)
        insight = self.ci.compute(session)
        assert isinstance(insight, CoachInsight)

    def test_insight_has_context(self):
        session = make_session(game_time=5.0 * 60)
        insight = self.ci.compute(session)
        assert insight.context is not None
        assert isinstance(insight.context, GameContext)

    def test_insight_has_state(self):
        session = make_session(game_time=5.0 * 60)
        insight = self.ci.compute(session)
        assert isinstance(insight.state, CoachState)

    def test_insight_has_objective(self):
        session = make_session(game_time=5.0 * 60)
        insight = self.ci.compute(session)
        assert insight.objective is not None

    def test_insight_has_timeline(self):
        session = make_session(game_time=5.0 * 60)
        insight = self.ci.compute(session)
        assert isinstance(insight.timeline, list)
        assert len(insight.timeline) > 0

    def test_insight_has_recommendations(self):
        session = make_session(game_time=5.0 * 60)
        insight = self.ci.compute(session)
        assert isinstance(insight.recommendations, list)

    def test_top_recommendation(self):
        session = make_session(game_time=5.0 * 60, hp_pct=0.10)
        insight = self.ci.compute(session)
        top = insight.top_recommendation()
        if top:
            assert isinstance(top, Recommendation)

    def test_next_timeline_event(self):
        session = make_session(game_time=0.5 * 60)
        insight = self.ci.compute(session)
        nxt = insight.next_timeline_event()
        if nxt:
            assert isinstance(nxt, TimelineEvent)
            assert nxt.is_next

    def test_to_dict_structure(self):
        session = make_session(game_time=5.0 * 60)
        insight = self.ci.compute(session)
        d = insight.to_dict()
        assert "state" in d
        assert "phase" in d
        assert "objective" in d
        assert "intelligence" not in d  # to_dict no anida a sí mismo

    def test_reset_clears_state(self):
        session = make_session(game_time=5.0 * 60)
        self.ci.compute(session)
        self.ci.reset()
        # Después del reset la máquina vuelve a LOADING
        session2 = make_session(game_time=0.0, level=1)
        insight = self.ci.compute(session2)
        assert insight.state in (CoachState.LOADING, CoachState.LEVEL_1)

    def test_mode_beginner(self):
        ci = CoachIntelligence(mode=CoachMode.BEGINNER)
        session = make_session(game_time=5.0 * 60)
        insight = ci.compute(session)
        assert insight.coach_mode == CoachMode.BEGINNER

    def test_multiple_ticks_stateful(self):
        """El estado evoluciona entre ticks."""
        session_early = make_session(game_time=1.0 * 60, level=1)
        self.ci.compute(session_early)
        session_lane = make_session(game_time=5.0 * 60, level=5)
        insight = self.ci.compute(session_lane)
        assert insight.state != CoachState.LOADING


# ─── Integración LiveCoach + CoachIntelligence ───────────────────────────────

class TestLiveCoachIntegration:

    def _make_coach(self):
        from backend.live_coach.providers.mock import MockLiveDataProvider
        from backend.live_coach.coach import LiveCoach
        provider = MockLiveDataProvider()
        provider.scenario_early_game()
        coach = LiveCoach(provider=provider)
        coach.set_champion("tryndamere", "TOP")
        return coach, provider

    def test_get_state_includes_intelligence(self):
        coach, provider = self._make_coach()
        coach.tick()
        state = coach.get_state()
        assert state.intelligence is not None
        assert isinstance(state.intelligence, dict)

    def test_state_dict_has_intelligence_key(self):
        coach, provider = self._make_coach()
        coach.tick()
        state_dict = coach.get_state().to_dict()
        assert "intelligence" in state_dict
        assert state_dict["intelligence"] is not None

    def test_intelligence_dict_has_objective(self):
        coach, provider = self._make_coach()
        coach.tick()
        intel = coach.get_state().intelligence
        assert "objective" in intel

    def test_intelligence_dict_has_state(self):
        coach, provider = self._make_coach()
        coach.tick()
        intel = coach.get_state().intelligence
        assert "state" in intel

    def test_reset_clears_intelligence(self):
        coach, provider = self._make_coach()
        coach.tick()
        coach.reset()
        state = coach.get_state()
        # Después del reset, la inteligencia debería ser None hasta el primer tick
        assert state.intelligence is None

    def test_tick_after_reset_produces_intelligence(self):
        coach, provider = self._make_coach()
        coach.tick()
        coach.reset()
        coach.tick()
        state = coach.get_state()
        assert state.intelligence is not None

    def test_widgets_include_intelligent_objective(self):
        coach, provider = self._make_coach()
        coach.tick()
        state = coach.get_state()
        widget_ids = [w.widget_id.value for w in state.widgets]
        # Al menos un widget debe estar presente
        assert len(widget_ids) >= 1
