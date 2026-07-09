"""
backend/viewmodels/match_review_vm.py — ViewModel para la revisión de una partida.

Genera todo el análisis, la narrativa y los datos comparativos.
El frontend solo organiza y presenta lo que aquí se calcula.

FastAPI: GET /api/v1/matches/{match_id}/review
"""

from __future__ import annotations

from dataclasses import dataclass, field

import db
import scorer_v2
from scorer_v2 import (
    score_match, analyze_player, DimensionScore, PlayerBenchmarks, MetricStats
)


# ── Metadatos de métricas ──────────────────────────────────────────────────────
# (label_es, higher_is_better)
_METRIC_META: dict[str, tuple[str, bool]] = {
    "cs_per_min":          ("CS/min",                 True),
    "cs_at_10":            ("CS en min. 10",          True),
    "gold_per_min":        ("Oro/min",                True),
    "deaths":              ("Muertes",                False),
    "time_dead_pct":       ("Tiempo muerto",          False),
    "longest_alive_pct":   ("Racha viva",             True),
    "kill_participation":  ("Participación kills",    True),
    "team_damage_pct":     ("% daño equipo",          True),
    "objectives_per_min":  ("Daño obj./min",          True),
    "max_cs_advantage":    ("Ventaja CS",             True),
    "turrets_per_min":     ("Daño torres/min",        True),
    "turret_takedowns":    ("Torres destruidas",      True),
}

_DIM_ES: dict[str, str] = {
    "Economy":       "Economía",
    "Positioning":   "Posicionamiento",
    "Combat Impact": "Impacto en combate",
    "Lane Control":  "Control de línea",
    "Pressure":      "Presión",
    "Survival":      "Supervivencia",
}

_FOCUS_TIPS: dict[str, dict[str, str]] = {
    "Economy": {
        "ADC": "Practica el farming en práctica customizada. Meta: superar 7 CS/min antes de unirte a peleas.",
        "TOP": "Prioriza el CS en los primeros 10 minutos. Ganar la fase de línea empieza por el farm temprano.",
    },
    "Positioning": {
        "ADC": "Juega cerca de tu support en early game. Menos muertes = más daño sostenido = más victorias.",
        "TOP": "Elige tus peleas con ventaja clara. El TOP muerto no puede generar presión ni splitpushear.",
    },
    "Combat Impact": {
        "ADC": "Únete a las peleas de objetivos aunque no estés al 100%. Tu DPS en Dragon/Baron es decisivo.",
        "TOP": "Coordina el timing de Baron y Dragon con el equipo. Tu rol de frontline es clave en teamfights.",
    },
    "Lane Control": {
        "TOP": "Optimiza el CS en los primeros 10 minutos. Una ventaja de +10 CS sobre el rival equivale a ~200 de oro.",
    },
    "Pressure": {
        "TOP": "Convierte las victorias de línea en estructuras. Cuando dominas el 1v1, empuja y destruye torretas.",
    },
    "Survival": {
        "TOP": "Prioriza sobrevivir sobre iniciar. Una muerte innecesaria da al rival oro y tiempo de presión sin respuesta.",
    },
}


# ── Estructuras de datos ───────────────────────────────────────────────────────

@dataclass
class MetricReview:
    key:              str
    label:            str
    value_str:        str           # formateado: esta partida
    avg_str:          str | None    # formateado: promedio del jugador
    raw:              float | None
    raw_avg:          float | None
    direction:        str           # 'better' | 'worse' | 'neutral'
    higher_is_better: bool


@dataclass
class DimensionReview:
    name:         str
    name_es:      str
    score:        float | None
    avg_score:    float | None
    delta:        float | None      # score - avg_score (positivo = por encima del promedio)
    is_best:      bool
    is_worst:     bool
    metrics:      list[MetricReview]
    notes:        list[str]
    context:      str               # una línea: "5 puntos por encima de tu media"


@dataclass
class MatchReviewViewModel:
    found:          bool

    # Básicos (populados si found=True)
    match_id:       str = ""
    date:           str = ""
    champion:       str = ""
    role:           str = ""
    is_win:         bool = False
    is_surrender:   bool = False
    duration:       str = ""
    kda:            str = ""
    kills:          int = 0
    deaths_n:       int = 0
    assists:        int = 0
    cs:             int = 0

    # Score global
    overall_score:  float | None = None
    avg_overall:    float | None = None
    overall_delta:  float | None = None

    # Dimensiones
    dimensions:     list[DimensionReview] = field(default_factory=list)
    best_dim_name:  str | None = None
    worst_dim_name: str | None = None

    # Narrativa
    key_error_title: str | None = None
    key_error_body:  str | None = None
    focus_tip:       str | None = None

    # Meta
    sample_size:    int = 0
    confidence:     str = ""          # 'insufficient' | 'preliminary' | 'reliable' | 'robust'
    role_supported: bool = True


# ── Formateo de métricas ───────────────────────────────────────────────────────

