"""
backend/services/priority_engine.py — Motor de priorización accionable.

Transforma datos reales de win/loss en una lista ordenada de prioridades
con impacto estimado, evidencia numérica y recomendación específica.

Sin reglas genéricas. Todo derivado del historial del jugador.

Entrada: lista de partidas brutas + rol
Salida : list[Priority] ordenada de mayor a menor impacto
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

# ── Configuración de métricas ─────────────────────────────────────────────────

# Cada métrica define:
#   key            : campo en el dict de partida (o clave derivada)
#   lower_is_better: True para deaths (menos = mejor)
#   weight         : coeficiente de impacto máximo (1-20 escala final)
#   title          : nombre mostrable
#   unit           : unidad para el texto de evidencia
#   min_gap_pct    : diferencia relativa mínima para considerar la métrica relevante

_ADC_METRICS: list[dict] = [
    {"key": "deaths",             "lower_is_better": True,  "weight": 20, "title": "Reducir muertes",              "unit": "muertes/partida"},
    {"key": "cs_pm",              "lower_is_better": False, "weight": 15, "title": "Mejorar farm",                  "unit": "CS/min"},
    {"key": "kill_participation", "lower_is_better": False, "weight": 12, "title": "Mayor participación en peleas", "unit": "% KP"},
    {"key": "damage_pm",          "lower_is_better": False, "weight": 10, "title": "Mejorar daño",                  "unit": "daño/min"},
    {"key": "vision_pm",          "lower_is_better": False, "weight": 6,  "title": "Mejorar visión",               "unit": "visión/min"},
]

_TOP_METRICS: list[dict] = [
    {"key": "deaths",             "lower_is_better": True,  "weight": 20, "title": "Reducir muertes",              "unit": "muertes/partida"},
    {"key": "cs_pm",              "lower_is_better": False, "weight": 15, "title": "Mejorar farm",                  "unit": "CS/min"},
    {"key": "obj_pm",             "lower_is_better": False, "weight": 12, "title": "Más presión en objetivos",      "unit": "daño obj/min"},
    {"key": "damage_pm",          "lower_is_better": False, "weight": 10, "title": "Mejorar daño",                  "unit": "daño/min"},
    {"key": "vision_pm",          "lower_is_better": False, "weight": 6,  "title": "Mejorar visión",               "unit": "visión/min"},
]

_MIN_GAP_FRACTION = 0.07    # 7% de diferencia relativa mínima para incluir
_MIN_SPLIT_SIZE   = 3       # mínimo de wins Y losses para calcular


# ── Dataclass resultado ───────────────────────────────────────────────────────

@dataclass
class Priority:
    """Prioridad accionable derivada de datos win/loss del jugador."""
    title:           str           # "Reducir muertes"
    metric_key:      str           # clave interna
    impact_score:    int           # 1-20 (mayor = más mejora potencial)
    confidence:      str           # "low" | "medium" | "high"
    evidence:        str           # comparación win/loss con números
    recommendation:  str           # objetivo concreto
    current_value:   float | None  # promedio actual (todas las partidas)
    target_value:    float | None  # promedio en victorias (objetivo realista)
    unit:            str           # unidad de medida
    win_avg:         float | None = field(default=None, repr=False)
    loss_avg:        float | None = field(default=None, repr=False)
    n_wins:          int           = field(default=0,   repr=False)
    n_losses:        int           = field(default=0,   repr=False)


# ── Helpers de extracción ─────────────────────────────────────────────────────

def _safe_float(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _field_avg(matches: list[dict], key: str) -> float | None:
    vals = [_safe_float(m.get(key)) for m in matches]
    vals = [v for v in vals if v is not None]
    return statistics.mean(vals) if vals else None


def _derived_pm(matches: list[dict], field: str) -> float | None:
    """Valor 'field' por minuto de partida."""
    pairs = []
    for m in matches:
        v   = _safe_float(m.get(field))
        dur = _safe_float(m.get("duration_sec"))
        if v is not None and dur and dur > 60:
            pairs.append(v / (dur / 60.0))
    return statistics.mean(pairs) if pairs else None


def _extract(matches: list[dict], key: str) -> list[float]:
    """Extrae todos los valores no-None del campo (o campo derivado)."""
    if key == "cs_pm":
        vals = []
        for m in matches:
            cs  = _safe_float(m.get("cs"))
            dur = _safe_float(m.get("duration_sec"))
            if cs is not None and dur and dur > 60:
                vals.append(cs / (dur / 60.0))
        return vals
    if key == "damage_pm":
        vals = []
        for m in matches:
            d   = _safe_float(m.get("damage"))
            dur = _safe_float(m.get("duration_sec"))
            if d is not None and dur and dur > 60:
                vals.append(d / (dur / 60.0))
        return vals
    if key == "vision_pm":
        vals = []
        for m in matches:
            v   = _safe_float(m.get("vision_score"))
            dur = _safe_float(m.get("duration_sec"))
            if v is not None and dur and dur > 60:
                vals.append(v / (dur / 60.0))
        return vals
    if key == "obj_pm":
        vals = []
        for m in matches:
            v   = _safe_float(m.get("damage_to_objectives"))
            dur = _safe_float(m.get("duration_sec"))
            if v is not None and dur and dur > 60:
                vals.append(v / (dur / 60.0))
        return vals
    if key == "kill_participation":
        vals = []
        for m in matches:
            v = _safe_float(m.get("kill_participation"))
            if v is not None:
                vals.append(v)
        return vals
    # Directo del dict
    return [v for m in matches if (v := _safe_float(m.get(key))) is not None]


def _confidence(n_wins: int, n_losses: int) -> str:
    if n_wins < _MIN_SPLIT_SIZE or n_losses < _MIN_SPLIT_SIZE:
        return "low"
    if n_wins < 6 or n_losses < 6:
        return "medium"
    return "high"


# ── Generadores de texto ──────────────────────────────────────────────────────

def _evidence_text(
    key: str,
    title: str,
    unit: str,
    win_avg: float,
    loss_avg: float,
    lower_is_better: bool,
    n_wins: int,
    n_losses: int,
) -> str:
    """Genera evidencia con números reales del historial del jugador."""
    if key == "kill_participation":
        diff = abs(win_avg - loss_avg) * 100
        return (
            f"Tus {n_wins} victorias promedian {win_avg:.0%} KP. "
            f"Tus {n_losses} derrotas: {loss_avg:.0%} KP. "
            f"Diferencia de {diff:.0f} puntos porcentuales."
        )
    if key == "deaths":
        delta = loss_avg - win_avg
        pct   = delta / max(win_avg, 0.1) * 100
        return (
            f"Tus {n_wins} victorias promedian {win_avg:.1f} muertes. "
            f"Tus {n_losses} derrotas: {loss_avg:.1f} muertes. "
            f"Tus derrotas tienen {delta:.1f} muertes más ({pct:.0f}% superior)."
        )
    if key == "cs_pm":
        delta = win_avg - loss_avg
        pct   = delta / max(loss_avg, 0.1) * 100
        return (
            f"Tus {n_wins} victorias promedian {win_avg:.1f} CS/min. "
            f"Tus {n_losses} derrotas: {loss_avg:.1f} CS/min. "
            f"Produces {delta:.1f} CS/min más cuando ganas ({pct:.0f}% superior)."
        )
    if key == "damage_pm":
        delta = win_avg - loss_avg
        pct   = delta / max(loss_avg, 0.1) * 100
        return (
            f"Tus {n_wins} victorias promedian {win_avg:.0f} daño/min. "
            f"Tus {n_losses} derrotas: {loss_avg:.0f} daño/min. "
            f"Diferencia de {delta:.0f} daño/min ({pct:.0f}% más en victorias)."
        )
    if key == "obj_pm":
        delta = win_avg - loss_avg
        pct   = delta / max(loss_avg, 0.1) * 100
        return (
            f"Tus {n_wins} victorias promedian {win_avg:.0f} daño obj/min. "
            f"Tus {n_losses} derrotas: {loss_avg:.0f} daño obj/min. "
            f"Diferencia de {delta:.0f} ({pct:.0f}% más presión en victorias)."
        )
    if key == "vision_pm":
        delta = win_avg - loss_avg
        pct   = delta / max(loss_avg, 0.1) * 100
        return (
            f"Tus {n_wins} victorias promedian {win_avg:.1f} visión/min. "
            f"Tus {n_losses} derrotas: {loss_avg:.1f} visión/min. "
            f"Diferencia de {delta:.1f} ({pct:.0f}% más en victorias)."
        )
    # Genérico
    return (
        f"Victorias ({n_wins}): {win_avg:.2f} {unit}. "
        f"Derrotas ({n_losses}): {loss_avg:.2f} {unit}."
    )


def _recommendation_text(
    title: str,
    unit: str,
    current: float,
    target: float,
    key: str,
) -> str:
    """Genera recomendación específica con objetivo concreto."""
    if key == "deaths":
        return (
            f"Objetivo: {target:.1f} muertes/partida en las próximas 10 partidas. "
            f"Situación actual: {current:.1f} muertes/partida."
        )
    if key == "cs_pm":
        return (
            f"Objetivo: {target:.1f} CS/min durante las próximas 10 partidas. "
            f"Situación actual: {current:.1f} CS/min."
        )
    if key == "kill_participation":
        return (
            f"Objetivo: {target:.0%} de participación en las próximas 10 partidas. "
            f"Situación actual: {current:.0%}."
        )
    if key == "damage_pm":
        return (
            f"Objetivo: {target:.0f} daño/min en las próximas 10 partidas. "
            f"Situación actual: {current:.0f} daño/min."
        )
    if key == "vision_pm":
        return (
            f"Objetivo: {target:.1f} visión/min en las próximas 10 partidas. "
            f"Situación actual: {current:.1f} visión/min."
        )
    return (
        f"Objetivo: alcanzar {target:.2f} {unit} en las próximas 10 partidas. "
        f"Situación actual: {current:.2f} {unit}."
    )


# ── Motor principal ───────────────────────────────────────────────────────────

def compute_priorities(
    matches: list[dict],
    role: str,
) -> list[Priority]:
    """
    Calcula prioridades accionables ordenadas de mayor a menor impacto.

    Parámetros
    ----------
    matches : partidas ya filtradas por rol (list[dict])
    role    : "ADC" o "TOP"

    Retorna
    -------
    list[Priority] — vacío si no hay suficientes datos.
    """
    wins   = [m for m in matches if m.get("result") == "WIN"]
    losses = [m for m in matches if m.get("result") == "LOSS"]

    if len(wins) < _MIN_SPLIT_SIZE or len(losses) < _MIN_SPLIT_SIZE:
        return []

    metrics = _ADC_METRICS if role == "ADC" else _TOP_METRICS
    priorities: list[Priority] = []

    for cfg in metrics:
        key              = cfg["key"]
        lower_is_better  = cfg["lower_is_better"]
        weight           = cfg["weight"]
        title            = cfg["title"]
        unit             = cfg["unit"]

        win_vals  = _extract(wins,   key)
        loss_vals = _extract(losses, key)
        all_vals  = _extract(matches, key)

        if not win_vals or not loss_vals:
            continue

        win_avg  = statistics.mean(win_vals)
        loss_avg = statistics.mean(loss_vals)
        current  = statistics.mean(all_vals) if all_vals else win_avg

        # Determinar cuál promedio es "bueno" y cuál "malo"
        if lower_is_better:
            good_avg, bad_avg = win_avg, loss_avg  # menos muertes = bueno
        else:
            good_avg, bad_avg = win_avg, loss_avg  # más cs = bueno

        gap_fraction = abs(good_avg - bad_avg) / max(abs(bad_avg), 0.01)

        if gap_fraction < _MIN_GAP_FRACTION:
            continue  # diferencia no significativa

        # ¿El jugador está actualmente lejos del objetivo?
        if lower_is_better:
            metric_is_problematic = current > win_avg * 1.05
        else:
            metric_is_problematic = current < win_avg * 0.95

        if not metric_is_problematic:
            continue  # ya está cerca de su nivel de victorias

        impact_score = round(min(20, max(1, gap_fraction * weight)))
        conf         = _confidence(len(win_vals), len(loss_vals))

        if conf == "low":
            continue

        evidence       = _evidence_text(key, title, unit, win_avg, loss_avg, lower_is_better, len(win_vals), len(loss_vals))
        recommendation = _recommendation_text(title, unit, current, win_avg, key)

        priorities.append(Priority(
            title          = title,
            metric_key     = key,
            impact_score   = impact_score,
            confidence     = conf,
            evidence       = evidence,
            recommendation = recommendation,
            current_value  = current,
            target_value   = win_avg,
            unit           = unit,
            win_avg        = win_avg,
            loss_avg       = loss_avg,
            n_wins         = len(win_vals),
            n_losses       = len(loss_vals),
        ))

    # Ordenar por impacto descendente
    priorities.sort(key=lambda p: p.impact_score, reverse=True)
    return priorities[:5]  # máximo 5 prioridades
