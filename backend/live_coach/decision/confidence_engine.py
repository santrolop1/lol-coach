"""
ConfidenceEngine — calcula la confianza (0.0–1.0) de cada decisión candidata.

La confianza mide cuánto respalda el contexto actual a una decisión.
No es la misma que la prioridad — una decisión puede ser urgente
pero tener confianza baja si el contexto no la apoya del todo.

Reglas:
  - No usa IA
  - Todo basado en reglas deterministas
  - Stateless — produce un float por llamada
"""

from __future__ import annotations
from .models import Decision, DecisionType
from backend.live_coach.intelligence.models import GameContext, CoachState, GamePhase


class ConfidenceEngine:
    """
    Calcula la confianza de una decisión dado el contexto actual.
    """

    def compute(
        self,
        decision: Decision,
        ctx: GameContext,
        state: CoachState,
    ) -> float:
        """
        Returns:
            float en [0.0, 1.0] — mayor = más respaldo del contexto.
        """
        base = self._base_confidence(decision.type, ctx, state)
        modifiers = self._modifiers(decision.type, ctx, state)
        raw = base + modifiers
        return round(max(0.0, min(1.0, raw)), 3)

    # ── Base por tipo ─────────────────────────────────────────────────────────

    def _base_confidence(
        self,
        dtype: DecisionType,
        ctx: GameContext,
        state: CoachState,
    ) -> float:
        match dtype:
            case DecisionType.EMERGENCY:
                # Alta confianza si realmente hay peligro
                if ctx.is_dead or ctx.is_low_hp:
                    return 0.95
                return 0.40

            case DecisionType.RETREAT:
                if ctx.is_low_hp:
                    return 0.90
                return 0.30

            case DecisionType.RECALL:
                if ctx.is_recall_window:
                    return 0.85
                if ctx.player_gold >= 800:
                    return 0.50
                return 0.20

            case DecisionType.POWER_SPIKE:
                if ctx.is_power_spike_window:
                    return 0.88
                return 0.15

            case DecisionType.OBJECTIVE:
                if ctx.is_objective_window:
                    return 0.82
                return 0.20

            case DecisionType.TRADE:
                if ctx.phase == GamePhase.LANE_PHASE and not ctx.is_low_hp and not ctx.is_dead:
                    return 0.60
                return 0.25

            case DecisionType.ALL_IN:
                if ctx.is_power_spike_window and not ctx.is_low_hp:
                    return 0.75
                return 0.20

            case DecisionType.FREEZE:
                if ctx.phase == GamePhase.LANE_PHASE and not ctx.has_first_item:
                    return 0.65
                return 0.30

            case DecisionType.CRASH:
                if ctx.is_recall_window:
                    return 0.80
                if ctx.phase in (GamePhase.LANE_PHASE, GamePhase.MID_GAME):
                    return 0.55
                return 0.25

            case DecisionType.SLOW_PUSH:
                if ctx.phase == GamePhase.LANE_PHASE:
                    return 0.55
                return 0.25

            case DecisionType.SPLIT_PUSH:
                if ctx.has_two_items and ctx.phase in (GamePhase.MID_GAME, GamePhase.LATE_GAME):
                    return 0.75
                return 0.35

            case DecisionType.TEAMFIGHT:
                if ctx.phase in (GamePhase.MID_GAME, GamePhase.LATE_GAME):
                    return 0.60
                return 0.25

            case DecisionType.ROTATE:
                if ctx.is_objective_window:
                    return 0.65
                return 0.30

            case DecisionType.WARD:
                if ctx.phase == GamePhase.LANE_PHASE and ctx.game_time_minutes > 3.0:
                    return 0.55
                return 0.30

            case DecisionType.FARM:
                if ctx.phase in (GamePhase.EARLY, GamePhase.LANE_PHASE):
                    return 0.70
                return 0.40

            case DecisionType.WAIT:
                if ctx.is_dead:
                    return 0.95
                return 0.20

            case DecisionType.TRAINING:
                return 0.50

            case DecisionType.BUILD:
                return 0.40

            case _:
                return 0.30

    # ── Modificadores contextuales ────────────────────────────────────────────

    def _modifiers(
        self,
        dtype: DecisionType,
        ctx: GameContext,
        state: CoachState,
    ) -> float:
        mod = 0.0

        # Si el jugador está muerto, solo WAIT es relevante
        if ctx.is_dead and dtype != DecisionType.WAIT:
            mod -= 0.70

        # CS bajo penaliza todo lo que no sea FARM o CRASH
        if ctx.cs_per_min < 4.0 and dtype not in (
            DecisionType.FARM, DecisionType.FREEZE, DecisionType.CRASH,
            DecisionType.SLOW_PUSH, DecisionType.EMERGENCY, DecisionType.WAIT,
        ):
            mod -= 0.10

        # Power spike activo refuerza decisiones ofensivas
        if ctx.is_power_spike_window and dtype in (DecisionType.TRADE, DecisionType.ALL_IN):
            mod += 0.15

        # Recall window refuerza RECALL y CRASH
        if ctx.is_recall_window and dtype in (DecisionType.RECALL, DecisionType.CRASH):
            mod += 0.10

        # Objetivo activo refuerza OBJECTIVE y ROTATE, penaliza FARM
        if ctx.is_objective_window and dtype == DecisionType.FARM:
            mod -= 0.15
        if ctx.is_objective_window and dtype in (DecisionType.OBJECTIVE, DecisionType.ROTATE):
            mod += 0.10

        # Vida baja refuerza EMERGENCY y RETREAT
        if ctx.is_low_hp and dtype in (DecisionType.TRADE, DecisionType.ALL_IN, DecisionType.SPLIT_PUSH):
            mod -= 0.25

        # Late game refuerza SPLIT_PUSH y TEAMFIGHT
        if ctx.phase == GamePhase.LATE_GAME and dtype in (DecisionType.SPLIT_PUSH, DecisionType.TEAMFIGHT):
            mod += 0.10

        return mod
