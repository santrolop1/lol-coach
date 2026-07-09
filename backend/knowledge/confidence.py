"""
backend/knowledge/confidence.py — Sistema de confianza para el Knowledge Engine.

Cada recomendación o insight recibe una puntuación 0-1 basada en:
- Tamaño de la muestra
- Consistencia (qué fracción de partidas muestra el patrón)
- Estabilidad (inverso de la desviación estándar relativa)
"""

from __future__ import annotations

import math


def calc_confidence(
    n_games:     int,
    consistency: float,   # 0-1: fracción de partidas que muestran el patrón
    std_ratio:   float,   # std / mean (coeficiente de variación); 0 = muy estable
) -> float:
    """Devuelve confianza 0-1. No devuelve 1.0 (nunca certeza total)."""

    # Factor de muestra: más partidas = más confianza
    if n_games >= 30:
        size_f = 1.0
    elif n_games >= 20:
        size_f = 0.85
    elif n_games >= 10:
        size_f = 0.65
    elif n_games >= 5:
        size_f = 0.45
    else:
        size_f = 0.20

    # Factor de consistencia
    cons_f = max(0.0, min(consistency, 1.0))

    # Factor de estabilidad (inverso de varianza relativa)
    stab_f = max(0.0, 1.0 - min(std_ratio, 1.5) / 1.5)

    # Combinar ponderado
    raw = size_f * 0.45 + cons_f * 0.35 + stab_f * 0.20
    return round(min(raw, 0.97), 3)


def to_pct(conf: float) -> int:
    """Convierte confianza 0-1 a porcentaje entero."""
    return int(round(conf * 100))


def label(conf: float) -> str:
    if conf >= 0.80:
        return "Alta"
    if conf >= 0.55:
        return "Media"
    return "Baja"


def is_sufficient(conf: float, threshold: float = 0.45) -> bool:
    """Solo mostrar recomendaciones con confianza suficiente."""
    return conf >= threshold


def std_ratio(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    if mean < 0.001:
        return 0.0
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance) / mean
