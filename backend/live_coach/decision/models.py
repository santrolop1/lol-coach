"""
Modelos de dominio del Decision Intelligence Engine.

Una Decision es el resultado de sintetizar toda la información disponible
en una sola acción recomendada con confianza medible.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import time


# ── Tipo de decisión ──────────────────────────────────────────────────────────

class DecisionType(str, Enum):
    """
    Tipo de acción recomendada. El orden define la prioridad absoluta
    (menor índice = mayor urgencia).
    """
    EMERGENCY   = "emergency"   # escape, no morir
    OBJECTIVE   = "objective"   # barón, dragón, heraldo
    POWER_SPIKE = "power_spike" # ventana de spike activa
    RECALL      = "recall"      # recall óptimo
    TRADE       = "trade"       # intercambio favorable
    ALL_IN      = "all_in"      # all-in con R
    FREEZE      = "freeze"      # congelar oleada
    CRASH       = "crash"       # crashear oleada
    SLOW_PUSH   = "slow_push"   # empuje lento
    SPLIT_PUSH  = "split_push"  # presión lateral
    TEAMFIGHT   = "teamfight"   # pelea de equipo
    ROTATE      = "rotate"      # rotación al mapa
    WARD        = "ward"        # visión
    RETREAT     = "retreat"     # retroceder sin morir
    FARM        = "farm"        # farmear default
    WAIT        = "wait"        # esperar respawn / cargar
    BUILD       = "build"       # recordatorio de build
    TRAINING    = "training"    # enfoque de entrenamiento
    INFORMATION = "information" # dato informativo bajo


# Prioridad absoluta por tipo (sin modificar vía policy)
ABSOLUTE_PRIORITY: dict[DecisionType, int] = {
    DecisionType.EMERGENCY:   100,
    DecisionType.OBJECTIVE:    85,
    DecisionType.POWER_SPIKE:  80,
    DecisionType.RECALL:       70,
    DecisionType.ALL_IN:       65,
    DecisionType.TRADE:        55,
    DecisionType.FREEZE:       50,
    DecisionType.CRASH:        50,
    DecisionType.SLOW_PUSH:    45,
    DecisionType.SPLIT_PUSH:   60,
    DecisionType.TEAMFIGHT:    60,
    DecisionType.ROTATE:       50,
    DecisionType.WARD:         35,
    DecisionType.RETREAT:      75,
    DecisionType.FARM:         30,
    DecisionType.WAIT:         15,
    DecisionType.BUILD:        20,
    DecisionType.TRAINING:     25,
    DecisionType.INFORMATION:  10,
}


# ── Ciclo de vida ─────────────────────────────────────────────────────────────

class DecisionState(str, Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    COMPLETED = "completed"
    EXPIRED   = "expired"
    CANCELLED = "cancelled"


# ── Decisión ──────────────────────────────────────────────────────────────────

@dataclass
class Decision:
    """
    Una única decisión recomendada al jugador.

    El overlay siempre muestra la última decisión ACTIVE.
    """
    id: str
    type: DecisionType
    title: str
    explanation: str
    action: str                      # verbo corto: "Freeze", "Recall", "Escapar"
    confidence: float                # 0.0–1.0
    priority: int                    # absoluto (de ABSOLUTE_PRIORITY)
    origin: str                      # engine/source que la generó
    reasons: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    duration_seconds: float = 30.0  # cuánto tiempo aplica esta decisión
    champion_specific: bool = False
    highlight: bool = False

    state: DecisionState = DecisionState.PENDING
    timestamp: float = field(default_factory=time.time)
    activated_at: float = 0.0
    resolved_at: float = 0.0

    @property
    def confidence_pct(self) -> int:
        return int(self.confidence * 100)

    @property
    def is_active(self) -> bool:
        return self.state == DecisionState.ACTIVE

    @property
    def age_seconds(self) -> float:
        return time.time() - self.timestamp

    def activate(self) -> None:
        self.state = DecisionState.ACTIVE
        self.activated_at = time.time()

    def expire(self) -> None:
        self.state = DecisionState.EXPIRED
        self.resolved_at = time.time()

    def complete(self) -> None:
        self.state = DecisionState.COMPLETED
        self.resolved_at = time.time()

    def cancel(self) -> None:
        self.state = DecisionState.CANCELLED
        self.resolved_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "explanation": self.explanation,
            "action": self.action,
            "confidence": round(self.confidence, 3),
            "confidence_pct": self.confidence_pct,
            "priority": self.priority,
            "origin": self.origin,
            "reasons": self.reasons,
            "champion_specific": self.champion_specific,
            "state": self.state.value,
            "duration_seconds": self.duration_seconds,
            "age_seconds": round(self.age_seconds, 1),
        }


# ── Candidato de decisión ─────────────────────────────────────────────────────

@dataclass
class DecisionCandidate:
    """
    Propuesta de decisión antes de pasar por el Conflict Resolver.
    Incluye la puntuación compuesta calculada por el DecisionScorer.
    """
    decision: Decision
    score: float = 0.0   # puntuación compuesta del DecisionScorer


# ── Historial ─────────────────────────────────────────────────────────────────

@dataclass
class DecisionHistoryEntry:
    """Registro de una decisión en el historial."""
    decision_id: str
    decision_type: str
    title: str
    confidence: float
    appeared_at: float
    resolved_at: float = 0.0
    resolution: str = ""     # "completed" | "expired" | "superseded"
    superseded_by: str = ""  # id de la decisión que la reemplazó

    @property
    def duration_seconds(self) -> float:
        if self.resolved_at:
            return self.resolved_at - self.appeared_at
        return time.time() - self.appeared_at
