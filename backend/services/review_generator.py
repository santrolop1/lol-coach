"""
backend/services/review_generator.py — Motores de análisis para Post Game Review.

Genera fortalezas, errores, foco y comparaciones a partir de datos reales.
Sin textos hardcodeados. Sin benchmarks externos.
"""

from __future__ import annotations

from .review_models import MatchComparison


# ── Thresholds ────────────────────────────────────────────────────────────────

# Diferencia mínima para calificar como "mejor/peor de lo normal"
_BETTER_THRESHOLD_PCT = 10.0   # 10% mejor que el promedio
_WORSE_THRESHOLD_PCT  = 10.0   # 10% peor que el promedio

# Para errores repetidos: cuántas de las últimas N partidas con el mismo problema
_REPEAT_STREAK = 3   # 3 seguidas = patrón
_REPEAT_OUT_OF = 5   # "X de las últimas 5"


def _safe(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _cs_pm(m: dict) -> float | None:
    cs  = _safe(m.get("cs"))
    dur = _safe(m.get("duration_sec"))
    if cs is not None and dur and dur > 60:
        return cs / (dur / 60.0)
    return None


def _dmg_pm(m: dict) -> float | None:
    dmg = _safe(m.get("damage"))
    dur = _safe(m.get("duration_sec"))
    if dmg is not None and dur and dur > 60:
        return dmg / (dur / 60.0)
    return None


# ── Clasificación de partida ──────────────────────────────────────────────────

def classify_match(
    result: str,
    score: float | None,
    score_avg: float | None,
) -> tuple[str, str]:
    """
    Clasifica la partida en: Excelente / Buena / Normal / Mala / Muy mala.
    Retorna (rating, color_hex).
    """
    if score is None:
        label = "Victoria" if result == "WIN" else "Derrota"
        color = "#22C55E" if result == "WIN" else "#EF4444"
        return label, color

    delta = score - (score_avg or score)

    if result == "WIN":
        if score >= 75 or delta >= 15:
            return "Excelente", "#22C55E"
        if score >= 55 or delta >= 0:
            return "Buena", "#8B5CF6"
        return "Normal", "#3B82F6"
    else:
        if score >= 60 or delta >= 10:
            return "Normal", "#3B82F6"
        if score >= 40 or delta >= -10:
            return "Mala", "#F59E0B"
        return "Muy mala", "#EF4444"


# ── Comparaciones métricas ────────────────────────────────────────────────────

def build_comparisons(
    match: dict,
    champ_avgs: dict,
) -> list[MatchComparison]:
    """
    Genera comparaciones métricas de esta partida vs el promedio del campeón.
    Solo incluye métricas con datos disponibles en ambos lados.
    """
    comparisons: list[MatchComparison] = []

    def _compare(label, current_val, avg_val, unit, lower_is_better=False):
        if current_val is None or avg_val is None or avg_val == 0:
            return
        delta_abs = current_val - avg_val
        delta_pct = delta_abs / abs(avg_val) * 100
        # Para lower_is_better, invertimos el signo para que positivo = mejor
        player_delta = -delta_pct if lower_is_better else delta_pct
        if player_delta >= _BETTER_THRESHOLD_PCT:
            verdict = "Mejor de lo normal"
        elif player_delta <= -_WORSE_THRESHOLD_PCT:
            verdict = "Peor de lo normal"
        else:
            verdict = "Normal"
        comparisons.append(MatchComparison(
            label     = label,
            current   = current_val,
            avg       = avg_val,
            unit      = unit,
            verdict   = verdict,
            delta_pct = player_delta,
        ))

    # Muertes
    deaths_now = _safe(match.get("deaths"))
    _compare("Muertes", deaths_now, champ_avgs.get("deaths"), "muertes", lower_is_better=True)

    # CS/min
    cs_now = _cs_pm(match)
    _compare("CS/min", cs_now, champ_avgs.get("cs_pm"), "CS/min")

    # Daño/min
    dmg_now = _dmg_pm(match)
    _compare("Daño/min", dmg_now, champ_avgs.get("damage_pm"), "daño/min")

    # KP
    kp_now = _safe(match.get("kill_participation"))
    _compare("Participación", kp_now, champ_avgs.get("kp"), "% KP")

    return comparisons


# ── Strength Engine ───────────────────────────────────────────────────────────

def build_strengths(
    comparisons: list[MatchComparison],
    match: dict,
    champ_avgs: dict,
) -> list[str]:
    """
    Genera hasta 3 fortalezas basadas en comparaciones con el promedio.
    Solo frases con datos reales.
    """
    strengths: list[str] = []

    for c in comparisons:
        if c.verdict != "Mejor de lo normal":
            continue
        if c.label == "Muertes":
            strengths.append(
                f"Menos muertes que tu promedio con este campeón "
                f"({c.current:.0f} vs {c.avg:.1f} habitual)."
            )
        elif c.label == "CS/min":
            strengths.append(
                f"Farm superior a tu media: {c.current:.1f} CS/min vs {c.avg:.1f} habitual."
            )
        elif c.label == "Daño/min":
            strengths.append(
                f"Daño/min por encima de tu promedio "
                f"({c.current:.0f} vs {c.avg:.0f} habitual)."
            )
        elif c.label == "Participación":
            strengths.append(
                f"KP superior a tu media: {c.current:.0%} vs {c.avg:.0%} habitual."
            )
        if len(strengths) == 3:
            break

    return strengths


# ── Mistake Engine ────────────────────────────────────────────────────────────

def build_mistakes(
    comparisons: list[MatchComparison],
    match: dict,
    champ_avgs: dict,
) -> list[str]:
    """
    Genera hasta 3 errores basados en comparaciones con el promedio.
    """
    mistakes: list[str] = []

    for c in comparisons:
        if c.verdict != "Peor de lo normal":
            continue
        if c.label == "Muertes":
            mistakes.append(
                f"Muertes por encima de tu promedio con este campeón "
                f"({c.current:.0f} vs {c.avg:.1f} habitual)."
            )
        elif c.label == "CS/min":
            mistakes.append(
                f"Farm inferior a tu media: {c.current:.1f} CS/min vs {c.avg:.1f} habitual."
            )
        elif c.label == "Daño/min":
            mistakes.append(
                f"Daño/min por debajo de tu promedio "
                f"({c.current:.0f} vs {c.avg:.0f} habitual)."
            )
        elif c.label == "Participación":
            mistakes.append(
                f"Participación baja en peleas: {c.current:.0%} vs {c.avg:.0%} habitual."
            )
        if len(mistakes) == 3:
            break

    return mistakes


# ── Focus Engine ──────────────────────────────────────────────────────────────

def build_focus(
    mistakes: list[str],
    comparisons: list[MatchComparison],
    champ_avgs: dict,
    priorities: list | None = None,
) -> str | None:
    """
    Genera 1 único objetivo para la próxima partida.

    Jerarquía:
    1. Peor métrica de esta partida (comparaciones con el promedio)
    2. Prioridad global del motor de prioridades (si existe)
    3. None si no hay datos
    """
    # Prioridad: la métrica más problemática de la partida actual
    worst: MatchComparison | None = None
    for c in comparisons:
        if c.verdict == "Peor de lo normal":
            if worst is None or c.delta_pct < worst.delta_pct:
                worst = c

    if worst is not None:
        avg = champ_avgs.get(worst.label.lower().replace("/", "_").replace("ó", "o").replace("participaci", "k"))
        if worst.label == "Muertes":
            target = champ_avgs.get("deaths")
            if target is not None:
                return f"Próxima partida: menos de {target:.0f} muertes."
        elif worst.label == "CS/min":
            target = champ_avgs.get("cs_pm")
            if target is not None:
                return f"Próxima partida: alcanzar {target:.1f} CS/min."
        elif worst.label == "Daño/min":
            target = champ_avgs.get("damage_pm")
            if target is not None:
                return f"Próxima partida: superar {target:.0f} daño/min."
        elif worst.label == "Participación":
            target = champ_avgs.get("kp")
            if target is not None:
                return f"Próxima partida: {target:.0%} de participación en peleas."

    # Fallback: prioridad global (si viene del Priority Engine)
    if priorities:
        p = priorities[0]
        if p.target_value is not None:
            if p.metric_key == "deaths":
                return f"Próxima partida: menos de {p.target_value:.0f} muertes."
            elif p.metric_key == "cs_pm":
                return f"Próxima partida: alcanzar {p.target_value:.1f} CS/min."
            elif p.metric_key == "kill_participation":
                return f"Próxima partida: {p.target_value:.0%} de KP."

    return None


# ── Repeated Mistakes ─────────────────────────────────────────────────────────

def detect_repeated_mistakes(
    champion: str,
    history: list[dict],
    exclude_match_id: str | None = None,
) -> list[str]:
    """
    Detecta errores repetidos en las últimas partidas del campeón.

    Analiza muertes, farm y participación.
    Devuelve frases descriptivas de los patrones detectados.
    """
    champ_hist = [
        m for m in history
        if m.get("champion") == champion
        and (exclude_match_id is None or m.get("match_id") != exclude_match_id)
    ]
    recent = champ_hist[:_REPEAT_OUT_OF]
    if len(recent) < _REPEAT_STREAK:
        return []

    # Necesitamos promedios globales del campeón para referencia
    all_deaths  = [_safe(m.get("deaths"))            for m in champ_hist if _safe(m.get("deaths")) is not None]
    all_cs      = [_cs_pm(m)                         for m in champ_hist if _cs_pm(m) is not None]
    all_kp      = [_safe(m.get("kill_participation")) for m in champ_hist if _safe(m.get("kill_participation")) is not None]

    if not all_deaths:
        return []

    import statistics as _stats
    avg_deaths = _stats.mean(all_deaths) if all_deaths else None
    avg_cs     = _stats.mean(all_cs)     if all_cs     else None
    avg_kp     = _stats.mean(all_kp)     if all_kp     else None

    repeated: list[str] = []

    # Muertes elevadas
    if avg_deaths is not None:
        high_death_count = sum(
            1 for m in recent
            if (_safe(m.get("deaths")) or 0) > avg_deaths * 1.20
        )
        if high_death_count >= _REPEAT_STREAK:
            repeated.append(
                f"Exceso de muertes detectado en {high_death_count} "
                f"de las últimas {len(recent)} partidas con {champion}."
            )

    # Farm bajo
    if avg_cs is not None:
        low_cs_count = sum(
            1 for m in recent
            if (_cs_pm(m) or float("inf")) < avg_cs * 0.85
        )
        if low_cs_count >= _REPEAT_STREAK:
            repeated.append(
                f"Farm por debajo de tu media en {low_cs_count} "
                f"de las últimas {len(recent)} partidas con {champion}."
            )

    # KP bajo
    if avg_kp is not None:
        low_kp_count = sum(
            1 for m in recent
            if (_safe(m.get("kill_participation")) or 1.0) < avg_kp * 0.80
        )
        if low_kp_count >= _REPEAT_STREAK:
            repeated.append(
                f"Participación baja repetida en {low_kp_count} "
                f"de las últimas {len(recent)} partidas con {champion}."
            )

    return repeated


# ── Champion Coach Integration ────────────────────────────────────────────────

def check_pattern_repeated(
    match: dict,
    champion_patterns: list,
) -> tuple[str | None, bool]:
    """
    Compara los patrones históricos del Champion Coach con la partida actual.

    Retorna (problema_recurrente, coincide_hoy).
    coincide_hoy = True si el problema vuelve a ocurrir en esta partida.
    """
    if not champion_patterns:
        return None, False

    worst_pattern = champion_patterns[0]
    problem_text  = worst_pattern.title

    deaths_now = _safe(match.get("deaths"))

    # Revisamos si el error del patrón se repitió hoy
    if worst_pattern.pattern_type == "deaths" and deaths_now is not None:
        # El patrón dice que las derrotas tienen muchas muertes
        # Se considera repetido si las muertes superan el win_avg del análisis
        coincides = deaths_now > (getattr(worst_pattern, "metric_delta", 0) * 0.5)
    else:
        coincides = False

    return problem_text, coincides


# ── Matchup Context ───────────────────────────────────────────────────────────

def build_matchup_context(
    enemy_champion: str | None,
    wr: float | None,
    games: int,
    match_result: str,
) -> str | None:
    """Genera texto de contexto del matchup de esta partida."""
    if enemy_champion is None or games < 2:
        return None

    if wr is None:
        return None

    result_text = "Victoria" if match_result == "WIN" else "Derrota"

    if wr < 0.40:
        if match_result == "WIN":
            return (
                f"Victoria contra {enemy_champion} — "
                f"un matchup históricamente difícil para ti (WR {wr:.0%} en {games} partidas)."
            )
        else:
            return (
                f"Jugaste contra {enemy_champion}. "
                f"Tu WR histórico contra {enemy_champion} es {wr:.0%} ({games} partidas). "
                f"El resultado coincide con tu tendencia."
            )
    elif wr > 0.60:
        if match_result == "LOSS":
            return (
                f"Derrota contra {enemy_champion} — "
                f"un matchup que normalmente dominas (WR {wr:.0%} en {games} partidas)."
            )
        else:
            return (
                f"Victoria contra {enemy_champion}. "
                f"Tu WR histórico en este matchup es {wr:.0%} ({games} partidas). Normal."
            )
    else:
        return (
            f"Jugaste contra {enemy_champion} (WR histórico {wr:.0%} en {games} partidas). {result_text}."
        )
