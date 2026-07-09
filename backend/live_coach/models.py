"""
Modelos de dominio del Live Coach.

Todos los modelos son independientes de Game Intelligence — solo estructuras
de datos para el flujo LiveDataProvider → EventBus → Widgets → Overlay.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Eventos ───────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    GAME_STARTED        = "game_started"
    LOADING_FINISHED    = "loading_finished"
    CHAMPION_LOADED     = "champion_loaded"
    LEVEL_UP            = "level_up"
    ITEM_PURCHASED      = "item_purchased"
    ABILITY_LEVELED     = "ability_leveled"
    DEATH               = "death"
    RESPAWN             = "respawn"
    RECALL              = "recall"
    FIRST_BLOOD         = "first_blood"
    TOWER_DESTROYED     = "tower_destroyed"
    OBJECTIVE_TAKEN     = "objective_taken"
    GAME_ENDED          = "game_ended"
    VICTORY             = "victory"
    DEFEAT              = "defeat"
    TICK                = "tick"       # latido periódico (cada 5s)
    GAME_TIME_UPDATE    = "game_time_update"
    GOLD_THRESHOLD      = "gold_threshold"   # cuando el jugador puede comprar ítem clave


@dataclass
class GameEvent:
    type: EventType
    timestamp: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


# ── Estado de partida activa ──────────────────────────────────────────────────

@dataclass
class PlayerStats:
    """Snapshot de las estadísticas del jugador en vivo."""
    champion: str = ""
    level: int = 1
    gold: int = 0
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    cs: int = 0
    game_time: float = 0.0      # segundos transcurridos
    hp_pct: float = 1.0         # 0.0 – 1.0
    mana_pct: float = 1.0
    items: list[str] = field(default_factory=list)
    abilities_leveled: dict[str, int] = field(default_factory=dict)  # {"Q": 3, "W": 1, ...}
    is_dead: bool = False
    role: str = ""


@dataclass
class LiveSession:
    """Estado completo de la sesión de coaching en vivo."""
    active: bool = False
    champion: str = ""
    role: str = ""
    game_time: float = 0.0
    player_stats: PlayerStats = field(default_factory=PlayerStats)
    phase: str = "idle"     # "idle" | "loading" | "in_game" | "post_game"
    provider_connected: bool = False


# ── Widgets ───────────────────────────────────────────────────────────────────

class WidgetId(str, Enum):
    CHAMPION        = "champion"
    CURRENT_OBJ     = "current_objective"
    POWER_SPIKE     = "power_spike"
    BUILD           = "build"
    TRAINING        = "training"
    NOTIFICATIONS   = "notifications"
    STATUS          = "status"
    WAVE_TIP        = "wave_tip"
    MACRO_TIP       = "macro_tip"


class Priority(int, Enum):
    """Prioridad de un widget o notificación. Mayor número = más urgente."""
    LOW         = 10
    NORMAL      = 20
    HIGH        = 30
    CRITICAL    = 40


@dataclass
class WidgetContent:
    """Contenido renderizable de un widget."""
    widget_id: WidgetId
    title: str
    lines: list[str] = field(default_factory=list)
    priority: Priority = Priority.NORMAL
    visible: bool = True
    icon: str = ""              # emoji / icono corto
    highlight: bool = False     # destacar visualmente
    ttl: float = 0.0            # 0 = permanente; >0 = segundos hasta expirar
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OverlayState:
    """Estado completo del overlay en un momento dado."""
    session: LiveSession = field(default_factory=LiveSession)
    widgets: list[WidgetContent] = field(default_factory=list)
    active_notification: WidgetContent | None = None
    compact_mode: bool = False
    timestamp: float = 0.0
    intelligence: dict | None = None      # CoachInsight.to_dict() cuando está disponible
    current_decision: dict | None = None  # Decision.to_dict() — la única acción recomendada ahora

    def to_dict(self) -> dict:
        """Serialización para enviar por WebSocket / HTTP."""
        import time
        return {
            "active": self.session.active,
            "champion": self.session.champion,
            "role": self.session.role,
            "game_time": self.session.game_time,
            "phase": self.session.phase,
            "provider_connected": self.session.provider_connected,
            "player": {
                "level": self.session.player_stats.level,
                "gold": self.session.player_stats.gold,
                "kills": self.session.player_stats.kills,
                "deaths": self.session.player_stats.deaths,
                "assists": self.session.player_stats.assists,
                "cs": self.session.player_stats.cs,
                "hp_pct": self.session.player_stats.hp_pct,
                "is_dead": self.session.player_stats.is_dead,
                "items": self.session.player_stats.items,
            },
            "widgets": [
                {
                    "id": w.widget_id.value,
                    "title": w.title,
                    "lines": w.lines,
                    "priority": w.priority.value,
                    "visible": w.visible,
                    "icon": w.icon,
                    "highlight": w.highlight,
                    "ttl": w.ttl,
                }
                for w in self.widgets if w.visible
            ],
            "notification": {
                "title": self.active_notification.title,
                "lines": self.active_notification.lines,
                "priority": self.active_notification.priority.value,
                "highlight": self.active_notification.highlight,
            } if self.active_notification else None,
            "compact_mode": self.compact_mode,
            "timestamp": self.timestamp or time.time(),
            "intelligence": self.intelligence,
            "current_decision": self.current_decision,
        }
