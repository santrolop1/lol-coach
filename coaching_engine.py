"""
coaching_engine.py — Motor de coaching basado en reglas y datos reales.

PRINCIPIOS:
    - Sin IA, sin LLM, sin Machine Learning.
    - Cada diagnóstico está respaldado por datos calculados desde el historial.
    - Umbrales documentados con su fuente (research vs player_relative).

ROLES IMPLEMENTADOS: ADC, TOP, MID
PENDIENTE: JUNGLE, SUPPORT, Champion Select, Meta

FLUJO:
    match_history + ScoreResultV2 → reglas → CoachingResult

    1. Extraer métricas crudas del historial (últimas N partidas).
    2. Evaluar condiciones de cada regla (absolutos + relativos).
    3. Seleccionar problema principal por severidad.
    4. Generar evidencia con números concretos.
    5. Generar objetivo semanal derivado de los datos.
    6. Detectar fortalezas desde victorias vs derrotas.
    7. Construir CoachingResult.
"""

import statistics
from dataclasses import dataclass, field
from typing import Optional

import scorer_v2 as sv2
import coaching_rules as rules


# ---------------------------------------------------------------------------
# Dataclasses de salida
# ---------------------------------------------------------------------------

@dataclass
class WeeklyGoal:
    """Objetivo único, medible y alcanzable para las próximas 10 partidas."""
    description: str    # "Reducir muertes de 7.0 a 5.8 en las próximas 10 partidas"
    metric:      str    # "deaths" | "kill_participation" | "cs_at_10" | ...
    current:     float  # valor actual (promedio de historial)
    target:      float  # valor objetivo (derivado de datos)
    window:      str    # "próximas 10 partidas" | "hoy" | ...


@dataclass
class TrainingPlan:
    """1 acción principal + exactamente 2 secundarias."""
    primary:   str
    secondary: list[str]


@dataclass
class Strength:
    """Fortaleza detectada con evidencia numérica."""
    name:     str
    evidence: str


@dataclass
class CoachingResult:
    """
    Resultado completo del análisis de coaching.

    Campos:
        primary_problem  — hábito con mayor impacto negativo (solo uno)
        evidence         — números concretos que respaldan el diagnóstico
        probable_cause   — explicación del origen del problema
        impact           — consecuencia medible en la partida
        weekly_goal      — objetivo SMART para la próxima semana
        training_plan    — 1 acción principal + 2 secundarias
        strengths        — máx 3 fortalezas basadas en datos
        improvements     — problemas secundarios detectados (sin el principal)
        trend_summary    — resumen de tendencia + consistencia
        confidence_level — "insufficient" | "preliminary" | "reliable" | "robust"
        sample_size      — N partidas analizadas
        session_warning  — alerta de tilt o racha (puede ser None)
    """
    role:             str
    confidence_level: str

    primary_problem:  str
    evidence:         str
    probable_cause:   str
    impact:           str

    weekly_goal:      WeeklyGoal
    training_plan:    TrainingPlan

    strengths:        list[Strength]
    improvements:     list[str]

    trend_summary:    str

    sample_size:      int
    session_warning:  Optional[str]


# ---------------------------------------------------------------------------
# Helpers de extracción
# ---------------------------------------------------------------------------

def _vals(matches: list[dict], key: str) -> list[float]:
    """Extrae valores no-nulos de una lista de partidas."""
    return [float(m[key]) for m in matches if m.get(key) is not None]


def _avg(values: list[float]) -> Optional[float]:
    return statistics.mean(values) if values else None


def _split_by_result(
    matches: list[dict],
) -> tuple[list[dict], list[dict]]:
    wins   = [m for m in matches if m.get("result") == "WIN"]
    losses = [m for m in matches if m.get("result") == "LOSS"]
    return wins, losses


def _cs_per_min_list(matches: list[dict]) -> list[float]:
    """CS/min para cada partida (excluye las que faltan duración o cs)."""
    result = []
    for m in matches:
        cs  = m.get("cs")
        dur = m.get("duration_sec")
        if cs is not None and dur and dur > 0:
            result.append(float(cs) / (float(dur) / 60.0))
    return result


def _obj_per_min_list(matches: list[dict]) -> list[float]:
    """Damage a objetivos por minuto para cada partida."""
    result = []
    for m in matches:
        obj = m.get("damage_to_objectives")
        dur = m.get("duration_sec")
        if obj is not None and dur and dur > 0:
            result.append(float(obj) / (float(dur) / 60.0))
    return result


def _dmg_per_min_list(matches: list[dict]) -> list[float]:
    """Daño a campeones por minuto para cada partida."""
    result = []
    for m in matches:
        dmg = m.get("damage")
        dur = m.get("duration_sec")
        if dmg is not None and dur and dur > 0:
            result.append(float(dmg) / (float(dur) / 60.0))
    return result


# ---------------------------------------------------------------------------
# Helpers de temporalidad y tilt
# ---------------------------------------------------------------------------

def _hours_since(dt_str: str) -> float:
    """Horas transcurridas desde una fecha ISO hasta ahora."""
    from datetime import datetime
    if not dt_str:
        return float("inf")
    clean = dt_str.replace("Z", "").replace("+00:00", "")[:19]
    try:
        delta = datetime.now() - datetime.fromisoformat(clean)
        return delta.total_seconds() / 3600.0
    except Exception:
        return float("inf")


def _tilt_severity(hours_since: float, consecutive: int, same_day: int, threshold: int) -> float:
    """
    Severity del tilt con decaimiento temporal.

    Brackets:
        < 12h:   85  — sesión activa, tilt urgente
        12-24h:  50  — reciente, todavía diagnóstico primario válido
        24-48h:  15  — hace 1-2 días; reglas de habilidad (~20+) toman precedencia
        > 48h:   5   — histórico: solo contexto, no primary_problem

    Con 24-48h → severity=15 está por debajo de HIGH_DEATHS (~19) y
    LOW_KILL_PARTICIPATION (~14), permitiendo que emerjan como primary.
    """
    if consecutive < threshold or same_day < threshold:
        return 0.0
    if hours_since < 12:
        return 85.0
    if hours_since < 24:
        return 50.0
    if hours_since < 48:
        return 15.0
    return 5.0


def _count_consecutive_losses(matches_sorted_desc: list[dict]) -> tuple[int, int, str]:
    """
    Fuente única de verdad para detección de tilt.

    Counts consecutive losses starting from the most recent match.

    Args:
        matches_sorted_desc: partidas ordenadas más reciente primero.

    Returns:
        (consecutive, same_day_count, most_recent_date)
    """
    if not matches_sorted_desc:
        return 0, 0, ""
    most_recent_date = (matches_sorted_desc[0].get("played_at") or "")[:10]
    consecutive = 0
    same_day    = 0
    for m in matches_sorted_desc:
        if m.get("result") != "LOSS":
            break
        consecutive += 1
        if (m.get("played_at") or "")[:10] == most_recent_date:
            same_day += 1
    return consecutive, same_day, most_recent_date


# ---------------------------------------------------------------------------
# Detección de tilt / racha
# ---------------------------------------------------------------------------

