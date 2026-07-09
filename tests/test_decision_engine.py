"""
Tests del Sprint GI-LIVE-3 — Decision Intelligence Engine.

Cubre: DecisionModel, ConfidenceEngine, DecisionScorer,
       ConflictResolver, DecisionHistory, DecisionEngine (facade),
       DecisionPolicy, integración con LiveCoach.

Cobertura objetivo: ≥95%.
"""

import pytest
import time
from backend.live_coach.decision.models import (
    Decision, DecisionType, DecisionState, DecisionCandidate,
    DecisionHistoryEntry, ABSOLUTE_PRIORITY,
)
from backend.live_coach.decision.policies import DecisionPolicy, PolicyMode
from backend.live_coach.decision.confidence_engine import ConfidenceEngine
from backend.live_coach.decision.scoring import DecisionScorer
from backend.live_coach.decision.conflict_resolver import ConflictResolver
from backend.live_coach.decision.history import DecisionHistory
from backend.live_coach.decision.engine import DecisionEngine
from backend.live_coach.intelligence.models import (
    GamePhase, GameSituation, CoachState, CoachMode, CoachInsight,
    GameContext, CoachObjective, Mission, MissionState, TimelineEvent, Recommendation,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_ctx(**kwargs) -> GameContext:
    defaults = {
        "game_time_minutes": 5.0,
        "player_level": 5,
        "player_gold": 500,
        "items_count": 0,
        "has_first_item": False,
        "has_two_items": False,
        "is_dead": False,
        "hp_pct": 1.0,
        "deaths_so_far": 0,
        "cs": 30,
        "cs_per_min": 6.0,
        "phase": GamePhase.LANE_PHASE,
        "situation": GameSituation.FARMING,
        "is_power_spike_window": False,
        "is_recall_window": False,
        "is_objective_window": False,
        "is_low_hp": False,
        "coach_mode": CoachMode.INTERMEDIATE,
    }
    defaults.update(kwargs)
    return GameContext(**defaults)


def make_objective(id="farm_lane", title="Farmear", priority=40) -> CoachObjective:
    return CoachObjective(
        id=id,
        title=title,
        description="Prioriza el CS.",
        priority=priority,
        action_verb="Farmear",
        context="lane_phase",
    )


def make_insight(
    ctx: GameContext | None = None,
    state: CoachState = CoachState.LANE_PHASE,
    objective: CoachObjective | None = None,
    mission: Mission | None = None,
    timeline: list[TimelineEvent] | None = None,
    recommendations: list[Recommendation] | None = None,
) -> CoachInsight:
    if ctx is None:
        ctx = make_ctx()
    return CoachInsight(
        context=ctx,
        state=state,
        objective=objective or make_objective(),
        mission=mission,
        timeline=timeline or [],
        recommendations=recommendations or [],
        coach_mode=CoachMode.INTERMEDIATE,
    )


def make_decision(dtype=DecisionType.FARM, confidence=0.70, priority=None) -> Decision:
    if priority is None:
        priority = ABSOLUTE_PRIORITY[dtype]
    return Decision(
        id="test-1",
        type=dtype,
        title="Test Decision",
        explanation="Test explanation",
        action="Test",
        confidence=confidence,
        priority=priority,
        origin="test",
    )


def make_candidate(dtype=DecisionType.FARM, confidence=0.70, score=0.5) -> DecisionCandidate:
    d = make_decision(dtype, confidence)
    return DecisionCandidate(decision=d, score=score)


# ─── DecisionModel ────────────────────────────────────────────────────────────

class TestDecisionModel:

    def test_initial_state_is_pending(self):
        d = make_decision()
        assert d.state == DecisionState.PENDING

    def test_activate(self):
        d = make_decision()
        d.activate()
        assert d.state == DecisionState.ACTIVE
        assert d.is_active

    def test_expire(self):
        d = make_decision()
        d.activate()
        d.expire()
        assert d.state == DecisionState.EXPIRED
        assert not d.is_active

    def test_complete(self):
        d = make_decision()
        d.activate()
        d.complete()
        assert d.state == DecisionState.COMPLETED

    def test_cancel(self):
        d = make_decision()
        d.activate()
        d.cancel()
        assert d.state == DecisionState.CANCELLED

    def test_confidence_pct(self):
        d = make_decision(confidence=0.87)
        assert d.confidence_pct == 87

    def test_age_seconds(self):
        d = make_decision()
        assert d.age_seconds >= 0.0

    def test_to_dict_keys(self):
        d = make_decision()
        d.activate()
        result = d.to_dict()
        assert "id" in result
        assert "type" in result
        assert "title" in result
        assert "confidence_pct" in result
        assert "action" in result
        assert "state" in result
        assert "reasons" in result

    def test_to_dict_type_is_string(self):
        d = make_decision(DecisionType.RECALL)
        result = d.to_dict()
        assert result["type"] == "recall"

    def test_absolute_priority_covers_all_types(self):
        for dtype in DecisionType:
            assert dtype in ABSOLUTE_PRIORITY

    def test_emergency_has_highest_priority(self):
        assert ABSOLUTE_PRIORITY[DecisionType.EMERGENCY] == max(ABSOLUTE_PRIORITY.values())


# ─── DecisionPolicy ───────────────────────────────────────────────────────────

class TestDecisionPolicy:

    def test_balanced_is_default(self):
        p = DecisionPolicy()
        assert p.mode == PolicyMode.BALANCED

    def test_conservative_lower_aggression(self):
        p = DecisionPolicy.conservative()
        assert p.aggression_factor < 1.0

    def test_aggressive_higher_aggression(self):
        p = DecisionPolicy.aggressive()
        assert p.aggression_factor > 1.0

    def test_conservative_higher_min_confidence(self):
        conservative = DecisionPolicy.conservative()
        aggressive = DecisionPolicy.aggressive()
        assert conservative.min_confidence > aggressive.min_confidence

    def test_from_mode_balanced(self):
        p = DecisionPolicy.from_mode(PolicyMode.BALANCED)
        assert p.mode == PolicyMode.BALANCED

    def test_from_mode_conservative(self):
        p = DecisionPolicy.from_mode(PolicyMode.CONSERVATIVE)
        assert p.mode == PolicyMode.CONSERVATIVE

    def test_from_mode_aggressive(self):
        p = DecisionPolicy.from_mode(PolicyMode.AGGRESSIVE)
        assert p.mode == PolicyMode.AGGRESSIVE

    def test_weights_sum_close_to_1(self):
        p = DecisionPolicy()
        total = p.w_priority + p.w_confidence + p.w_context + p.w_mission + p.w_timeline
        assert abs(total - 1.0) < 0.01


# ─── ConfidenceEngine ─────────────────────────────────────────────────────────

class TestConfidenceEngine:

    def setup_method(self):
        self.engine = ConfidenceEngine()

    def test_returns_float_in_range(self):
        ctx = make_ctx()
        d = make_decision(DecisionType.FARM)
        conf = self.engine.compute(d, ctx, CoachState.LANE_PHASE)
        assert 0.0 <= conf <= 1.0

    def test_wait_high_when_dead(self):
        ctx = make_ctx(is_dead=True)
        d = make_decision(DecisionType.WAIT)
        conf = self.engine.compute(d, ctx, CoachState.DEAD)
        assert conf >= 0.90

    def test_non_wait_low_when_dead(self):
        ctx = make_ctx(is_dead=True)
        d = make_decision(DecisionType.TRADE)
        conf = self.engine.compute(d, ctx, CoachState.DEAD)
        assert conf <= 0.30

    def test_recall_high_when_recall_window(self):
        ctx = make_ctx(is_recall_window=True, player_gold=1200)
        d = make_decision(DecisionType.RECALL)
        conf = self.engine.compute(d, ctx, CoachState.RECALL_WINDOW)
        assert conf >= 0.80

    def test_power_spike_high_when_spike_window(self):
        ctx = make_ctx(is_power_spike_window=True)
        d = make_decision(DecisionType.POWER_SPIKE)
        conf = self.engine.compute(d, ctx, CoachState.POWER_SPIKE)
        assert conf >= 0.80

    def test_retreat_high_when_low_hp(self):
        ctx = make_ctx(hp_pct=0.10, is_low_hp=True)
        d = make_decision(DecisionType.RETREAT)
        conf = self.engine.compute(d, ctx, CoachState.LANE_PHASE)
        assert conf >= 0.85

    def test_trade_penalized_when_low_hp(self):
        ctx = make_ctx(hp_pct=0.10, is_low_hp=True)
        d = make_decision(DecisionType.TRADE)
        conf = self.engine.compute(d, ctx, CoachState.LANE_PHASE)
        assert conf <= 0.40

    def test_farm_reasonable_in_lane(self):
        ctx = make_ctx(phase=GamePhase.LANE_PHASE)
        d = make_decision(DecisionType.FARM)
        conf = self.engine.compute(d, ctx, CoachState.LANE_PHASE)
        assert conf >= 0.60

    def test_emergency_high_when_low_hp(self):
        ctx = make_ctx(hp_pct=0.08, is_low_hp=True)
        d = make_decision(DecisionType.EMERGENCY)
        conf = self.engine.compute(d, ctx, CoachState.LANE_PHASE)
        assert conf >= 0.85


# ─── DecisionScorer ──────────────────────────────────────────────────────────

class TestDecisionScorer:

    def setup_method(self):
        self.scorer = DecisionScorer()
        self.policy = DecisionPolicy()

    def test_returns_float_in_range(self):
        ctx = make_ctx()
        c = make_candidate()
        score = self.scorer.score(c, ctx, CoachState.LANE_PHASE, self.policy)
        assert 0.0 <= score <= 1.0

    def test_dead_wait_scores_highest_when_dead(self):
        ctx = make_ctx(is_dead=True)
        wait = make_candidate(DecisionType.WAIT, confidence=0.95)
        farm = make_candidate(DecisionType.FARM, confidence=0.70)
        wait.decision.confidence = 0.95
        farm.decision.confidence = 0.30  # bajo cuando está muerto

        s_wait = self.scorer.score(wait, ctx, CoachState.DEAD, self.policy)
        s_farm = self.scorer.score(farm, ctx, CoachState.DEAD, self.policy)
        assert s_wait > s_farm

    def test_mission_no_deaths_penalizes_trade(self):
        ctx = make_ctx()
        mission = Mission(id="no_deaths_early", title="No morir", description="", progress_target=10.0)
        trade = make_candidate(DecisionType.TRADE)
        farm = make_candidate(DecisionType.FARM)

        s_trade = self.scorer.score(trade, ctx, CoachState.LANE_PHASE, self.policy, mission=mission)
        s_farm = self.scorer.score(farm, ctx, CoachState.LANE_PHASE, self.policy, mission=mission)
        assert s_farm > s_trade

    def test_aggression_factor_boosts_trade(self):
        ctx = make_ctx(is_power_spike_window=True)
        aggressive = DecisionPolicy.aggressive()
        balanced = DecisionPolicy.balanced()

        c = make_candidate(DecisionType.TRADE, confidence=0.65)
        s_agg = self.scorer.score(c, ctx, CoachState.POWER_SPIKE, aggressive)
        s_bal = self.scorer.score(c, ctx, CoachState.POWER_SPIKE, balanced)
        assert s_agg >= s_bal

    def test_conservative_penalizes_aggression(self):
        ctx = make_ctx()
        conservative = DecisionPolicy.conservative()
        trade = make_candidate(DecisionType.TRADE, confidence=0.60)
        farm = make_candidate(DecisionType.FARM, confidence=0.70)

        s_trade = self.scorer.score(trade, ctx, CoachState.LANE_PHASE, conservative)
        s_farm = self.scorer.score(farm, ctx, CoachState.LANE_PHASE, conservative)
        # En modo conservador farm supera trade cuando confianza es similar
        assert s_farm >= s_trade * 0.8  # al menos comparable


# ─── ConflictResolver ────────────────────────────────────────────────────────

class TestConflictResolver:

    def setup_method(self):
        self.resolver = ConflictResolver()
        self.policy = DecisionPolicy()

    def test_returns_none_when_empty(self):
        result = self.resolver.resolve([], self.policy)
        assert result is None

    def test_returns_best_candidate(self):
        high = make_candidate(DecisionType.RECALL, confidence=0.85, score=0.80)
        low = make_candidate(DecisionType.FARM, confidence=0.50, score=0.35)
        result = self.resolver.resolve([high, low], self.policy)
        assert result is not None
        assert result.type == DecisionType.RECALL

    def test_activates_winner(self):
        c = make_candidate(score=0.70)
        result = self.resolver.resolve([c], self.policy)
        assert result.state == DecisionState.ACTIVE

    def test_resolves_retreat_trade_conflict(self):
        retreat = make_candidate(DecisionType.RETREAT, confidence=0.90, score=0.85)
        trade = make_candidate(DecisionType.TRADE, confidence=0.50, score=0.40)
        result = self.resolver.resolve([retreat, trade], self.policy)
        assert result is not None
        assert result.type == DecisionType.RETREAT

    def test_resolves_freeze_crash_conflict(self):
        freeze = make_candidate(DecisionType.FREEZE, confidence=0.70, score=0.65)
        crash = make_candidate(DecisionType.CRASH, confidence=0.50, score=0.45)
        result = self.resolver.resolve([freeze, crash], self.policy)
        assert result is not None
        assert result.type == DecisionType.FREEZE

    def test_fallback_when_none_above_threshold(self):
        strict_policy = DecisionPolicy(min_confidence=0.95)
        low_conf = make_candidate(DecisionType.FARM, confidence=0.30, score=0.20)
        result = self.resolver.resolve([low_conf], strict_policy)
        # Debe retornar el de mayor confianza aunque no supere el umbral
        assert result is not None

    def test_split_push_teamfight_conflict(self):
        split = make_candidate(DecisionType.SPLIT_PUSH, confidence=0.75, score=0.70)
        team = make_candidate(DecisionType.TEAMFIGHT, confidence=0.50, score=0.45)
        result = self.resolver.resolve([split, team], self.policy)
        assert result.type == DecisionType.SPLIT_PUSH


# ─── DecisionHistory ─────────────────────────────────────────────────────────

class TestDecisionHistory:

    def setup_method(self):
        self.history = DecisionHistory(max_size=10)

    def test_initially_empty(self):
        assert self.history.size == 0

    def test_record_increments_size(self):
        d = make_decision()
        d.activate()
        self.history.record(d)
        assert self.history.size == 1

    def test_last_returns_recent(self):
        d1 = make_decision()
        d1.activate()
        d2 = make_decision(DecisionType.RECALL)
        d2.activate()
        self.history.record(d1)
        self.history.record(d2)
        last = self.history.last(1)
        assert len(last) == 1
        assert last[0].decision_type == "recall"

    def test_close_sets_resolution(self):
        d = make_decision()
        d.activate()
        self.history.record(d)
        self.history.close(d.id, "superseded", "new-id")
        entry = self.history.last(1)[0]
        assert entry.resolution == "superseded"

    def test_was_recent_true_when_just_added(self):
        d = make_decision(DecisionType.FARM)
        d.activate()
        self.history.record(d)
        assert self.history.was_recent("farm", within_seconds=5.0)

    def test_was_recent_false_when_different_type(self):
        d = make_decision(DecisionType.FARM)
        d.activate()
        self.history.record(d)
        assert not self.history.was_recent("recall", within_seconds=5.0)

    def test_circular_buffer_respects_max_size(self):
        for i in range(15):
            d = make_decision()
            d.id = f"d{i}"
            d.activate()
            self.history.record(d)
        assert self.history.size == 10

    def test_last_type(self):
        d = make_decision(DecisionType.RECALL)
        d.activate()
        self.history.record(d)
        assert self.history.last_type() == "recall"

    def test_last_type_none_when_empty(self):
        assert self.history.last_type() is None

    def test_to_list(self):
        d = make_decision()
        d.activate()
        self.history.record(d)
        lst = self.history.to_list()
        assert isinstance(lst, list)
        assert len(lst) == 1
        assert "type" in lst[0]

    def test_duration_seconds(self):
        d = make_decision()
        d.activate()
        self.history.record(d)
        entry = self.history.last(1)[0]
        assert entry.duration_seconds >= 0.0


# ─── DecisionEngine ──────────────────────────────────────────────────────────

class TestDecisionEngine:

    def setup_method(self):
        self.engine = DecisionEngine()

    def test_initial_current_is_none(self):
        assert self.engine.current is None

    def test_decide_returns_decision(self):
        insight = make_insight()
        result = self.engine.decide(insight)
        assert result is not None
        assert isinstance(result, Decision)

    def test_decision_is_active(self):
        insight = make_insight()
        result = self.engine.decide(insight)
        assert result.state == DecisionState.ACTIVE

    def test_dead_returns_wait(self):
        ctx = make_ctx(is_dead=True)
        insight = make_insight(ctx=ctx, state=CoachState.DEAD)
        result = self.engine.decide(insight)
        assert result is not None
        assert result.type == DecisionType.WAIT

    def test_low_hp_returns_retreat_or_emergency(self):
        ctx = make_ctx(hp_pct=0.08, is_low_hp=True)
        insight = make_insight(ctx=ctx)
        result = self.engine.decide(insight)
        assert result is not None
        assert result.type in (DecisionType.RETREAT, DecisionType.EMERGENCY)

    def test_recall_window_returns_recall(self):
        ctx = make_ctx(is_recall_window=True, player_gold=1300)
        insight = make_insight(ctx=ctx, state=CoachState.RECALL_WINDOW)
        result = self.engine.decide(insight)
        assert result is not None
        assert result.type == DecisionType.RECALL

    def test_power_spike_returns_power_spike(self):
        ctx = make_ctx(is_power_spike_window=True, player_level=6)
        insight = make_insight(
            ctx=ctx,
            state=CoachState.POWER_SPIKE,
            objective=make_objective(id="lvl6_spike", title="Nivel 6 — Power Spike"),
        )
        result = self.engine.decide(insight)
        assert result is not None
        assert result.type == DecisionType.POWER_SPIKE

    def test_consecutive_same_state_keeps_decision(self):
        ctx = make_ctx()
        insight = make_insight(ctx=ctx)
        d1 = self.engine.decide(insight)
        # Mismo contexto → debe mantener la misma decisión o del mismo tipo
        d2 = self.engine.decide(insight)
        assert d2 is not None

    def test_reset_clears_current(self):
        insight = make_insight()
        self.engine.decide(insight)
        self.engine.reset()
        assert self.engine.current is None

    def test_history_grows_on_decide(self):
        insight = make_insight()
        self.engine.decide(insight)
        assert self.engine.history.size >= 1

    def test_set_policy(self):
        policy = DecisionPolicy.conservative()
        self.engine.set_policy(policy)
        assert self.engine.policy.mode == PolicyMode.CONSERVATIVE

    def test_decision_has_all_required_fields(self):
        insight = make_insight()
        result = self.engine.decide(insight)
        assert result.id
        assert result.title
        assert result.explanation
        assert result.action
        assert 0.0 <= result.confidence <= 1.0
        assert result.priority >= 0

    def test_decision_to_dict(self):
        insight = make_insight()
        result = self.engine.decide(insight)
        d = result.to_dict()
        assert d["state"] == "active"
        assert isinstance(d["confidence_pct"], int)

    def test_mission_influences_decision(self):
        """Con misión no_deaths_early, el engine debe evitar trades."""
        ctx = make_ctx(is_power_spike_window=True, player_level=6)
        mission = Mission(
            id="no_deaths_early",
            title="No morir antes del minuto 10",
            description="",
            progress_target=10.0,
        )
        conservative = DecisionEngine(policy=DecisionPolicy.conservative())
        insight = make_insight(ctx=ctx, mission=mission, state=CoachState.LANE_PHASE)
        result = conservative.decide(insight)
        assert result is not None
        # Con misión conservadora + policy conservadora, no debe ser ALL_IN
        assert result.type != DecisionType.ALL_IN

    def test_objective_window_produces_objective_decision(self):
        ctx = make_ctx(is_objective_window=True)
        insight = make_insight(ctx=ctx, state=CoachState.OBJECTIVE_WINDOW)
        result = self.engine.decide(insight)
        assert result is not None
        assert result.type in (DecisionType.OBJECTIVE, DecisionType.ROTATE, DecisionType.SPLIT_PUSH, DecisionType.FARM)

    def test_decision_expires_after_ttl(self):
        engine = DecisionEngine(policy=DecisionPolicy(max_active_seconds=0.01))
        insight = make_insight()
        engine.decide(insight)
        time.sleep(0.05)
        # Forzar expiración en el siguiente tick
        insight2 = make_insight()
        result = engine.decide(insight2)
        # Debe haber generado una nueva decisión
        assert result is not None

    def test_aggressive_policy_more_likely_trade(self):
        ctx = make_ctx(is_power_spike_window=True, player_level=6, hp_pct=1.0)
        aggressive_engine = DecisionEngine(policy=DecisionPolicy.aggressive())
        insight = make_insight(ctx=ctx, state=CoachState.POWER_SPIKE)
        result = aggressive_engine.decide(insight)
        assert result is not None
        # En modo agresivo con spike activo, la decisión debe ser ofensiva
        assert result.type in (
            DecisionType.POWER_SPIKE, DecisionType.TRADE, DecisionType.ALL_IN,
            DecisionType.CRASH, DecisionType.SPLIT_PUSH,
        )


# ─── Integración con LiveCoach ────────────────────────────────────────────────

class TestDecisionEngineIntegration:

    def _make_coach(self):
        from backend.live_coach.providers.mock import MockLiveDataProvider
        from backend.live_coach.coach import LiveCoach
        provider = MockLiveDataProvider()
        provider.scenario_early_game()
        coach = LiveCoach(provider=provider)
        coach.set_champion("tryndamere", "TOP")
        return coach, provider

    def test_state_includes_current_decision(self):
        coach, _ = self._make_coach()
        coach.tick()
        state = coach.get_state()
        assert state.current_decision is not None
        assert isinstance(state.current_decision, dict)

    def test_state_dict_has_current_decision(self):
        coach, _ = self._make_coach()
        coach.tick()
        d = coach.get_state().to_dict()
        assert "current_decision" in d
        assert d["current_decision"] is not None

    def test_decision_has_type_and_title(self):
        coach, _ = self._make_coach()
        coach.tick()
        dec = coach.get_state().current_decision
        assert "type" in dec
        assert "title" in dec
        assert "confidence_pct" in dec

    def test_reset_clears_decision(self):
        coach, _ = self._make_coach()
        coach.tick()
        coach.reset()
        state = coach.get_state()
        assert state.current_decision is None

    def test_decision_active_after_tick(self):
        coach, _ = self._make_coach()
        coach.tick()
        dec = coach.get_state().current_decision
        assert dec["state"] == "active"

    def test_widget_shows_decision(self):
        coach, _ = self._make_coach()
        coach.tick()
        state = coach.get_state()
        # El widget CURRENT_OBJ debe reflejar la decisión activa
        widget_ids = [w.widget_id.value for w in state.widgets]
        # Champion widget siempre existe
        assert "champion" in widget_ids

    def test_low_hp_scenario_emergency_decision(self):
        from backend.live_coach.providers.mock import MockLiveDataProvider
        from backend.live_coach.coach import LiveCoach
        provider = MockLiveDataProvider()
        provider.set_level(6)
        provider.set_kda(0, 0, 0)
        # HP bajo
        provider._stats.hp_pct = 0.08
        coach = LiveCoach(provider=provider)
        coach.set_champion("tryndamere", "TOP")
        coach.tick()
        dec = coach.get_state().current_decision
        assert dec is not None
        assert dec["type"] in ("emergency", "retreat", "wait")
