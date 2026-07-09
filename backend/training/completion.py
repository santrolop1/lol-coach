"""
Lógica de detección de ejercicio completado y transición al siguiente.
"""
from __future__ import annotations
from datetime import datetime, timezone


def is_complete(exercise: dict, success_count: int, games_checked: int) -> bool:
    required     = exercise.get("required_success", 4)
    target_games = exercise.get("target_games", 5)
    return games_checked >= target_games and success_count >= required


def complete_and_advance(
    state: dict,
    exercise: dict,
    success_count: int,
    score_before: float | None,
    score_after:  float | None,
) -> dict:
    """Marca el ejercicio como completado y actualiza el estado."""
    now = datetime.now(timezone.utc).isoformat()

    impact = 0.0
    if score_before is not None and score_after is not None:
        impact = round(score_after - score_before, 1)

    history_entry = {
        "exercise_id":   exercise["id"],
        "skill_key":     exercise["skill_key"],
        "skill_name":    exercise.get("skill_name", exercise["skill_key"]),
        "title":         exercise["title"],
        "started_at":    exercise.get("started_at", now),
        "completed_at":  now,
        "games_checked": exercise.get("target_games", 5),
        "success_count": success_count,
        "impact":        impact,
    }

    completed_keys = state.get("completed_skill_keys", [])
    skill_key = exercise["skill_key"]
    if skill_key not in completed_keys:
        completed_keys = completed_keys + [skill_key]

    new_state = dict(state)
    new_state["history"]              = state.get("history", []) + [history_entry]
    new_state["completed_skill_keys"] = completed_keys
    new_state["active_exercise"]      = None
    new_state["active_skill"]         = exercise.get("unlocks")

    return new_state


def current_exercise_status(success_count: int, games_checked: int, target_games: int, required: int) -> str:
    if games_checked == 0:
        return "active"
    pct = success_count / max(1, games_checked)
    if games_checked >= target_games and success_count >= required:
        return "completed"
    needed_remaining = required - success_count
    remaining_games  = target_games - games_checked
    if remaining_games > 0 and needed_remaining > remaining_games:
        return "failed"
    return "active"