def _detect_session_warning(role_matches: list[dict]) -> Optional[str]:
    """
    Detecta tilt activo o racha negativa.

    TILT ACTIVO    : 4+ derrotas consecutivas en el mismo día (del juego más reciente).
    RACHA NEGATIVA : 3+ derrotas consecutivas (cualquier día).

    Devuelve string descriptivo o None.
    """
    if not role_matches:
        return None

    recent = sorted(role_matches, key=lambda m: m.get("played_at", ""), reverse=True)
    consecutive, same_day, most_recent_date = _count_consecutive_losses(recent)

    role_key   = recent[0].get("role", "ADC")
    thresh_map = rules.THRESHOLDS.get(role_key, rules.THRESHOLDS["ADC"])
    tilt_val   = thresh_map.get("tilt_consecutive_losses", {}).get("value", 4)
    streak_val = thresh_map.get("losing_streak", {}).get("value", 3)

    hours = _hours_since(recent[0].get("played_at", ""))
    age_note = ""
    if hours >= 48:
        age_note = " (sesion de hace 2+ dias)"
    elif hours >= 24:
        age_note = " (sesion de ayer)"

    if same_day >= tilt_val and consecutive >= tilt_val:
        return (
            f"TILT ACTIVO: {consecutive} derrotas consecutivas, "
            f"{same_day} en la misma sesion ({most_recent_date}){age_note}. "
            f"Detente antes de la siguiente partida ranked."
        )

    if consecutive >= streak_val:
        return (
            f"RACHA NEGATIVA: {consecutive} derrotas consecutivas. "
            f"Revisa el patron comun entre ellas antes de continuar."
        )

    return None


# ---------------------------------------------------------------------------
# Evaluadores compartidos entre roles
# ---------------------------------------------------------------------------
# Estos bloques eran idénticos en ADC y TOP (solo cambiaban la clave del
# problema y el multiplicador de severidad). Extraídos al agregar MID para
# no mantener una tercera copia. El comportamiento es exactamente el mismo.

def _eval_tilt(role_matches: list[dict], thresh: dict) -> Optional[dict]:
    """TILT_SESSION: derrotas consecutivas con decaimiento temporal."""
    recent = sorted(role_matches, key=lambda m: m.get("played_at", ""), reverse=True)
    consecutive, same_day, most_recent_date = _count_consecutive_losses(recent)
    tilt_val = thresh.get("tilt_consecutive_losses", {}).get("value", 4)
    hours    = _hours_since((recent[0].get("played_at") or "") if recent else "")
    sev_tilt = _tilt_severity(hours, consecutive, same_day, tilt_val)
    if sev_tilt <= 0:
        return None
    return {
        "key": "TILT_SESSION",
        "triggered": True,
        "severity": sev_tilt,
        "raw_data": {
            "consecutive_losses": consecutive,
            "same_day": same_day,
            "date": most_recent_date,
            "hours_since": hours,
        },
    }


def _eval_high_deaths(
    role_matches: list[dict],
    wins: list[dict],
    losses: list[dict],
    benchmarks: sv2.PlayerBenchmarks,
    thresh: dict,
    key: str,
    severity_mult: float,
) -> Optional[dict]:
    """Exceso de muertes: promedio por encima del umbral de research."""
    all_deaths  = _vals(role_matches, "deaths")
    avg_deaths  = _avg(all_deaths)
    death_thresh = thresh["deaths_high"]["value"]

    if avg_deaths is None or avg_deaths <= death_thresh:
        return None
    return {
        "key": key,
        "triggered": True,
        "severity": min(100.0, (avg_deaths - death_thresh) * severity_mult),
        "raw_data": {
            "avg_deaths":  avg_deaths,
            "win_deaths":  _avg(_vals(wins, "deaths")),
            "loss_deaths": _avg(_vals(losses, "deaths")),
            "threshold":   death_thresh,
            "n":           len(all_deaths),
            "n_wins":      len(wins),
            "n_losses":    len(losses),
            "bm":          benchmarks.metrics.get("deaths"),
        },
    }


def _eval_bad_lane_phase(
    role_matches: list[dict],
    benchmarks: sv2.PlayerBenchmarks,
    thresh: dict,
) -> Optional[dict]:
    """BAD_LANE_PHASE: CS@10 por debajo del umbral de research (solo lanes)."""
    all_cs10 = _vals(role_matches, "cs_at_10")
    avg_cs10 = _avg(all_cs10)
    cs10_thresh = thresh["cs_at_10_low"]["value"]

    if avg_cs10 is None or len(all_cs10) < 3 or avg_cs10 >= cs10_thresh:
        return None
    return {
        "key": "BAD_LANE_PHASE",
        "triggered": True,
        "severity": min(100.0, (cs10_thresh - avg_cs10) * 3.0),
        "raw_data": {
            "avg_cs10":  avg_cs10,
            "threshold": cs10_thresh,
            "n":         len(all_cs10),
            "bm":        benchmarks.metrics.get("cs_at_10"),
        },
    }


def _eval_inconsistency(
    score_result: sv2.ScoreResultV2,
    thresh: dict,
    key: str,
) -> Optional[dict]:
    """Inconsistencia: consistency score bajo el umbral híbrido."""
    consistency = score_result.consistency_score
    cons_thresh = thresh.get("consistency_low", {}).get("value", 65.0)

    if consistency is None or consistency >= cons_thresh:
        return None
    overall_scores = sorted(
        ms.overall_score
        for ms in score_result.match_scores
        if ms.overall_score is not None
    )
    n_os = len(overall_scores)
    floor_s   = overall_scores[max(0, int(n_os * 0.25))] if n_os >= 4 else None
    ceiling_s = overall_scores[max(0, int(n_os * 0.75))] if n_os >= 4 else None
    return {
        "key": key,
        "triggered": True,
        "severity": min(100.0, (cons_thresh - consistency) * 2.0),
        "raw_data": {
            "consistency":   consistency,
            "threshold":     cons_thresh,
            "floor_score":   floor_s,
            "ceiling_score": ceiling_s,
            "n":             n_os,
        },
    }


def _eval_low_kp(
    role_matches: list[dict],
    wins: list[dict],
    losses: list[dict],
    benchmarks: sv2.PlayerBenchmarks,
    thresh: dict,
) -> Optional[dict]:
    """LOW_KILL_PARTICIPATION: KP promedio bajo el umbral de research."""
    all_kp  = _vals(role_matches, "kill_participation")
    avg_kp  = _avg(all_kp)
    kp_thresh = thresh["kill_participation_low"]["value"]

    if avg_kp is None or avg_kp >= kp_thresh:
        return None
    return {
        "key": "LOW_KILL_PARTICIPATION",
        "triggered": True,
        "severity": min(100.0, (kp_thresh - avg_kp) * 200.0),
        "raw_data": {
            "avg_kp":    avg_kp,
            "win_kp":    _avg(_vals(wins, "kill_participation")),
            "loss_kp":   _avg(_vals(losses, "kill_participation")),
            "threshold": kp_thresh,
            "n":         len(all_kp),
            "bm":        benchmarks.metrics.get("kill_participation"),
        },
    }


# ---------------------------------------------------------------------------
# Evaluación de problemas — ADC
# ---------------------------------------------------------------------------

