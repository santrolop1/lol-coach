"""
backend/knowledge/engine.py — Orquestador del Knowledge Engine.

Responde: ¿Qué debería decirle al jugador en este momento?

No duplica análisis. Reutiliza:
  - scorer_v2         → scores por partida y benchmarks
  - priority_engine   → prioridades win/loss accionables
  - knowledge.memory  → objetivos adaptativos persistentes
  - knowledge.rules   → detección de patrones
  - knowledge.insights → generación de insights
  - knowledge.recommendations → recomendaciones priorizadas
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone, timedelta

import db
import scorer_v2
from scorer_v2 import score_match, analyze_player
from backend.services.priority_engine import compute_priorities

from backend.knowledge import memory as mem_mod
from backend.knowledge import rules
from backend.knowledge import insights as insights_mod
from backend.knowledge import recommendations as recs_mod
from backend.knowledge import confidence as conf_mod
from backend.knowledge.models import (
    KnowledgeViewModel, SessionSummary, SessionMatch,
    Goal, MemoryEntry,
)


# ── Configuración ──────────────────────────────────────────────────────────────

_MAX_MATCHES    = 50
_MIN_FOR_ENGINE = 10
_SESSION_HOURS  = 4         # ventana de "sesión activa"

# Métricas que el Knowledge Engine puede usar como objetivo
_GOAL_CANDIDATES: dict[str, tuple[str, bool, float]] = {
    # key → (label_es, higher_is_better, tol_factor)
    "deaths":             ("muertes",             False, 1.0),
    "cs_per_min":         ("CS/min",              True,  1.0),
    "kill_participation": ("participación kills",  True,  1.0),
    "time_dead_pct":      ("tiempo muerto",        False, 1.0),
    "gold_per_min":       ("oro/min",              True,  1.0),
}

# Cómo formatear los targets de objetivo
_TARGET_FMT: dict[str, str] = {
    "deaths":             "< {:.0f}",
    "cs_per_min":         "> {:.1f}",
    "kill_participation": "> {:.0f}%",
    "time_dead_pct":      "< {:.0f}%",
    "gold_per_min":       "> {:.0f}",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _avg(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _get_metric_from_ms(ms, key: str) -> float | None:
    for dim in ms.dimensions:
        if key in dim.metrics:
            v = dim.metrics[key]
            return v if v is not None else None
    return None


def _best_worst_dim(ms) -> tuple[str | None, str | None]:
    scored = [d for d in ms.dimensions if d.score is not None]
    if not scored:
        return None, None
    best  = max(scored, key=lambda d: d.score)
    worst = min(scored, key=lambda d: d.score)
    _es = {
        "Economy": "Economía", "Positioning": "Posicionamiento",
        "Combat Impact": "Impacto", "Lane Control": "Línea",
        "Pressure": "Presión", "Survival": "Supervivencia",
    }
    return _es.get(best.name, best.name), _es.get(worst.name, worst.name)


# ── Detección de sesión ────────────────────────────────────────────────────────

def _detect_session(
    all_matches: list[dict],
    role_matches: list[dict],
) -> list[dict]:
    """Devuelve las partidas jugadas en las últimas _SESSION_HOURS horas."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=_SESSION_HOURS)

    session: list[dict] = []
    for m in all_matches:
        played_at_raw = m.get("played_at") or ""
        try:
            played_at = datetime.fromisoformat(played_at_raw.replace("Z", "+00:00"))
            if played_at.tzinfo is None:
                played_at = played_at.replace(tzinfo=timezone.utc)
        except (ValueError, AttributeError):
            continue
        if played_at >= cutoff:
            session.append(m)

    return session


