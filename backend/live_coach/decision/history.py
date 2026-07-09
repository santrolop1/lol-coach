"""
DecisionHistory — historial circular de las últimas N decisiones.

Registra cuándo apareció, cuánto duró y por qué cambió cada decisión.
Útil para depuración y para evitar oscilaciones (flicker) entre decisiones.
"""

from __future__ import annotations
import time
from collections import deque
from .models import Decision, DecisionHistoryEntry


class DecisionHistory:
    """
    Historial circular de decisiones.

    Uso:
        history.record(decision)                # cuando se activa
        history.close(decision_id, "superseded", new_id)  # cuando se reemplaza
    """

    def __init__(self, max_size: int = 50) -> None:
        self._entries: deque[DecisionHistoryEntry] = deque(maxlen=max_size)
        self._active_id: str | None = None

    def record(self, decision: Decision) -> None:
        """Registra una nueva decisión activa."""
        entry = DecisionHistoryEntry(
            decision_id=decision.id,
            decision_type=decision.type.value,
            title=decision.title,
            confidence=decision.confidence,
            appeared_at=decision.timestamp,
        )
        self._entries.append(entry)
        self._active_id = decision.id

    def close(
        self,
        decision_id: str,
        resolution: str,
        superseded_by: str = "",
    ) -> None:
        """Cierra (resuelve) una entrada del historial."""
        for entry in reversed(self._entries):
            if entry.decision_id == decision_id and not entry.resolved_at:
                entry.resolved_at = time.time()
                entry.resolution = resolution
                entry.superseded_by = superseded_by
                return

    def last(self, n: int = 10) -> list[DecisionHistoryEntry]:
        """Devuelve las últimas N entradas."""
        entries = list(self._entries)
        return entries[-n:]

    def was_recent(self, decision_type: str, within_seconds: float = 10.0) -> bool:
        """
        Indica si una decisión del mismo tipo fue tomada recientemente.
        Útil para evitar flicker: no cambiar decisión si la anterior era igual y es reciente.
        """
        now = time.time()
        for entry in reversed(self._entries):
            if entry.decision_type == decision_type:
                age = now - entry.appeared_at
                return age <= within_seconds
        return False

    def last_type(self) -> str | None:
        """Tipo de la última decisión registrada."""
        if not self._entries:
            return None
        return self._entries[-1].decision_type

    @property
    def size(self) -> int:
        return len(self._entries)

    def to_list(self) -> list[dict]:
        return [
            {
                "id": e.decision_id,
                "type": e.decision_type,
                "title": e.title,
                "confidence": round(e.confidence, 3),
                "appeared_at": e.appeared_at,
                "duration_seconds": round(e.duration_seconds, 1),
                "resolution": e.resolution,
            }
            for e in self._entries
        ]
