"""
PriorityManager — decide qué mostrar, cuándo y por cuánto tiempo.

Reglas:
  - Una notificación CRITICAL reemplaza cualquier otra en curso.
  - Una HIGH solo reemplaza LOW/NORMAL.
  - Las notificaciones temporales (ttl > 0) expiran automáticamente.
  - El jugador nunca ve más de MAX_VISIBLE_WIDGETS widgets simultáneos.
  - Los widgets están ordenados por prioridad descendente.
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field

from .models import WidgetContent, WidgetId, Priority

MAX_VISIBLE_WIDGETS = 5


@dataclass
class _ActiveNotification:
    content: WidgetContent
    expires_at: float      # 0 = permanente


class PriorityManager:
    """
    Gestiona la cola de contenido a mostrar en el overlay.

    Los widgets permanentes se registran una vez.
    Las notificaciones efímeras se empujan con push_notification().
    """

    def __init__(self) -> None:
        self._widgets: dict[WidgetId, WidgetContent] = {}
        self._notification: _ActiveNotification | None = None
        self._hidden: set[WidgetId] = set()

    # ── Widgets permanentes ───────────────────────────────────────────────────

    def register_widget(self, content: WidgetContent) -> None:
        """Registra o actualiza un widget permanente."""
        self._widgets[content.widget_id] = content

    def update_widget(self, widget_id: WidgetId, content: WidgetContent) -> None:
        """Actualiza el contenido de un widget ya registrado."""
        self._widgets[widget_id] = content

    def hide_widget(self, widget_id: WidgetId) -> None:
        self._hidden.add(widget_id)

    def show_widget(self, widget_id: WidgetId) -> None:
        self._hidden.discard(widget_id)

    def toggle_widget(self, widget_id: WidgetId) -> bool:
        """Invierte la visibilidad. Retorna el nuevo estado (True=visible)."""
        if widget_id in self._hidden:
            self._hidden.discard(widget_id)
            return True
        self._hidden.add(widget_id)
        return False

    # ── Notificaciones efímeras ───────────────────────────────────────────────

    def push_notification(self, content: WidgetContent) -> bool:
        """
        Intenta mostrar una notificación efímera.

        Solo reemplaza la notificación actual si tiene mayor prioridad.
        Returns True si fue aceptada.
        """
        now = time.time()
        if self._notification and self._notification.expires_at > now:
            if content.priority <= self._notification.content.priority:
                return False

        expires_at = (now + content.ttl) if content.ttl > 0 else 0.0
        self._notification = _ActiveNotification(content=content, expires_at=expires_at)
        return True

    def clear_notification(self) -> None:
        self._notification = None

    # ── Snapshot para el overlay ──────────────────────────────────────────────

    def get_visible_widgets(self) -> list[WidgetContent]:
        """
        Devuelve la lista de widgets visibles ordenados por prioridad (mayor primero).
        Máximo MAX_VISIBLE_WIDGETS.
        """
        now = time.time()
        result = []
        for wid, content in self._widgets.items():
            if wid in self._hidden:
                continue
            if content.ttl > 0 and content.metadata.get("registered_at", 0) + content.ttl < now:
                continue
            result.append(content)

        result.sort(key=lambda w: w.priority.value, reverse=True)
        return result[:MAX_VISIBLE_WIDGETS]

    def get_active_notification(self) -> WidgetContent | None:
        """Devuelve la notificación activa si no ha expirado."""
        if self._notification is None:
            return None
        now = time.time()
        if self._notification.expires_at > 0 and self._notification.expires_at < now:
            self._notification = None
            return None
        return self._notification.content

    def tick(self) -> None:
        """Llamar periódicamente para limpiar notificaciones expiradas."""
        now = time.time()
        if self._notification and 0 < self._notification.expires_at < now:
            self._notification = None

    def reset(self) -> None:
        """Limpia todo el estado (nueva partida)."""
        self._widgets.clear()
        self._notification = None
        self._hidden.clear()

    @property
    def widget_count(self) -> int:
        return len(self._widgets)

    @property
    def has_notification(self) -> bool:
        return self.get_active_notification() is not None
