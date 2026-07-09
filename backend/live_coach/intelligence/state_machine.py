"""
CoachStateMachine — máquina de estados del Live Coach.

Estados:
  LOADING → LEVEL_1 → LANE_PHASE → [RECALL_WINDOW | POWER_SPIKE | OBJECTIVE_WINDOW]
          → SPLIT_PUSH | TEAMFIGHT → LATE_GAME → POST_GAME
  En cualquier estado → DEAD (y vuelta al estado previo al respawn)

La máquina no controla el UI — solo determina el estado semántico
que guía los demás motores.
"""

from __future__ import annotations
import logging
from .models import CoachState, GameContext, GamePhase, GameSituation

logger = logging.getLogger(__name__)


class CoachStateMachine:
    """
    Máquina de estados del coach. Stateful — mantiene el estado actual.

    El LiveCoach la mantiene viva entre ticks.
    """

    def __init__(self) -> None:
        self._state = CoachState.LOADING
        self._pre_death_state = CoachState.LANE_PHASE

    @property
    def state(self) -> CoachState:
        return self._state

    def transition(self, ctx: GameContext) -> CoachState:
        """
        Evalúa el contexto actual y transiciona si corresponde.

        Retorna el nuevo estado (o el mismo si no hay transición).
        """
        prev = self._state

        if ctx.is_dead:
            self._pre_death_state = self._state if self._state != CoachState.DEAD else self._pre_death_state
            self._state = CoachState.DEAD
        elif prev == CoachState.DEAD:
            # Respawn: volver al estado previo
            self._state = self._pre_death_state
        elif ctx.phase == GamePhase.EARLY and ctx.player_level == 1:
            self._state = CoachState.LEVEL_1
        elif ctx.phase == GamePhase.LATE_GAME:
            if ctx.situation == GameSituation.SPLIT_PUSH:
                self._state = CoachState.SPLIT_PUSH
            else:
                self._state = CoachState.LATE_GAME
        elif ctx.phase == GamePhase.MID_GAME:
            if ctx.is_objective_window:
                self._state = CoachState.OBJECTIVE_WINDOW
            elif ctx.situation == GameSituation.SPLIT_PUSH:
                self._state = CoachState.SPLIT_PUSH
            else:
                self._state = CoachState.LANE_PHASE
        elif ctx.is_power_spike_window:
            self._state = CoachState.POWER_SPIKE
        elif ctx.is_recall_window:
            self._state = CoachState.RECALL_WINDOW
        elif ctx.is_objective_window:
            self._state = CoachState.OBJECTIVE_WINDOW
        elif ctx.phase in (GamePhase.LANE_PHASE, GamePhase.EARLY):
            self._state = CoachState.LANE_PHASE
        else:
            self._state = CoachState.LOADING

        if prev != self._state:
            logger.debug("CoachState: %s → %s", prev.value, self._state.value)

        return self._state

    def force_state(self, state: CoachState) -> None:
        """Para tests y configuración manual."""
        self._state = state

    def reset(self) -> None:
        self._state = CoachState.LOADING
        self._pre_death_state = CoachState.LANE_PHASE
