"""
Persistencia del estado de entrenamiento y evaluación de ejercicios.
Estado guardado en db config bajo la clave TRAINING_KEY.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone

import db

TRAINING_KEY = "training_state_v1"

_EMPTY_STATE: dict = {
    "active_skill":           None,
    "active_exercise":        None,
    "completed_skill_keys":   [],
    "history":                [],
}


def load() -> dict:
    raw = db.get_config(TRAINING_KEY)
    if not raw:
        return dict(_EMPTY_STATE)
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return dict(_EMPTY_STATE)


def save(state: dict) -> None:
    db.save_config(TRAINING_KEY, json.dumps(state, ensure_ascii=False))


def evaluate_exercise(
    exercise: dict,
    scored: list[tuple],        # [(match_dict, MatchScore), ...]
    overall_scores: list[float],
) -> tuple[int, int, list[dict]]:
    """
    Evalúa el ejercicio activo contra las partidas recientes.
    Devuelve (success_count, games_checked, dots).
    Solo procesa partidas jugadas DESPUÉS de started_at.
    """
    from .rules import get_metric_from_ms, check_exercise_condition

    started_at    = exercise.get("started_at", "")
    metric_key    = exercise["metric_key"]
    threshold     = exercise["threshold"]
    direction     = exercise["direction"]
    target_games  = exercise.get("target_games", 5)

    # Filtrar partidas posteriores al inicio del ejercicio
    relevant: list[tuple] = []
    for match, ms in scored:
        played = match.get("played_at", "")
        if played >= started_at:
            relevant.append((match, ms))

    # Tomar las más recientes hasta target_games
    to_check = relevant[:target_games]

    dots: list[dict] = []
    success_count = 0
    for match, ms in to_check:
        if metric_key == "__overall_std__":
            idx    = scored.index((match, ms))
            val    = overall_scores[idx] if idx < len(overall_scores) else None
        else:
            val = get_metric_from_ms(ms, metric_key)

        success = False
        if val is not None:
            success = check_exercise_condition(val, threshold, direction)
            if success:
                success_count += 1

        dots.append({
            "match_id":  match.get("match_id", ""),
            "success":   success,
            "value":     val,
            "played_at": match.get("played_at", ""),
        })

    return success_count, len(to_check), dots
