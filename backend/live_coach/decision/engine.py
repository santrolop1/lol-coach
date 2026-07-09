"""
DecisionEngine — cerebro central del Live Coach.

Sintetiza toda la información disponible en una única decisión priorizada.

Flujo por tick:
  1. Leer CoachInsight (ya computado por CoachIntelligence)
  2. Generar candidatos de decisión para cada situación detectada
  3. Calcular confianza para cada candidato (ConfidenceEngine)
  4. Calcular score compuesto para cada candidato (DecisionScorer)
  5. Resolver conflictos y elegir el ganador (ConflictResolver)
  6. Verificar TTL de la decisión activa (expirar si corresponde)
  7. Registrar en historial
  8. Retornar la decisión activa

Restricciones:
  - No accede a registries ni a la DB
  - No duplica cálculos: lee de CoachInsight, no recomputa
  - Todo el conocimiento del campeón viene del objetivo/misión del insight
"""

from __future__ import annotations
import time
import logging
import uuid
from .models import (
    Decision, DecisionType, DecisionCandidate, DecisionState,
    ABSOLUTE_PRIORITY,
)
from .confidence_engine import ConfidenceEngine
from .scoring import DecisionScorer
from .conflict_resolver import ConflictResolver
from .history import DecisionHistory
from .policies import DecisionPolicy, PolicyMode
from backend.live_coach.intelligence.models import (
    GameContext, CoachState, CoachInsight, GamePhase,
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Motor de decisiones. Stateful — mantiene la decisión activa entre ticks.
    """

    def __init__(self, policy: DecisionPolicy | None = None) -> None:
        self._policy = policy or DecisionPolicy.balanced()
        self._confidence = ConfidenceEngine()
        self._scorer = DecisionScorer()
        self._resolver = ConflictResolver()
        self._history = DecisionHistory(max_size=self._policy.history_size)
        self._current: Decision | None = None

    @property
    def current(self) -> Decision | None:
        return self._current if (self._current and self._current.is_active) else None

    @property
    def policy(self) -> DecisionPolicy:
        return self._policy

    @property
    def history(self) -> DecisionHistory:
        return self._history

    def set_policy(self, policy: DecisionPolicy) -> None:
        self._policy = policy
        self._history = DecisionHistory(max_size=policy.history_size)

    def decide(self, insight: CoachInsight) -> Decision | None:
        """
        Produce la mejor decisión para el instante actual.

        Args:
            insight: CoachInsight computado por CoachIntelligence en este tick

        Returns:
            Decision activa (puede ser la misma del tick anterior si no expiró)
        """
        ctx = insight.context
        state = insight.state
        mission = insight.mission
        next_event = insight.next_timeline_event()

        # Expirar la decisión actual si superó su TTL
        if self._current and self._current.is_active:
            age = self._current.age_seconds
            if age >= self._policy.max_active_seconds:
                self._history.close(self._current.id, "expired")
                self._current.expire()
                self._current = None

        # Generar candidatos
        candidates = self._generate_candidates(ctx, state, insight)

        # Calcular confianza y score para cada candidato
        for c in candidates:
            c.decision.confidence = self._confidence.compute(c.decision, ctx, state)
            c.score = self._scorer.score(c, ctx, state, self._policy, mission, next_event)

        # Elegir el ganador
        winner = self._resolver.resolve(candidates, self._policy)

        if winner is None:
            return self._current  # mantener la decisión anterior si no hay nueva

        # Verificar si es mejor que la actual (evitar flicker)
        if self._current and self._current.is_active:
            current_candidate = DecisionCandidate(decision=self._current)
            current_candidate.decision.confidence = self._confidence.compute(
                self._current, ctx, state
            )
            current_candidate.score = self._scorer.score(
                current_candidate, ctx, state, self._policy, mission, next_event
            )

            # Solo cambiar si el ganador supera en >5% de score
            # Y no es del mismo tipo (evitar recrear la misma decisión)
            if (
                winner.type != self._current.type
                and current_candidate.score + 0.05 >= DecisionCandidate(decision=winner, score=candidates[0].score if candidates else 0).score
            ):
                # La decisión actual sigue siendo buena — mantenerla
                if self._history.was_recent(self._current.type.value, within_seconds=8.0):
                    winner.cancel()
                    return self._current

        # Nueva decisión ganadora — cerrar la anterior
        if self._current and self._current.is_active:
            self._history.close(self._current.id, "superseded", winner.id)
            self._current.cancel()

        self._history.record(winner)
        self._current = winner
        return self._current

    def reset(self) -> None:
        """Reinicia el estado para una nueva partida."""
        if self._current:
            self._current.cancel()
        self._current = None

    # ── Generación de candidatos ──────────────────────────────────────────────

    def _generate_candidates(
        self,
        ctx: GameContext,
        state: CoachState,
        insight: CoachInsight,
    ) -> list[DecisionCandidate]:
        """
        Genera todos los candidatos posibles para el contexto actual.

        Cada situación genera 1 candidato del tipo más apropiado.
        El ConflictResolver elige el mejor.
        """
        candidates: list[DecisionCandidate] = []

        # ── Situaciones de emergencia (siempre primero)
        if ctx.is_dead:
            candidates.append(self._candidate_wait(ctx))
            return candidates  # nada más importa cuando estás muerto

        if ctx.is_low_hp:
            candidates.append(self._candidate_retreat(ctx))
            candidates.append(self._candidate_emergency(ctx))

        # ── Power Spike
        if ctx.is_power_spike_window:
            candidates.append(self._candidate_power_spike(ctx, insight))

        # ── Recall window
        if ctx.is_recall_window:
            candidates.append(self._candidate_recall(ctx))

        # ── Objetivo del mapa
        if ctx.is_objective_window:
            candidates.append(self._candidate_objective(ctx, insight))

        # ── Wave management (fase de carril)
        if state in (CoachState.LANE_PHASE, CoachState.LEVEL_1):
            candidates.extend(self._candidates_wave(ctx, insight))

        # ── Split push
        if state == CoachState.SPLIT_PUSH:
            candidates.append(self._candidate_split_push(ctx, insight))

        # ── Late game
        if state == CoachState.LATE_GAME:
            candidates.append(self._candidate_late_game(ctx, insight))

        # ── Teamfight
        if state == CoachState.TEAMFIGHT:
            candidates.append(self._candidate_teamfight(ctx))

        # ── Ward (recordatorio bajo prioridad)
        if ctx.phase == GamePhase.LANE_PHASE and ctx.game_time_minutes > 3.5:
            candidates.append(self._candidate_ward(ctx))

        # ── Farm (siempre disponible como fallback)
        candidates.append(self._candidate_farm(ctx, insight))

        return candidates

    # ── Constructores de candidatos ───────────────────────────────────────────

    def _mk(self, dtype: DecisionType, **kwargs) -> DecisionCandidate:
        """Helper: crea un DecisionCandidate con los campos mínimos."""
        d = Decision(
            id=str(uuid.uuid4())[:8],
            type=dtype,
            priority=ABSOLUTE_PRIORITY[dtype],
            confidence=0.0,   # se asigna después por ConfidenceEngine
            origin="decision_engine",
            **kwargs,
        )
        return DecisionCandidate(decision=d)

    def _candidate_wait(self, ctx: GameContext) -> DecisionCandidate:
        return self._mk(
            DecisionType.WAIT,
            title="Esperando respawn",
            explanation="Analiza qué salió mal mientras esperas volver a la partida.",
            action="Esperar",
            reasons=["Jugador muerto"],
            duration_seconds=20.0,
        )

    def _candidate_emergency(self, ctx: GameContext) -> DecisionCandidate:
        hp = int(ctx.hp_pct * 100)
        return self._mk(
            DecisionType.EMERGENCY,
            title=f"¡Peligro! {hp}% de vida",
            explanation="Estás en zona de peligro. Aléjate del enemigo antes de comprometerte.",
            action="Escapar",
            reasons=[f"Vida crítica: {hp}%"],
            highlight=True,
            duration_seconds=15.0,
        )

    def _candidate_retreat(self, ctx: GameContext) -> DecisionCandidate:
        hp = int(ctx.hp_pct * 100)
        return self._mk(
            DecisionType.RETREAT,
            title=f"Retroceder — {hp}% vida",
            explanation="Con poca vida eres un objetivo fácil. Cura y reorganízate.",
            action="Retroceder",
            reasons=[f"Vida baja: {hp}%"],
            duration_seconds=15.0,
        )

    def _candidate_power_spike(self, ctx: GameContext, insight: CoachInsight) -> DecisionCandidate:
        obj = insight.objective
        title = "Power Spike — actúa ahora"
        explanation = "Acabas de alcanzar un punto de poder. Busca un intercambio favorable."
        reasons = ["Ventana de Power Spike activa"]

        if obj and obj.id in ("lvl6_spike", "first_item_spike"):
            title = obj.title
            explanation = obj.description[:120]
            reasons = [obj.context]

        return self._mk(
            DecisionType.POWER_SPIKE,
            title=title,
            explanation=explanation,
            action="Presionar",
            reasons=reasons,
            champion_specific=obj is not None,
            highlight=True,
            duration_seconds=25.0,
        )

    def _candidate_recall(self, ctx: GameContext) -> DecisionCandidate:
        return self._mk(
            DecisionType.RECALL,
            title=f"Recall óptimo — {ctx.player_gold}g",
            explanation="Tienes oro suficiente. Crashea la oleada y haz recall para comprar.",
            action="Recall",
            reasons=[
                f"{ctx.player_gold}g acumulados",
                "Ventana de recall detectada",
            ],
            duration_seconds=30.0,
        )

    def _candidate_objective(self, ctx: GameContext, insight: CoachInsight) -> DecisionCandidate:
        obj = insight.objective
        split_push = obj and "split_and_win" in (obj.context or "")
        if split_push:
            return self._mk(
                DecisionType.SPLIT_PUSH,
                title="Presionar para forzar reacción",
                explanation="Hay un objetivo en el mapa. Presiona tu carril para forzar rotaciones enemigas.",
                action="Presionar",
                reasons=["Objetivo en el mapa", "Win condition: split push"],
                champion_specific=True,
                duration_seconds=30.0,
            )
        return self._mk(
            DecisionType.OBJECTIVE,
            title="Objetivo del mapa — rotar",
            explanation="Tu equipo puede pelear por un objetivo. Decide si rotas o presionas.",
            action="Rotar",
            reasons=["Ventana de objetivo activa"],
            duration_seconds=30.0,
        )

    def _candidates_wave(self, ctx: GameContext, insight: CoachInsight) -> list[DecisionCandidate]:
        obj = insight.objective
        candidates = []

        if obj and obj.id.startswith("wave_"):
            technique = obj.id.replace("wave_", "")
            TYPE_MAP = {
                "freeze": DecisionType.FREEZE,
                "crash":  DecisionType.CRASH,
                "slow_push": DecisionType.SLOW_PUSH,
                "fast_push": DecisionType.CRASH,
                "bounce": DecisionType.FREEZE,
            }
            dtype = TYPE_MAP.get(technique, DecisionType.FARM)
            candidates.append(self._mk(
                dtype,
                title=obj.title,
                explanation=obj.description[:120],
                action=obj.action_verb,
                reasons=[obj.context],
                champion_specific=True,
                duration_seconds=20.0,
            ))
        elif obj and obj.id in ("scale_farm", "farm_lane"):
            candidates.append(self._mk(
                DecisionType.FARM,
                title=obj.title,
                explanation=obj.description[:120],
                action=obj.action_verb,
                reasons=[obj.context],
                duration_seconds=20.0,
            ))
        else:
            candidates.append(self._candidate_farm(ctx, insight))

        return candidates

    def _candidate_split_push(self, ctx: GameContext, insight: CoachInsight) -> DecisionCandidate:
        obj = insight.objective
        return self._mk(
            DecisionType.SPLIT_PUSH,
            title=obj.title if obj else "Split Push — presiona estructuras",
            explanation=(obj.description[:120] if obj else "Empuja el carril lateral y amenaza estructuras."),
            action="Split Push",
            reasons=["Estado: Split Push"],
            champion_specific=obj is not None,
            duration_seconds=40.0,
        )

    def _candidate_late_game(self, ctx: GameContext, insight: CoachInsight) -> DecisionCandidate:
        obj = insight.objective
        return self._mk(
            DecisionType.SPLIT_PUSH if (obj and "split" in (obj.id or "")) else DecisionType.TEAMFIGHT,
            title=obj.title if obj else "Late Game — muévete con tu equipo",
            explanation=(obj.description[:120] if obj else "No te pierdas. Decisiones macro determinan la victoria."),
            action=obj.action_verb if obj else "Agruparse",
            reasons=["Partida en fase tardía"],
            champion_specific=obj is not None,
            duration_seconds=40.0,
        )

    def _candidate_teamfight(self, ctx: GameContext) -> DecisionCandidate:
        return self._mk(
            DecisionType.TEAMFIGHT,
            title="Pelea de equipo",
            explanation="Sigue a tu equipo. Prioriza los carries enemigos.",
            action="Pelear",
            reasons=["Estado: Teamfight"],
            duration_seconds=30.0,
        )

    def _candidate_ward(self, ctx: GameContext) -> DecisionCandidate:
        return self._mk(
            DecisionType.WARD,
            title="Ward el río",
            explanation="Sin visión del río eres vulnerable a gankeos. Coloca un ward antes del minuto 4.",
            action="Ward",
            reasons=["Sin visión del río detectada", f"Minuto {ctx.game_time_minutes:.1f}"],
            duration_seconds=20.0,
        )

    def _candidate_farm(self, ctx: GameContext, insight: CoachInsight) -> DecisionCandidate:
        obj = insight.objective
        if obj and obj.id == "scale_farm":
            return self._mk(
                DecisionType.FARM,
                title=obj.title,
                explanation=obj.description[:120],
                action="Farmear",
                reasons=["Escalar es la prioridad", f"CS: {ctx.cs}"],
                champion_specific=True,
                duration_seconds=20.0,
            )
        return self._mk(
            DecisionType.FARM,
            title="Farmear",
            explanation=f"Prioriza el CS. Tienes {ctx.cs} minions. Objetivo: 7+ CS/min.",
            action="Farmear",
            reasons=[f"CS actual: {ctx.cs}", f"CS/min: {ctx.cs_per_min:.1f}"],
            duration_seconds=20.0,
        )
