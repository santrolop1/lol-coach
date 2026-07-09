"""
backend/knowledge/insights.py — Generación de insights específicos y accionables.

Max 5 insights, priorizados por impacto y confianza.
Cada insight responde: ¿qué pasa, con qué evidencia?

No genera frases genéricas. Todo basado en números del jugador.
"""

from __future__ import annotations

from backend.knowledge.models import Insight, Pattern
from backend.knowledge import confidence as conf_mod
from backend.services.priority_engine import Priority


# ── Helpers ────────────────────────────────────────────────────────────────────

def _avg(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _get_metric(ms, key: str) -> float | None:
    for dim in ms.dimensions:
        if key in dim.metrics:
            v = dim.metrics[key]
            return v if v is not None else None
    return None


# ── Insight desde la prioridad principal ──────────────────────────────────────

def _from_priority(pri: Priority, n_games: int) -> Insight | None:
    if pri.current_value is None or pri.target_value is None:
        return None

    gap_pct = abs(pri.current_value - pri.target_value) / max(abs(pri.current_value), 0.001) * 100
    conf    = conf_mod.calc_confidence(n_games, consistency=0.65, std_ratio=0.25)

    if not conf_mod.is_sufficient(conf):
        return None

    category = "negative" if pri.impact_score >= 12 else "neutral"

    text = (
        f"Tu mayor oportunidad de mejora es {pri.title.lower()}: "
        f"{pri.current_value:.1f} {_unit(pri.metric_key)} en tus partidas "
        f"vs {pri.target_value:.1f} en tus victorias "
        f"({gap_pct:.0f}% de diferencia)."
    )

    return Insight(
        rank=1,
        text=text,
        evidence=pri.evidence,
        category=category,
        confidence=conf,
    )


def _unit(key: str) -> str:
    units = {
        "deaths":   "muertes",
        "cs_pm":    "CS/min",
        "damage_pm":"daño/min",
        "vision_pm":"visión/min",
        "obj_pm":   "daño obj/min",
    }
    return units.get(key, "")


# ── Insight desde tendencias de dimensiones ───────────────────────────────────

def _dim_es(name: str) -> str:
    return {
        "Economy": "Economía", "Positioning": "Posicionamiento",
        "Combat Impact": "Impacto en combate", "Lane Control": "Control de línea",
        "Pressure": "Presión", "Survival": "Supervivencia",
    }.get(name, name)


def _from_dim_trend(
    dim_name: str,
    recent_avg: float,
    baseline_avg: float,
    n_recent: int,
    n_baseline: int,
) -> Insight | None:
    delta     = recent_avg - baseline_avg
    delta_pct = abs(delta) / max(baseline_avg, 1) * 100
    if delta_pct < 5 or n_recent < 5 or n_baseline < 5:
        return None

    conf = conf_mod.calc_confidence(n_recent + n_baseline, consistency=0.7, std_ratio=0.25)
    if not conf_mod.is_sufficient(conf):
        return None

    name_es  = _dim_es(dim_name)
    category = "positive" if delta > 0 else "negative"

    if delta > 0:
        text = (
            f"Tu {name_es.lower()} mejoró un {delta_pct:.0f}% durante las últimas "
            f"{n_recent} partidas: de {baseline_avg:.0f} a {recent_avg:.0f} puntos."
        )
    else:
        text = (
            f"Tu {name_es.lower()} cayó un {delta_pct:.0f}% en las últimas "
            f"{n_recent} partidas: de {baseline_avg:.0f} a {recent_avg:.0f} puntos."
        )

    return Insight(
        rank=2,
        text=text,
        evidence=f"Comparativa de {n_recent} partidas recientes vs {n_baseline} anteriores.",
        category=category,
        confidence=conf,
    )


# ── Insight desde patrones ────────────────────────────────────────────────────

def _from_pattern(pattern: Pattern, rank: int) -> Insight:
    return Insight(
        rank=rank,
        text=pattern.description,
        evidence=pattern.evidence,
        category="negative" if pattern.category in ("death", "pool") else
                 "positive" if pattern.category == "trend" else "neutral",
        confidence=pattern.confidence,
    )


# ── Insight desde sesión ──────────────────────────────────────────────────────

def _from_session(scored_session: list[tuple]) -> Insight | None:
    if len(scored_session) < 2:
        return None

    scores = [ms.overall_score for _, ms in scored_session if ms.overall_score is not None]
    wins   = sum(1 for m, _ in scored_session if m.get("result") == "WIN")

    if not scores:
        return None

    avg_score = sum(scores) / len(scores)
    winrate   = wins / len(scored_session)
    n         = len(scored_session)
    conf      = conf_mod.calc_confidence(n, consistency=winrate, std_ratio=0.2)

    if winrate >= 0.6 and avg_score >= 65:
        text = (
            f"En la sesión de hoy ({n} partidas) obtuviste {avg_score:.0f}/100 de promedio "
            f"con {int(winrate*100)}% de winrate. Buena sesión."
        )
        category = "positive"
    elif winrate < 0.35:
        text = (
            f"En la sesión de hoy ({n} partidas) tienes un {int(winrate*100)}% de winrate. "
            "Considera descansar o cambiar el enfoque."
        )
        category = "negative"
    else:
        text = (
            f"Sesión de hoy: {n} partidas, {avg_score:.0f}/100 de promedio, "
            f"{wins}W-{n-wins}L."
        )
        category = "neutral"

    return Insight(rank=5, text=text, evidence="Partidas de las últimas 4 horas.", category=category, confidence=conf)


# ── Build principal ────────────────────────────────────────────────────────────

def build_insights(
    scored:          list[tuple],
    scored_session:  list[tuple],
    priorities:      list[Priority],
    patterns:        list[Pattern],
    dim_trends:      list[dict],   # [{"name", "recent_avg", "baseline_avg", "n_recent", "n_baseline"}]
) -> list[Insight]:
    candidates: list[Insight] = []

    # 1. Desde la prioridad principal
    if priorities:
        ins = _from_priority(priorities[0], len(scored))
        if ins:
            candidates.append(ins)

    # 2. Tendencias de dimensiones (peor primero)
    declining = sorted(
        [t for t in dim_trends if t["recent_avg"] < t["baseline_avg"]],
        key=lambda t: t["recent_avg"] - t["baseline_avg"],
    )
    for t in declining[:2]:
        ins = _from_dim_trend(
            t["name"], t["recent_avg"], t["baseline_avg"],
            t["n_recent"], t["n_baseline"],
        )
        if ins:
            candidates.append(ins)

    # 3. Desde patrones detectados (máx 2)
    for i, p in enumerate(patterns[:2]):
        candidates.append(_from_pattern(p, rank=3 + i))

    # 4. Mejora más notable
    improving = sorted(
        [t for t in dim_trends if t["recent_avg"] > t["baseline_avg"] + 3],
        key=lambda t: t["recent_avg"] - t["baseline_avg"],
        reverse=True,
    )
    if improving:
        t   = improving[0]
        ins = _from_dim_trend(
            t["name"], t["recent_avg"], t["baseline_avg"],
            t["n_recent"], t["n_baseline"],
        )
        if ins:
            candidates.append(ins)

    # 5. Insight de sesión
    session_ins = _from_session(scored_session)
    if session_ins:
        candidates.append(session_ins)

    # Filtrar baja confianza, deduplicar y limitar a 5
    seen_texts: set[str] = set()
    final: list[Insight] = []
    for ins in sorted(candidates, key=lambda i: -i.confidence):
        key = ins.text[:40]
        if key not in seen_texts and conf_mod.is_sufficient(ins.confidence, threshold=0.35):
            seen_texts.add(key)
            final.append(ins)
        if len(final) == 5:
            break

    for i, ins in enumerate(final, 1):
        ins.rank = i

    return final