def _evaluate_adc_problems(
    role_matches: list[dict],
    benchmarks: sv2.PlayerBenchmarks,
    score_result: sv2.ScoreResultV2,
) -> list[dict]:
    """
    Evalúa patrones de coaching ADC.

    Devuelve lista de problemas detectados, cada uno con:
        key       : clave en ADC_PROBLEMS
        triggered : True
        severity  : 0-100 (mayor = más urgente)
        raw_data  : valores crudos para generar evidencia
    """
    problems: list[dict] = []
    wins, losses = _split_by_result(role_matches)
    thresh = rules.THRESHOLDS["ADC"]

    # --- TILT / RACHA ---
    if (p := _eval_tilt(role_matches, thresh)):
        problems.append(p)

    # --- EXCESO DE MUERTES ---
    if (p := _eval_high_deaths(role_matches, wins, losses, benchmarks,
                               thresh, "HIGH_DEATHS", severity_mult=20.0)):
        problems.append(p)

    # --- BAJA PARTICIPACIÓN EN PELEAS ---
    if (p := _eval_low_kp(role_matches, wins, losses, benchmarks, thresh)):
        problems.append(p)

    # --- FARM DEFICIENTE EN EARLY (cs_at_10) ---
    all_cs10 = _vals(role_matches, "cs_at_10")
    avg_cs10 = _avg(all_cs10)
    cs10_thresh = thresh["cs_at_10_low"]["value"]  # 55

    # ADVERTENCIA: en el dataset de este jugador CS@10 NO correlaciona con victorias.
    # La regla se mantiene por evidencia externa pero con baja confianza.
    # Solo se activa si hay ≥5 muestras y la distancia es significativa (>10 CS).
    # La severity se reduce a 40% cuando la correlación local está invertida,
    # para que reglas validadas localmente (muertes, KP) puedan superarla.
    if avg_cs10 is not None and len(all_cs10) >= 5 and avg_cs10 < (cs10_thresh - 5):
        raw_severity = min(100.0, (cs10_thresh - avg_cs10) * 3.0)
        win_cs10  = _avg(_vals(wins, "cs_at_10"))
        loss_cs10 = _avg(_vals(losses, "cs_at_10"))
        is_inverted = (
            win_cs10 is not None
            and loss_cs10 is not None
            and len(wins) >= 3
            and win_cs10 < loss_cs10   # más CS@10 en derrotas que en victorias
        )
        severity = raw_severity * (0.40 if is_inverted else 1.0)
        problems.append({
            "key": "LOW_CS_AT_10",
            "triggered": True,
            "severity": severity,
            "raw_data": {
                "avg_cs10":      avg_cs10,
                "threshold":     cs10_thresh,
                "n":             len(all_cs10),
                "bm":            benchmarks.metrics.get("cs_at_10"),
                "inverted_note": is_inverted,
                "win_cs10":      win_cs10,
                "loss_cs10":     loss_cs10,
            },
        })

    # --- INCONSISTENCIA ---
    if (p := _eval_inconsistency(score_result, thresh, "HIGH_INCONSISTENCY")):
        problems.append(p)

    # --- BAJA CONTRIBUCIÓN A OBJETIVOS ---
    # Condición: N >= 10, N_wins >= 2, avg obj/min < 80% del promedio en victorias.
    # Fuente: discriminador real (WIN avg=310.8 vs LOSS avg=195.0, delta=37%).
    all_opm  = _obj_per_min_list(role_matches)
    win_opm  = _obj_per_min_list(wins)
    n_total  = len(all_opm)
    n_wins_opm = len(win_opm)
    if n_total >= 10 and n_wins_opm >= 2:
        avg_opm     = statistics.mean(all_opm)
        win_avg_opm = statistics.mean(win_opm)
        if win_avg_opm > 0 and avg_opm < win_avg_opm * 0.80:
            sev_obj = min(100.0, (1.0 - avg_opm / win_avg_opm) * 55.0)
            problems.append({
                "key": "LOW_OBJECTIVE_CONTRIBUTION",
                "triggered": True,
                "severity": sev_obj,
                "raw_data": {
                    "avg_opm":     avg_opm,
                    "win_avg_opm": win_avg_opm,
                    "n":           n_total,
                    "n_wins":      n_wins_opm,
                },
            })

    return problems


# ---------------------------------------------------------------------------
# Evaluación de problemas — TOP
# ---------------------------------------------------------------------------

def _evaluate_top_problems(
    role_matches: list[dict],
    benchmarks: sv2.PlayerBenchmarks,
    score_result: sv2.ScoreResultV2,
) -> list[dict]:
    """Evalúa patrones de coaching TOP."""
    problems: list[dict] = []
    wins, losses = _split_by_result(role_matches)
    thresh = rules.THRESHOLDS["TOP"]

    # --- TILT / RACHA ---
    if (p := _eval_tilt(role_matches, thresh)):
        problems.append(p)

    # --- EXCESO DE MUERTES TOP ---
    if (p := _eval_high_deaths(role_matches, wins, losses, benchmarks,
                               thresh, "HIGH_DEATHS_TOP", severity_mult=25.0)):
        problems.append(p)

    # --- MALA FASE DE LÍNEAS (cs_at_10) ---
    if (p := _eval_bad_lane_phase(role_matches, benchmarks, thresh)):
        problems.append(p)

    # --- BAJA PRESIÓN LATERAL ---
    pressure_score = score_result.dimensions.get("Pressure")
    press_thresh = thresh.get("pressure_score_low", {}).get("value", 40.0)

    if pressure_score is not None and pressure_score < press_thresh:
        severity = min(100.0, (press_thresh - pressure_score) * 2.0)
        all_tt = _vals(role_matches, "turret_takedowns")
        problems.append({
            "key": "LOW_PRESSURE",
            "triggered": True,
            "severity": severity,
            "raw_data": {
                "pressure_score": pressure_score,
                "threshold":      press_thresh,
                "avg_turrets":    _avg(all_tt),
                "n":              len(role_matches),
            },
        })

    # --- INCONSISTENCIA ---
    if (p := _eval_inconsistency(score_result, thresh, "HIGH_INCONSISTENCY_TOP")):
        problems.append(p)

    # --- BAJA CONVERSIÓN DE VENTAJA DE LÍNEA ---
    # Condición: lane_control_score > 50 (gana la lane) Y pressure_score < 40 (no convierte).
    # N >= 5 para que los scores auto-relativos sean estables.
    # Fuente: dimensiones de scorer_v2 (Lane Control vs Pressure).
    if len(role_matches) >= 5:
        lane_score     = score_result.dimensions.get("Lane Control")
        pressure_score = score_result.dimensions.get("Pressure")
        lane_thresh    = thresh.get("lane_score_low", {}).get("value", 40.0)
        press_thresh   = thresh.get("pressure_score_low", {}).get("value", 40.0)

        if (
            lane_score is not None and pressure_score is not None
            and lane_score > 50
            and pressure_score < press_thresh
        ):
            sev_conv = min(100.0, (50.0 - pressure_score) * 1.5)
            all_tt = _vals(role_matches, "turret_takedowns")
            bm_tt  = benchmarks.metrics.get("turret_takedowns")
            problems.append({
                "key": "LOW_ADVANTAGE_CONVERSION",
                "triggered": True,
                "severity": sev_conv,
                "raw_data": {
                    "lane_score":     lane_score,
                    "pressure_score": pressure_score,
                    "avg_turrets":    _avg(all_tt),
                    "p25_tt":         bm_tt.p25 if bm_tt else None,
                    "n":              len(role_matches),
                },
            })

    return problems


