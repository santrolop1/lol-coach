"""Entidades de salida del Champion Intelligence Engine."""

from __future__ import annotations
from dataclasses import dataclass, field
from .champion import PowerSpike


@dataclass
class LiveCoachHints:
    """
    Información preparada para el futuro overlay de coaching en vivo.
    No implementa UI — solo genera datos listos para renderizar.
    """
    current_objective: str = ""             # "Farmear y escalar"
    next_power_spike: PowerSpike | None = None
    reminders: list[str] = field(default_factory=list)
    recommended_build_id: str = ""
    recommended_rune_page_id: str = ""
    training_focus: str = ""


@dataclass
class DetectedMistake:
    """Un error del perfil detectado en las partidas recientes."""
    mistake_text: str                       # descripción del error (del perfil)
    evidence: str = ""                      # qué métrica lo sugiere
    severity: str = "medium"               # "low" | "medium" | "high"
    games_observed: int = 0


@dataclass
class ChampionAnalysis:
    """
    Resultado del Champion Intelligence Engine para un campeón y jugador.
    Todo lo que necesita la UI para mostrar el análisis de campeón.
    """
    champion: str
    role: str
    has_profile: bool = False

    # Fortalezas del campeón que el jugador está realizando (según estadísticas)
    strengths_realized: list[str] = field(default_factory=list)
    # Debilidades del campeón que están siendo explotadas
    weaknesses_exposed: list[str] = field(default_factory=list)
    # Errores del perfil detectados en partidas recientes
    detected_mistakes: list[DetectedMistake] = field(default_factory=list)
    # Power spikes ordenados por relevancia
    power_spikes: list[PowerSpike] = field(default_factory=list)
    # Top 3 áreas de mejora
    focus_areas: list[str] = field(default_factory=list)
    # Build recomendada (ID de ItemBuild)
    build_recommendation: str = ""
    # Página de runas recomendada (ID)
    rune_recommendation: str = ""
    # Wave strategies prioritarias para este campeón
    wave_priorities: list[str] = field(default_factory=list)
    # Macro patterns más importantes
    macro_priorities: list[str] = field(default_factory=list)
    # Datos para el Live Coach
    live_coach: LiveCoachHints = field(default_factory=LiveCoachHints)
    # Confianza del análisis
    confidence: str = "insufficient"       # "insufficient"|"low"|"medium"|"high"
    games_analyzed: int = 0
    # Mensaje si no hay perfil o datos insuficientes
    message: str = ""
