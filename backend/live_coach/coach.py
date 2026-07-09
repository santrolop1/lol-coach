"""
LiveCoach — facade principal del módulo Live Coach.

Orquesta:
  LiveDataProvider → EventBus → ChampionIntelligenceEngine
                              → PriorityManager → WidgetManager
                              → OverlayState

Uso:
    coach = LiveCoach(provider=RiotLiveClientProvider())
    coach.set_champion("tryndamere", "TOP")
    coach.tick()                 # llamar cada N segundos
    state = coach.get_state()   # → OverlayState serializable
"""

from __future__ import annotations
import logging
import time

from .models import (
    LiveSession, OverlayState, GameEvent, EventType,
    PlayerStats,
)
from .event_bus import EventBus
from .priority_manager import PriorityManager
from .widget_manager import WidgetManager
from .providers.base import LiveDataProvider
from .intelligence import CoachIntelligence, CoachMode
from .decision import DecisionEngine, DecisionPolicy

logger = logging.getLogger(__name__)


class LiveCoach:
    """
    Facade del Live Coach.

    Thread-safety: diseñado para uso single-threaded con polling desde FastAPI.
    El WebSocket endpoint llama a tick() + get_state() desde el event loop de uvicorn.
    """

    def __init__(
        self,
        provider: LiveDataProvider,
        knowledge_api=None,
    ) -> None:
        self._provider = provider
        self._knowledge = knowledge_api
        self._event_bus = EventBus()
        self._priority_manager = PriorityManager()
        self._widget_manager = WidgetManager(self._priority_manager)

        self._session = LiveSession()
        self._analysis = None       # ChampionAnalysis | None
        self._champion: str = ""
        self._role: str = ""
        self._intelligence = CoachIntelligence()
        self._decision_engine = DecisionEngine()
        self._last_insight = None
        self._last_decision = None
        self._profile = None    # ChampionProfile cacheado

        self._last_level: int = 0
        self._last_death_count: int = 0
        self._was_dead: bool = False
        self._last_item_count: int = 0
        self._last_was_recalling: bool = False

        self._subscribe_widget_reactions()

    # ── API pública ───────────────────────────────────────────────────────────

    def set_champion(self, champion: str, role: str) -> None:
        """Configura el campeón activo. Recarga el análisis si cambia."""
        if champion != self._champion or role != self._role:
            self._champion = champion.lower()
            self._role = role.upper()
            self._analysis = None
            self._reload_analysis()
            self._event_bus.publish(GameEvent(
                type=EventType.CHAMPION_LOADED,
                data={"champion": self._champion, "role": self._role},
            ))

    def tick(self) -> None:
        """
        Ciclo principal de actualización.
        Llamar cada ~2-5 segundos desde el polling loop.
        """
        session = self._provider.get_session_snapshot()
        self._detect_events(session)
        self._session = session
        self._priority_manager.tick()

        # Si el provider detectó el campeón automáticamente (Live Client), sincronizar
        if session.champion and session.champion != self._champion:
            self.set_champion(session.champion, session.role or self._role)

        if self._analysis is None and self._champion:
            self._reload_analysis()

        # Computar inteligencia y decisión antes de refrescar widgets
        profile = self._get_profile()
        self._last_insight = self._intelligence.compute(session, profile=profile)
        self._last_decision = self._decision_engine.decide(self._last_insight)

        self._widget_manager.refresh(session, self._analysis, self._last_insight, self._last_decision)
        self._event_bus.publish(GameEvent(
            type=EventType.TICK,
            data={"game_time": session.game_time},
        ))

    def get_state(self) -> OverlayState:
        """Devuelve el estado serializable del overlay en este instante."""
        insight = getattr(self, "_last_insight", None)
        decision = getattr(self, "_last_decision", None)
        return OverlayState(
            session=self._session,
            widgets=self._priority_manager.get_visible_widgets(),
            active_notification=self._priority_manager.get_active_notification(),
            timestamp=time.time(),
            intelligence=insight.to_dict() if insight else None,
            current_decision=decision.to_dict() if (decision and decision.is_active) else None,
        )

    def reset(self) -> None:
        """Reinicia el estado para una nueva partida."""
        self._session = LiveSession()
        self._analysis = None
        self._last_level = 0
        self._last_death_count = 0
        self._was_dead = False
        self._last_item_count = 0
        self._last_insight = None
        self._last_decision = None
        self._intelligence.reset()
        self._decision_engine.reset()
        self._priority_manager.reset()
        self._event_bus.publish(GameEvent(type=EventType.GAME_STARTED))

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def priority_manager(self) -> PriorityManager:
        return self._priority_manager

    @property
    def widget_manager(self) -> WidgetManager:
        return self._widget_manager

    # ── Detección de eventos ──────────────────────────────────────────────────

    def _detect_events(self, new_session: LiveSession) -> None:
        """Compara el estado anterior con el nuevo para emitir eventos."""
        old = self._session
        stats = new_session.player_stats

        # Level up
        if stats.level > self._last_level and self._last_level > 0:
            self._event_bus.publish(GameEvent(
                type=EventType.LEVEL_UP,
                data={"level": stats.level, "previous": self._last_level},
            ))
        if stats.level != self._last_level:
            self._last_level = stats.level

        # Muerte
        if stats.deaths > self._last_death_count:
            self._event_bus.publish(GameEvent(
                type=EventType.DEATH,
                data={"deaths": stats.deaths, "game_time": new_session.game_time},
            ))
        self._last_death_count = stats.deaths

        # Respawn
        if self._was_dead and not stats.is_dead:
            self._event_bus.publish(GameEvent(type=EventType.RESPAWN))
        self._was_dead = stats.is_dead

        # Ítem comprado
        new_item_count = len(stats.items)
        if new_item_count > self._last_item_count:
            new_items = stats.items[self._last_item_count:]
            for item in new_items:
                self._event_bus.publish(GameEvent(
                    type=EventType.ITEM_PURCHASED,
                    data={"item": item},
                ))
        self._last_item_count = new_item_count

        # Inicio / fin de partida
        if new_session.phase == "in_game" and old.phase != "in_game":
            self._event_bus.publish(GameEvent(type=EventType.GAME_STARTED))
        elif new_session.phase == "post_game" and old.phase == "in_game":
            self._event_bus.publish(GameEvent(type=EventType.GAME_ENDED))

        # Update de tiempo (siempre)
        if new_session.active:
            self._event_bus.publish(GameEvent(
                type=EventType.GAME_TIME_UPDATE,
                data={"time": new_session.game_time},
            ))

    # ── Análisis ──────────────────────────────────────────────────────────────

    def _reload_analysis(self) -> None:
        """Carga o recarga el ChampionAnalysis del campeón activo."""
        if not self._champion or self._knowledge is None:
            return
        try:
            from backend.game_intelligence.engines.champion.engine import (
                ChampionIntelligenceEngine,
            )
            engine = ChampionIntelligenceEngine(self._knowledge)
            self._analysis = engine.analyze(
                champion=self._champion,
                role=self._role,
                raw_matches=[],   # sin historial en vivo — solo perfil
            )
        except Exception as exc:
            logger.warning("No se pudo cargar análisis para %s: %s", self._champion, exc)
            self._analysis = None

        # Cachear el perfil para pasarlo a CoachIntelligence
        self._profile = self._load_profile()

    def _load_profile(self):
        """Carga ChampionProfile del knowledge_api si está disponible."""
        if not self._champion or self._knowledge is None:
            return None
        try:
            return self._knowledge.get_champion(self._champion)
        except Exception:
            return None

    def _get_profile(self):
        """Devuelve el perfil cacheado."""
        return self._profile

    # ── Suscripciones del WidgetManager a eventos ─────────────────────────────

    def _subscribe_widget_reactions(self) -> None:
        wm = self._widget_manager

        def on_death(event: GameEvent) -> None:
            wm.on_event_death(self._session)

        def on_level_up(event: GameEvent) -> None:
            wm.on_event_level_up(self._session, event.get("level", 0))

        def on_item(event: GameEvent) -> None:
            wm.on_event_item_purchased(self._session, event.get("item", ""))

        def on_recall(event: GameEvent) -> None:
            wm.on_event_recall(self._session)

        self._event_bus.subscribe(EventType.DEATH, on_death)
        self._event_bus.subscribe(EventType.LEVEL_UP, on_level_up)
        self._event_bus.subscribe(EventType.ITEM_PURCHASED, on_item)
        self._event_bus.subscribe(EventType.RECALL, on_recall)
