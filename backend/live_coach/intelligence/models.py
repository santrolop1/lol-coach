"""
Modelos de dominio de la capa de inteligencia del Live Coach.

Todos los modelos son inmutables (frozen=True) para que los motores
produzcan snapshots en lugar de mutar estado compartido.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


# ── Fase y situación ──────────────────────────────────────────────────────────

class GamePhase(str, Enum):
    EARLY           = "early"           # min 0–2, nivel 1
    LANE_PHASE      = "lane_phase"      # min 2–14, fase de carril
    MID_GAME        = "mid_game"        # min 14–25, peleas de objetivos
    LATE_GAME       = "late_game"       # min 25+, decisiones macro


class GameSituation(str, Enum):
    FARMING         = "farming"         # farmear sin presión
    RECALL_WINDOW   = "recall_window"   # momento óptimo de recall
    POWER_SPIKE     = "power_spike"     # acaba de alcanzar un spike
    OBJECTIVE_WINDOW= "objective_window"# ventana de objetivo importante
    IN_DANGER       = "in_danger"       # HP bajo o situación de peligro
    SPLIT_PUSH      = "split_push"      # empujando un carril lateral
    ROAMING         = "roaming"         # rotando por el mapa
    DEAD            = "dead"            # muerto, esperando respawn


# ── Estado de la máquina ──────────────────────────────────────────────────────

class CoachState(str, Enum):
    LOADING         = "loading"
    LEVEL_1         = "level_1"
    LANE_PHASE      = "lane_phase"
    RECALL_WINDOW   = "recall_window"
    POWER_SPIKE     = "power_spike"
    OBJECTIVE_WINDOW= "objective_window"
    SPLIT_PUSH      = "split_push"
    TEAMFIGHT       = "teamfight"
    LATE_GAME       = "late_game"
    DEAD            = "dead"
    POST_GAME       = "post_game"


# ── Modo de coaching ──────────────────────────────────────────────────────────

class CoachMode(str, Enum):
    BEGINNER        = "beginner"        # más frecuente, más detalle, más básico
    INTERMEDIATE    = "intermediate"    # balanceado
    ADVANCED        = "advanced"        # conciso, solo lo crítico


# ── Contexto de partida ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class GameContext:
    """
    Estado interpretado de la partida en un instante dado.

    El ContextEngine toma PlayerStats + ChampionProfile → GameContext.
    Los demás motores leen GameContext; nunca leen PlayerStats directamente.
    """
    game_time_minutes: float = 0.0
    player_level: int = 1
    player_gold: int = 500
    items_count: int = 0
    has_first_item: bool = False
    has_two_items: bool = False
    is_dead: bool = False
    hp_pct: float = 1.0
    deaths_so_far: int = 0
    cs: int = 0
    cs_per_min: float = 0.0

    phase: GamePhase = GamePhase.EARLY
    situation: GameSituation = GameSituation.FARMING

    is_power_spike_window: bool = False
    is_recall_window: bool = False
    is_objective_window: bool = False
    is_low_hp: bool = False

    coach_mode: CoachMode = CoachMode.INTERMEDIATE


# ── Objetivo principal ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CoachObjective:
    """El único objetivo que el jugador debe perseguir ahora mismo."""
    id: str
    title: str          # corto: "Congelar la oleada"
    description: str    # detallado: "La oleada está cerca de tu torre..."
    priority: int       # 1–100; mayor = más urgente
    action_verb: str    # "Congelar" | "Recall" | "Split Push" | ...
    context: str        # fase en la que aplica
    highlight: bool = False


# ── Misión ────────────────────────────────────────────────────────────────────

class MissionState(str, Enum):
    ACTIVE   = "active"
    SUCCESS  = "success"
    FAILED   = "failed"
    EXPIRED  = "expired"


@dataclass
class Mission:
    """
    Misión activa con seguimiento de progreso.

    A diferencia del resto de modelos, Mission es mutable porque
    MissionEngine actualiza su progreso en cada tick.
    """
    id: str
    title: str
    description: str
    state: MissionState = MissionState.ACTIVE

    progress_current: float = 0.0
    progress_target: float = 1.0
    progress_unit: str = ""         # "muertes" | "minutos" | "CS"

    success_message: str = ""
    failure_message: str = ""
    time_limit_minutes: float = 0.0  # 0 = sin límite

    @property
    def progress_pct(self) -> float:
        if self.progress_target <= 0:
            return 1.0
        return min(1.0, self.progress_current / self.progress_target)

    @property
    def is_active(self) -> bool:
        return self.state == MissionState.ACTIVE


# ── Línea temporal ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TimelineEvent:
    """Un evento en la línea temporal de la partida."""
    id: str
    time_minutes: float
    title: str
    description: str
    type: str           # "wave" | "objective" | "power_spike" | "macro" | "recall"
    completed: bool = False
    is_next: bool = False


# ── Recomendación ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Recommendation:
    """Recomendación corta y accionable."""
    id: str
    title: str          # "No uses E para iniciar"
    reason: str         # "Necesitas E para escapar de rotaciones"
    priority: int       # 1–100
    type: str           # "tip" | "warning" | "action" | "reminder"
    champion_specific: bool = False


# ── Salida del CoachIntelligence ──────────────────────────────────────────────

@dataclass
class CoachInsight:
    """
    Snapshot completo del estado del coach para un instante dado.

    CoachIntelligence.compute() → CoachInsight
    LiveCoach lo consume para actualizar widgets y notificaciones.
    """
    context: GameContext
    state: CoachState
    objective: CoachObjective | None = None
    mission: Mission | None = None
    timeline: list[TimelineEvent] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    coach_mode: CoachMode = CoachMode.INTERMEDIATE

    def top_recommendation(self) -> Recommendation | None:
        if not self.recommendations:
            return None
        return max(self.recommendations, key=lambda r: r.priority)

    def next_timeline_event(self) -> TimelineEvent | None:
        upcoming = [e for e in self.timeline if not e.completed and e.is_next]
        return upcoming[0] if upcoming else None

    def to_dict(self) -> dict:
        obj = None
        if self.objective:
            obj = {
                "id": self.objective.id,
                "title": self.objective.title,
                "description": self.objective.description,
                "action_verb": self.objective.action_verb,
                "highlight": self.objective.highlight,
                "priority": self.objective.priority,
            }

        mission = None
        if self.mission and self.mission.is_active:
            mission = {
                "id": self.mission.id,
                "title": self.mission.title,
                "description": self.mission.description,
                "state": self.mission.state.value,
                "progress_pct": round(self.mission.progress_pct, 2),
                "progress_current": self.mission.progress_current,
                "progress_target": self.mission.progress_target,
                "progress_unit": self.mission.progress_unit,
            }

        next_event = self.next_timeline_event()
        timeline_next = None
        if next_event:
            timeline_next = {
                "id": next_event.id,
                "time_minutes": next_event.time_minutes,
                "title": next_event.title,
                "description": next_event.description,
                "type": next_event.type,
            }

        top_rec = self.top_recommendation()
        recommendation = None
        if top_rec:
            recommendation = {
                "id": top_rec.id,
                "title": top_rec.title,
                "reason": top_rec.reason,
                "type": top_rec.type,
                "priority": top_rec.priority,
            }

        return {
            "state": self.state.value,
            "phase": self.context.phase.value,
            "situation": self.context.situation.value,
            "objective": obj,
            "mission": mission,
            "timeline_next": timeline_next,
            "recommendation": recommendation,
            "is_power_spike": self.context.is_power_spike_window,
            "is_recall_window": self.context.is_recall_window,
            "coach_mode": self.coach_mode.value,
        }
