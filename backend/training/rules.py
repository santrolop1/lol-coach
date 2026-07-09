"""
Definiciones del Skill Tree y reglas de evaluación de ejercicios.
Cada skill mapea a una dimensión de scorer_v2 y a su métrica principal.
"""
from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────────────
# Skill catalog — común a ambos roles excepto donde se indica
# ──────────────────────────────────────────────────────────────────────────────

SKILL_CATALOG: dict[str, dict] = {
    "survival": {
        "name":           "Supervivencia",
        "description":    "Minimizar muertes evitables para no regalar ventaja.",
        "dim_key":        "Positioning",          # ADC
        "dim_key_top":    "Survival",             # TOP (si existe)
        "primary_metric": "deaths",
        "direction":      "less_than",
        "roles":          ["ADC", "TOP"],
        "base_priority":  1,                      # menor = más prioritario
    },
    "farming": {
        "name":           "Farm",
        "description":    "Maximizar CS/min para conseguir el poder económico necesario.",
        "dim_key":        "Economy",
        "dim_key_top":    "Lane Control",
        "primary_metric": "cs_per_min",
        "direction":      "greater_than",
        "roles":          ["ADC", "TOP"],
        "base_priority":  2,
    },
    "impact": {
        "name":           "Impacto en combate",
        "description":    "Participar en peleas y maximizar daño para cerrar ventajas.",
        "dim_key":        "Combat Impact",
        "dim_key_top":    "Combat Impact",
        "primary_metric": "kill_participation",
        "direction":      "greater_than",
        "roles":          ["ADC", "TOP"],
        "base_priority":  3,
    },
    "pressure": {
        "name":           "Presión macro",
        "description":    "Convertir ventajas en estructuras y objetivos concretos.",
        "dim_key":        "Pressure",
        "dim_key_top":    "Pressure",
        "primary_metric": "objectives_per_min",
        "direction":      "greater_than",
        "roles":          ["TOP"],
        "base_priority":  2,
    },
    "consistency": {
        "name":           "Consistencia",
        "description":    "Rendir de forma estable partida tras partida.",
        "dim_key":        "__consistency__",      # especial: usa std de overall_score
        "dim_key_top":    "__consistency__",
        "primary_metric": "__overall_std__",
        "direction":      "less_than",
        "roles":          ["ADC", "TOP"],
        "base_priority":  4,
    },
}

# Orden progresivo de skills por rol
ROLE_PROGRESSION: dict[str, list[str]] = {
    "ADC": ["survival", "farming", "impact", "consistency"],
    "TOP": ["survival", "farming", "pressure", "impact", "consistency"],
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers para leer métricas de un MatchScore
# ──────────────────────────────────────────────────────────────────────────────

def get_metric_from_ms(ms, metric_key: str) -> float | None:
    """Extrae el valor de una métrica del objeto MatchScore de scorer_v2."""
    if ms is None:
        return None
    for dim in ms.dimensions:
        val = dim.metrics.get(metric_key)
        if val is not None:
            return float(val)
    return None


def check_exercise_condition(metric_val: float, threshold: float, direction: str) -> bool:
    if direction == "less_than":
        return metric_val <= threshold
    return metric_val >= threshold


# ──────────────────────────────────────────────────────────────────────────────
# Plantillas de tips por skill (para DailyPlan)
# ──────────────────────────────────────────────────────────────────────────────

FOCUS_TIPS: dict[str, str] = {
    "survival":    "Antes de cada pelea pregúntate: ¿tengo escapatoria si sale mal?",
    "farming":     "En los minutos 1-8 prioriza el CS sobre cualquier pelea opcional.",
    "impact":      "Intenta llegar a cada dragon/baron del equipo sin morir para contribuir.",
    "pressure":    "Cuando ganes la línea, mueve a drag o bot para crear presión global.",
    "consistency": "Juega como si la puntuación fuera a cero: ninguna partida es 'de práctica'.",
}

SUCCESS_TEMPLATES: dict[str, str] = {
    "survival":    "Si terminas con ≤ {threshold:.0f} muertes",
    "farming":     "Si consigues ≥ {threshold:.1f} CS/min",
    "impact":      "Si superas el {threshold:.0%} de participación en kills",
    "pressure":    "Si contribuyes en al menos {threshold:.1f} objetivos/min",
    "consistency": "Si tu puntuación general no baja de {threshold:.0f}",
}
