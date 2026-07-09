"""
backend/services/matchup_models.py — Modelos de datos para Matchup Intelligence.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MatchupRecord:
    """Estadísticas agregadas de un matchup (mi campeón vs campeón enemigo)."""
    champion:      str           # mi campeón (o "ALL" para agregados)
    enemy:         str           # campeón enemigo de carril
    role:          str           # "ADC" | "TOP"
    games:         int
    wins:          int
    losses:        int
    winrate:       float         # 0.0 – 1.0
    avg_score:     float | None  # promedio del score general (de scorer_v2)
    avg_deaths:    float
    avg_cs_min:    float         # CS por minuto
    avg_damage_min: float        # daño a campeones por minuto
    trend:         str           # "improving" | "declining" | "stable" | "insufficient"
    confidence:    str           # "low" | "medium" | "high"

    # Campos internos para patrones (no se muestran directamente)
    overall_avg_deaths:    float = field(default=0.0, repr=False)
    overall_avg_cs_min:    float = field(default=0.0, repr=False)
    overall_avg_damage_min: float = field(default=0.0, repr=False)

    @property
    def deaths_delta_pct(self) -> float:
        """% de diferencia de muertes vs promedio global (positivo = más muertes)."""
        base = max(self.overall_avg_deaths, 0.1)
        return (self.avg_deaths - base) / base * 100

    @property
    def cs_delta_pct(self) -> float:
        """% de diferencia de CS/min vs promedio global (negativo = menos CS)."""
        base = max(self.overall_avg_cs_min, 0.1)
        return (self.avg_cs_min - base) / base * 100

    @property
    def damage_delta_pct(self) -> float:
        """% de diferencia de daño/min vs promedio global (negativo = menos daño)."""
        base = max(self.overall_avg_damage_min, 0.1)
        return (self.avg_damage_min - base) / base * 100


@dataclass
class MatchupPattern:
    """Patrón estadístico detectado en un matchup."""
    enemy:        str
    pattern_type: str   # "deaths_spike" | "cs_drop" | "damage_drop"
    description:  str   # "Tus muertes aumentan 37% contra Draven"
    severity:     str   # "warning" | "critical"


@dataclass
class BanRecommendation:
    """Recomendación de ban derivada del historial del jugador."""
    enemy:       str
    games:       int
    winrate:     float
    ban_score:   float         # 0-100: mayor = más urgente banear
    reasons:     list[str]     # razones con datos reales
    confidence:  str           # "low" | "medium" | "high"


@dataclass
class MatchupResult:
    """Resultado completo del análisis de matchups para un rol."""
    role:          str
    all_matchups:  list[MatchupRecord]
    best:          list[MatchupRecord]          # top 5 por WR (min muestra)
    worst:         list[MatchupRecord]          # top 5 peores WR
    ban:           BanRecommendation | None
    patterns:      list[MatchupPattern]
    raw_coverage:  int    # cuántas partidas tienen JSON raw disponible
    total_matches: int    # partidas totales del rol