# ---------------------------------------------------------------------------
# Evaluación de problemas — MID
# ---------------------------------------------------------------------------

def _evaluate_mid_problems(
    role_matches: list[dict],
    benchmarks: sv2.PlayerBenchmarks,
    score_result: sv2.ScoreResultV2,
) -> list[dict]:
    """Evalúa patrones de coaching MID."""
    problems: list[dict] = []
    wins, losses = _split_by_result(role_matches)
    thresh = rules.THRESHOLDS["MID"]

    # --- TILT / RACHA ---
    if (p := _eval_tilt(role_matches, thresh)):
        problems.append(p)

    # --- EXCESO DE MUERTES MID ---
    # Multiplicador 20.0 (igual que ADC): mismo umbral de 6 muertes.
    if (p := _eval_high_deaths(role_matches, wins, losses, benchmarks,
                               thresh, "HIGH_DEATHS_MID", severity_mult=20.0)):
        problems.append(p)

    # --- MALA FASE DE LÍNEAS (cs_at_10) ---
    if (p := _eval_bad_lane_phase(role_matches, benchmarks, thresh)):
        problems.append(p)

    # --- BAJA PRESENCIA DE MAPA (kill participation) ---
    if (p := _eval_low_kp(role_matches, wins, losses, benchmarks, thresh)):
        problems.append(p)

    # --- BAJO IMPACTO DE DAÑO ---
    # Condición: dimensión Damage Impact < 40 (score auto-relativo).
    # Misma estructura que LOW_PRESSURE de TOP: dimensión de scorer_v2 + datos
    # crudos (daño/min) para la evidencia.
    damage_score = score_result.dimensions.get("Damage Impact")
    dmg_thresh   = thresh.get("damage_score_low", {}).get("value", 40.0)

    if damage_score is not None and damage_score < dmg_thresh:
        all_dpm = _dmg_per_min_list(role_matches)
        win_dpm = _dmg_per_min_list(wins)
        problems.append({
            "key": "LOW_DAMAGE_IMPACT",
            "triggered": True,
            "severity": min(100.0, (dmg_thresh - damage_score) * 2.0),
            "raw_data": {
                "damage_score": damage_score,
                "threshold":    dmg_thresh,
                "avg_dpm":      _avg(all_dpm),
                "win_avg_dpm":  _avg(win_dpm),
                "n":            len(role_matches),
            },
        })

    # --- INCONSISTENCIA ---
    if (p := _eval_inconsistency(score_result, thresh, "HIGH_INCONSISTENCY_MID")):
        problems.append(p)

    return problems


# ---------------------------------------------------------------------------
# Selección de problema principal
# ---------------------------------------------------------------------------

def _select_primary(problems: list[dict]) -> Optional[dict]:
    """Problema con mayor severidad. None si no hay ninguno."""
    return max(problems, key=lambda p: p["severity"]) if problems else None


# ---------------------------------------------------------------------------
# Generación de evidencia
# ---------------------------------------------------------------------------

def _generate_evidence(problem: dict, role: str) -> str:
    """
    Genera texto de evidencia con números concretos del historial del jugador.
    Cada cifra proviene de los datos, no de valores inventados.
    """
    key  = problem["key"]
    data = problem["raw_data"]

    if key == "TILT_SESSION":
        cons = data["consecutive_losses"]
        same = data["same_day"]
        date = data["date"]
        return (
            f"{cons} derrotas consecutivas, "
            f"{same} de ellas en la misma sesion del {date}. "
            f"Este patron indica que la toma de decisiones esta comprometida "
            f"por la frustracion acumulada."
        )

    if key in ("HIGH_DEATHS", "HIGH_DEATHS_TOP", "HIGH_DEATHS_MID"):
        avg  = data["avg_deaths"]
        wd   = data.get("win_deaths")
        ld   = data.get("loss_deaths")
        thr  = data["threshold"]
        n    = data["n"]
        nw   = data.get("n_wins", "?")
        nl   = data.get("n_losses", "?")

        parts = [
            f"Promedio muertes ({n} partidas {role}): {avg:.1f} "
            f"— umbral de investigacion: <={thr:.0f}."
        ]
        if wd is not None and ld is not None:
            delta = ld - wd
            parts.append(
                f"En tus {nw} victorias: {wd:.2f} muertes. "
                f"En tus {nl} derrotas: {ld:.2f} muertes. "
                f"Diferencia: +{delta:.2f} muertes cuando pierdes."
            )
        bm = data.get("bm")
        if bm:
            parts.append(
                f"Tu historial: P25={bm.p25:.0f} / P50={bm.p50:.0f} / P75={bm.p75:.0f} muertes."
            )
        return " ".join(parts)

    if key == "LOW_KILL_PARTICIPATION":
        avg  = data["avg_kp"]
        wkp  = data.get("win_kp")
        lkp  = data.get("loss_kp")
        thr  = data["threshold"]
        n    = data["n"]

        parts = [
            f"Kill participation promedio ({n} partidas {role}): {avg:.0%} "
            f"— umbral para {role} Gold: >{thr:.0%}."
        ]
        if wkp is not None and lkp is not None:
            parts.append(
                f"En victorias: {wkp:.0%}. En derrotas: {lkp:.0%}. "
                f"La diferencia es de {(wkp - lkp):.0%} puntos."
            )
        return " ".join(parts)

    if key == "LOW_CS_AT_10":
        avg  = data["avg_cs10"]
        thr  = data["threshold"]
        n    = data["n"]
        bm   = data.get("bm")
        note = (
            "ATENCION: en este historial, CS@10 no correlaciona con victorias "
            f"(puede ser sesgo de muestra N={n}). "
            "La regla se mantiene por evidencia externa."
        )
        parts = [
            f"CS@10 promedio ({n} partidas ADC): {avg:.0f} "
            f"— umbral de investigacion: >={thr:.0f}. {note}"
        ]
        if bm:
            parts.append(
                f"Tu historial: P25={bm.p25:.0f} / P50={bm.p50:.0f} / P75={bm.p75:.0f} CS@10."
            )
        return " ".join(parts)

    if key == "BAD_LANE_PHASE":
        avg = data["avg_cs10"]
        thr = data["threshold"]
        n   = data["n"]
        bm  = data.get("bm")

        parts = [
            f"CS@10 promedio ({n} partidas {role}): {avg:.0f} "
            f"— umbral de investigacion: >={thr:.0f}."
        ]
        if bm:
            parts.append(
                f"Tu historial {role}: P25={bm.p25:.0f} / P50={bm.p50:.0f} / P75={bm.p75:.0f} CS@10."
            )
        return " ".join(parts)

    if key == "LOW_PRESSURE":
        score = data["pressure_score"]
        thr   = data["threshold"]
        tt    = data.get("avg_turrets")
        n     = data["n"]
        parts = [
            f"Dimension Pressure: {score:.0f}/100 "
            f"— por debajo del umbral de {thr:.0f} (N={n} partidas TOP)."
        ]
        if tt is not None:
            parts.append(f"Torres destruidas promedio: {tt:.1f} por partida.")
        return " ".join(parts)

    if key == "LOW_DAMAGE_IMPACT":
        score   = data["damage_score"]
        thr     = data["threshold"]
        avg_dpm = data.get("avg_dpm")
        win_dpm = data.get("win_avg_dpm")
        n       = data["n"]
        parts = [
            f"Dimension Damage Impact: {score:.0f}/100 "
            f"— por debajo del umbral de {thr:.0f} (N={n} partidas MID)."
        ]
        if avg_dpm is not None:
            parts.append(f"Daño a campeones promedio: {avg_dpm:.0f}/min.")
            if win_dpm is not None and win_dpm > avg_dpm:
                parts.append(
                    f"En tus victorias: {win_dpm:.0f}/min "
                    f"— cuando haces más daño, ganas más."
                )
        return " ".join(parts)

    if key in ("HIGH_INCONSISTENCY", "HIGH_INCONSISTENCY_TOP", "HIGH_INCONSISTENCY_MID"):
        cons  = data["consistency"]
        thr   = data["threshold"]
        floor_s = data.get("floor_score")
        ceil_s  = data.get("ceiling_score")
        n       = data["n"]

        parts = [
            f"Consistency score: {cons:.0f}/100 "
            f"— umbral minimo recomendado: {thr:.0f} (N={n} partidas)."
        ]
        if floor_s is not None and ceil_s is not None:
            gap = ceil_s - floor_s
            parts.append(
                f"Tus partidas oscilan entre ~{floor_s:.0f} (P25) y ~{ceil_s:.0f} (P75) "
                f"de overall score — rango de {gap:.0f} puntos."
            )
        return " ".join(parts)

    if key == "LOW_OBJECTIVE_CONTRIBUTION":
        avg_opm     = data["avg_opm"]
        win_avg_opm = data["win_avg_opm"]
        n           = data["n"]
        n_wins      = data["n_wins"]
        ratio       = avg_opm / win_avg_opm if win_avg_opm > 0 else 0
        delta_pct   = (1.0 - ratio) * 100

        return (
            f"Damage a objetivos/min promedio ({n} partidas ADC): {avg_opm:.0f}. "
            f"En tus {n_wins} victorias: {win_avg_opm:.0f}/min. "
            f"Diferencia: -{delta_pct:.0f}% menos contribucion a objetivos en tus partidas en general. "
            f"Los objetivos del mapa son el mayor diferenciador entre victorias y derrotas en ADC."
        )

    if key == "LOW_ADVANTAGE_CONVERSION":
        lane  = data["lane_score"]
        press = data["pressure_score"]
        tt    = data.get("avg_turrets")
        p25   = data.get("p25_tt")
        n     = data["n"]

        parts = [
            f"Lane Control: {lane:.0f}/100 (por encima de P50 — estas ganando la fase de lineas). "
            f"Pressure: {press:.0f}/100 — por debajo del umbral de conversion ({press:.0f} < 40). "
            f"(N={n} partidas TOP)"
        ]
        if tt is not None:
            parts.append(f"Torres destruidas promedio: {tt:.1f} por partida.")
            if p25 is not None:
                parts.append(f"Tu P25 de torres es {p25:.1f}.")
        return " ".join(parts)

    return "Sin datos suficientes para generar evidencia cuantitativa."


