"""
scorer_v2.py — Motor de scoring profesional por rol.

Arquitectura:
    Rol → Responsabilidades → Métricas → Dimensiones → Scores

Roles implementados:
    ADC: Economy / Positioning / Combat Impact
    TOP: Lane Control / Pressure / Survival

Roles pendientes (arquitectura lista):
    MID / JUNGLE / SUPPORT

Principios de diseño:
    1. Scores son relativos a la distribución histórica del propio jugador.
       No hay benchmarks externos inventados.
    2. Pesos entre métricas: IGUALES por ahora.
       Con N=27 ADC (WIN=11 / LOSS=16), la muestra es insuficiente para
       derivar pesos estadísticamente significativos vía regresión logística.
       Excepción documentada: kill_participation es el mayor discriminador
       de win/loss en este dataset (delta +0.106). Pero con N<50 por rol,
       cualquier peso derivado tendría error estándar > 30%.
    3. Métricas normalizadas por duración cuando aplica (gold/min, dmg/min).
       Esto hace que las partidas cortas (incluyendo surrenders) sean
       comparables con partidas largas sin introducir sesgo sistemático.
    4. Surrenders (game_ended_surrender=1): se analizan, se marcan, no se ocultan.
    5. Campos NULL: si una métrica no existe, se excluye del cálculo
       y se registra en notes. El score se calcula con las métricas disponibles.
"""

import math
import statistics
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Umbral de pendiente para clasificar tendencia (puntos por partida).
# Justificación: en 10 juegos, una mejora de 15 puntos (1.5/game) es
# perceptible y no atribuible solo a varianza de muestreo.
_TREND_THRESHOLD = 1.5

# Mínimo de partidas para calcular distribución de referencia.
# Con N < _MIN_REF_SAMPLES, el percentile rank es poco fiable.
_MIN_REF_SAMPLES = 3


# ---------------------------------------------------------------------------
# Estructuras de datos
# ---------------------------------------------------------------------------

@dataclass
class DimensionScore:
    """Score de una dimensión de coaching para una partida individual."""
    name:    str
    score:   Optional[float]    # 0–100; None si no hay datos suficientes
    metrics: dict               # {metric_name: raw_value}
    notes:   list[str]          # advertencias, métricas omitidas, contexto


@dataclass
class MatchScore:
    """Scoring de una partida individual relativo a la distribución histórica."""
    match_id:     str
    role:         str
    overall_score: Optional[float]
    dimensions:   list[DimensionScore]
    is_surrender: bool
    played_at:    str
    result:       str           # 'WIN' | 'LOSS'
    champion:     str


@dataclass
class MetricStats:
    """Estadísticas de una métrica calculadas desde datos reales."""
    n:    int
    mean: float
    std:  float
    p25:  float
    p50:  float
    p75:  float
    p90:  float


@dataclass
class PlayerBenchmarks:
    """
    Percentiles calculados exclusivamente desde los datos reales del jugador.
    NO contiene valores inventados o importados de fuentes externas.
    """
    role:        str
    sample_size: int
    metrics:     dict[str, MetricStats]   # {metric_name: MetricStats}
    note:        str                      # limitaciones de muestra detectadas


@dataclass
class ScoreResultV2:
    """Análisis completo del jugador sobre N partidas de un rol."""
    # Identidad
    role:             str
    dominant_role:    str       # igual que role; extensible para team analysis
    role_distribution: dict     # {role: count}; extensible para team analysis

    # Scores agregados
    overall_score:   Optional[float]
    dimensions:      dict[str, Optional[float]]   # {dim_name: avg_score}
    primary_problem: Optional[str]                # dimensión con peor score

    # Análisis temporal
    consistency_score: Optional[float]  # 0–100, mayor = más consistente
    trend:             str              # 'improving' | 'stable' | 'declining'
    trend_slope:       float            # pendiente de regresión lineal

    # Calidad de muestra
    confidence_level: str   # 'insufficient' | 'preliminary' | 'reliable' | 'robust'
    sample_size:      int
    surrender_count:  int

    # Detalle por partida
    match_scores:  list[MatchScore]
    benchmarks:    PlayerBenchmarks

    # Documentación
    limitations:   list[str]   # limitaciones detectadas en esta sesión


# ---------------------------------------------------------------------------
# Utilidades matemáticas
# ---------------------------------------------------------------------------

def _safe(match: dict, key: str) -> Optional[float]:
    """Extrae un campo del dict de partida. Devuelve None si es NULL."""
    v = match.get(key)
    return None if v is None else float(v)


