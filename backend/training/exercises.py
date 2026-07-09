"""
Generación de ejercicios medibles a partir de benchmarks del jugador.
Cada ejercicio tiene condición de éxito auto-evaluable post-partida.
"""
from __future__ import annotations
import statistics
from .rules import SKILL_CATALOG, FOCUS_TIPS, SUCCESS_TEMPLATES


# ──────────────────────────────────────────────────────────────────────────────
# Thresholds adaptativos desde los benchmarks del jugador
# ──────────────────────────────────────────────────────────────────────────────

def _target_for_metric(metric_key: str, direction: str, benchmarks) -> float | None:
    """
    Deriva el umbral de éxito desde los percentiles del jugador.
    - "less_than": objetivo = p25 (mejor que el 75% de tus partidas)
    - "greater_than": objetivo = p75 (mejor que el 75% de tus partidas)
    Si no hay benchmarks, devuelve None.
    """
    if benchmarks is None:
        return None
    stats = benchmarks.metrics.get(metric_key)
    if stats is None:
        return None
    if direction == "less_than":
        return round(max(1.0, stats.p25), 1)
    return round(stats.p75, 2)


def _fallback_target(skill_key: str) -> float:
    """Umbral genérico cuando no hay suficiente historial."""
    defaults = {
        "survival":    4.0,
        "farming":     6.5,
        "impact":      0.55,
        "pressure":    150.0,
        "consistency": 55.0,
    }
    return defaults.get(skill_key, 5.0)


# ──────────────────────────────────────────────────────────────────────────────
# Textos explicativos por skill
# ──────────────────────────────────────────────────────────────────────────────

_WHY: dict[str, str] = {
    "survival": (
        "En tus derrotas mueres significativamente más que en victorias. "
        "Cada muerte regala oro y tiempo libre al rival. "
        "Reducir muertes es el cambio con mayor impacto inmediato en tu winrate."
    ),
    "farming": (
        "El CS/min determina tu poder de escala. "
        "En partidas donde farmeas bien tienes consistentemente más impacto. "
        "Mejorar la economía desbloquea la capacidad de ganar partidas incluso con mal inicio."
    ),
    "impact": (
        "Tu participación en kills baja cuando juegas de forma pasiva o llegas tarde a las peleas. "
        "Estar presente en los momentos clave es lo que convierte ventajas individuales en victorias globales."
    ),
    "pressure": (
        "Ganar la línea sin convertirlo en estructuras o dragones no se traduce en victorias. "
        "La presión macro es el puente entre el dominio individual y el cierre de partida."
    ),
    "consistency": (
        "Tienes partidas muy buenas pero también caídas bruscas. "
        "La consistencia es lo que diferencia a un jugador fiable de uno que depende del mood. "
        "Cada partida dentro del objetivo suma, incluso las que no se ganan."
    ),
}

_HOW_MEASURED: dict[str, str] = {
    "survival":    "Al finalizar cada partida el sistema comprueba automáticamente tus muertes.",
    "farming":     "Al finalizar cada partida el sistema calcula tu CS por minuto real.",
    "impact":      "Al finalizar cada partida se calcula tu participación: (kills + assists) / total kills del equipo.",
    "pressure":    "Al finalizar cada partida se calcula daño a objetivos por minuto.",
    "consistency": "Al finalizar cada partida se compara tu puntuación general contra el objetivo.",
}

_EXPECTED_GAIN: dict[str, str] = {
    "survival":    "Alcanzar el objetivo en 5 partidas se asocia con ~8-12 puntos de mejora en Posicionamiento.",
    "farming":     "Alcanzar el objetivo en 5 partidas se asocia con ~6-10 puntos de mejora en Economía.",
    "impact":      "Alcanzar el objetivo en 5 partidas se asocia con ~7-11 puntos de mejora en Impacto.",
    "pressure":    "Alcanzar el objetivo en 5 partidas se asocia con ~5-9 puntos de mejora en Presión.",
    "consistency": "Mantener la consistencia en 5 partidas consolida la base para atacar el siguiente cuello de botella.",
}

# Qué skill se desbloquea después (progresión sugerida)
_UNLOCKS: dict[str, str | None] = {
    "survival":    "farming",
    "farming":     "impact",
    "impact":      "pressure",
    "pressure":    "consistency",
    "consistency": None,
}


# ──────────────────────────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────────────────────────

def generate_exercise(skill_key: str, benchmarks, role: str) -> dict | None:
    """
    Genera la definición de un ejercicio para `skill_key`.
    Devuelve un dict serializable (sin dataclasses) para almacenar en DB.
    """
    cfg = SKILL_CATALOG.get(skill_key)
    if cfg is None:
        return None

    metric_key = cfg["primary_metric"]
    direction  = cfg["direction"]
    skill_name = cfg["name"]

    # Umbral adaptativo — derivado de benchmarks del jugador
    threshold  = _target_for_metric(metric_key, direction, benchmarks)
    if threshold is None:
        threshold = _fallback_target(skill_key)

    # Para kill_participation: expresar como decimal (0.55) pero mostrar como %
    display_thr = threshold
    if metric_key == "kill_participation":
        display_thr = threshold  # ya está en 0-1

    title = _build_title(skill_key, metric_key, threshold, direction)

    return {
        "id":               f"{skill_key}_{metric_key}_{threshold:.2f}",
        "skill_key":        skill_key,
        "skill_name":       skill_name,
        "title":            title,
        "description":      f"Ejercicio de {skill_name.lower()} durante las próximas 5 partidas.",
        "metric_key":       metric_key,
        "threshold":        threshold,
        "direction":        direction,
        "target_games":     5,
        "required_success": 4,
        "why":              _WHY.get(skill_key, ""),
        "how_measured":     _HOW_MEASURED.get(skill_key, ""),
        "expected_gain":    _EXPECTED_GAIN.get(skill_key, ""),
        "unlocks":          _UNLOCKS.get(skill_key),
    }


def _build_title(skill_key: str, metric_key: str, threshold: float, direction: str) -> str:
    if skill_key == "survival":
        return f"No morir más de {threshold:.0f} veces por partida"
    if skill_key == "farming":
        return f"Mantener ≥ {threshold:.1f} CS/min"
    if skill_key == "impact":
        pct = int(threshold * 100)
        return f"Alcanzar ≥ {pct}% de participación en kills"
    if skill_key == "pressure":
        return f"Conseguir ≥ {threshold:.0f} de daño a objetivos/min"
    if skill_key == "consistency":
        return f"Mantener puntuación ≥ {threshold:.0f} en cada partida"
    return f"Mejorar {metric_key}"


def build_daily_focus_tip(skill_key: str, threshold: float, direction: str) -> tuple[str, str]:
    """Devuelve (focus_tip, success_condition) para el DailyPlan."""
    tip = FOCUS_TIPS.get(skill_key, "Mantén la concentración durante toda la partida.")
    tpl = SUCCESS_TEMPLATES.get(skill_key, "Si cumples el objetivo")
    sc  = tpl.format(threshold=threshold)
    return tip, sc