# ---------------------------------------------------------------------------
# Generación de objetivo semanal
# ---------------------------------------------------------------------------

def _generate_weekly_goal(problem: dict, role: str) -> WeeklyGoal:
    """
    Genera el objetivo semanal (1 solo) derivado de los datos del problema.

    Targets calculados desde el historial del jugador:
        - Deaths:  target = promedio en victorias (WIN avg)
        - KP:      target = promedio en victorias
        - CS@10:   target = P75 personal
        - Consistency: target = actual + 10 puntos
        - Tilt:    target = ganar 1 partida hoy
    """
    key  = problem["key"]
    data = problem["raw_data"]

    if key == "TILT_SESSION":
        cons = data["consecutive_losses"]
        return WeeklyGoal(
            description=(
                f"Ganar 1 partida ranked antes de terminar la sesion. "
                f"Si no se logra en 2 intentos tras la racha de {cons}, "
                f"hacer una pausa de minimo 30 minutos."
            ),
            metric="tilt_recovery",
            current=float(cons),
            target=0.0,
            window="hoy",
        )

    if key in ("HIGH_DEATHS", "HIGH_DEATHS_TOP", "HIGH_DEATHS_MID"):
        current = data["avg_deaths"]
        win_d   = data.get("win_deaths")
        bm      = data.get("bm")

        if win_d is not None:
            target = round(win_d, 1)
        elif bm:
            target = bm.p25
        else:
            target = max(1.0, round(current * 0.80, 1))

        return WeeklyGoal(
            description=(
                f"Reducir muertes de {current:.1f} a {target:.1f} "
                f"en las proximas 10 partidas. "
                f"(Target = tu promedio en victorias)"
            ),
            metric="deaths",
            current=current,
            target=target,
            window="proximas 10 partidas",
        )

    if key == "LOW_KILL_PARTICIPATION":
        current = data["avg_kp"]
        win_kp  = data.get("win_kp")
        bm      = data.get("bm")

        if win_kp is not None and win_kp > current:
            target = round(win_kp, 2)
        elif bm:
            target = round(min(0.85, bm.p75), 2)
        else:
            target = round(min(0.85, current + 0.10), 2)

        return WeeklyGoal(
            description=(
                f"Subir kill participation de {current:.0%} a {target:.0%} "
                f"en las proximas 10 partidas. "
                f"(Target = tu promedio en victorias)"
            ),
            metric="kill_participation",
            current=current,
            target=target,
            window="proximas 10 partidas",
        )

    if key == "LOW_CS_AT_10":
        current = data["avg_cs10"]
        bm      = data.get("bm")

        if bm:
            target = bm.p75
        else:
            target = current + 10

        return WeeklyGoal(
            description=(
                f"Alcanzar {target:.0f} CS al minuto 10 de forma consistente. "
                f"(Target = tu P75 personal o threshold de investigacion)"
            ),
            metric="cs_at_10",
            current=current,
            target=target,
            window="proximas 10 partidas",
        )

    if key == "BAD_LANE_PHASE":
        current = data["avg_cs10"]
        bm      = data.get("bm")
        target  = bm.p75 if bm else min(80, current + 15)

        return WeeklyGoal(
            description=(
                f"Alcanzar {target:.0f} CS al minuto 10 "
                f"en las proximas 10 partidas {role}."
            ),
            metric="cs_at_10",
            current=current,
            target=target,
            window="proximas 10 partidas",
        )

    if key == "LOW_PRESSURE":
        current = data.get("avg_turrets") or 0.0
        target  = round(current + 1.0, 1)
        return WeeklyGoal(
            description=(
                f"Destruir {target:.0f}+ torres por partida en las proximas 10 partidas TOP."
            ),
            metric="turret_takedowns",
            current=current,
            target=target,
            window="proximas 10 partidas",
        )

    if key == "LOW_DAMAGE_IMPACT":
        current = data.get("avg_dpm") or 0.0
        win_dpm = data.get("win_avg_dpm")
        # Target: promedio en victorias si es mayor; si no, +10% del actual.
        if win_dpm is not None and win_dpm > current:
            target = round(win_dpm, 0)
            target_note = "(Target = tu promedio en victorias)"
        else:
            target = round(current * 1.10, 0)
            target_note = "(Target = +10% sobre tu promedio actual)"
        return WeeklyGoal(
            description=(
                f"Subir tu daño a campeones de {current:.0f} a {target:.0f} por minuto "
                f"en las proximas 10 partidas. {target_note}"
            ),
            metric="damage_per_min",
            current=current,
            target=target,
            window="proximas 10 partidas",
        )

    if key in ("HIGH_INCONSISTENCY", "HIGH_INCONSISTENCY_TOP", "HIGH_INCONSISTENCY_MID"):
        current   = data["consistency"]
        floor_s   = data.get("floor_score") or 30.0
        target    = min(100.0, current + 10.0)
        return WeeklyGoal(
            description=(
                f"Eliminar partidas con overall score menor a {floor_s:.0f} "
                f"en las proximas 10 partidas. "
                f"Objetivo: no tener ninguna partida por debajo del suelo actual."
            ),
            metric="consistency_score",
            current=current,
            target=target,
            window="proximas 10 partidas",
        )

    if key == "LOW_OBJECTIVE_CONTRIBUTION":
        current     = data["avg_opm"]
        win_avg_opm = data["win_avg_opm"]
        target      = round(win_avg_opm * 0.85, 0)   # objetivo intermedio: 85% del promedio en victorias
        return WeeklyGoal(
            description=(
                f"Aumentar daño a objetivos/min de {current:.0f} a {target:.0f} "
                f"en las proximas 10 partidas. "
                f"(Target = 85% de tu promedio en victorias: {win_avg_opm:.0f}/min)"
            ),
            metric="objectives_per_min",
            current=current,
            target=target,
            window="proximas 10 partidas",
        )

    if key == "LOW_ADVANTAGE_CONVERSION":
        current = data.get("avg_turrets") or 0.0
        target  = round(current + 1.0, 1)
        return WeeklyGoal(
            description=(
                f"Destruir {target:.0f}+ torres por partida en las proximas 10 partidas TOP "
                f"cuando tengas ventaja en la fase de lineas."
            ),
            metric="turret_takedowns",
            current=current,
            target=target,
            window="proximas 10 partidas",
        )

    # Fallback
    return WeeklyGoal(
        description="Enfocarse en el problema principal durante 10 partidas consecutivas.",
        metric="overall_score",
        current=0.0,
        target=0.0,
        window="proximas 10 partidas",
    )


