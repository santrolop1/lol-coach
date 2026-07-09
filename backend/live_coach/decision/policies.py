"""
Decision Policies — configuración de los pesos del DecisionScorer.

Una policy modifica solo los pesos del algoritmo de puntuación.
No cambia la arquitectura ni los tipos de decisión disponibles.

Modos:
  CONSERVATIVE — prioriza supervivencia y CS sobre trades
  BALANCED     — default, pesos equilibrados
  AGGRESSIVE   — prioriza trades y objetivos sobre la vida
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class PolicyMode(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED     = "balanced"
    AGGRESSIVE   = "aggressive"


@dataclass
class DecisionPolicy:
    """
    Pesos que gobiernan el DecisionScorer.

    Todos los pesos deben sumar ≈ 1.0 para mantener el score en rango
    interpretable, pero el scorer normaliza por si acaso.
    """
    mode: PolicyMode = PolicyMode.BALANCED

    # Pesos de los factores del score compuesto
    w_priority:     float = 0.30   # prioridad absoluta del tipo de decisión
    w_confidence:   float = 0.25   # confianza calculada por ConfidenceEngine
    w_context:      float = 0.20   # alineación con el contexto actual
    w_mission:      float = 0.15   # compatibilidad con misión activa
    w_timeline:     float = 0.10   # alineación con el próximo evento de timeline

    # Umbrales
    min_confidence: float = 0.20   # confianza mínima para mostrar decisión
    max_active_seconds: float = 45.0  # TTL de una decisión activa
    history_size: int = 50

    # Agresividad de trades (escala los candidatos de tipo TRADE/ALL_IN)
    aggression_factor: float = 1.0  # 0.5 (conservador) — 1.5 (agresivo)

    @classmethod
    def conservative(cls) -> "DecisionPolicy":
        return cls(
            mode=PolicyMode.CONSERVATIVE,
            w_priority=0.25,
            w_confidence=0.30,
            w_context=0.20,
            w_mission=0.20,
            w_timeline=0.05,
            min_confidence=0.35,
            aggression_factor=0.5,
        )

    @classmethod
    def balanced(cls) -> "DecisionPolicy":
        return cls()

    @classmethod
    def aggressive(cls) -> "DecisionPolicy":
        return cls(
            mode=PolicyMode.AGGRESSIVE,
            w_priority=0.35,
            w_confidence=0.20,
            w_context=0.20,
            w_mission=0.10,
            w_timeline=0.15,
            min_confidence=0.15,
            aggression_factor=1.5,
        )

    @classmethod
    def from_mode(cls, mode: PolicyMode) -> "DecisionPolicy":
        match mode:
            case PolicyMode.CONSERVATIVE:
                return cls.conservative()
            case PolicyMode.AGGRESSIVE:
                return cls.aggressive()
            case _:
                return cls.balanced()
