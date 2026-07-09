"""
Training Engine — orquestador principal del sistema de entrenamiento progresivo.
Consume: scorer_v2, priority_engine, db.
NO modifica coaching_engine.py ni scorer_v2.py.
"""
from __future__ import annotations
from datetime import datetime, timezone

import db
import scorer_v2
from backend.services.priority_engine import compute_priorities

from . import exercises as ex_module
from . import goals as goals_module
from . import progress as prog_module
from . import completion as comp_module
from . import planner as plan_module
from .models import TrainingViewModel, Exercise, ExerciseDot


_MIN_GAMES = 5


def build_training() -> TrainingViewModel:
    puuid = db.get_config("puuid")
    if not puuid:
        return TrainingViewModel(has_data=False, games_needed_msg="Configura tu cuenta en Ajustes.")

    all_matches = db.get_matches(puuid, limit=60)
    if not all_matches:
        return TrainingViewModel(has_data=False, games_needed_msg="Sin historial de partidas.")

    # Determinar rol dominante
    from collections import Counter
    roles = [m.get("role", "") for m in all_matches if m.get("role")]
    role  = Counter(roles).most_common(1)[0][0] if roles else "ADC"

    role_matches = [m for m in all_matches if m.get("role") == role]
    if len(role_matches) < _MIN_GAMES:
        needed = _MIN_GAMES - len(role_matches)
        return TrainingViewModel(
            has_data=False,
            games_needed_msg=f"Necesitas {needed} partida{'s' if needed > 1 else ''} más de {role} para activar el Training Engine.",
        )

    # Scoring
    scored: list[tuple] = []
    for m in role_matches:
        try:
            ms = scorer_v2.score_match(m, role_matches)
            scored.append((m, ms))
        except Exception:
            pass

    if not scored:
        return TrainingViewModel(has_data=False, games_needed_msg="Error al analizar las partidas.")

    # Análisis del jugador para benchmarks
    try:
        result = scorer_v2.analyze_player(role_matches, role)
        benchmarks  = result.benchmarks
        dim_averages = result.dimensions   # dict[str, float]
        overall_avg  = result.overall_score or 0.0
        confidence   = result.confidence_level or "insufficient"
    except Exception:
        benchmarks  = None
        dim_averages = {}
        overall_avg  = 0.0
        confidence   = "insufficient"

    # Prioridades del Priority Engine
    try:
        priorities = compute_priorities(role_matches, role)
    except Exception:
        priorities = []

    # Cargar estado de entrenamiento
    state = prog_module.load()

    # Overall scores para ejercicios de consistencia
    overall_scores = [
        ms.overall_score or 0.0
        for _, ms in scored
        if ms is not None
    ]

    # ── Seleccionar skill si no hay ninguna activa ────────────────────────────
    if not state.get("active_skill"):
        completed_keys = state.get("completed_skill_keys", [])
        skill_key = goals_module.select_skill(priorities, role, completed_keys, benchmarks)
        state["active_skill"] = skill_key

    # ── Generar ejercicio si no hay ninguno activo ────────────────────────────
    if not state.get("active_exercise"):
        skill_key = state["active_skill"]
        exercise_dict = ex_module.generate_exercise(skill_key, benchmarks, role)
        if exercise_dict:
            exercise_dict["started_at"] = datetime.now(timezone.utc).isoformat()
            state["active_exercise"] = exercise_dict
            prog_module.save(state)

    active_ex_dict = state.get("active_exercise")

    # ── Evaluar progreso del ejercicio activo ────────────────────────────────
    success_count, games_checked, dots = 0, 0, []
    if active_ex_dict:
        success_count, games_checked, dots = prog_module.evaluate_exercise(
            active_ex_dict, scored, overall_scores
        )

    # ── Detectar completación ─────────────────────────────────────────────────
    if active_ex_dict and comp_module.is_complete(active_ex_dict, success_count, games_checked):
        # Calcular impacto: score promedio en últimas 5 partidas vs previas
        recent_scores   = overall_scores[:games_checked]
        previous_scores = overall_scores[games_checked : games_checked * 2]
        before = sum(previous_scores) / len(previous_scores) if previous_scores else None
        after  = sum(recent_scores)   / len(recent_scores)   if recent_scores   else None

        state = comp_module.complete_and_advance(state, active_ex_dict, success_count, before, after)
        prog_module.save(state)

        # Seleccionar próxima skill
        if not state.get("active_skill"):
            next_skill = goals_module.select_skill(
                priorities, role, state.get("completed_skill_keys", []), benchmarks
            )
            state["active_skill"] = next_skill

        # Generar nuevo ejercicio
        next_ex = ex_module.generate_exercise(state["active_skill"], benchmarks, role)
        if next_ex:
            next_ex["started_at"] = datetime.now(timezone.utc).isoformat()
            state["active_exercise"] = next_ex
            prog_module.save(state)

        active_ex_dict = state.get("active_exercise")
        success_count, games_checked, dots = 0, 0, []
        if active_ex_dict:
            success_count, games_checked, dots = prog_module.evaluate_exercise(
                active_ex_dict, scored, overall_scores
            )

    active_ex_dict = state.get("active_exercise")
    active_sk_key  = state.get("active_skill")

    # ── Construir Exercise dataclass ─────────────────────────────────────────
    active_exercise = None
    if active_ex_dict:
        ex_status = comp_module.current_exercise_status(
            success_count, games_checked,
            active_ex_dict.get("target_games", 5),
            active_ex_dict.get("required_success", 4),
        )
        active_exercise = Exercise(
            id               = active_ex_dict["id"],
            skill_key        = active_ex_dict["skill_key"],
            skill_name       = active_ex_dict.get("skill_name", active_ex_dict["skill_key"]),
            title            = active_ex_dict["title"],
            description      = active_ex_dict.get("description", ""),
            metric_key       = active_ex_dict["metric_key"],
            threshold        = active_ex_dict["threshold"],
            direction        = active_ex_dict["direction"],
            target_games     = active_ex_dict.get("target_games", 5),
            required_success = active_ex_dict.get("required_success", 4),
            success_count    = success_count,
            games_checked    = games_checked,
            started_at       = active_ex_dict.get("started_at", ""),
            why              = active_ex_dict.get("why", ""),
            how_measured     = active_ex_dict.get("how_measured", ""),
            expected_gain    = active_ex_dict.get("expected_gain", ""),
            unlocks          = active_ex_dict.get("unlocks"),
            status           = ex_status,
            dots             = [
                ExerciseDot(
                    match_id  = d["match_id"],
                    success   = d["success"],
                    value     = d["value"],
                    played_at = d["played_at"],
                )
                for d in dots
            ],
        )

    # ── Skill Tree ────────────────────────────────────────────────────────────
    skill_tree = goals_module.build_skill_tree(
        scored              = scored,
        dim_averages        = dim_averages,
        role                = role,
        priorities          = priorities,
        completed_skill_keys = state.get("completed_skill_keys", []),
        active_skill_key    = active_sk_key,
    )

    # ── Planes ───────────────────────────────────────────────────────────────
    daily_plan   = plan_module.build_daily_plan(active_ex_dict, success_count, games_checked)
    weekly_roadmap = plan_module.build_weekly_roadmap(
        role                 = role,
        active_skill_key     = active_sk_key,
        completed_skill_keys = state.get("completed_skill_keys", []),
        history              = state.get("history", []),
    )
    history = plan_module.build_history(state.get("history", []))

    # ── Next skill preview ────────────────────────────────────────────────────
    unlocks = active_ex_dict.get("unlocks") if active_ex_dict else None
    from .rules import SKILL_CATALOG
    next_skill_name   = SKILL_CATALOG[unlocks]["name"] if unlocks and unlocks in SKILL_CATALOG else None
    next_skill_reason = (
        f"Cuando completes {active_exercise.title if active_exercise else 'este ejercicio'}, "
        f"el Training Engine activará el bloque de {next_skill_name}."
    ) if next_skill_name else None

    return TrainingViewModel(
        has_data          = True,
        role              = role,
        total_matches     = len(role_matches),
        skill_tree        = skill_tree,
        active_exercise   = active_exercise,
        daily_plan        = daily_plan,
        weekly_roadmap    = weekly_roadmap,
        history           = history,
        next_skill_name   = next_skill_name,
        next_skill_reason = next_skill_reason,
        confidence        = confidence,
    )
