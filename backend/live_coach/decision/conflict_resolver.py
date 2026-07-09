"""
ConflictResolver — elige la mejor decisión entre múltiples candidatos.

Garantiza:
  1. Nunca mostrar decisiones contradictorias
  2. Siempre mostrar una única decisión priorizada
  3. Respetar la confianza mínima de la policy
  4. En empate de score, la prioridad absoluta desempata
"""

from __future__ import annotations
import logging
from .models import Decision, DecisionCandidate, DecisionType, ABSOLUTE_PRIORITY
from .policies import DecisionPolicy

logger = logging.getLogger(__name__)

# Pares de tipos mutuamente contradictorios
# Si ambos están en la lista de candidatos, se elimina el de menor score
_CONFLICTS: list[frozenset[DecisionType]] = [
    frozenset({DecisionType.RETREAT, DecisionType.TRADE}),
    frozenset({DecisionType.RETREAT, DecisionType.ALL_IN}),
    frozenset({DecisionType.FARM, DecisionType.ROTATE}),
    frozenset({DecisionType.FREEZE, DecisionType.CRASH}),
    frozenset({DecisionType.FREEZE, DecisionType.SLOW_PUSH}),
    frozenset({DecisionType.SPLIT_PUSH, DecisionType.TEAMFIGHT}),
    frozenset({DecisionType.WAIT, DecisionType.TRADE}),
    frozenset({DecisionType.WAIT, DecisionType.ALL_IN}),
]


class ConflictResolver:
    """
    Recibe una lista de DecisionCandidate y devuelve la mejor decisión.
    Stateless.
    """

    def resolve(
        self,
        candidates: list[DecisionCandidate],
        policy: DecisionPolicy,
    ) -> Decision | None:
        """
        Selecciona la mejor decisión del pool de candidatos.

        Returns:
            Decision activada, o None si no hay candidatos válidos.
        """
        if not candidates:
            return None

        # 1. Filtrar por confianza mínima
        valid = [c for c in candidates if c.decision.confidence >= policy.min_confidence]
        if not valid:
            # Si ninguno supera el umbral, tomar el de mayor confianza de todos
            valid = [max(candidates, key=lambda c: c.decision.confidence)]
            logger.debug("ConflictResolver: ninguno supera min_confidence=%.2f, tomando el mejor", policy.min_confidence)

        # 2. Resolver conflictos (eliminar el perdedor de cada par contradictorio)
        valid = self._resolve_conflicts(valid)

        # 3. Ordenar: primero por score (desc), luego por prioridad absoluta (desc)
        valid.sort(key=lambda c: (c.score, c.decision.priority), reverse=True)

        winner = valid[0].decision
        winner.activate()
        return winner

    def _resolve_conflicts(
        self,
        candidates: list[DecisionCandidate],
    ) -> list[DecisionCandidate]:
        """
        Para cada par en conflicto, elimina el candidato de menor score.
        """
        types_present = {c.decision.type: c for c in candidates}
        eliminated: set[DecisionType] = set()

        for conflict_pair in _CONFLICTS:
            types_in_pair = conflict_pair & set(types_present)
            if len(types_in_pair) < 2:
                continue
            # Ordenar el par por score y eliminar el perdedor
            sorted_pair = sorted(
                types_in_pair,
                key=lambda t: (types_present[t].score, types_present[t].decision.priority),
                reverse=True,
            )
            loser = sorted_pair[-1]
            eliminated.add(loser)
            logger.debug(
                "ConflictResolver: %s eliminado por conflicto con %s",
                loser.value, sorted_pair[0].value,
            )

        return [c for c in candidates if c.decision.type not in eliminated]
