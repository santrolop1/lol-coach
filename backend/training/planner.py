"""
Generación de planes: diario, semanal y hoja de ruta mensual.
No contiene lógica de negocio — solo transforma datos en planes estructurados.
"""
from __future__ import annotations
from .models import DailyPlan, WeeklySlot, TrainingHistoryEntry
from .exercises import build_daily_focus_tip
from .rules import ROLE_PROGRESSION, SKILL_CATALOG


def build_daily_plan(
    active_exercise: dict | None,
    success_count: int,
    games_checked: int,
) -> DailyPlan | None:
    if active_exercise is None:
        return None

    skill_key   = active_exercise["skill_key"]
    skill_name  = active_exercise.get("skill_name", skill_key)
    threshold   = active_exercise["threshold"]
    direction   = active_exercise["direction"]
    target      = active_exercise.get("target_games", 5)
    remaining   = max(0, target - games_checked)

    focus_tip, success_condition = build_daily_focus_tip(skill_key, threshold, direction)

    if success_count >= active_exercise.get("required_success", 4):
        priority_label = "Alta — ¡casi completado!"
    elif games_checked == 0:
        priority_label = "Alta — primer día"
    else:
        priority_label = "Alta" if remaining <= 2 else "Media"

    return DailyPlan(
        skill_name        = skill_name,
        exercise_title    = active_exercise["title"],
        focus_tip         = focus_tip,
        success_condition = success_condition,
        estimated_games   = remaining if remaining > 0 else 1,
        priority_label    = priority_label,
    )


def build_weekly_roadmap(
    role: str,
    active_skill_key: str | None,
    completed_skill_keys: list[str],
    history: list[dict],
) -> list[WeeklySlot]:
    """
    Construye un roadmap de 4 semanas mostrando el progreso del jugador.
    Semanas pasadas = skills completadas. Semana actual = activa. Futuras = próximas.
    """
    progression = ROLE_PROGRESSION.get(role.upper(), ROLE_PROGRESSION["ADC"])
    slots: list[WeeklySlot] = []

    # Intentar asignar semanas desde el historial real
    completed_ordered: list[str] = []
    for entry in history:
        if entry["skill_key"] not in completed_ordered:
            completed_ordered.append(entry["skill_key"])

    # Rellenar con el orden de progresión para skills no historizadas
    for sk in progression:
        if sk in completed_skill_keys and sk not in completed_ordered:
            completed_ordered.append(sk)

    # Construir slots para máx. 4 semanas
    shown_skills: list[str] = []

    # Semanas pasadas (completadas)
    for sk in completed_ordered[:3]:
        cfg = SKILL_CATALOG.get(sk, {})
        entry = next((h for h in reversed(history) if h["skill_key"] == sk), None)
        goal_str = entry["title"] if entry else cfg.get("name", sk)
        shown_skills.append(sk)
        slots.append(WeeklySlot(
            week       = len(shown_skills),
            skill_name = cfg.get("name", sk),
            skill_key  = sk,
            is_current = False,
            status     = "completed",
            goal_str   = goal_str,
        ))

    # Semana actual
    if active_skill_key and active_skill_key not in shown_skills:
        cfg = SKILL_CATALOG.get(active_skill_key, {})
        shown_skills.append(active_skill_key)
        slots.append(WeeklySlot(
            week       = len(shown_skills),
            skill_name = cfg.get("name", active_skill_key),
            skill_key  = active_skill_key,
            is_current = True,
            status     = "active",
            goal_str   = cfg.get("description", ""),
        ))

    # Semanas futuras (rellenar hasta 4)
    for sk in progression:
        if sk in shown_skills:
            continue
        if len(slots) >= 4:
            break
        cfg = SKILL_CATALOG.get(sk, {})
        shown_skills.append(sk)
        slots.append(WeeklySlot(
            week       = len(shown_skills),
            skill_name = cfg.get("name", sk),
            skill_key  = sk,
            is_current = False,
            status     = "upcoming",
            goal_str   = cfg.get("description", ""),
        ))

    # Reajustar números de semana si no empezamos desde 1
    for i, slot in enumerate(slots):
        slot.week = i + 1

    return slots[:4]


def build_history(raw_history: list[dict]) -> list[TrainingHistoryEntry]:
    entries: list[TrainingHistoryEntry] = []
    for h in reversed(raw_history):   # más reciente primero
        entries.append(TrainingHistoryEntry(
            exercise_id   = h.get("exercise_id", ""),
            skill_key     = h.get("skill_key", ""),
            skill_name    = h.get("skill_name", h.get("skill_key", "")),
            title         = h.get("title", ""),
            started_at    = h.get("started_at", ""),
            completed_at  = h.get("completed_at"),
            games_checked = h.get("games_checked", 0),
            success_count = h.get("success_count", 0),
            impact        = h.get("impact", 0.0),
        ))
    return entries