def _fmt(key: str, val: float | None) -> str:
    if val is None:
        return "—"
    if key in ("time_dead_pct", "longest_alive_pct", "kill_participation", "team_damage_pct"):
        return f"{val * 100:.0f}%"
    if key in ("cs_per_min", "gold_per_min", "objectives_per_min", "turrets_per_min"):
        return f"{val:.1f}"
    if key == "max_cs_advantage":
        return f"{val:+.0f}"
    return f"{val:.0f}"


def _direction(key: str, val: float, stats: MetricStats) -> str:
    _, hib = _METRIC_META.get(key, ("", True))
    if stats.std < 0.001:
        return "neutral"
    z = (val - stats.mean) / stats.std
    effective_z = z if hib else -z
    if effective_z > 0.4:
        return "better"
    if effective_z < -0.4:
        return "worse"
    return "neutral"


def _context(score: float | None, avg: float | None) -> str:
    if score is None or avg is None:
        return "Sin referencia suficiente"
    delta = score - avg
    if delta >= 10:
        return f"+{delta:.0f} puntos sobre tu media"
    if delta >= 3:
        return f"Ligeramente por encima de tu media (+{delta:.0f})"
    if delta >= -3:
        return "Dentro de tu media habitual"
    if delta >= -10:
        return f"Ligeramente por debajo de tu media ({delta:.0f})"
    return f"{delta:.0f} puntos bajo tu media"


# ── Narrativa del error principal ──────────────────────────────────────────────

def _key_error(worst_dim: DimensionScore, benchmarks: PlayerBenchmarks) -> tuple[str, str] | None:
    """Encuentra la métrica más problemática y genera título + cuerpo explicativo."""
    worst_key: str | None = None
    worst_eff_z = 0.0

    for key, val in worst_dim.metrics.items():
        if val is None or key not in _METRIC_META:
            continue
        stats = benchmarks.metrics.get(key)
        if stats is None or stats.std < 0.001:
            continue
        _, hib = _METRIC_META[key]
        z = (val - stats.mean) / stats.std
        eff_z = z if hib else -z
        if eff_z < worst_eff_z:
            worst_eff_z = eff_z
            worst_key = key

    if worst_key is None:
        return None

    val   = worst_dim.metrics[worst_key]
    stats = benchmarks.metrics[worst_key]
    label, _ = _METRIC_META[worst_key]
    v_str  = _fmt(worst_key, val)
    a_str  = _fmt(worst_key, stats.mean)

    templates: dict[str, tuple[str, str]] = {
        "deaths": (
            f"{int(val)} muertes — {val / stats.mean:.1f}× tu promedio de {a_str}",
            f"Cada muerte cede entre 300–500 de oro al rival. Con {int(val)} muertes y un promedio "
            f"de {a_str}, cediste un exceso de ~{int((val - stats.mean) * 400):,} de oro extra."
        ),
        "time_dead_pct": (
            f"{val*100:.0f}% del tiempo muerto — tu media es {stats.mean*100:.0f}%",
            f"El tiempo muerto es tiempo sin farmear, sin presionar y sin participar en objetivos. "
            f"Reducir el tiempo muerto al {stats.mean*100:.0f}% habitual liberaría minutos de juego útil."
        ),
        "longest_alive_pct": (
            f"Racha de vida de {val*100:.0f}% — tu media es {stats.mean*100:.0f}%",
            f"Una racha de vida corta indica que moriste en momentos clave. En tus mejores partidas "
            f"logras sobrevivir el {stats.mean*100:.0f}% de la duración sin morir."
        ),
        "cs_per_min": (
            f"Solo {v_str} CS/min — {stats.mean - val:.1f} por debajo de tu media de {a_str}",
            f"Cada 0.1 CS/min de diferencia en 30 minutos equivale a ~60 de oro. Con {stats.mean - val:.1f} "
            f"CS/min menos, dejaste de generar ~{int((stats.mean - val) * 600):,} de oro en esta partida."
        ),
        "gold_per_min": (
            f"Solo {v_str} de oro/min — tu media es {a_str}",
            f"La eficiencia económica por debajo de tu media limita el poder en mid y late game. "
            f"Mejorar el farm y la presencia en objetivos aumentará el oro generado."
        ),
        "kill_participation": (
            f"Solo {val*100:.0f}% de participación en kills — tu media es {stats.mean*100:.0f}%",
            f"La participación en kills es el mayor predictor de victoria en este rol. "
            f"Estar en más peleas aumenta directamente las probabilidades de ganar."
        ),
        "team_damage_pct": (
            f"Solo {val*100:.0f}% del daño del equipo — tu media es {stats.mean*100:.0f}%",
            f"Tu rol requiere ser el principal generador de daño. Una aportación inferior a tu media "
            f"puede indicar posicionamiento defensivo excesivo o falta de items."
        ),
        "objectives_per_min": (
            f"Poco daño a objetivos ({v_str}/min) — tu media es {a_str}",
            f"Los objetivos (Dragón, Barón) son los que ganan partidas en fases finales. "
            f"Participar más en peleas de objetivo aumenta la presión y las opciones de cierre."
        ),
        "max_cs_advantage": (
            f"Ventaja de CS de {v_str} — tu media es {a_str}",
            f"No conseguir ventaja de CS en la fase de línea cede presión económica al rival. "
            f"Ganar el match-up en CS temprano genera opciones de juego más amplias."
        ),
        "turret_takedowns": (
            f"Solo {int(val)} torres destruidas — tu media es {a_str}",
            f"Las torretas son la forma más eficiente de convertir ventajas en oro estructural. "
            f"Cuando ganas tu línea, prioriza destruir la torreta antes de rotar."
        ),
    }

    return templates.get(worst_key, (
        f"{label} bajo en esta partida ({v_str} vs media {a_str})",
        "Este indicador estuvo por debajo de tu historial. Revisa las métricas para más contexto."
    ))


