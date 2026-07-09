"""
backend/services/champion_models.py — Modelos de datos para Champion Coach.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChampionAnalysis:
    """Estadísticas de rendimiento de un campeón específico."""
    champion_name:    str
    role:             str
    games:            int
    wins:             int
    losses:           int
    winrate:          float         # 0.0 – 1.0
    avg_score:        float | None  # promedio del score general
    avg_deaths:       float
    avg_cs_min:       float         # CS por minuto
    avg_damage_min:   float         # daño a campeones por minuto
    avg_kp:           float         # kill participation 0.0-1.0
    trend:            str           # "improving" | "declining" | "stable" | "insufficient"
    confidence:       str           # "low" | "medium" | "high"
    score_std:        float = 0.0   # desviación estándar (para consistencia)

    # Splits internos (usados por patterns y goals)
    win_avg_deaths:    float = field(default=0.0, repr=False)
    loss_avg_deaths:   float = field(default=0.0, repr=False)
    win_avg_cs_min:    float = field(default=0.0, repr=False)
    loss_avg_cs_min:   float = field(default=0.0, repr=False)
    win_avg_damage_min: float = field(default=0.0, repr=False)
    loss_avg_damage_min: float = field(default=0.0, repr=False)
    win_avg_kp:        float = field(default=0.0, repr=False)
    loss_avg_kp:       float = field(default=0.0, repr=False)

    @property
    def consistency_cv(self) -> float:
        """Coeficiente de variación del score (0 = perfecto, 1 = muy variable)."""
        return self.score_std / max(self.avg_score or 1.0, 1.0)

    @property
    def is_consistent(self) -> bool:
        return self.consistency_cv < 0.30

    @property
    def deaths_win_loss_delta_pct(self) -> float:
        """% de muertes adicionales en derrotas vs victorias."""
        base = max(self.win_avg_deaths, 0.1)
        return (self.loss_avg_deaths - base) / base * 100

    @property
    def cs_win_loss_delta_pct(self) -> float:
        """% de variación de CS/min entre victorias y derrotas."""
        base = max(self.win_avg_cs_min, 0.1)
        return (self.loss_avg_cs_min - base) / base * 100

    @property
    def damage_win_loss_delta_pct(self) -> float:
        """% de variación de daño/min entre victorias y derrotas."""
        base = max(self.win_avg_damage_min, 0.1)
        return (self.loss_avg_damage_min - base) / base * 100

    @property
    def kp_win_loss_delta_pct(self) -> float:
        """% de variación de KP entre victorias y derrotas."""
        base = max(self.win_avg_kp, 0.01)
        return (self.loss_avg_kp - base) / base * 100


@dataclass
class ChampionPattern:
    """Patrón de rendimiento detectado para un campeón específico."""
    pattern_type: str   # "deaths" | "farm" | "damage" | "kp" | "consistency"
    title:        str   # "Muertes elevadas en derrotas"
    description:  str   # "Tus derrotas con Kai'Sa tienen 45% más muertes."
    severity:     str   # "warning" | "critical"
    metric_delta: float # magnitud de la diferencia (%)


@dataclass
class ChampionGoal:
    """Objetivo específico y accionable para un campeón."""
    metric_key:  str           # "deaths" | "cs_pm" | "damage_pm" | "kp"
    title:       str           # "Reducir muertes"
    description: str           # "Objetivo: 6.5 muertes/partida. Actual: 8.1"
    current:     float
    target:      float
    unit:        str
    impact_desc: str           # "Igualas tu nivel de victorias con este campeón"


@dataclass
class ChampionCoachResult:
    """Resultado completo del coaching por campeón."""
    analysis:       ChampionAnalysis
    patterns:       list[ChampionPattern]
    goal:           ChampionGoal | None
    strengths:      list[str]    # frases con datos: "✓ Daño superior a tu media ADC"
    weaknesses:     list[str]    # frases con datos: "⚠ Muertes elevadas en derrotas"
    priority_class: str          # "main" | "growth" | "risk" | "insufficient"
    primary_problem: str | None  # texto del problema más urgente
    # Integración con Matchup Intelligence (se rellena desde fuera si hay datos)
    matchup_best:   str | None = None   # campeón contra quien mejor WR con este pick
    matchup_worst:  str | None = None   # campeón contra quien peor WR con este pick