def _derived_per_min(match: dict, key: str) -> Optional[float]:
    """
    Normaliza un campo por la duración de la partida (valor / minutos).
    Devuelve None si el campo o la duración son inválidos.
    Esto elimina el sesgo de partidas cortas vs largas.
    """
    val = _safe(match, key)
    dur = _safe(match, "duration_sec")
    if val is None or dur is None or dur <= 0:
        return None
    return val / (dur / 60.0)


def _cs_per_min(match: dict) -> Optional[float]:
    """CS/min = (totalMinionsKilled + neutralMinionsKilled) / minutos."""
    cs  = _safe(match, "cs")
    dur = _safe(match, "duration_sec")
    if cs is None or dur is None or dur <= 0:
        return None
    return cs / (dur / 60.0)


def _time_dead_pct(match: dict) -> Optional[float]:
    """Fracción del tiempo de juego que el jugador estuvo muerto [0–1]."""
    dead = _safe(match, "time_spent_dead")
    dur  = _safe(match, "duration_sec")
    if dead is None or dur is None or dur <= 0:
        return None
    return dead / dur


def _longest_alive_pct(match: dict) -> Optional[float]:
    """Fracción de la duración en la que el jugador vivió sin morir [0–1]."""
    alive = _safe(match, "longest_time_alive")
    dur   = _safe(match, "duration_sec")
    if alive is None or dur is None or dur <= 0:
        return None
    return min(alive / dur, 1.0)


# ---------------------------------------------------------------------------
# Scoring de métricas individuales
# ---------------------------------------------------------------------------

def _build_ref(matches: list[dict], extract_fn) -> list[float]:
    """
    Construye una lista de referencia extrayendo una métrica de cada partida.
    Excluye automáticamente los valores None.
    """
    return [v for m in matches if (v := extract_fn(m)) is not None]


def _percentile_score(value: float, ref: list[float], higher_is_better: bool = True) -> float:
    """
    Calcula score [0–100] basado en el percentile rank del valor en la
    distribución de referencia.

    Fórmula: score = (fracción de ref ≤ value) × 100

    Para métricas donde MENOR es mejor (deaths, time_dead), se invierte:
        score = (fracción de ref ≥ value) × 100
        equivalente a: score = (1 – percentile_rank) × 100

    Esta función no asume ninguna forma de distribución (no-paramétrica).
    Un valor en P50 → score = 50. En P75 → score = 75.
    """
    if len(ref) < _MIN_REF_SAMPLES:
        return 50.0  # neutral por falta de datos

    if higher_is_better:
        rank = sum(1 for v in ref if v <= value) / len(ref)
    else:
        rank = sum(1 for v in ref if v >= value) / len(ref)

    return rank * 100.0


def _score_metric(
    value: Optional[float],
    ref:   list[float],
    higher_is_better: bool = True,
) -> Optional[float]:
    """Score de una métrica individual. Devuelve None si value es None."""
    if value is None:
        return None
    if not ref:
        return None
    return _percentile_score(value, ref, higher_is_better)


def _avg_scores(scores: list[Optional[float]]) -> Optional[float]:
    """Promedio de scores, ignorando None. Devuelve None si todos son None."""
    valid = [s for s in scores if s is not None]
    if not valid:
        return None
    return statistics.mean(valid)


# ---------------------------------------------------------------------------
# Cálculo de benchmarks (solo desde datos reales)
# ---------------------------------------------------------------------------

def _metric_stats(values: list[float]) -> Optional[MetricStats]:
    """Calcula estadísticas de una lista de valores. None si N < 2."""
    n = len(values)
    if n < 2:
        return None
    s = sorted(values)
    return MetricStats(
        n=n,
        mean=statistics.mean(s),
        std=statistics.stdev(s),
        p25=s[max(0, int(n * 0.25))],
        p50=s[max(0, int(n * 0.50))],
        p75=s[max(0, int(n * 0.75))],
        p90=s[max(0, min(int(n * 0.90), n - 1))],
    )


