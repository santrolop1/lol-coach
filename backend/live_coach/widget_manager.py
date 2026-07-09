"""
WidgetManager — instancia y coordina todos los widgets del overlay.

Cada widget es una función que transforma (LiveSession, ChampionAnalysis) → WidgetContent.
Los widgets no tienen estado — son funciones puras.
El estado vive en PriorityManager.

Agregar un widget nuevo = registrar una función. Cero cambios al resto.
"""

from __future__ import annotations
import time
import logging
from typing import Callable, Any

from .models import (
    WidgetContent, WidgetId, Priority,
    LiveSession, PlayerStats,
)
from .priority_manager import PriorityManager

logger = logging.getLogger(__name__)

WidgetFn = Callable[[LiveSession, Any, Any, Any], WidgetContent | None]


class WidgetManager:
    """
    Orquesta el ciclo de vida de los widgets.

    Uso:
        wm = WidgetManager(priority_manager)
        wm.refresh(session, champion_analysis)
    """

    def __init__(self, priority_manager: PriorityManager) -> None:
        self._pm = priority_manager
        self._registry: dict[WidgetId, WidgetFn] = {}
        self._register_defaults()

    def register(self, widget_id: WidgetId, fn: WidgetFn) -> None:
        """Registra o reemplaza un widget por su función generadora."""
        self._registry[widget_id] = fn

    def refresh(
        self,
        session: LiveSession,
        analysis: Any = None,
        insight: Any = None,
        decision: Any = None,
    ) -> None:
        """
        Recalcula todos los widgets con el estado actual.
        Llama a cada función registrada y actualiza el PriorityManager.
        """
        for widget_id, fn in self._registry.items():
            try:
                try:
                    content = fn(session, analysis, insight, decision)
                except TypeError:
                    try:
                        content = fn(session, analysis, insight)
                    except TypeError:
                        # Widgets registrados externamente con firma (session, analysis)
                        content = fn(session, analysis)
                if content is not None:
                    self._pm.register_widget(content)
                else:
                    self._pm.hide_widget(widget_id)
            except Exception as exc:
                logger.error("Widget %s falló: %s", widget_id, exc, exc_info=True)

    def on_event_death(self, session: LiveSession) -> None:
        """Reacción específica a muerte del jugador."""
        stats = session.player_stats
        msg = (
            f"Muerte #{stats.deaths}. "
            "Revisar posición y estado de la R antes del próximo intercambio."
        )
        self._pm.push_notification(WidgetContent(
            widget_id=WidgetId.NOTIFICATIONS,
            title="⚠ Muerte",
            lines=[msg],
            priority=Priority.HIGH,
            highlight=True,
            ttl=12.0,
        ))

    def on_event_level_up(self, session: LiveSession, level: int) -> None:
        """Notificación de level up con contexto del spike."""
        from .models import EventType
        lines = [f"Nivel {level} alcanzado."]
        priority = Priority.NORMAL

        # Nivel 6 es especialmente importante
        if level == 6:
            lines = [
                "Nivel 6 — R desbloqueada.",
                "Puedes ahora aceptar intercambios de alto riesgo.",
                "Activa R entre 15-25% HP para maximizar curación.",
            ]
            priority = Priority.HIGH

        self._pm.push_notification(WidgetContent(
            widget_id=WidgetId.NOTIFICATIONS,
            title=f"▲ Nivel {level}",
            lines=lines,
            priority=priority,
            highlight=level == 6,
            ttl=8.0,
        ))

    def on_event_item_purchased(self, session: LiveSession, item_name: str) -> None:
        """Notificación al comprar un ítem."""
        self._pm.push_notification(WidgetContent(
            widget_id=WidgetId.NOTIFICATIONS,
            title="✓ Ítem comprado",
            lines=[item_name, "Actualiza tu plan de build."],
            priority=Priority.NORMAL,
            ttl=6.0,
        ))

    def on_event_recall(self, session: LiveSession) -> None:
        """Recordatorio al hacer recall."""
        self._pm.push_notification(WidgetContent(
            widget_id=WidgetId.NOTIFICATIONS,
            title="↩ Recall",
            lines=["Compra el ítem más caro posible.", "Vuelve empujando la oleada."],
            priority=Priority.NORMAL,
            ttl=8.0,
        ))

    # ── Widgets por defecto ───────────────────────────────────────────────────

    def _register_defaults(self) -> None:
        self.register(WidgetId.CHAMPION, _widget_champion)
        self.register(WidgetId.CURRENT_OBJ, _widget_current_objective)
        self.register(WidgetId.POWER_SPIKE, _widget_power_spike)
        self.register(WidgetId.BUILD, _widget_build)
        self.register(WidgetId.TRAINING, _widget_training)
        self.register(WidgetId.STATUS, _widget_status)
        self.register(WidgetId.WAVE_TIP, _widget_wave_tip)
        self.register(WidgetId.MACRO_TIP, _widget_macro_tip)


