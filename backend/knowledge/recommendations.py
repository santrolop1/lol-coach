"""
backend/knowledge/recommendations.py — Generación de recomendaciones priorizadas.

Max 3 recomendaciones. Cada una responde:
  ¿Por qué? ¿Con qué evidencia? ¿Qué impacto? ¿Cómo medir si mejoró?

No se genera nada sin confianza suficiente.
"""

from __future__ import annotations

from backend.knowledge.models import Recommendation, Pattern
from backend.knowledge import confidence as conf_mod
from backend.services.priority_engine import Priority


_DIFFICULTY: dict[str, str] = {
    "deaths":             "Media",
    "cs_pm":              "Baja",
    "kill_participation": "Alta",
    "damage_pm":          "Media",
    "vision_pm":          "Baja",
    "obj_pm":             "Media",
}

_GOAL_TEMPLATES: dict[str, str] = {
    "deaths":             "Mantener ≤ {target:.0f} muertes durante las próximas 5 partidas.",
    "cs_pm":              "Conseguir ≥ {target:.1f} CS/min durante las próximas 5 partidas.",
    "kill_participation": "Participar en ≥ {target:.0f}% de kills durante las próximas 5 partidas.",
    "damage_pm":          "Superar {target:.0f} de daño/min durante las próximas 5 partidas.",
    "vision_pm":          "Conseguir ≥ {target:.1f} visión/min durante las próximas 5 partidas.",
    "obj_pm":             "Superar {target:.0f} daño a objetivos/min durante las próximas 5 partidas.",
}

_IMPACT_WEIGHTS = {
    "deaths": 0.95, "cs_pm": 0.75, "kill_participation": 0.80,
    "damage_pm": 0.65, "vision_pm": 0.50, "obj_pm": 0.60,
}


def _goal_str(key: str, target: float | None) -> str:
    tpl = _GOAL_TEMPLATES.get(key, "Mejorar {target:.1f} en la próxima semana.")
    return tpl.format(target=target or 0)


def _from_priority(pri: Priority, n_games: int) -> Recommendation | None:
    conf = conf_mod.calc_confidence(n_games, consistency=0.65, std_ratio=0.3)
    if not conf_mod.is_sufficient(conf):
        return None

    impact_pct = min(int(_IMPACT_WEIGHTS.get(pri.metric_key, 0.5) * 100), 95)

    return Recommendation(
        rank=1,
        title=pri.title,
        body=pri.recommendation,
        why=pri.evidence,
        impact="Alto" if pri.impact_score >= 12 else "Medio",
        impact_pct=impact_pct,
        confidence=conf,
        difficulty=_DIFFICULTY.get(pri.metric_key, "Media"),
        goal_str=_goal_str(pri.metric_key, pri.target_value),
        metric_key=pri.metric_key,
    )


def _from_pattern(pattern: Pattern, rank: int) -> Recommendation | None:
    if not conf_mod.is_sufficient(pattern.confidence, threshold=0.50):
        return None

    return Recommendation(
        rank=rank,
        title=pattern.title,
        body=pattern.actionable,
        why=pattern.description,
        impact="Alto" if pattern.category == "death" else "Medio",
        impact_pct=70 if pattern.category == "death" else 55,
        confidence=pattern.confidence,
        difficulty="Media",
        goal_str=pattern.actionable,
        metric_key=None,
    )


def _from_active_goal(goal: dict) -> Recommendation | None:
    metric_key = goal.get("metric_key", "")
    target     = goal.get("target_value")
    label      = goal.get("metric_label", metric_key)
    target_str = goal.get("target_str", "")

    conf = 0.70  # objetivo explícito = confianza inherente alta

    return Recommendation(
        rank=3,
        title=f"Objetivo activo: {target_str} de {label}",
        body=(
            "Este es tu objetivo de la semana. Mantén el foco en él "
            "antes de trabajar en otros aspectos."
        ),
        why="Objetivo generado a partir de tu mayor cuello de botella identificado.",
        impact="Alto",
        impact_pct=80,
        confidence=conf,
        difficulty=_DIFFICULTY.get(metric_key, "Media"),
        goal_str=_goal_str(metric_key, target),
        metric_key=metric_key,
    )


def build_recommendations(
    priorities:   list[Priority],
    patterns:     list[Pattern],
    active_goal:  dict | None,
    n_games:      int,
    already_used: set[str],     # metric_keys ya usados en otros recs
) -> list[Recommendation]:
    recs: list[Recommendation] = []
    used_keys: set[str] = set()

    # 1. Prioridad principal (la más impactante según win/loss)
    for pri in priorities:
        if pri.metric_key in already_used:
            continue
        rec = _from_priority(pri, n_games)
        if rec and rec.metric_key not in used_keys:
            recs.append(rec)
            used_keys.add(rec.metric_key or "")
            break

    # 2. Patrón más relevante que no sea de la misma métrica
    for p in patterns:
        rec = _from_pattern(p, rank=len(recs) + 1)
        if rec and rec.title not in {r.title for r in recs}:
            recs.append(rec)
            break

    # 3. Objetivo activo si no está ya cubierto
    if active_goal and len(recs) < 3:
        gk  = active_goal.get("metric_key", "")
        if gk not in used_keys:
            rec = _from_active_goal(active_goal)
            if rec:
                recs.append(rec)

    # Renumerar y limitar a 3
    for i, r in enumerate(recs[:3], 1):
        r.rank = i

    return recs[:3]