# ---------------------------------------------------------------------------
# Generación de plan de entrenamiento
# ---------------------------------------------------------------------------

def _generate_training_plan(problem_key: str, role: str) -> TrainingPlan:
    """Obtiene acciones desde coaching_rules.py según la clave de problema."""
    rule_map = rules.PROBLEMS_BY_ROLE.get(role, rules.ADC_PROBLEMS)
    rule_def = rule_map.get(problem_key, {})

    primary   = rule_def.get(
        "primary_action",
        "Enfocarse en reducir el problema detectado en cada partida."
    )
    secondary = list(rule_def.get(
        "secondary_actions",
        [
            "Practica el aspecto identificado en partidas normales antes de volver a ranked.",
            "Revisa VODs de tus victorias recientes y compara la toma de decisiones.",
        ],
    ))

    return TrainingPlan(
        primary=primary,
        secondary=secondary[:2],
    )


# ---------------------------------------------------------------------------
# Detección de fortalezas
# ---------------------------------------------------------------------------

def _detect_strengths_adc(
    role_matches: list[dict],
    benchmarks: sv2.PlayerBenchmarks,
    score_result: sv2.ScoreResultV2,
) -> list[Strength]:
    """
    Detecta hasta 3 fortalezas del jugador ADC basadas en datos.

    Criterios (en orden de prioridad):
        1. Farm: CS/min >= P50 de propio historial
        2. Supervivencia en victorias: deaths en victorias < 80% del promedio general
        3. KP en victorias: kill_participation >= 45% en victorias
        4. Techo reciente: mejor partida WIN en últimas 5 con overall >= 70
    """
    strengths: list[tuple[float, Strength]] = []
    wins, losses = _split_by_result(role_matches)

    # 1. Farm consistente
    cspm_vals = _cs_per_min_list(role_matches)
    if cspm_vals:
        avg_cspm = statistics.mean(cspm_vals)
        bm_cspm  = benchmarks.metrics.get("cs_per_min")
        if bm_cspm and avg_cspm >= bm_cspm.p50:
            percentil = (
                sum(1 for v in cspm_vals if v <= avg_cspm) / len(cspm_vals) * 100
            )
            strengths.append((avg_cspm, Strength(
                name="Farm consistente",
                evidence=(
                    f"CS/min promedio {avg_cspm:.2f} — {percentil:.0f} percentil "
                    f"de tus partidas (N={len(cspm_vals)})."
                ),
            )))

    # 2. Menos muertes en victorias
    win_deaths = _vals(wins, "deaths")
    all_deaths = _vals(role_matches, "deaths")
    if win_deaths and len(wins) >= 3 and all_deaths:
        avg_wd  = statistics.mean(win_deaths)
        avg_all = statistics.mean(all_deaths)
        if avg_all > 0 and avg_wd < avg_all * 0.82:
            strengths.append((avg_all - avg_wd, Strength(
                name="Mejor supervivencia en victorias",
                evidence=(
                    f"{avg_wd:.1f} muertes promedio en {len(wins)} victorias "
                    f"vs {avg_all:.1f} de media general — "
                    f"{avg_all - avg_wd:.1f} muertes menos cuando ganas."
                ),
            )))

    # 3. KP en victorias
    win_kp = _vals(wins, "kill_participation")
    if win_kp and len(wins) >= 3:
        avg_wkp = statistics.mean(win_kp)
        if avg_wkp >= 0.45:
            strengths.append((avg_wkp, Strength(
                name="Buena participacion en peleas (victorias)",
                evidence=(
                    f"Kill participation promedio en victorias: {avg_wkp:.0%} "
                    f"({len(wins)} partidas)."
                ),
            )))

    # 4. Nivel P75 alcanzable de forma repetida (mínimo 3 victorias sobre P75).
    # Reemplaza el criterio anterior basado en 1 partida outlier, que no
    # representa un patrón real sino un accidente estadístico.
    all_overall = sorted(
        ms.overall_score for ms in score_result.match_scores if ms.overall_score is not None
    )
    n_os = len(all_overall)
    if n_os >= 8:
        p75_threshold = all_overall[max(0, int(n_os * 0.75))]
        high_wins = [
            ms for ms in score_result.match_scores
            if ms.result == "WIN" and ms.overall_score is not None and ms.overall_score >= p75_threshold
        ]
        if len(high_wins) >= 3:
            strengths.append((len(high_wins), Strength(
                name="Nivel P75 alcanzable de forma repetida",
                evidence=(
                    f"Superas tu nivel P75 (overall score >= {p75_threshold:.0f}) "
                    f"en {len(high_wins)} de tus partidas ganadas. "
                    f"El nivel alto no es un accidente — es repetible."
                ),
            )))

    # Ordenar por prioridad y devolver top 3
    strengths.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in strengths[:3]]