def _build_session_summary(
    session_matches: list[dict],
    role_matches:    list[dict],
    active_goal:     dict | None,
) -> tuple[SessionSummary, list[tuple]]:
    if not session_matches:
        return SessionSummary(has_session=False), []

    # Escorar solo las partidas de la sesión
    scored_session: list[tuple] = []
    for m in session_matches:
        ms = score_match(m, role_matches)
        if ms is not None:
            scored_session.append((m, ms))

    wins   = sum(1 for m, _ in scored_session if m.get("result") == "WIN")
    total  = len(scored_session)
    scores = [ms.overall_score for _, ms in scored_session if ms.overall_score is not None]
    avg_s  = _avg(scores)

    # Mejor y peor aspecto (dimensión más frecuente entre best/worst)
    best_counts: dict[str, int]  = defaultdict(int)
    worst_counts: dict[str, int] = defaultdict(int)
    for _, ms in scored_session:
        b, w = _best_worst_dim(ms)
        if b:
            best_counts[b] += 1
        if w:
            worst_counts[w] += 1

    best_aspect  = max(best_counts,  key=best_counts.__getitem__)  if best_counts  else None
    worst_aspect = max(worst_counts, key=worst_counts.__getitem__) if worst_counts else None

    # Progreso del objetivo activo en la sesión
    goal_progress = None
    if active_goal:
        key = active_goal.get("metric_key", "")
        target = active_goal.get("target_value")
        hib    = active_goal.get("higher_is_better", True)
        if target is not None:
            count = 0
            for m, ms in scored_session:
                v = _get_metric_from_ms(ms, key)
                if v is not None:
                    meets = (v >= target) if hib else (v <= target)
                    if meets:
                        count += 1
            goal_progress = f"{count} / {total} partidas cumpliendo el objetivo"

    # Tip de sesión
    if wins / total < 0.35 and total >= 3:
        tip = "Llevas varias derrotas seguidas. Considera tomar un descanso de 15 minutos."
    elif avg_s and avg_s >= 75:
        tip = "Excelente sesión. Mantén el foco y no fuerces la victoria."
    else:
        tip = None

    # Matches de sesión simplificados
    match_objs: list[SessionMatch] = []
    for m, ms in scored_session:
        b, w = _best_worst_dim(ms)
        match_objs.append(SessionMatch(
            match_id=m.get("match_id", ""),
            champion=m.get("champion", "?"),
            role=m.get("role", ""),
            is_win=m.get("result") == "WIN",
            kda=f"{m.get('kills',0)}/{m.get('deaths',0)}/{m.get('assists',0)}",
            overall_score=ms.overall_score,
            best_dim=b,
            worst_dim=w,
        ))

    return SessionSummary(
        has_session=True,
        total_games=total,
        wins=wins,
        losses=total - wins,
        avg_score=round(avg_s, 1) if avg_s else None,
        best_aspect=best_aspect,
        worst_aspect=worst_aspect,
        goal_progress=goal_progress,
        tip=tip,
        session_label="Hoy",
        matches=match_objs,
    ), scored_session


# ── Evaluación y actualización del objetivo activo ────────────────────────────

def _evaluate_and_refresh_goal(
    mem:         dict,
    scored:      list[tuple],
    benchmarks,
    priorities,
    role:        str,
) -> dict | None:
    """
    1. Si hay objetivo activo, evalúa si está completado (4/5 recientes).
    2. Si completado → marca done, crea nuevo.
    3. Si no hay objetivo → crea uno.
    """
    active = mem_mod.get_active(mem)

    if active:
        key    = active.get("metric_key", "")
        target = active.get("target_value")
        hib    = active.get("higher_is_better", True)
        window = active.get("check_window", 5)

        if target is not None:
            count = 0
            checked = 0
            for _, ms in scored[:window]:
                v = _get_metric_from_ms(ms, key)
                if v is not None:
                    checked += 1
                    meets = (v >= target) if hib else (v <= target)
                    if meets:
                        count += 1

            # Si >= 80% de las ventanas cumplieron el objetivo → completado
            if checked >= 3 and count / checked >= 0.8:
                mem_mod.complete_goal(mem, active["id"])
                active = None  # crear nuevo

    if active is None:
        # Seleccionar nuevo objetivo desde la prioridad más alta no usada recientemente
        used = mem_mod.recently_targeted_keys(mem, n=3)

        # Intentar con prioridades primero
        for pri in priorities:
            key = pri.metric_key
            if key in used:
                continue
            # Mapear clave de priority_engine a la de scorer_v2
            # priority_engine usa "deaths", "cs_pm", "kill_participation", "damage_pm"
            # para la memoria usamos las mismas claves pero los valores los verificamos
            # contra el target de la prioridad
            target = pri.target_value
            if target is None:
                continue
            label_map = {
                "deaths": "muertes", "cs_pm": "CS/min",
                "kill_participation": "participación en kills",
                "damage_pm": "daño/min", "vision_pm": "visión/min", "obj_pm": "obj/min",
            }
            label = label_map.get(key, key)
            hib   = not bool({"deaths", "obj_pm"} & {key})

            # Formato del target
            fmt_map = {
                "deaths": "< {:.0f}", "cs_pm": "> {:.1f}",
                "kill_participation": "> {:.0f}%",
                "damage_pm": "> {:.0f}", "vision_pm": "> {:.1f}", "obj_pm": "> {:.1f}",
            }
            target_str = fmt_map.get(key, "> {:.1f}").format(target)

            active = mem_mod.add_goal(
                mem, key, label, target, target_str, hib
            )
            break

        # Si no hay prioridades, usar benchmarks del peor dimension de scorer_v2
        if active is None and benchmarks:
            for key, (label, hib, _) in _GOAL_CANDIDATES.items():
                if key in used:
                    continue
                stats = benchmarks.metrics.get(key)
                if stats is None:
                    continue
                target = stats.mean
                fmt    = _TARGET_FMT.get(key, "> {:.1f}")
                val    = target * 100 if "pct" in key else target
                target_str = fmt.format(val)
                active = mem_mod.add_goal(mem, key, label, target, target_str, hib)
                break

    return active


# ── Trends de dimensiones (para insights) ─────────────────────────────────────

def _compute_dim_trends(scored: list[tuple], dim_names: list[str]) -> list[dict]:
    recent   = scored[:10]
    baseline = scored[10:30]

    results = []
    for dim in dim_names:
        r_scores = [
            d.score for _, ms in recent
            for d in ms.dimensions
            if d.name == dim and d.score is not None
        ]
        b_scores = [
            d.score for _, ms in baseline
            for d in ms.dimensions
            if d.name == dim and d.score is not None
        ]
        if not r_scores or not b_scores:
            continue
        results.append({
            "name":         dim,
            "recent_avg":   sum(r_scores) / len(r_scores),
            "baseline_avg": sum(b_scores) / len(b_scores),
            "n_recent":     len(r_scores),
            "n_baseline":   len(b_scores),
        })
    return results