def calculate_benchmarks(matches: list[dict], role: str) -> PlayerBenchmarks:
    """
    Calcula percentiles P25/P50/P75/P90 desde los datos reales del jugador.

    IMPORTANTE: estos son benchmarks propios del jugador, no benchmarks de elo.
    Un score de 75 significa "rendiste mejor que el 75% de tus propias partidas",
    no "rendiste en P75 de todos los jugadores de tu elo".

    Para benchmarks de elo se requieren datos externos (no disponibles en la API
    de Riot sin acceso a datasets masivos). Documentado en limitaciones.
    """
    role_matches = [m for m in matches if m.get("role") == role]
    n = len(role_matches)

    note_parts = []
    if n < 5:
        note_parts.append(
            f"N={n} insuficiente para benchmarks estadísticamente fiables. "
            "Scores son estimaciones de muy baja confianza."
        )
    elif n < 20:
        note_parts.append(
            f"N={n} es una muestra pequeña. Benchmarks mejorarán con más partidas. "
            "P90 en particular es poco fiable con N<20."
        )
    note_parts.append(
        "Benchmarks son auto-relativos (jugador vs sí mismo), no vs otros jugadores del mismo elo."
    )

    # Definición de métricas a calcular y cómo extraerlas
    extractors = {
        "cs_per_min":          _cs_per_min,
        "cs_at_10":            lambda m: _safe(m, "cs_at_10"),
        "gold_per_min":        lambda m: _derived_per_min(m, "gold_earned"),
        "deaths":              lambda m: _safe(m, "deaths"),
        "time_dead_pct":       _time_dead_pct,
        "longest_alive_pct":   _longest_alive_pct,
        "kill_participation":  lambda m: _safe(m, "kill_participation"),
        "team_damage_pct":     lambda m: _safe(m, "team_damage_pct"),
        "objectives_per_min":  lambda m: _derived_per_min(m, "damage_to_objectives"),
        "max_cs_advantage":    lambda m: _safe(m, "max_cs_advantage"),
        "turrets_per_min":     lambda m: _derived_per_min(m, "damage_to_turrets"),
        "turret_takedowns":    lambda m: _safe(m, "turret_takedowns"),
    }

    metrics: dict[str, MetricStats] = {}
    for name, fn in extractors.items():
        values = _build_ref(role_matches, fn)
        stats = _metric_stats(values)
        if stats is not None:
            metrics[name] = stats

    return PlayerBenchmarks(
        role=role,
        sample_size=n,
        metrics=metrics,
        note=" | ".join(note_parts),
    )


# ---------------------------------------------------------------------------
# Dimensiones ADC
# ---------------------------------------------------------------------------

def _score_adc_economy(match: dict, ref: list[dict]) -> DimensionScore:
    """
    Economy — ¿Está el ADC generando el gold necesario para escalar?

    Métricas:
        cs_per_min:   CS/min durante toda la partida.
        cs_at_10:     CS en los primeros 10 minutos (challenges). Mide la
                      eficiencia en lane phase antes de que el mapa se abra.
                      NULL en partidas anteriores al parche 12.x.
        gold_per_min: gold_earned / duración. Normalizado para que partidas
                      cortas y largas sean comparables.

    Peso entre métricas: IGUAL (1/3 cada una).
    Justificación del peso igual: con N=27 ADC y WIN/LOSS desbalanceados
    (11/16), el error estándar de pesos derivados de regresión sería > 30%.
    No hay base estadística para pesos asimétricos con esta muestra.
    """
    notes = []

    # cs/min
    cs_pm     = _cs_per_min(match)
    ref_cspm  = _build_ref(ref, _cs_per_min)
    s_cspm    = _score_metric(cs_pm, ref_cspm, higher_is_better=True)

    # cs_at_10
    cs10      = _safe(match, "cs_at_10")
    ref_cs10  = _build_ref(ref, lambda m: _safe(m, "cs_at_10"))
    s_cs10    = _score_metric(cs10, ref_cs10, higher_is_better=True)
    if cs10 is None:
        notes.append("cs_at_10 no disponible (parche pre-12.x o campo ausente).")

    # gold/min
    gpm       = _derived_per_min(match, "gold_earned")
    ref_gpm   = _build_ref(ref, lambda m: _derived_per_min(m, "gold_earned"))
    s_gpm     = _score_metric(gpm, ref_gpm, higher_is_better=True)
    if gpm is None:
        notes.append("gold_earned no disponible.")

    is_surr = bool(match.get("game_ended_surrender"))
    if is_surr:
        notes.append(
            "Partida rendida: gold_per_min y cs/min calculados hasta el momento del surrender. "
            "Valores generalmente menores que en partidas completas (juego no llegó a late game)."
        )

    score = _avg_scores([s_cspm, s_cs10, s_gpm])

    return DimensionScore(
        name="Economy",
        score=round(score, 1) if score is not None else None,
        metrics={
            "cs_per_min":  round(cs_pm, 2)  if cs_pm  is not None else None,
            "cs_at_10":    int(cs10)         if cs10   is not None else None,
            "gold_per_min": round(gpm, 1)   if gpm    is not None else None,
        },
        notes=notes,
    )