def _detect_strengths_top(
    role_matches: list[dict],
    benchmarks: sv2.PlayerBenchmarks,
    score_result: sv2.ScoreResultV2,
) -> list[Strength]:
    """Detecta hasta 3 fortalezas del jugador TOP."""
    strengths: list[tuple[float, Strength]] = []
    wins, losses = _split_by_result(role_matches)

    # 1. CS@10 por encima de P50
    cs10_vals = _vals(role_matches, "cs_at_10")
    if cs10_vals and "cs_at_10" in benchmarks.metrics:
        avg_cs10 = statistics.mean(cs10_vals)
        bm       = benchmarks.metrics["cs_at_10"]
        if avg_cs10 >= bm.p50:
            strengths.append((avg_cs10 - bm.p50, Strength(
                name="Fase de lineas razonable",
                evidence=(
                    f"CS@10 promedio {avg_cs10:.0f} — en tu mediana personal "
                    f"({bm.p50:.0f}) o por encima."
                ),
            )))

    # 2. Supervivencia
    all_deaths = _vals(role_matches, "deaths")
    if all_deaths and "deaths" in benchmarks.metrics:
        avg_d = statistics.mean(all_deaths)
        bm    = benchmarks.metrics["deaths"]
        if avg_d <= bm.p50:
            strengths.append((bm.p50 - avg_d, Strength(
                name="Buena supervivencia",
                evidence=(
                    f"Promedio {avg_d:.1f} muertes — "
                    f"en tu mediana historica ({bm.p50:.0f}) o por debajo."
                ),
            )))

    # 3. Presión de torretas
    tt_vals = _vals(role_matches, "turret_takedowns")
    if tt_vals and "turret_takedowns" in benchmarks.metrics:
        avg_tt = statistics.mean(tt_vals)
        bm     = benchmarks.metrics["turret_takedowns"]
        if avg_tt >= bm.p75:
            strengths.append((avg_tt, Strength(
                name="Buena presion de torres",
                evidence=(
                    f"Promedio {avg_tt:.1f} torres destruidas — "
                    f"en tu P75 historico ({bm.p75:.0f})."
                ),
            )))

    strengths.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in strengths[:3]]


def _detect_strengths_mid(
    role_matches: list[dict],
    benchmarks: sv2.PlayerBenchmarks,
    score_result: sv2.ScoreResultV2,
) -> list[Strength]:
    """
    Detecta hasta 3 fortalezas del jugador MID basadas en datos.

    Criterios (mismo patrón auto-relativo que TOP):
        1. Lane: CS@10 >= P50 de propio historial
        2. Supervivencia: deaths <= P50
        3. Daño: team_damage_pct >= P50 (rol de carry cumplido)
    """
    strengths: list[tuple[float, Strength]] = []

    # 1. CS@10 en la mediana o por encima
    cs10_vals = _vals(role_matches, "cs_at_10")
    if cs10_vals and "cs_at_10" in benchmarks.metrics:
        avg_cs10 = statistics.mean(cs10_vals)
        bm       = benchmarks.metrics["cs_at_10"]
        if avg_cs10 >= bm.p50:
            strengths.append((avg_cs10 - bm.p50, Strength(
                name="Fase de lineas solida",
                evidence=(
                    f"CS@10 promedio {avg_cs10:.0f} — en tu mediana personal "
                    f"({bm.p50:.0f}) o por encima."
                ),
            )))

    # 2. Supervivencia
    all_deaths = _vals(role_matches, "deaths")
    if all_deaths and "deaths" in benchmarks.metrics:
        avg_d = statistics.mean(all_deaths)
        bm    = benchmarks.metrics["deaths"]
        if avg_d <= bm.p50:
            strengths.append((bm.p50 - avg_d, Strength(
                name="Buena supervivencia",
                evidence=(
                    f"Promedio {avg_d:.1f} muertes — "
                    f"en tu mediana historica ({bm.p50:.0f}) o por debajo."
                ),
            )))

    # 3. Impacto de daño (share del daño del equipo)
    tdp_vals = _vals(role_matches, "team_damage_pct")
    if tdp_vals and "team_damage_pct" in benchmarks.metrics:
        avg_tdp = statistics.mean(tdp_vals)
        bm      = benchmarks.metrics["team_damage_pct"]
        if avg_tdp >= bm.p50:
            strengths.append((avg_tdp, Strength(
                name="Alto impacto de daño",
                evidence=(
                    f"{avg_tdp:.0%} del daño total del equipo en promedio — "
                    f"estas cumpliendo el rol de carry de daño."
                ),
            )))

    strengths.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in strengths[:3]]


# ---------------------------------------------------------------------------
# Resumen de tendencia
# ---------------------------------------------------------------------------

def _build_trend_summary(
    score_result: sv2.ScoreResultV2,
) -> str:
    trend       = score_result.trend
    slope       = score_result.trend_slope
    consistency = score_result.consistency_score

    trend_info = rules.TREND_SUMMARIES.get(trend, rules.TREND_SUMMARIES["stable"])
    parts = [
        f"Tendencia: {trend_info['title']} (pendiente OLS: {slope:+.2f} pts/partida).",
        trend_info["description"],
    ]

    if consistency is not None:
        if consistency >= 80:
            cons_label = "Muy consistente"
        elif consistency >= 65:
            cons_label = "Moderadamente consistente"
        else:
            cons_label = "Variable"
        parts.append(f"Consistencia: {consistency:.0f}/100 — {cons_label}.")

    # Suelo y techo
    overall_scores = sorted(
        ms.overall_score
        for ms in score_result.match_scores
        if ms.overall_score is not None
    )
    n = len(overall_scores)
    if n >= 4:
        floor_s   = overall_scores[max(0, int(n * 0.25))]
        ceiling_s = overall_scores[max(0, int(n * 0.75))]
        parts.append(
            f"Tu suelo (P25) es ~{floor_s:.0f} y tu techo (P75) es ~{ceiling_s:.0f}. "
            f"El trabajo esta semana es elevar el suelo."
        )

    # Win rate — contexto crítico que ningún score individual captura
    n_wins  = sum(1 for ms in score_result.match_scores if ms.result == "WIN")
    n_total = len(score_result.match_scores)
    if n_total >= 10:
        wr = n_wins / n_total * 100
        if wr < 45:
            parts.append(
                f"Win rate: {wr:.1f}% ({n_wins} victorias / {n_total} partidas). "
                f"Con WR por debajo del 45% en {n_total} partidas, "
                f"la prioridad es estabilizar el nivel antes de optimizar metricas individuales."
            )
        elif wr > 55:
            parts.append(
                f"Win rate: {wr:.1f}% ({n_wins} victorias / {n_total} partidas) — "
                f"rendimiento positivo."
            )
        else:
            parts.append(
                f"Win rate: {wr:.1f}% ({n_wins} victorias / {n_total} partidas) — "
                f"equilibrado."
            )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Resultados de borde
# ---------------------------------------------------------------------------

