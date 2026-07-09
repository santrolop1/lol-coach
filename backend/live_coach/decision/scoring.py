"""
DecisionScorer — combina prioridad, confianza y contexto en una puntuación compuesta.

El score es el criterio de ranking entre candidatos en el ConflictResolver.
Todos los pesos vienen de la DecisionPolicy activa — nada hardcodeado.

score = w_priority   * normalized_priority
      + w_confidence * confidence
      + w_context    * context_score
      + w_mission    * mission_score
      + w_timeline   * timeline_score

Rango final: [0.0, 1.0]
"""

from __future__ import annotations
from .models import Decision, DecisionType, DecisionCandidate, ABSOLUTE_PRIORITY
from .policies import DecisionPolicy
from backend.live_coach.intelligence.models import (
    GameContext, CoachState, GamePhase, Mission, TimelineEvent,
)

_MAX_PRIORITY = max(ABSOLUTE_PRIORITY.values())  # 100


class DecisionScorer:
    """
    Calcula el score compuesto de un candidato.
    Stateless.
    """

    def score(
        self,
        candidate: DecisionCandidate,
        ctx: GameContext,
        state: CoachState,
        policy: DecisionPolicy,
        mission: "Mission | None" = None,
        next_timeline: "TimelineEvent | None" = None,
    ) -> float:
        """
        Returns:
            float en [0.0, 1.0] — mayor = mejor decisión ahora mismo.
        """
        d = candidate.decision
        p = policy

        # Aplicar factor de agresividad a candidatos ofensivos
        agg_boost = 0.0
        if d.type in (DecisionType.TRADE, DecisionType.ALL_IN) and p.aggression_factor != 1.0:
            agg_boost = (p.aggression_factor - 1.0) * 0.15

        s_priority   = (d.priority / _MAX_PRIORITY) * p.w_priority
        s_confidence = d.confidence * p.w_confidence
        s_context    = self._context_score(d, ctx, state) * p.w_context
        s_mission    = self._mission_score(d, mission) * p.w_mission
        s_timeline   = self._timeline_score(d, next_timeline) * p.w_timeline

        raw = s_priority + s_confidence + s_context + s_mission + s_timeline + agg_boost
        return round(min(1.0, max(0.0, raw)), 4)

    # ── Factores ──────────────────────────────────────────────────────────────

    def _context_score(
        self,
        d: Decision,
        ctx: GameContext,
        state: CoachState,
    ) -> float:
        """Cuánto respalda el contexto actual este tipo de decisión."""
        score = 0.5  # neutral

        # Alineación con el estado del coach
        STATE_AFFINITY: dict[CoachState, set[DecisionType]] = {
            CoachState.DEAD:             {DecisionType.WAIT},
            CoachState.RECALL_WINDOW:    {DecisionType.RECALL, DecisionType.CRASH},
            CoachState.POWER_SPIKE:      {DecisionType.TRADE, DecisionType.ALL_IN, DecisionType.POWER_SPIKE},
            CoachState.OBJECTIVE_WINDOW: {DecisionType.OBJECTIVE, DecisionType.ROTATE, DecisionType.SPLIT_PUSH},
            CoachState.SPLIT_PUSH:       {DecisionType.SPLIT_PUSH, DecisionType.CRASH},
            CoachState.LATE_GAME:        {DecisionType.SPLIT_PUSH, DecisionType.TEAMFIGHT},
            CoachState.LANE_PHASE:       {DecisionType.FARM, DecisionType.FREEZE, DecisionType.CRASH, DecisionType.SLOW_PUSH, DecisionType.WARD},
            CoachState.LEVEL_1:          {DecisionType.FARM, DecisionType.WAIT},
        }
        affinity = STATE_AFFINITY.get(state, set())
        if d.type in affinity:
            score += 0.30

        # Penalizar si el contexto contradice la decisión
        if ctx.is_low_hp and d.type in (DecisionType.TRADE, DecisionType.ALL_IN, DecisionType.SPLIT_PUSH):
            score -= 0.40
        if ctx.is_dead and d.type != DecisionType.WAIT:
            score -= 0.90
        if not ctx.is_objective_window and d.type == DecisionType.OBJECTIVE:
            score -= 0.30
        if not ctx.is_recall_window and d.type == DecisionType.RECALL:
            score -= 0.20
        if not ctx.is_power_spike_window and d.type == DecisionType.POWER_SPIKE:
            score -= 0.30

        return max(0.0, min(1.0, score))

    def _mission_score(
        self,
        d: Decision,
        mission: "Mission | None",
    ) -> float:
        """Qué tan compatible es la decisión con la misión activa."""
        if mission is None or not mission.is_active:
            return 0.5  # neutral

        # Misión de no-morir: penalizar decisiones arriesgadas
        if mission.id in ("no_deaths_early", "deaths_limit"):
            if d.type in (DecisionType.TRADE, DecisionType.ALL_IN, DecisionType.TEAMFIGHT):
                return 0.1
            if d.type in (DecisionType.FARM, DecisionType.FREEZE, DecisionType.RETREAT, DecisionType.WAIT):
                return 0.9
            return 0.6

        # Misión de CS: reforzar farming
        if mission.id in ("cs_target",):
            if d.type in (DecisionType.FARM, DecisionType.FREEZE, DecisionType.CRASH, DecisionType.SLOW_PUSH):
                return 0.9
            if d.type in (DecisionType.RECALL,):
                return 0.5  # recall interrumpe el farm pero es necesario
            return 0.4

        # Misión de sobrevivir hasta spike: conservador
        if mission.id == "survive_to_spike":
            if d.type in (DecisionType.FARM, DecisionType.FREEZE, DecisionType.WAIT):
                return 0.85
            if d.type in (DecisionType.TRADE, DecisionType.ALL_IN):
                return 0.15
            return 0.5

        return 0.5  # neutral para misiones desconocidas

    def _timeline_score(
        self,
        d: Decision,
        next_event: "TimelineEvent | None",
    ) -> float:
        """Qué tan alineada está la decisión con el próximo evento de timeline."""
        if next_event is None:
            return 0.5

        # Mapear tipo de evento a tipos de decisión afines
        EVENT_AFFINITY: dict[str, set[DecisionType]] = {
            "recall":      {DecisionType.RECALL, DecisionType.CRASH},
            "objective":   {DecisionType.OBJECTIVE, DecisionType.ROTATE},
            "power_spike": {DecisionType.POWER_SPIKE, DecisionType.TRADE, DecisionType.ALL_IN},
            "macro":       {DecisionType.SPLIT_PUSH, DecisionType.ROTATE, DecisionType.FARM},
        }
        affinity = EVENT_AFFINITY.get(next_event.type, set())
        if d.type in affinity:
            # Mayor score si el evento está próximo (menos de 1 minuto)
            minutes_away = next_event.time_minutes - 0  # se calcula desde el contexto
            return 0.85 if minutes_away <= 1.0 else 0.70

        return 0.40
