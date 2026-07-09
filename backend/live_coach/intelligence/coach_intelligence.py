"""
CoachIntelligence — facade que orquesta los 5 motores de inteligencia.

Entrada:  LiveSession + ChampionProfile (opcional) + CoachMode
Salida:   CoachInsight (snapshot completo del estado del coach)

Cada llamada a compute() actualiza el estado de la máquina de estados
y las misiones activas. El resto de motores son stateless.
"""

from __future__ import annotations
from .models import CoachInsight, CoachMode
from .context_engine import ContextEngine
from .state_machine import CoachStateMachine
from .objective_engine import ObjectiveEngine
from .mission_engine import MissionEngine
from .timeline_engine import TimelineEngine
from .recommendation_engine import RecommendationEngine


class CoachIntelligence:
    """
    Orquestador de los 5 motores de inteligencia.

    Es stateful porque mantiene CoachStateMachine y MissionEngine.
    Debe vivir mientras dure la sesión de juego.
    """

    def __init__(self, mode: CoachMode = CoachMode.INTERMEDIATE) -> None:
        self._mode = mode
        self._context_engine = ContextEngine()
        self._state_machine = CoachStateMachine()
        self._objective_engine = ObjectiveEngine()
        self._mission_engine = MissionEngine()
        self._timeline_engine = TimelineEngine()
        self._recommendation_engine = RecommendationEngine()

    @property
    def mode(self) -> CoachMode:
        return self._mode

    def set_mode(self, mode: CoachMode) -> None:
        self._mode = mode

    def compute(self, session, profile=None) -> CoachInsight:
        """
        Produce un CoachInsight a partir de la sesión live actual.

        Args:
            session: LiveSession — snapshot del estado de partida
            profile: ChampionProfile | None — perfil del campeón activo

        Returns:
            CoachInsight — snapshot inmutable para consumo del LiveCoach
        """
        # 1. Interpretar la sesión en contexto semántico
        ctx = self._context_engine.compute(session, profile=profile, mode=self._mode)

        # 2. Transicionar el estado del coach
        state = self._state_machine.transition(ctx)

        # 3. Determinar el objetivo principal
        objective = self._objective_engine.compute(ctx, state, profile=profile)

        # 4. Actualizar/seleccionar misión activa
        mission = self._mission_engine.tick(ctx, state, profile=profile)

        # 5. Generar timeline
        timeline = self._timeline_engine.compute(ctx, profile=profile)

        # 6. Generar recomendaciones
        recommendations = self._recommendation_engine.compute(ctx, state, profile=profile)

        return CoachInsight(
            context=ctx,
            state=state,
            objective=objective,
            mission=mission,
            timeline=timeline,
            recommendations=recommendations,
            coach_mode=self._mode,
        )

    def reset(self) -> None:
        """Reinicia el estado para una nueva partida."""
        self._state_machine.reset()
        self._mission_engine.reset()