def _coaching_insufficient(
    role: str,
    score_result: sv2.ScoreResultV2,
    n: int,
    session_warning: Optional[str],
) -> CoachingResult:
    """Resultado cuando hay datos insuficientes para diagnosticar."""
    min_needed = 5
    return CoachingResult(
        role=role,
        confidence_level="insufficient",
        primary_problem="Datos insuficientes para diagnostico",
        evidence=(
            f"Solo {n} partidas de {role} en la base de datos. "
            f"Minimo recomendado para coaching: {min_needed}."
        ),
        probable_cause="No hay suficientes partidas para detectar patrones de comportamiento.",
        impact=(
            "El coaching requiere al menos 5 partidas del mismo rol para generar "
            "diagnosticos con base estadistica."
        ),
        weekly_goal=WeeklyGoal(
            description=(
                f"Jugar al menos {min_needed - n} partidas mas de {role} "
                f"para activar el sistema de coaching."
            ),
            metric="sample_size",
            current=float(n),
            target=float(min_needed),
            window="proximas sesiones",
        ),
        training_plan=TrainingPlan(
            primary=f"Juega mas partidas de {role} para que el sistema pueda detectar patrones.",
            secondary=[
                "Mantener un rol principal acelera la deteccion de habitos.",
                "Con 10+ partidas del mismo rol obtendrás nivel de confianza 'reliable'.",
            ],
        ),
        strengths=[],
        improvements=[],
        trend_summary="Datos insuficientes para calcular tendencia.",
        sample_size=n,
        session_warning=session_warning,
    )


def _coaching_no_problems(
    role: str,
    score_result: sv2.ScoreResultV2,
    strengths: list[Strength],
    n: int,
    session_warning: Optional[str],
) -> CoachingResult:
    """Resultado cuando no se detectan problemas en los umbrales actuales."""
    trend_summary = _build_trend_summary(score_result)
    return CoachingResult(
        role=role,
        confidence_level=score_result.confidence_level,
        primary_problem="Sin problemas criticos detectados",
        evidence=(
            f"Todas las metricas estan dentro de los umbrales esperados "
            f"(N={n} partidas {role})."
        ),
        probable_cause="El jugador esta rindiendo dentro del rango aceptable en todas las dimensiones.",
        impact="Mantener el nivel actual y trabajar en consistencia para subir elo.",
        weekly_goal=WeeklyGoal(
            description="Mantener el nivel actual durante 10 partidas consecutivas sin partidas outlier.",
            metric="consistency_score",
            current=score_result.consistency_score or 70.0,
            target=min(100.0, (score_result.consistency_score or 70.0) + 5.0),
            window="proximas 10 partidas",
        ),
        training_plan=TrainingPlan(
            primary="Mantén los hábitos que te están funcionando. Consolida antes de expandir.",
            secondary=[
                "Reduce tu pool de champions a 2 y estudia cada match-up en profundidad.",
                "Trabaja la mentalidad entre partidas: no dejes que las derrotas cambien tu estilo de juego.",
            ],
        ),
        strengths=strengths,
        improvements=[],
        trend_summary=trend_summary,
        sample_size=n,
        session_warning=session_warning,
    )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def analyze_coaching(
    score_result: sv2.ScoreResultV2,
    match_history: list[dict],
    role: str,
) -> CoachingResult:
    """
    Analiza el historial del jugador y genera diagnóstico de coaching.

    Args:
        score_result:  Resultado de scorer_v2.analyze_player() para el rol.
        match_history: Lista de todas las partidas del jugador (cualquier rol).
                       Se filtra internamente por `role`.
        role:          'ADC', 'TOP' o 'MID' (roles implementados).

    Returns:
        CoachingResult con diagnóstico basado en reglas y datos.
        Sin IA, sin invención de métricas.

    Limitaciones:
        - Benchmarks son auto-relativos (jugador vs sí mismo).
        - Umbrales absolutos provienen del documento de Arquitectura V2.
        - Todos los roles requieren N >= 5 para análisis mínimo.
        - JUNGLE / SUPPORT no implementados.
    """
    # Filtrar y ordenar por rol (más reciente primero)
    role_matches = sorted(
        [m for m in match_history if m.get("role") == role],
        key=lambda m: m.get("played_at", ""),
        reverse=True,
    )
    n = len(role_matches)

    # Detectar tilt / racha de sesión
    session_warning = _detect_session_warning(role_matches)

    # Datos insuficientes
    if score_result.confidence_level == "insufficient":
        return _coaching_insufficient(role, score_result, n, session_warning)

    # Roles no soportados
    if role not in sv2.SUPPORTED_ROLES:
        return CoachingResult(
            role=role,
            confidence_level="insufficient",
            primary_problem=f"Rol {role} no implementado",
            evidence=f"El coaching de {role} esta pendiente de implementacion (Sprint futuro).",
            probable_cause="Rol no soportado.",
            impact="Sin diagnostico disponible.",
            weekly_goal=WeeklyGoal(
                description="Jugar ADC, TOP o MID para obtener coaching.",
                metric="role",
                current=0.0,
                target=1.0,
                window="proximas sesiones",
            ),
            training_plan=TrainingPlan(
                primary="Juega partidas de ADC, TOP o MID para acceder al coaching.",
                secondary=["JUNGLE y SUPPORT seran implementados en una version futura.", ""],
            ),
            strengths=[],
            improvements=[],
            trend_summary="Rol no soportado.",
            sample_size=n,
            session_warning=session_warning,
        )

    # Evaluar problemas por rol
    if role == "ADC":
        problems  = _evaluate_adc_problems(role_matches, score_result.benchmarks, score_result)
        strengths = _detect_strengths_adc(role_matches, score_result.benchmarks, score_result)
    elif role == "TOP":
        problems  = _evaluate_top_problems(role_matches, score_result.benchmarks, score_result)
        strengths = _detect_strengths_top(role_matches, score_result.benchmarks, score_result)
    else:  # MID
        problems  = _evaluate_mid_problems(role_matches, score_result.benchmarks, score_result)
        strengths = _detect_strengths_mid(role_matches, score_result.benchmarks, score_result)

    # Sin problemas detectados
    primary = _select_primary(problems)
    if primary is None:
        return _coaching_no_problems(role, score_result, strengths, n, session_warning)

    # Problema principal
    primary_key = primary["key"]
    rule_map    = rules.PROBLEMS_BY_ROLE.get(role, rules.ADC_PROBLEMS)
    rule_def    = rule_map.get(primary_key, {})

    evidence      = _generate_evidence(primary, role)
    weekly_goal   = _generate_weekly_goal(primary, role)
    training_plan = _generate_training_plan(primary_key, role)
    trend_summary = _build_trend_summary(score_result)

    # Problemas secundarios (sin el principal, ordenados por severidad)
    secondary = sorted(
        [p for p in problems if p["key"] != primary_key],
        key=lambda p: p["severity"],
        reverse=True,
    )
    improvements = [
        rule_map[p["key"]]["display_name"]
        for p in secondary[:2]
        if p["key"] in rule_map
    ]

    return CoachingResult(
        role=role,
        confidence_level=score_result.confidence_level,
        primary_problem=rule_def.get("name", primary_key),
        evidence=evidence,
        probable_cause=rule_def.get("probable_cause", "No documentado."),
        impact=rule_def.get("impact", "No documentado."),
        weekly_goal=weekly_goal,
        training_plan=training_plan,
        strengths=strengths,
        improvements=improvements,
        trend_summary=trend_summary,
        sample_size=n,
        session_warning=session_warning,
    )