def _score_adc_positioning(match: dict, ref: list[dict]) -> DimensionScore:
    """
    Positioning — ¿Está el ADC muriendo en momentos que cuestan la partida?

    Métricas:
        deaths:          Número total de muertes. Más directo e interpretable.
        time_dead_pct:   Tiempo muerto / duración total. Normalizado: una
                         muerte en minuto 5 cuesta más tiempo relativo que
                         en minuto 35 (respawn mayor pero partida más corta).
        longest_alive_pct: Mayor racha de vida / duración. Indica si el
                         jugador puede sobrevivir en las peleas importantes.

    Peso entre métricas: IGUAL.

    Limitación conocida: no distingue entre muerte evitable vs intercambio
    favorable. Riot API no provee contexto de si la muerte fue «correcta».
    Un ADC que muere para salvar al carry en Baron puede tener deaths=5
    pero todos justificados. Este sistema trata todas las muertes igual.
    """
    notes = []

    # deaths
    deaths      = _safe(match, "deaths")
    ref_deaths  = _build_ref(ref, lambda m: _safe(m, "deaths"))
    s_deaths    = _score_metric(deaths, ref_deaths, higher_is_better=False)

    # time_dead_pct
    td_pct      = _time_dead_pct(match)
    ref_tdp     = _build_ref(ref, _time_dead_pct)
    s_tdp       = _score_metric(td_pct, ref_tdp, higher_is_better=False)
    if td_pct is None:
        notes.append("time_spent_dead no disponible.")

    # longest_alive_pct
    la_pct      = _longest_alive_pct(match)
    ref_lap     = _build_ref(ref, _longest_alive_pct)
    s_lap       = _score_metric(la_pct, ref_lap, higher_is_better=True)
    if la_pct is None:
        notes.append("longest_time_alive no disponible.")

    if bool(match.get("game_ended_surrender")):
        notes.append(
            "Partida rendida: deaths y tiempo muerto medidos en partida corta. "
            "Muertes tempranas tienen mayor peso relativo en partidas de 15 min."
        )

    score = _avg_scores([s_deaths, s_tdp, s_lap])

    return DimensionScore(
        name="Positioning",
        score=round(score, 1) if score is not None else None,
        metrics={
            "deaths":           int(deaths)        if deaths  is not None else None,
            "time_dead_pct":    round(td_pct, 3)   if td_pct  is not None else None,
            "longest_alive_pct": round(la_pct, 3)  if la_pct  is not None else None,
        },
        notes=notes,
    )


