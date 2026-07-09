"""
backend/viewmodels/progress_vm.py — Coaching Progresivo.

Responde: ¿Qué está mejorando este jugador y qué debe entrenar ahora?

Reutiliza scorer_v2 sin duplicar lógica. No expone datos crudos al frontend;
todo análisis, narrativa y confianza se calculan aquí.

FastAPI: GET /api/v1/progress
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from collections import defaultdict
from typing import Optional

import db
import scorer_v2
from scorer_v2 import score_match, analyze_player, MatchScore


# ── Configuración ──────────────────────────────────────────────────────────────

_MAX_MATCHES    = 50       # cuántas partidas analizar como máximo
_MIN_FOR_TRENDS = 10       # mínimo para calcular tendencias
_GOAL_WINDOW    = 5        # partidas recientes para medir el objetivo semanal
_RECENT_WINDOW  = 10       # "últimas N partidas" para comparar
_BASELINE_START = 10       # comparación: partidas 10-30
_BASELINE_END   = 30

# Umbrales de confianza para insights (partidas en cada ventana)
_CONF_HIGH  = 8
_CONF_MED   = 5

# Dimensión → nombre en español
_DIM_ES: dict[str, str] = {
    "Economy":       "Economía",
    "Positioning":   "Posicionamiento",
    "Combat Impact": "Impacto en combate",
    "Lane Control":  "Control de línea",
    "Pressure":      "Presión",
    "Survival":      "Supervivencia",
}

# Métrica → (label_es, higher_is_better, unidad_str, formato)
_METRIC_META: dict[str, tuple[str, bool, str, str]] = {
    "cs_per_min":         ("CS/min",             True,  "cs/min", "{:.1f}"),
    "cs_at_10":           ("CS en min. 10",       True,  "",        "{:.0f}"),
    "gold_per_min":       ("oro/min",             True,  "oro/min", "{:.0f}"),
    "deaths":             ("muertes",             False, "muertes", "{:.0f}"),
    "time_dead_pct":      ("tiempo muerto",       False, "%",       "{:.0f}%"),
    "longest_alive_pct":  ("racha de vida",       True,  "%",       "{:.0f}%"),
    "kill_participation": ("participación kills", True,  "%",       "{:.0f}%"),
    "team_damage_pct":    ("% daño equipo",       True,  "%",       "{:.0f}%"),
    "objectives_per_min": ("daño obj./min",       True,  "",        "{:.2f}"),
    "max_cs_advantage":   ("ventaja de CS",       True,  "",        "{:+.0f}"),
    "turrets_per_min":    ("daño torres/min",     True,  "",        "{:.2f}"),
    "turret_takedowns":   ("torres destruidas",   True,  "",        "{:.1f}"),
}


# ── Estructuras de salida ──────────────────────────────────────────────────────

@dataclass
class TimelinePoint:
    label:             str            # "Hoy" | "Hace 10 partidas" etc
    games_ago_start:   int
    games_ago_end:     int
    avg_score:         float | None
    dominant_champion: str | None
    sample_size:       int
    trend_arrow:       str            # "up" | "down" | "flat" | ""


@dataclass
class TrendInsight:
    category:   str           # "improving" | "declining" | "stable"
    dim_name:   str
    label:      str           # texto completo generado
    delta:      float
    delta_pct:  float
    confidence: str           # "high" | "medium" | "low"
    champion:   str | None    # si la tendencia es específica de un campeón


@dataclass
class WeeklyGoal:
    title:           str
    metric_key:      str
    metric_label:    str
    target_value:    float
    target_str:      str      # "< 5 muertes" | "> 7.0 CS/min"
    current_avg:     float    # promedio últimas 5
    baseline:        float    # promedio histórico
    progress_count:  int      # partidas de las últimas 5 que cumplen el objetivo
    total_count:     int      # siempre 5 (o menos si hay menos partidas)
    pct:             float
    status:          str      # "completed" | "on_track" | "at_risk" | "not_started"
    motivation:      str


@dataclass
class Habit:
    type:        str   # "positive" | "negative"
    title:       str
    description: str
    streak:      int
    is_active:   bool


@dataclass
class ChampionInsight:
    champion:   str
    games:      int
    avg_score:  float
    vs_overall: float   # delta vs promedio global
    role:       str


@dataclass
class Recommendation:
    rank:       int
    title:      str
    body:       str
    evidence:   str   # "Basado en X partidas" / "En 4 de las últimas 5 partidas..."
    impact:     str   # "high" | "medium"
    metric_key: str | None


@dataclass
class ProgressViewModel:
    has_data:    bool
    role:        str = ""
    total_matches: int = 0

    # Hero
    overall_trend:       str         = "stable"
    overall_trend_label: str         = "Estable"
    overall_delta:       float | None = None
    avg_recent:          float | None = None
    confidence:          str         = "insufficient"

    # Timeline + sparkline
    timeline:     list[TimelinePoint]  = field(default_factory=list)
    score_series: list[float]          = field(default_factory=list)  # oldest→newest

    # Insights (solo los relevantes)
    improving: list[TrendInsight] = field(default_factory=list)
    declining: list[TrendInsight] = field(default_factory=list)
    stable:    list[TrendInsight] = field(default_factory=list)

    # Hábitos (máx 5)
    habits: list[Habit] = field(default_factory=list)

    # Objetivo semanal
    weekly_goal: WeeklyGoal | None = None

    # Análisis por campeón
    champion_insights: list[ChampionInsight] = field(default_factory=list)

    # Recomendaciones (máx 3)
    recommendations: list[Recommendation] = field(default_factory=list)

    # Metadatos
    min_games_needed: int = _MIN_FOR_TRENDS
    games_needed_msg: str | None = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _window_dim_scores(scored: list[tuple], dim_name: str) -> list[float]:
    """Scores de una dimensión para un slice de scored_matches."""
    result = []
    for _, ms in scored:
        for d in ms.dimensions:
            if d.name == dim_name and d.score is not None:
                result.append(d.score)
                break
    return result


def _avg(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))


def _insight_confidence(n_recent: int, n_baseline: int, std_r: float, avg_r: float | None) -> str:
    if n_recent < _CONF_MED or n_baseline < _CONF_MED:
        return "low"
    cv = (std_r / avg_r) if (avg_r and avg_r > 0) else 1.0
    if n_recent >= _CONF_HIGH and n_baseline >= _CONF_HIGH and cv < 0.35:
        return "high"
    return "medium"


def _dominant_champion(scored: list[tuple]) -> str | None:
    counts: dict[str, int] = defaultdict(int)
    for match, _ in scored:
        champ = match.get("champion")
        if champ:
            counts[champ] += 1
    return max(counts, key=counts.__getitem__) if counts else None


def _fmt_metric(key: str, val: float) -> str:
    _, hib, _, fmt = _METRIC_META.get(key, ("", True, "", "{:.1f}"))
    if "%" in fmt:
        return fmt.format(val * 100)
    return fmt.format(val)


def _metric_target_str(key: str, target: float, hib: bool) -> str:
    direction = ">" if hib else "<"
    _, _, unit, fmt = _METRIC_META.get(key, ("", True, "", "{:.1f}"))
    if "%" in fmt:
        val_str = f"{target * 100:.0f}%"
    else:
        val_str = fmt.format(target)
    return f"{direction} {val_str} {unit}".strip()


# ── Tendencias por dimensión ───────────────────────────────────────────────────

def _build_dim_trends(
    scored: list[tuple],
    dim_names: list[str],
) -> list[TrendInsight]:
    recent   = scored[:_RECENT_WINDOW]
    baseline = scored[_BASELINE_START:_BASELINE_END]

    insights: list[TrendInsight] = []

    for dim in dim_names:
        r_scores = _window_dim_scores(recent,   dim)
        b_scores = _window_dim_scores(baseline, dim)

        avg_r = _avg(r_scores)
        avg_b = _avg(b_scores)

        if avg_r is None or avg_b is None or not b_scores:
            continue

        delta     = avg_r - avg_b
        delta_pct = (delta / avg_b * 100) if avg_b else 0.0
        conf      = _insight_confidence(len(r_scores), len(b_scores), _std(r_scores), avg_r)

        # Solo mostrar insights con confianza media o alta
        if conf == "low":
            continue

        name_es = _DIM_ES.get(dim, dim)
        n_recent_label = min(len(scored), _RECENT_WINDOW)

        if abs(delta_pct) < 3:
            category = "stable"
            text     = f"Tu {name_es.lower()} se mantiene estable en las últimas {n_recent_label} partidas."
        elif delta > 0:
            category = "improving"
            text     = f"Tu {name_es.lower()} mejoró un {abs(delta_pct):.0f}% en las últimas {n_recent_label} partidas."
        else:
            category = "declining"
            text     = f"Tu {name_es.lower()} empeoró un {abs(delta_pct):.0f}% en las últimas {n_recent_label} partidas."

        insights.append(TrendInsight(
            category=category,
            dim_name=dim,
            label=text,
            delta=round(delta, 1),
            delta_pct=round(delta_pct, 1),
            confidence=conf,
            champion=None,
        ))

    return insights


# ── Tendencias por campeón ─────────────────────────────────────────────────────

def _build_champion_insights(
    scored: list[tuple],
    overall_avg: float | None,
) -> list[ChampionInsight]:
    by_champ: dict[str, list[float]] = defaultdict(list)
    role_map: dict[str, str] = {}

    for match, ms in scored[:30]:
        champ = match.get("champion", "?")
        if ms.overall_score is not None:
            by_champ[champ].append(ms.overall_score)
            role_map[champ] = match.get("role", "")

    insights = []
    for champ, scores in by_champ.items():
        if len(scores) < 2:
            continue
        avg = sum(scores) / len(scores)
        delta = (avg - overall_avg) if overall_avg is not None else 0.0
        insights.append(ChampionInsight(
            champion=champ, games=len(scores),
            avg_score=round(avg, 1), vs_overall=round(delta, 1),
            role=role_map.get(champ, ""),
        ))

    return sorted(insights, key=lambda c: c.avg_score, reverse=True)


# ── Hábitos ───────────────────────────────────────────────────────────────────

def _extract_metric(match: dict, ms: MatchScore, key: str) -> float | None:
    for dim in ms.dimensions:
        if key in dim.metrics:
            return dim.metrics[key]
    return None


def _build_habits(scored: list[tuple], benchmarks) -> list[Habit]:
    if not scored:
        return []

    habits: list[Habit] = []

    # Definir checks de hábitos: (metric_key, positive_if_above, threshold_factor, title_pos, title_neg)
    checks = [
        ("deaths",            False,  0.8,  "Pocas muertes",        "Demasiadas muertes"),
        ("cs_per_min",        True,   1.0,  "Buen farmeo",          "Bajo farmeo"),
        ("kill_participation",True,   0.95, "Alta participación",   "Baja participación"),
        ("time_dead_pct",     False,  0.85, "Menos tiempo muerto",  "Mucho tiempo muerto"),
    ]

    for key, positive_if_above, factor, title_pos, title_neg in checks:
        stats = benchmarks.metrics.get(key)
        if stats is None or stats.mean < 0.001:
            continue

        threshold = stats.mean * factor
        _, hib, unit, _ = _METRIC_META.get(key, ("", True, "", "{}"))

        streak  = 0
        active  = True
        for i, (match, ms) in enumerate(scored[:10]):
            val = _extract_metric(match, ms, key)
            if val is None:
                active = False
                break
            meets = (val >= threshold) if positive_if_above else (val <= threshold)
            if i == 0 and not meets:
                active = False
                streak = 0
                break
            if meets:
                streak += 1
            else:
                active = False
                break  # streak ends

        if streak < 2:
            continue

        is_positive = positive_if_above  # simplification
        th_str = f"{threshold:.0f}" if not unit else f"{threshold:.1f} {unit}"

        if is_positive:
            desc = f"{streak} partidas seguidas superando el umbral de {th_str}."
        else:
            desc = f"{streak} partidas seguidas por debajo del umbral de {th_str}."

        habits.append(Habit(
            type="positive" if is_positive else "negative",
            title=title_pos if is_positive else title_neg,
            description=desc,
            streak=streak,
            is_active=active,
        ))

    # Ordenar: activos primero, luego por streak
    habits.sort(key=lambda h: (-int(h.is_active), -h.streak))
    return habits[:5]


# ── Objetivo semanal ───────────────────────────────────────────────────────────

def _build_weekly_goal(
    scored:     list[tuple],
    benchmarks,
    worst_dim:  str | None,
) -> WeeklyGoal | None:
    if not worst_dim or len(scored) < _GOAL_WINDOW:
        return None

    # Encontrar la métrica más problemática de la peor dimensión
    # Comparar valor reciente vs media histórica usando z-scores
    recent5 = scored[:_GOAL_WINDOW]

    worst_key: str | None = None
    worst_eff_z = 0.0

    # Obtener las métricas del peor dim de la última partida (como referencia)
    if recent5:
        _, ms0 = recent5[0]
        worst_dim_obj = next((d for d in ms0.dimensions if d.name == worst_dim), None)
        if worst_dim_obj:
            for key, val in worst_dim_obj.metrics.items():
                if val is None or key not in _METRIC_META:
                    continue
                stats = benchmarks.metrics.get(key)
                if stats is None or stats.std < 0.001:
                    continue
                _, hib, _, _ = _METRIC_META[key]
                z = (val - stats.mean) / stats.std
                eff_z = z if hib else -z
                if eff_z < worst_eff_z:
                    worst_eff_z = eff_z
                    worst_key = key

    if worst_key is None:
        return None

    stats  = benchmarks.metrics[worst_key]
    label, hib, unit, _ = _METRIC_META[worst_key]

    # Target: llegar a la media histórica (razonablemente alcanzable)
    target = stats.mean

    # Contar cuántas de las últimas 5 cumplen el objetivo
    count = 0
    vals_recent5 = []
    for match, ms in recent5:
        val = _extract_metric(match, ms, worst_key)
        if val is None:
            continue
        vals_recent5.append(val)
        meets = (val >= target) if hib else (val <= target)
        if meets:
            count += 1

    total     = len(vals_recent5)
    pct       = (count / total * 100) if total else 0.0
    cur_avg   = _avg(vals_recent5) or 0.0
    target_str = _metric_target_str(worst_key, target, hib)

    if total == 0:
        return None

    if pct >= 80:
        status = "completed"
    elif pct >= 50:
        status = "on_track"
    elif pct >= 20:
        status = "at_risk"
    else:
        status = "not_started"

    # Título del objetivo
    title = f"Alcanzar {target_str} de {label}"

    # Motivación según estado
    motivations = {
        "completed":   f"¡Excelente! Conseguiste el objetivo en {count} de {total} partidas.",
        "on_track":    f"Buen progreso. {count} de {total} partidas cumpliendo el objetivo.",
        "at_risk":     f"Solo {count} de {total} partidas. Mantén el foco en este aspecto.",
        "not_started": f"Tu {label} promedio es {_fmt_metric(worst_key, cur_avg)} vs el objetivo de {target_str}.",
    }

    return WeeklyGoal(
        title=title,
        metric_key=worst_key,
        metric_label=label,
        target_value=target,
        target_str=target_str,
        current_avg=round(cur_avg, 2),
        baseline=round(stats.mean, 2),
        progress_count=count,
        total_count=total,
        pct=round(pct, 1),
        status=status,
        motivation=motivations[status],
    )


# ── Recomendaciones ────────────────────────────────────────────────────────────

def _build_recommendations(
    insights:     list[TrendInsight],
    habits:       list[Habit],
    champ_data:   list[ChampionInsight],
    overall_avg:  float | None,
) -> list[Recommendation]:
    recs: list[Recommendation] = []

    # 1. Peor tendencia declinante de alta confianza
    declining_high = [i for i in insights if i.category == "declining" and i.confidence in ("high", "medium")]
    declining_high.sort(key=lambda x: x.delta_pct)  # más negativo primero
    if declining_high:
        ins = declining_high[0]
        recs.append(Recommendation(
            rank=1,
            title=f"Reforzar {ins.dim_name}",
            body=ins.label,
            evidence=f"Caída del {abs(ins.delta_pct):.0f}% en las últimas 10 partidas con confianza {ins.confidence}.",
            impact="high",
            metric_key=None,
        ))

    # 2. Hábito negativo activo
    neg_habits = [h for h in habits if h.type == "negative" and h.is_active]
    if neg_habits:
        h = neg_habits[0]
        recs.append(Recommendation(
            rank=len(recs) + 1,
            title=f"Romper el hábito: {h.title}",
            body=h.description,
            evidence=f"Llevas {h.streak} partidas consecutivas con este patrón.",
            impact="high",
            metric_key=None,
        ))

    # 3. Campeón con rendimiento muy inferior al promedio
    if overall_avg is not None:
        bad_champs = [c for c in champ_data if c.vs_overall < -10 and c.games >= 3]
        if bad_champs:
            c = bad_champs[-1]  # el peor
            recs.append(Recommendation(
                rank=len(recs) + 1,
                title=f"Evalúa si seguir jugando {c.champion}",
                body=f"Con {c.champion} obtienes un promedio de {c.avg_score:.0f}/100, {abs(c.vs_overall):.0f} puntos por debajo de tu media.",
                evidence=f"Análisis de {c.games} partidas.",
                impact="medium",
                metric_key=None,
            ))

    # 4. Si no hay recomendaciones urgentes, reconocer la mejora más fuerte
    if not recs:
        improving = [i for i in insights if i.category == "improving" and i.confidence in ("high", "medium")]
        if improving:
            best = max(improving, key=lambda x: x.delta_pct)
            recs.append(Recommendation(
                rank=1,
                title=f"Mantén el momentum en {best.dim_name}",
                body=best.label,
                evidence=f"Mejora del {best.delta_pct:.0f}% bien documentada.",
                impact="medium",
                metric_key=None,
            ))

    # Ordenar y limitar a 3
    for i, r in enumerate(recs[:3], 1):
        r.rank = i

    return recs[:3]


# ── Timeline ───────────────────────────────────────────────────────────────────

def _build_timeline(scored: list[tuple]) -> list[TimelinePoint]:
    buckets: list[tuple[str, int, int]] = [
        ("Hoy",             0,  5),
        ("Hace 10",        5,  15),
        ("Hace 20",       15,  25),
        ("Hace 30",       25,  35),
        ("Hace 50",       35,  50),
    ]

    points: list[TimelinePoint] = []
    for label, start, end in buckets:
        window = scored[start:end]
        if not window:
            continue
        overall_scores = [ms.overall_score for _, ms in window if ms.overall_score is not None]
        avg = _avg(overall_scores)
        dom = _dominant_champion(window)
        points.append(TimelinePoint(
            label=label,
            games_ago_start=start,
            games_ago_end=end,
            avg_score=round(avg, 1) if avg is not None else None,
            dominant_champion=dom,
            sample_size=len(window),
            trend_arrow="",  # se rellena en un segundo paso
        ))

    # Calcular flechas comparando punto actual vs anterior (reversed = oldest first)
    for i in range(len(points) - 1):
        newer = points[i]
        older = points[i + 1]
        if newer.avg_score is not None and older.avg_score is not None:
            diff = newer.avg_score - older.avg_score
            points[i].trend_arrow = "up" if diff > 2 else "down" if diff < -2 else "flat"

    return list(reversed(points))  # oldest → newest para el timeline visual


# ── Build principal ────────────────────────────────────────────────────────────

def build_progress() -> ProgressViewModel:
    puuid = db.get_config("puuid")
    if not puuid:
        return ProgressViewModel(has_data=False)

    all_matches = db.get_matches(puuid, limit=_MAX_MATCHES + 20)

    # Detectar rol primario (el que tiene más partidas)
    role_counts: dict[str, int] = defaultdict(int)
    for m in all_matches:
        r = m.get("role", "")
        if r in ("ADC", "TOP"):
            role_counts[r] += 1

    if not role_counts:
        return ProgressViewModel(has_data=False, games_needed_msg="No hay partidas de ADC o TOP.")

    primary_role = max(role_counts, key=role_counts.__getitem__)
    role_matches = [m for m in all_matches if m.get("role") == primary_role][:_MAX_MATCHES]

    if len(role_matches) < _MIN_FOR_TRENDS:
        needed = _MIN_FOR_TRENDS - len(role_matches)
        return ProgressViewModel(
            has_data=False,
            role=primary_role,
            total_matches=len(role_matches),
            games_needed_msg=f"Necesitas {needed} partidas más de {primary_role} para ver tu progreso.",
        )

    # Escorar todas las partidas (más reciente primero)
    scored: list[tuple] = []
    for match in role_matches:
        ms = score_match(match, role_matches)
        if ms is not None:
            scored.append((match, ms))

    if len(scored) < _MIN_FOR_TRENDS:
        return ProgressViewModel(has_data=False, role=primary_role,
                                 games_needed_msg="Datos insuficientes para generar análisis.")

    # Promedios generales
    overall_scores = [ms.overall_score for _, ms in scored if ms.overall_score is not None]
    recent_scores  = [ms.overall_score for _, ms in scored[:_RECENT_WINDOW] if ms.overall_score is not None]
    baseline_s     = [ms.overall_score for _, ms in scored[_BASELINE_START:_BASELINE_END] if ms.overall_score is not None]

    avg_recent   = _avg(recent_scores)
    avg_baseline = _avg(baseline_s)

    overall_delta = round(avg_recent - avg_baseline, 1) if (avg_recent and avg_baseline) else None

    if overall_delta is None or abs(overall_delta) < 3:
        trend       = "stable"
        trend_label = "Estable"
    elif overall_delta > 0:
        trend       = "improving"
        trend_label = "Mejorando"
    else:
        trend       = "declining"
        trend_label = "Necesita atención"

    # Confianza global
    n = len(scored)
    if n >= 30:
        conf = "reliable"
    elif n >= 15:
        conf = "preliminary"
    else:
        conf = "insufficient"

    # Nombres de dimensiones presentes
    dim_names: list[str] = []
    if scored:
        _, ms0 = scored[0]
        dim_names = [d.name for d in ms0.dimensions]

    # Benchmarks del jugador (para hábitos y objetivo)
    player_result = analyze_player(role_matches, primary_role)

    # Timeline
    timeline    = _build_timeline(scored)
    score_series = list(reversed(overall_scores[:30]))  # oldest→newest para sparkline

    # Insights de tendencia por dimensión
    all_insights = _build_dim_trends(scored, dim_names)
    improving = [i for i in all_insights if i.category == "improving"]
    declining = [i for i in all_insights if i.category == "declining"]
    stable    = [i for i in all_insights if i.category == "stable"]

    # Hábitos
    habits = _build_habits(scored, player_result.benchmarks)

    # Objetivo semanal — enfocado en la peor tendencia declinante
    worst_dim = declining[0].dim_name if declining else (stable[0].dim_name if stable else None)
    weekly_goal = _build_weekly_goal(scored, player_result.benchmarks, worst_dim)

    # Análisis por campeón
    champion_insights = _build_champion_insights(scored, _avg(overall_scores))

    # Recomendaciones
    recommendations = _build_recommendations(all_insights, habits, champion_insights, _avg(overall_scores))

    return ProgressViewModel(
        has_data=True,
        role=primary_role,
        total_matches=len(scored),
        overall_trend=trend,
        overall_trend_label=trend_label,
        overall_delta=overall_delta,
        avg_recent=round(avg_recent, 1) if avg_recent else None,
        confidence=conf,
        timeline=timeline,
        score_series=score_series,
        improving=improving[:4],
        declining=declining[:4],
        stable=stable[:3],
        habits=habits,
        weekly_goal=weekly_goal,
        champion_insights=champion_insights[:5],
        recommendations=recommendations,
        min_games_needed=_MIN_FOR_TRENDS,
        games_needed_msg=None,
    )