# ── Funciones de widget (puras, sin estado) ───────────────────────────────────
# Firma: (session, analysis, insight) → WidgetContent | None
# 'analysis' es ChampionAnalysis (legado), 'insight' es CoachInsight (nuevo)

def _widget_champion(session: LiveSession, analysis: Any, insight: Any = None, decision: Any = None) -> WidgetContent | None:
    if not session.champion:
        return None
    stats = session.player_stats
    lines = [f"Nivel {stats.level}"]
    if stats.kills or stats.deaths or stats.assists:
        lines.append(f"{stats.kills}/{stats.deaths}/{stats.assists}")
    cs_pm = (stats.cs / (session.game_time / 60)) if session.game_time > 60 else stats.cs
    if session.game_time > 60:
        lines.append(f"CS: {stats.cs} ({cs_pm:.1f}/min)")
    # Añadir objetivo del insight si está disponible
    if insight and insight.objective:
        lines.append(f"▶ {insight.objective.action_verb}")
    return WidgetContent(
        widget_id=WidgetId.CHAMPION,
        title=session.champion.title(),
        lines=lines,
        priority=Priority.NORMAL,
        icon="🏆",
        highlight=bool(insight and insight.objective and insight.objective.highlight),
    )


def _widget_current_objective(session: LiveSession, analysis: Any, insight: Any = None, decision: Any = None) -> WidgetContent | None:
    # Prioridad 1: mostrar la decisión actual del DecisionEngine
    if decision and getattr(decision, "is_active", False):
        confidence_pct = decision.confidence_pct
        reasons = decision.reasons[:2]
        lines = [decision.explanation[:120]]
        if reasons:
            lines.append(f"↳ {reasons[0]}")
        lines.append(f"Confianza: {confidence_pct}%")
        p = Priority.CRITICAL if decision.priority >= 85 else (
            Priority.HIGH if decision.priority >= 65 else Priority.NORMAL
        )
        return WidgetContent(
            widget_id=WidgetId.CURRENT_OBJ,
            title=f"▶ {decision.title}",
            lines=lines,
            priority=p,
            icon="🎯",
            highlight=getattr(decision, "highlight", False) or decision.priority >= 80,
            metadata={"decision_type": decision.type.value, "confidence": decision.confidence},
        )
    # Fallback al insight (objetivo sin decisión)
    if insight and insight.objective:
        obj = insight.objective
        return WidgetContent(
            widget_id=WidgetId.CURRENT_OBJ,
            title=obj.title,
            lines=[obj.description[:120]],
            priority=Priority.HIGH if obj.priority >= 70 else Priority.NORMAL,
            icon="▶",
            highlight=obj.highlight,
        )
    # Fallback al analysis legado
    if not analysis or not analysis.has_profile:
        return None
    live = analysis.live_coach
    if not live.current_objective:
        return None
    return WidgetContent(
        widget_id=WidgetId.CURRENT_OBJ,
        title="Objetivo actual",
        lines=[live.current_objective],
        priority=Priority.HIGH,
        icon="▶",
    )


def _widget_power_spike(session: LiveSession, analysis: Any, insight: Any = None, decision: Any = None) -> WidgetContent | None:
    # Mostrar si el insight detecta que estamos en ventana de power spike
    if insight and insight.context.is_power_spike_window:
        return WidgetContent(
            widget_id=WidgetId.POWER_SPIKE,
            title="⚡ Power Spike activo",
            lines=["Aprovecha este momento de poder.", "Busca intercambios favorables."],
            priority=Priority.HIGH,
            icon="⚡",
            highlight=True,
        )
    # Fallback al analysis legado
    if not analysis or not analysis.has_profile:
        return None
    live = analysis.live_coach
    spike = live.next_power_spike
    if not spike:
        return None

    level = session.player_stats.level
    if spike.id == "level_6" and level >= 6:
        all_spikes = analysis.power_spikes
        future = [s for s in all_spikes if s.id != "level_6"]
        if not future:
            return None
        spike = future[0]

    return WidgetContent(
        widget_id=WidgetId.POWER_SPIKE,
        title="Próximo Spike",
        lines=[spike.timing, spike.action[:80] if spike.action else ""],
        priority=Priority.NORMAL,
        icon="⚡",
    )


