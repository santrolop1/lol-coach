"""
recommendations.py — Sistema de recomendaciones basado en reglas.

Lógica:
  score < 40  → debilidad (necesitas trabajar esto)
  score > 70  → fortaleza (estás haciendo esto bien)
  40-70       → zona de mejora (no crítico, pero mejorable)

Devuelve RecommendationResult con listas de debilidades, fortalezas y un tip prioritario.
"""

from dataclasses import dataclass, field
from scorer import ScoreResult


# ---------------------------------------------------------------------------
# Modelo de salida
# ---------------------------------------------------------------------------

@dataclass
class RecommendationResult:
    weaknesses: list[str] = field(default_factory=list)  # Áreas críticas
    strengths:  list[str] = field(default_factory=list)  # Áreas sólidas
    priority_tip: str = ""                                # Una acción concreta


# ---------------------------------------------------------------------------
# Reglas
# ---------------------------------------------------------------------------

# (campo_en_ScoreResult, umbral, mensaje)
_WEAKNESS_RULES: list[tuple[str, float, str]] = [
    (
        "farm_score", 40,
        "Tu farmeo es el punto más débil. Cada 10 CS = ~300 oro perdido. "
        "Practica 10 minutos de farmeo sin matar en partida de práctica antes de rankear.",
    ),
    (
        "survival_score", 40,
        "Estás muriendo demasiado. Las muertes tempranas ceden ventaja de oro y "
        "presión de mapa. Juega conservador cuando no tienes visión de river.",
    ),
    (
        "fight_score", 40,
        "Tu impacto en peleas es bajo. Revisa si estás llegando tarde a teamfights "
        "o si estás muriendo antes de hacer daño. Posiciónate atrás y ataca primero.",
    ),
]

_STRENGTH_RULES: list[tuple[str, float, str]] = [
    ("farm_score",     70, "Buen farmeo — CS/min consistente y por encima del promedio."),
    ("survival_score", 70, "Buena supervivencia — pocas muertes y KDA positivo."),
    ("fight_score",    70, "Buen impacto en pelea — daño alto y KDA sólido."),
]

# Tip prioritario según el score más bajo
_PRIORITY_TIPS: dict[str, str] = {
    "farm_score": (
        "Prioridad esta semana: CS. Objetivo concreto: llegar a 7 CS/min en tus próximas 5 partidas. "
        "Si estás en Gold o menos, ganar el farmeo suele ganar el lane."
    ),
    "survival_score": (
        "Prioridad esta semana: sobrevivir. Objetivo concreto: máximo 4 muertes por partida. "
        "Compra Control Ward cada base y retrocede cuando tu jungler no está visible."
    ),
    "fight_score": (
        "Prioridad esta semana: impacto en peleas. Objetivo concreto: aumentar daño total un 20%. "
        "Únete a teamfights en lugar de splitpushear cuando el equipo pelea 4v5."
    ),
}


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def get_recommendations(score: ScoreResult) -> RecommendationResult:
    """
    Analiza un ScoreResult y devuelve debilidades, fortalezas y tip prioritario.
    """
    score_map = {
        "farm_score":     score.farm_score,
        "survival_score": score.survival_score,
        "fight_score":    score.fight_score,
    }

    weaknesses = [
        msg
        for field_name, threshold, msg in _WEAKNESS_RULES
        if score_map[field_name] < threshold
    ]

    strengths = [
        msg
        for field_name, threshold, msg in _STRENGTH_RULES
        if score_map[field_name] >= threshold
    ]

    # Tip prioritario: área con el score más bajo, solo si está por debajo de 65
    lowest_field = min(score_map, key=score_map.get)
    priority_tip = ""
    if score_map[lowest_field] < 65:
        priority_tip = _PRIORITY_TIPS[lowest_field]

    return RecommendationResult(
        weaknesses=weaknesses,
        strengths=strengths,
        priority_tip=priority_tip,
    )