# ── Build principal ────────────────────────────────────────────────────────────

def build_match_review(match_id: str) -> MatchReviewViewModel:
    puuid = db.get_config("puuid")
    if not puuid:
        return MatchReviewViewModel(found=False)

    all_matches = db.get_matches(puuid, limit=200)
    match = next((m for m in all_matches if m.get("match_id") == match_id), None)

    if not match:
        return MatchReviewViewModel(found=False)

    role = match.get("role", "")
    if role not in ("ADC", "TOP"):
        return MatchReviewViewModel(found=True, match_id=match_id, role=role, role_supported=False,
                                     champion=match.get("champion", "?"),
                                     is_win=match.get("result") == "WIN")

    role_matches = [m for m in all_matches if m.get("role") == role]

    # Score de esta partida
    ms = score_match(match, role_matches)
    if ms is None:
        return MatchReviewViewModel(found=True, match_id=match_id, role=role, role_supported=False,
                                     champion=match.get("champion", "?"))

    # Promedios del jugador
    result = analyze_player(all_matches, role)

    # Básicos
    dur_sec  = match.get("duration_sec") or 0
    duration = f"{dur_sec // 60}m {dur_sec % 60:02d}s"

    # Mejor/peor dimensión
    scored = [d for d in ms.dimensions if d.score is not None]
    best   = max(scored, key=lambda d: d.score, default=None)
    worst  = min(scored, key=lambda d: d.score, default=None)

    # Construir dimensiones
    dimensions: list[DimensionReview] = []
    for dim in ms.dimensions:
        avg_s = result.dimensions.get(dim.name)
        delta = round(dim.score - avg_s, 1) if dim.score is not None and avg_s is not None else None

        # Métricas con comparación
        metrics: list[MetricReview] = []
        for key, val in dim.metrics.items():
            if key not in _METRIC_META:
                continue
            label, hib = _METRIC_META[key]
            stats = result.benchmarks.metrics.get(key)
            raw_avg = stats.mean if stats else None
            metrics.append(MetricReview(
                key=key, label=label,
                value_str=_fmt(key, val),
                avg_str=_fmt(key, raw_avg) if raw_avg is not None else None,
                raw=val, raw_avg=raw_avg,
                direction=_direction(key, val, stats) if (val is not None and stats) else "neutral",
                higher_is_better=hib,
            ))

        dimensions.append(DimensionReview(
            name=dim.name,
            name_es=_DIM_ES.get(dim.name, dim.name),
            score=dim.score,
            avg_score=round(avg_s, 1) if avg_s is not None else None,
            delta=delta,
            is_best=best is not None and dim.name == best.name,
            is_worst=worst is not None and dim.name == worst.name,
            metrics=metrics,
            notes=dim.notes,
            context=_context(dim.score, avg_s),
        ))

    # Score global vs promedio
    avg_overall = round(result.overall_score, 1) if result.overall_score is not None else None
    overall_delta = (
        round(ms.overall_score - result.overall_score, 1)
        if ms.overall_score is not None and result.overall_score is not None
        else None
    )

    # Narrativa
    key_err   = _key_error(worst, result.benchmarks) if worst else None
    focus_key = worst.name if worst else None
    focus_tip = (
        _FOCUS_TIPS.get(focus_key, {}).get(role)
        if focus_key else None
    )

    return MatchReviewViewModel(
        found=True,
        match_id=match_id,
        date=(match.get("played_at") or "")[:10],
        champion=match.get("champion", "?"),
        role=role,
        is_win=match.get("result") == "WIN",
        is_surrender=ms.is_surrender,
        duration=duration,
        kda=f"{match.get('kills',0)}/{match.get('deaths',0)}/{match.get('assists',0)}",
        kills=int(match.get("kills") or 0),
        deaths_n=int(match.get("deaths") or 0),
        assists=int(match.get("assists") or 0),
        cs=int(match.get("cs") or 0),
        overall_score=ms.overall_score,
        avg_overall=avg_overall,
        overall_delta=overall_delta,
        dimensions=dimensions,
        best_dim_name=best.name if best else None,
        worst_dim_name=worst.name if worst else None,
        key_error_title=key_err[0] if key_err else None,
        key_error_body=key_err[1] if key_err else None,
        focus_tip=focus_tip,
        sample_size=len(role_matches),
        confidence=result.confidence_level,
        role_supported=True,
    )
