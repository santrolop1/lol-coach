"""
EventBus — sistema de pub/sub para eventos del Live Coach.

Los widgets suscriben handlers. El LiveDataProvider publica eventos.
Desacoplamiento total: los widgets no conocen la fuente de datos.

Uso:
    bus = EventBus()
    bus.subscribe(EventType.LEVEL_UP, my_handler)
    bus.publish(GameEvent(type=EventType.LEVEL_UP, data={"level": 6}))
"""

from __future__ import annotations
import logging
import time
from collections import defaultdict
from typing import Callable

from .models import EventType, GameEvent

logger = logging.getLogger(__name__)

EventHandler = Callable[[GameEvent], None]


class EventBus:
    """
    Bus de eventos sincrónico para el Live Coach.

    Thread-safety: los handlers se ejecutan en el hilo que llama a publish().
    Para uso async ver AsyncEventBus (GI-LIVE-2+).
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: list[EventHandler] = []
        self._history: list[GameEvent] = []
        self._max_history: int = 100

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Suscribirse a un tipo de evento específico."""
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Suscribirse a todos los eventos (wildcard)."""
        if handler not in self._wildcard_handlers:
            self._wildcard_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def unsubscribe_all(self, handler: EventHandler) -> None:
        if handler in self._wildcard_handlers:
            self._wildcard_handlers.remove(handler)

    def publish(self, event: GameEvent) -> int:
        """
        Publica un evento. Llama a todos los handlers suscritos.

        Returns:
            Número de handlers notificados.
        """
        if event.timestamp == 0.0:
            event.timestamp = time.time()

        self._record(event)
        count = 0

        for handler in list(self._handlers.get(event.type, [])):
            try:
                handler(event)
                count += 1
            except Exception as exc:
                logger.error(
                    "Handler %s falló con evento %s: %s",
                    handler.__name__, event.type, exc, exc_info=True,
                )

        for handler in list(self._wildcard_handlers):
            try:
                handler(event)
                count += 1
            except Exception as exc:
                logger.error(
                    "Wildcard handler %s falló con evento %s: %s",
                    handler.__name__, event.type, exc, exc_info=True,
                )

        return count

    def clear(self) -> None:
        """Elimina todos los handlers y el historial."""
        self._handlers.clear()
        self._wildcard_handlers.clear()
        self._history.clear()

    def clear_handlers(self) -> None:
        """Elimina solo los handlers, mantiene historial."""
        self._handlers.clear()
        self._wildcard_handlers.clear()

    def history(self, event_type: EventType | None = None) -> list[GameEvent]:
        """Devuelve el historial de eventos, opcionalmente filtrado por tipo."""
        if event_type is None:
            return list(self._history)
        return [e for e in self._history if e.type == event_type]

    def last(self, event_type: EventType) -> GameEvent | None:
        """Último evento de un tipo dado."""
        for e in reversed(self._history):
            if e.type == event_type:
                return e
        return None

    def handler_count(self, event_type: EventType | None = None) -> int:
        if event_type is None:
            return sum(len(h) for h in self._handlers.values()) + len(self._wildcard_handlers)
        return len(self._handlers.get(event_type, []))

    def _record(self, event: GameEvent) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