# ── Build principal ────────────────────────────────────────────────────────────

def build_knowledge() -> KnowledgeViewModel:
    puuid = db.get_config("puuid")
    if not puuid:
        return KnowledgeViewModel(has_data=False)

    all_matches = db.get_matches(puuid, limit=_MAX_MATCHES + 10)

    # Detectar rol primario
    role_counts: dict[str, int] = defaultdict(int)
    for m in all_matches:
        r = m.get("role", "")
        if r in ("ADC", "TOP"):
            role_counts[r] += 1

    if not role_counts:
        return KnowledgeViewModel(has_data=False, games_needed_msg="Sin partidas de ADC o TOP.")

    primary_role  = max(role_counts, key=role_counts.__getitem__)
    role_matches  = [m for m in all_matches if m.get("role") == primary_role][:_MAX_MATCHES]

    if len(role_matches) < _MIN_FOR_ENGINE:
        needed = _MIN_FOR_ENGINE - len(role_matches)
        return KnowledgeViewModel(
            has_data=False,
            role=primary_role,
            total_matches=len(role_matches),
            games_needed_msg=f"Necesitas {needed} partidas más de {primary_role} para el coaching.",
        )

    # Escorar todas las partidas de rol (más reciente primero)
    scored: list[tuple] = []
    for m in role_matches:
        ms = score_match(m, role_matches)
        if ms is not None:
            scored.append((m, ms))

    if len(scored) < _MIN_FOR_ENGINE:
        return KnowledgeViewModel(has_data=False, games_needed_msg="Datos insuficientes.")

    overall_scores = [ms.overall_score for _, ms in scored if ms.overall_score is not None]
    overall_avg    = _avg(overall_scores)

    # Análisis de jugador (benchmarks)
    player_result = analyze_player(role_matches, primary_role)

    # Prioridades win/loss
    priorities = compute_priorities(role_matches, primary_role)

    # Memoria y objetivo adaptativo
    mem    = mem_mod.load()
    active_goal_dict = _evaluate_and_refresh_goal(
        mem, scored, player_result.benchmarks, priorities, primary_role
    )
    mem_mod.update_last_read(mem)

    # Sesión actual
    session_raw_matches = _detect_session(all_matches, role_matches)
    session, scored_session = _build_session_summary(
        session_raw_matches, role_matches, active_goal_dict
    )

    # Patrones
    patterns = rules.detect_all(scored, overall_avg)

    # Tendencias de dimensiones para insights
    dim_names = [d.name for d in scored[0][1].dimensions] if scored else []
    dim_trends = _compute_dim_trends(scored, dim_names)

    # Insights
    insights = insights_mod.build_insights(
        scored, scored_session, priorities, patterns, dim_trends
    )

    # Recomendaciones
    already_used = {r.metric_key for r in [] if r.metric_key}
    recommendations = recs_mod.build_recommendations(
        priorities, patterns, active_goal_dict,
        n_games=len(scored), already_used=set(),
    )

    # Construir objeto Goal a partir del dict
    goal_obj: Goal | None = None
    if active_goal_dict:
        key    = active_goal_dict.get("metric_key", "")
        target = active_goal_dict.get("target_value")
        hib    = active_goal_dict.get("higher_is_better", True)
        window = active_goal_dict.get("check_window", 5)

        progress_count = 0
        total_count    = 0
        for _, ms in scored[:window]:
            v = _get_metric_from_ms(ms, key)
            if v is not None:
                total_count += 1
                meets = (v >= target) if (hib and target is not None) else (v <= (target or 0))
                if meets:
                    progress_count += 1

        pct = (progress_count / total_count * 100) if total_count else 0.0

        goal_obj = Goal(
            id=active_goal_dict.get("id", ""),
            metric_key=key,
            metric_label=active_goal_dict.get("metric_label", key),
            target_value=active_goal_dict.get("target_value", 0.0),
            target_str=active_goal_dict.get("target_str", ""),
            higher_is_better=hib,
            check_window=window,
            status=active_goal_dict.get("status", "active"),
            created_at=active_goal_dict.get("created_at", ""),
            completed_at=active_goal_dict.get("completed_at"),
            progress_count=progress_count,
            total_count=total_count,
            pct=round(pct, 1),
        )

    # Memoria histórica
    memory_entries = mem_mod.to_memory_entries(mem)

    # Confianza global
    n = len(scored)
    confidence = "reliable" if n >= 30 else "preliminary" if n >= 15 else "insufficient"

    return KnowledgeViewModel(
        has_data=True,
        role=primary_role,
        total_matches=n,
        session=session,
        active_goal=goal_obj,
        memory=memory_entries,
        patterns=patterns,
        insights=insights,
        recommendations=recommendations,
        confidence=confidence,
    )