def _score_adc_combat(match: dict, ref: list[dict]) -> DimensionScore:
    """
    Combat Impact — ¿Está el ADC cumpliendo su rol de dealer de daño sostenido?

    Métricas:
        kill_participation:  Fracción de kills/assists del equipo donde participó.
                             En este dataset es el mayor discriminador de win/loss
                             para ADC (delta WIN-LOSS = +0.106, N=27).
        team_damage_pct:     Fracción del daño total del equipo. En este dataset
                             NO discrimina win/loss (delta = -0.001), posiblemente
                             por el tamaño de muestra. Se incluye por evidencia
                             externa (correlación 0.60-0.68 en datasets grandes).
        objectives_per_min:  damage_to_objectives / minuto. Mide presencia en
                             peleas de Dragon/Baron, que son las que ganan partidas.

    Nota sobre team_damage_pct: el análisis de este dataset (N=27) muestra
    que WIN y LOSS tienen prácticamente el mismo team_damage_pct (0.213 vs 0.214).
    Esto contradice estudios externos con N>10000. La causa probable es el
    tamaño de muestra insuficiente. Se mantiene la métrica por coherencia
    con la arquitectura V2, pero su peso real podría ser cercano a cero
    con esta muestra específica.
    """
    notes = []

    # kill_participation
    kp         = _safe(match, "kill_participation")
    ref_kp     = _build_ref(ref, lambda m: _safe(m, "kill_participation"))
    s_kp       = _score_metric(kp, ref_kp, higher_is_better=True)
    if kp is None:
        notes.append("kill_participation no disponible.")

    # team_damage_pct
    tdpct      = _safe(match, "team_damage_pct")
    ref_tdpct  = _build_ref(ref, lambda m: _safe(m, "team_damage_pct"))
    s_tdpct    = _score_metric(tdpct, ref_tdpct, higher_is_better=True)
    if tdpct is None:
        notes.append("team_damage_pct no disponible.")

    # objectives/min
    obj_pm     = _derived_per_min(match, "damage_to_objectives")
    ref_objpm  = _build_ref(ref, lambda m: _derived_per_min(m, "damage_to_objectives"))
    s_objpm    = _score_metric(obj_pm, ref_objpm, higher_is_better=True)
    if obj_pm is None:
        notes.append("damage_to_objectives no disponible.")

    if bool(match.get("game_ended_surrender")):
        notes.append(
            "Partida rendida: kill_participation calculado con menos fights. "
            "objectives_per_min puede ser bajo por falta de tiempo para Dragon/Baron."
        )

    score = _avg_scores([s_kp, s_tdpct, s_objpm])

    return DimensionScore(
        name="Combat Impact",
        score=round(score, 1) if score is not None else None,
        metrics={
            "kill_participation": round(kp, 3)    if kp     is not None else None,
            "team_damage_pct":    round(tdpct, 3) if tdpct  is not None else None,
            "objectives_per_min": round(obj_pm, 1) if obj_pm is not None else None,
        },
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Dimensiones TOP
# ---------------------------------------------------------------------------

def _score_top_lane_control(match: dict, ref: list[dict]) -> DimensionScore:
    """
    Lane Control — ¿Domina el TOP su fase de líneas?

    Métricas:
        cs_at_10:       CS en primeros 10 min. Mide eficiencia de farm early.
        max_cs_advantage: Ventaja máxima de CS vs rival (puede ser negativa).
                         Mide dominio del match-up. Disponible desde challenges.
        gold_per_min:   Gold total / minuto. Captura eficiencia económica
                         más allá de solo minions (platos, kills, heralds).

    Advertencia N=1 TOP: con una sola partida, los benchmarks son el propio
    valor de esa partida. El percentile rank de cualquier métrica será 50%.
    El score resultante es una estimación sin valor estadístico.
    """
    notes = []
    if len(ref) < 5:
        notes.append(
            f"Referencia insuficiente (N={len(ref)} partidas TOP). "
            "Scores TOP son estimaciones sin valor estadístico."
        )

    # cs_at_10
    cs10      = _safe(match, "cs_at_10")
    ref_cs10  = _build_ref(ref, lambda m: _safe(m, "cs_at_10"))
    s_cs10    = _score_metric(cs10, ref_cs10, higher_is_better=True)
    if cs10 is None:
        notes.append("cs_at_10 no disponible.")

    # max_cs_advantage (puede ser negativo → higher is still better)
    csa       = _safe(match, "max_cs_advantage")
    ref_csa   = _build_ref(ref, lambda m: _safe(m, "max_cs_advantage"))
    s_csa     = _score_metric(csa, ref_csa, higher_is_better=True)
    if csa is None:
        notes.append("max_cs_advantage no disponible.")

    # gold/min
    gpm       = _derived_per_min(match, "gold_earned")
    ref_gpm   = _build_ref(ref, lambda m: _derived_per_min(m, "gold_earned"))
    s_gpm     = _score_metric(gpm, ref_gpm, higher_is_better=True)
    if gpm is None:
        notes.append("gold_earned no disponible.")

    score = _avg_scores([s_cs10, s_csa, s_gpm])

    return DimensionScore(
        name="Lane Control",
        score=round(score, 1) if score is not None else None,
        metrics={
            "cs_at_10":         int(cs10)         if cs10  is not None else None,
            "max_cs_advantage":  int(csa)          if csa   is not None else None,
            "gold_per_min":      round(gpm, 1)     if gpm   is not None else None,
        },
        notes=notes,
    )


def _score_top_pressure(match: dict, ref: list[dict]) -> DimensionScore:
    """
    Pressure — ¿Convierte el TOP su ventaja en presión estructural?

    Métricas:
        turrets_per_min:   Daño a torretas / minuto. Normalizado para
                           comparar split pushers en todas las longitudes de partida.
        turret_takedowns:  Número de torres destruidas. Métrica absoluta
                           complementaria a turrets_per_min.
        objectives_per_min: Daño a objetivos (Dragon/Baron/Herald) / minuto.
                           Mide si el TOP asiste en objetivos o está pusheando solo.

    Limitación: presión lateral exitosa no siempre resulta en torres caídas.
    Un split efectivo que fuerza 2 rivales a responder mientras el equipo
    toma Baron 4v3 es victorioso pero puede mostrar 0 torres. La API solo
    captura el resultado estructural, no la presión generada.
    """
    notes = []
    if len(ref) < 5:
        notes.append(
            f"Referencia insuficiente (N={len(ref)} partidas TOP). "
            "Scores TOP son estimaciones sin valor estadístico."
        )

    # turrets/min
    turr_pm    = _derived_per_min(match, "damage_to_turrets")
    ref_tpm    = _build_ref(ref, lambda m: _derived_per_min(m, "damage_to_turrets"))
    s_tpm      = _score_metric(turr_pm, ref_tpm, higher_is_better=True)
    if turr_pm is None:
        notes.append("damage_to_turrets no disponible.")

    # turret_takedowns
    tt         = _safe(match, "turret_takedowns")
    ref_tt     = _build_ref(ref, lambda m: _safe(m, "turret_takedowns"))
    s_tt       = _score_metric(tt, ref_tt, higher_is_better=True)
    if tt is None:
        notes.append("turret_takedowns no disponible.")

    # objectives/min
    obj_pm     = _derived_per_min(match, "damage_to_objectives")
    ref_opm    = _build_ref(ref, lambda m: _derived_per_min(m, "damage_to_objectives"))
    s_opm      = _score_metric(obj_pm, ref_opm, higher_is_better=True)
    if obj_pm is None:
        notes.append("damage_to_objectives no disponible.")

    score = _avg_scores([s_tpm, s_tt, s_opm])

    return DimensionScore(
        name="Pressure",
        score=round(score, 1) if score is not None else None,
        metrics={
            "turrets_per_min":   round(turr_pm, 1) if turr_pm is not None else None,
            "turret_takedowns":  int(tt)            if tt      is not None else None,
            "objectives_per_min": round(obj_pm, 1) if obj_pm  is not None else None,
        },
        notes=notes,
    )


def _score_top_survival(match: dict, ref: list[dict]) -> DimensionScore:
    """
    Survival — ¿Sobrevive el TOP para cumplir su función?

    Métricas:
        deaths:         Muertes totales. Más directo e interpretable.
        time_dead_pct:  Tiempo muerto / duración. Normalizado por longitud
                        de partida. Un TOP que muere 3 veces en 15 min
                        pierde más tiempo relativo que en 40 min.

    Nota: a diferencia del ADC, TOP tiene más opciones para absorber muertes
    como parte de su rol (engage, initiate). Pero una muerte sin consecuencias
    positivas para el equipo sigue siendo costosa.
    """
    notes = []
    if len(ref) < 5:
        notes.append(
            f"Referencia insuficiente (N={len(ref)} partidas TOP). "
            "Scores TOP son estimaciones sin valor estadístico."
        )

    # deaths
    deaths     = _safe(match, "deaths")
    ref_d      = _build_ref(ref, lambda m: _safe(m, "deaths"))
    s_d        = _score_metric(deaths, ref_d, higher_is_better=False)

    # time_dead_pct
    td_pct     = _time_dead_pct(match)
    ref_tdp    = _build_ref(ref, _time_dead_pct)
    s_tdp      = _score_metric(td_pct, ref_tdp, higher_is_better=False)
    if td_pct is None:
        notes.append("time_spent_dead no disponible.")

    score = _avg_scores([s_d, s_tdp])

    return DimensionScore(
        name="Survival",
        score=round(score, 1) if score is not None else None,
        metrics={
            "deaths":        int(deaths)      if deaths  is not None else None,
            "time_dead_pct": round(td_pct, 3) if td_pct  is not None else None,
        },
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Dispatch por rol
# ---------------------------------------------------------------------------

def _score_dimensions(match: dict, ref: list[dict], role: str) -> list[DimensionScore]:
    """Calcula todas las dimensiones para un rol específico."""
    if role == "ADC":
        return [
            _score_adc_economy(match, ref),
            _score_adc_positioning(match, ref),
            _score_adc_combat(match, ref),
        ]
    if role == "TOP":
        return [
            _score_top_lane_control(match, ref),
            _score_top_pressure(match, ref),
            _score_top_survival(match, ref),
        ]
    # MID / JUNGLE / SUPPORT: pendiente de implementación
    return []


# ---------------------------------------------------------------------------
# Análisis temporal
# ---------------------------------------------------------------------------

def _linear_slope(y_values: list[float]) -> float:
    """
    Calcula la pendiente de la regresión lineal OLS sobre y_values.
    x = [0, 1, 2, ..., N-1] (índice cronológico, 0 = más antiguo).

    Fórmula OLS cerrada:
        slope = (N·Σ(xᵢ·yᵢ) − Σxᵢ·Σyᵢ) / (N·Σ(xᵢ²) − (Σxᵢ)²)

    Devuelve 0.0 si N < 2 o el denominador es 0.
    Positivo = mejora, negativo = deterioro.
    """
    n = len(y_values)
    if n < 2:
        return 0.0
    x = list(range(n))
    sx  = sum(x)
    sy  = sum(y_values)
    sxy = sum(xi * yi for xi, yi in zip(x, y_values))
    sxx = sum(xi * xi for xi in x)
    denom = n * sxx - sx * sx
    if denom == 0:
        return 0.0
    return (n * sxy - sx * sy) / denom


def _classify_trend(slope: float) -> str:
    """
    Clasifica la tendencia basada en la pendiente de regresión.

    Umbral ±1.5 puntos/partida:
        - En 10 partidas: ±15 puntos de cambio total.
        - 15 puntos de mejora en 10 partidas es perceptible y no atribuible
          solo a varianza aleatoria (con la desviación típica de ~15-25 pts
          que muestran los datos reales).
        - Por debajo del umbral: fluctuaciones normales entre partidas.
    """
    if slope > _TREND_THRESHOLD:
        return "improving"
    if slope < -_TREND_THRESHOLD:
        return "declining"
    return "stable"


def _consistency_cv(scores: list[float]) -> Optional[float]:
    """
    Consistencia basada en Coefficient of Variation (CV).

    Fórmula:
        CV      = (std_dev / |mean|) × 100
        score   = max(0, 100 − CV)

    Ejemplos de interpretación:
        [90, 90, 90, 10, 10]: mean=58, std=40, CV=69 → consistency=31
        [58, 58, 58, 58, 58]: mean=58, std=0,  CV=0  → consistency=100
        [40, 60, 40, 60, 40]: mean=48, std=10, CV=21 → consistency=79

    CV = 0   → consistencia perfecta (100)
    CV = 100 → misma magnitud de variación que la media (0)
    CV > 100 → peor que el peor caso teórico (se clampea a 0)

    Edge case: mean≈0 → se usa std directamente para evitar división por cero.
    """
    n = len(scores)
    if n < 2:
        return None
    mean_val = statistics.mean(scores)
    std_val  = statistics.stdev(scores)
    if abs(mean_val) < 1e-9:
        return max(0.0, 100.0 - std_val)
    cv = (std_val / abs(mean_val)) * 100.0
    return round(max(0.0, 100.0 - cv), 1)


def _confidence_level(n: int) -> str:
    """
    Nivel de confianza basado en el tamaño de muestra.

    Umbrales justificados:
        N < 5:   Un solo partido malo puede mover el score >30 puntos.
                 Los percentiles P25/P75 son el mismo punto en muchos casos.
        5-9:     P25/P75 son estimables pero P90 no. Tendencia visible pero ruidosa.
        10-19:   Suficiente para detectar patrones. Error estándar de la media ~8-15%.
        ≥20:     Benchmarks estables. Tendencia y consistencia son fiables.
    """
    if n < 5:
        return "insufficient"
    if n < 10:
        return "preliminary"
    if n < 20:
        return "reliable"
    return "robust"


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def score_match(match: dict, reference_matches: list[dict]) -> Optional[MatchScore]:
    """
    Calcula el score de una partida individual relativo a la distribución
    histórica del jugador.

    Args:
        match:             Dict de una partida (campos V1 + V2 de la DB).
        reference_matches: Lista de partidas del mismo rol usadas como
                           distribución de referencia. Puede incluir `match`.

    Returns:
        MatchScore con scores por dimensión y overall, o None si el rol
        no está soportado.

    Nota sobre surrenders:
        Si game_ended_surrender=1, la partida se analiza igualmente pero
        MatchScore.is_surrender=True. Cada dimensión incluye una nota
        explicando el impacto del surrender en sus métricas específicas.
    """
    role = match.get("role", "OTHER")
    if role not in ("ADC", "TOP"):
        return None

    # Filtrar referencia por mismo rol
    ref = [m for m in reference_matches if m.get("role") == role]

    dimensions = _score_dimensions(match, ref, role)

    # Overall = promedio de dimensiones con datos disponibles
    overall = _avg_scores([d.score for d in dimensions])

    return MatchScore(
        match_id=match.get("match_id", ""),
        role=role,
        overall_score=round(overall, 1) if overall is not None else None,
        dimensions=dimensions,
        is_surrender=bool(match.get("game_ended_surrender")),
        played_at=match.get("played_at", ""),
        result=match.get("result", ""),
        champion=match.get("champion", ""),
    )


def analyze_player(matches: list[dict], role: str) -> ScoreResultV2:
    """
    Análisis completo del jugador para un rol específico.

    Args:
        matches: Lista de partidas del jugador (cualquier rol). Se filtra
                 internamente por `role`. Orden no importa (se ordena por
                 played_at internamente para el cálculo de tendencia).
        role:    'ADC' o 'TOP' (roles soportados actualmente).

    Returns:
        ScoreResultV2 con todos los indicadores de la arquitectura V2.

    Algoritmo de tendencia:
        1. Ordenar partidas por played_at (cronológico, más antigua primero).
        2. Calcular overall_score para cada partida.
        3. Regresión lineal OLS sobre (índice, overall_score).
        4. Clasificar pendiente: > +1.5 → improving, < -1.5 → declining.

    Algoritmo de consistencia:
        Coefficient of Variation sobre los overall_scores.
        CV = std/mean × 100. consistency = max(0, 100 - CV).
    """
    role_matches = [m for m in matches if m.get("role") == role]
    n = len(role_matches)

    limitations: list[str] = []

    # Calcular benchmarks desde datos reales
    benchmarks = calculate_benchmarks(matches, role)

    # Score de cada partida
    match_scores: list[MatchScore] = []
    for m in role_matches:
        ms = score_match(m, role_matches)
        if ms is not None:
            match_scores.append(ms)

    surrender_count = sum(1 for ms in match_scores if ms.is_surrender)

    if n == 0:
        return ScoreResultV2(
            role=role,
            dominant_role=role,
            role_distribution={role: 0},
            overall_score=None,
            dimensions={},
            primary_problem=None,
            consistency_score=None,
            trend="stable",
            trend_slope=0.0,
            confidence_level="insufficient",
            sample_size=0,
            surrender_count=0,
            match_scores=[],
            benchmarks=benchmarks,
            limitations=["Sin partidas de este rol en la base de datos."],
        )

    # Dimensiones promedio sobre todas las partidas
    dim_names = [d.name for d in match_scores[0].dimensions] if match_scores else []
    dim_avgs: dict[str, Optional[float]] = {}
    for dim_name in dim_names:
        scores_for_dim = [
            d.score
            for ms in match_scores
            for d in ms.dimensions
            if d.name == dim_name and d.score is not None
        ]
        dim_avgs[dim_name] = round(statistics.mean(scores_for_dim), 1) if scores_for_dim else None

    # Overall promedio
    overall_scores = [ms.overall_score for ms in match_scores if ms.overall_score is not None]
    overall = round(statistics.mean(overall_scores), 1) if overall_scores else None

    # Problema principal = dimensión con menor score promedio
    scored_dims = {k: v for k, v in dim_avgs.items() if v is not None}
    primary_problem = min(scored_dims, key=scored_dims.get) if scored_dims else None

    # Tendencia — ordenar cronológicamente (más antiguo primero)
    sorted_scores = [
        ms.overall_score
        for ms in sorted(match_scores, key=lambda ms: ms.played_at)
        if ms.overall_score is not None
    ]
    slope = _linear_slope(sorted_scores)
    trend = _classify_trend(slope)

    # Consistencia
    consistency = _consistency_cv(overall_scores) if len(overall_scores) >= 2 else None

    # Nivel de confianza
    confidence = _confidence_level(n)

    # Documentar limitaciones
    if n < 5:
        limitations.append(
            f"N={n} partidas insuficientes para análisis fiable de rol {role}. "
            "Mínimo recomendado: 10 para 'reliable', 20 para 'robust'."
        )
    if n < 20:
        limitations.append(
            "Pesos entre métricas son IGUALES (no derivados de datos). "
            "Con N<50 por rol, el error estándar de pesos estadísticos supera el 30%. "
            "Los pesos se revisarán cuando N≥50."
        )
    if surrender_count > 0:
        limitations.append(
            f"{surrender_count} partida(s) rendida(s) incluidas en el análisis. "
            "Métricas de duración (gold/min, objectives/min) son comparables "
            "gracias a la normalización, pero el contexto de juego es diferente."
        )
    if role == "TOP" and n < 10:
        limitations.append(
            "TOP tiene muestra muy pequeña. Scores son referenciales, no diagnósticos."
        )

    return ScoreResultV2(
        role=role,
        dominant_role=role,
        role_distribution={role: n},
        overall_score=overall,
        dimensions=dim_avgs,
        primary_problem=primary_problem,
        consistency_score=consistency,
        trend=trend,
        trend_slope=round(slope, 3),
        confidence_level=confidence,
        sample_size=n,
        surrender_count=surrender_count,
        match_scores=match_scores,
        benchmarks=benchmarks,
        limitations=limitations,
    )