def _widget_build(session: LiveSession, analysis: Any, insight: Any = None, decision: Any = None) -> WidgetContent | None:
    if not analysis or not analysis.has_profile:
        return None
    build_id = analysis.build_recommendation
    if not build_id:
        return None
    return WidgetContent(
        widget_id=WidgetId.BUILD,
        title="Build",
        lines=[build_id.replace("_", " ").title()],
        priority=Priority.LOW,
        icon="🛡",
    )


def _widget_training(session: LiveSession, analysis: Any, insight: Any = None, decision: Any = None) -> WidgetContent | None:
    # Mostrar misión activa del insight
    if insight and insight.mission and insight.mission.is_active:
        m = insight.mission
        pct = int(m.progress_pct * 100)
        return WidgetContent(
            widget_id=WidgetId.TRAINING,
            title=m.title,
            lines=[m.description[:80], f"Progreso: {pct}%"],
            priority=Priority.NORMAL,
            icon="🎯",
        )
    # Fallback
    if not analysis:
        return None
    live = analysis.live_coach
    focus = live.training_focus if hasattr(live, "training_focus") else ""
    if not focus:
        return None
    return WidgetContent(
        widget_id=WidgetId.TRAINING,
        title="Entrenamiento activo",
        lines=[focus[:100]],
        priority=Priority.NORMAL,
        icon="🎯",
    )


def _widget_status(session: LiveSession, analysis: Any, insight: Any = None, decision: Any = None) -> WidgetContent | None:
    lines = []
    if not session.provider_connected:
        lines.append("Sin conexión al cliente de juego.")
    if session.phase == "loading":
        lines.append("Cargando partida...")
    if not lines:
        return None
    return WidgetContent(
        widget_id=WidgetId.STATUS,
        title="Estado",
        lines=lines,
        priority=Priority.HIGH if not session.provider_connected else Priority.NORMAL,
        icon="📡",
    )


def _widget_wave_tip(session: LiveSession, analysis: Any, insight: Any = None, decision: Any = None) -> WidgetContent | None:
    # Preferir insight
    if insight and insight.context.situation.value in ("farming", "lane_phase"):
        next_ev = insight.next_timeline_event()
        if next_ev and next_ev.type in ("wave_management", "recall"):
            return WidgetContent(
                widget_id=WidgetId.WAVE_TIP,
                title=next_ev.title,
                lines=[next_ev.description[:100]],
                priority=Priority.LOW,
                icon="〰",
            )
    # Fallback al analysis
    if not analysis or not analysis.wave_priorities:
        return None
    technique_id = analysis.wave_priorities[0]
    labels = {
        "freeze": "Congela la oleada cerca de tu torre.",
        "slow_push": "Empuja lento para construir una oleada grande.",
        "fast_push": "Empuja rápido y rota al mid o a objetivos.",
        "crash": "Empuja y crashea antes del recall.",
        "bounce": "Haz rebotar la oleada desde su lado.",
        "reset": "Resetea la oleada a posición neutral.",
    }
    tip = labels.get(technique_id, technique_id.replace("_", " ").title())
    return WidgetContent(
        widget_id=WidgetId.WAVE_TIP,
        title="Gestión de oleada",
        lines=[tip],
        priority=Priority.LOW,
        icon="〰",
    )


def _widget_macro_tip(session: LiveSession, analysis: Any, insight: Any = None, decision: Any = None) -> WidgetContent | None:
    # Mostrar la top recomendación del insight como macro tip
    if insight:
        rec = insight.top_recommendation()
        if rec and rec.type in ("action", "tip"):
            return WidgetContent(
                widget_id=WidgetId.MACRO_TIP,
                title=rec.title,
                lines=[rec.reason[:100]],
                priority=Priority.LOW,
                icon="🗺",
            )
    # Fallback al analysis
    if not analysis or not analysis.macro_priorities:
        return None
    pattern_id = analysis.macro_priorities[0]
    labels = {
        "split_push": "Presiona el carril lateral y fuerza rotaciones.",
        "recall_timing": "Recuerda hacer recall con la oleada empujada.",
        "side_lane_pressure": "Mantén presión en el carril lateral.",
        "rotation": "Rota al mid tras empujar el carril.",
        "tempo": "Juega el tempo — sé el primero en actuar.",
    }
    tip = labels.get(pattern_id, pattern_id.replace("_", " ").title())
    return WidgetContent(
        widget_id=WidgetId.MACRO_TIP,
        title="Macro",
        lines=[tip],
        priority=Priority.LOW,
        icon="🗺",
    )
