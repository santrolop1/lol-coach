"""
backend/services/champion_analyzer.py

Champion Intelligence: agrupa, clasifica y califica el champion pool
del jugador usando exclusivamente datos de partidas reales.

Flujo de datos:
    Riot API → parser.py → SQLite → scorer_v2 → este módulo → UI

NO se usan datos mock, hardcodes de campeones ni targets inventados.
Todo se calcula desde la distribución real del historial.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import scorer_v2


# ─── Umbrales (documentados) ─────────────────────────────────────────────────
#
# MIN_GAMES_QUALIFY: mínimo para entrar en clasificación y pool grade.
#   Elegido como 3 para evitar ruido estadístico con muestras de 1-2 partidas.
#
# MIN_GAMES_TABLE: mínimo para aparecer en la tabla de la UI.
#   2 partidas dan señal débil pero ya muestran un patrón inicial.
#
# TRAP_WR_MAX: WR por debajo de este umbral = TRAP.
#   Un campeón con ≤40% WR en suficientes partidas te está costando LP,
#   independientemente del score mecánico. La WR es la señal más honesta.
#   TRAP_SCORE_MAX: umbral adicional — si el score TAMBIÉN es bajo, el TRAP
#   se reporta con mayor severidad en los insights.
#
# CARRY_WR_MIN: para ser CARRY, el WR debe superar el 60%.
#   Umbral conservador que refleja ventaja real en una muestra pequeña.
#
# DEPENDENCY_HIGH / DEPENDENCY_MED: porcentaje de partidas en un solo campeón.
#   >50% = dependencia alta (1 ban te deja sin pick primario).
#   >33% = dependencia media (señal de alerta).

MIN_GAMES_QUALIFY = 3
MIN_GAMES_TABLE   = 2
TRAP_WR_MAX       = 0.40
TRAP_SCORE_MAX    = 45.0
CARRY_WR_MIN      = 0.60
DEPENDENCY_HIGH   = 0.50
DEPENDENCY_MED    = 0.33


# ─── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass
class ChampionStats:
    """Estadísticas agregadas de un campeón en un rol concreto."""
    champion:    str
    games:       int
    wins:        int
    losses:      int
    winrate:     float        # 0.0 – 1.0
    avg_score:   float        # scorer_v2 overall_score promedio
    score_std:   float        # desviación estándar del score
    avg_deaths:  float
    avg_kda:     float        # (kills + assists) / max(deaths, 1)
    avg_cs_pm:   float        # CS por minuto promedio
    avg_kp:      float        # kill_participation promedio (0.0 – 1.0)
    score_trend: float        # pendiente OLS de scores (+ mejora / – empeora)
    recent_wr:   float        # WR de las últimas 3 partidas (0.0 – 1.0)
    last_played: str          # fecha de la última partida (YYYY-MM-DD)

    @property
    def consistency_score(self) -> float:
        """0–100: mayor = más consistente (inverso del coeficiente de variación)."""
        if self.avg_score == 0:
            return 0.0
        cv = self.score_std / self.avg_score
        return max(0.0, min(100.0, (1.0 - cv) * 100.0))

    @property
    def carry_index(self) -> float:
        """Índice compuesto para ranking de carry: 60% WR + 40% score normalizado."""
        return self.winrate * 0.6 + (self.avg_score / 100.0) * 0.4

    @property
    def comfort_index(self) -> float:
        """Score ajustado por consistencia: penaliza variabilidad alta."""
        cv = self.score_std / max(self.avg_score, 1.0)
        return (self.avg_score / 100.0) * (1.0 - min(cv, 0.5))


@dataclass
class ChampionClassification:
    """Cuatro arquetipos derivados de los datos del jugador."""
    main:    Optional[ChampionStats]        = None  # mayor volumen de partidas
    comfort: Optional[ChampionStats]        = None  # score alto y consistente
    carry:   Optional[ChampionStats]        = None  # mejor WR + score
    trap:    list[ChampionStats]            = field(default_factory=list)


@dataclass
class PoolInsight:
    """Observación accionable derivada del análisis del pool."""
    level: str   # "warning" | "info" | "positive"
    text:  str


# ─── Sprint 6: estructuras preparadas (vacías hasta Sprint 6) ────────────────

@dataclass
class MatchupRecord:
    """
    Registro de un matchup específico (campeón vs campeón enemigo).
    Vacío hasta Sprint 6 — Matchup Intelligence.
    """
    my_champion:    str
    enemy_champion: str
    games:          int           = 0
    wins:           int           = 0
    avg_score:      float         = 0.0
    # Sprint 6 añadirá: early_gold_diff, cs_diff_at_10, etc.


@dataclass
class DraftHint:
    """
    Sugerencia de pick/ban para el draft.
    Vacío hasta Sprint 6 — Draft Assistant.
    """
    priority:  str    # "PRIORITIZE" | "SITUATIONAL" | "AVOID"
    champion:  str
    reason:    str
    confidence: float = 0.0   # 0.0–1.0, basado en N de partidas


# ─── Resultado principal ──────────────────────────────────────────────────────

@dataclass
class ChampionPoolAnalysis:
    """Análisis completo del champion pool para un rol."""
    role:            str
    grade:           str                      # A / B / C / D / F
    grade_score:     float                    # 0–100
    pool_depth:      int                      # campeones con ≥ MIN_GAMES_QUALIFY
    dependency_pct:  float                    # % partidas en el campeón más jugado
    avg_pool_score:  float                    # avg overall_score del pool calificado
    avg_pool_wr:     float                    # avg WR del pool calificado
    champions:       list[ChampionStats]      # todos con ≥ MIN_GAMES_TABLE
    classification:  ChampionClassification
    insights:        list[PoolInsight]
    total_games:     int
    # ── Sprint 6 hooks ────────────────────────────────────────────────────────
    matchup_records: dict[str, list[MatchupRecord]] = field(default_factory=dict)
    draft_hints:     list[DraftHint]                = field(default_factory=list)


# ─── API pública ──────────────────────────────────────────────────────────────

def analyze_champion_pool(
    matches: list[dict],
    role: str,
    match_scores: list | None = None,
) -> ChampionPoolAnalysis:
    """
    Analiza el champion pool del jugador a partir de partidas reales.

    Args:
        matches:       partidas filtradas por rol (db.get_matches)
        role:          "ADC" | "TOP" | "MID"
        match_scores:  lista de MatchScore de scorer_v2.analyze_player().
                       Si None, se calcula internamente.

    Returns:
        ChampionPoolAnalysis con clasificación, grade y insights.
    """
    if not matches:
        return _empty_analysis(role)

    if match_scores is None:
        sr = scorer_v2.analyze_player(matches, role)
        match_scores = sr.match_scores

    # 1. Agrupar por campeón
    champ_buckets = _bucket_by_champion(matches, match_scores)

    # 2. Calcular estadísticas por campeón
    all_stats = [_compute_stats(champ, data) for champ, data in champ_buckets.items()]

    # 3. Separar campeones calificados (para clasificación y grade)
    qualified = [s for s in all_stats if s.games >= MIN_GAMES_QUALIFY]

    # 4. Tabla visible en UI (umbral más bajo)
    table = sorted(
        [s for s in all_stats if s.games >= MIN_GAMES_TABLE],
        key=lambda s: (-s.games, -s.avg_score),
    )

    # 5. Clasificación
    classification = _classify(qualified)

    # 6. Pool grade
    grade_score, grade = _pool_grade(qualified, all_stats, len(matches))

    # 7. Métricas del pool calificado
    avg_pool_score = statistics.mean(s.avg_score for s in qualified) if qualified else 0.0
    avg_pool_wr    = statistics.mean(s.winrate   for s in qualified) if qualified else 0.0
    top_champ_pct  = max(s.games for s in all_stats) / len(matches) if all_stats else 0.0

    # 8. Insights accionables
    insights = _generate_insights(classification, qualified, len(matches), top_champ_pct)

    return ChampionPoolAnalysis(
        role           = role,
        grade          = grade,
        grade_score    = grade_score,
        pool_depth     = len(qualified),
        dependency_pct = top_champ_pct,
        avg_pool_score = avg_pool_score,
        avg_pool_wr    = avg_pool_wr,
        champions      = table,
        classification = classification,
        insights       = insights,
        total_games    = len(matches),
    )


# ─── Funciones internas ───────────────────────────────────────────────────────

def _bucket_by_champion(
    matches: list[dict],
    match_scores: list,
) -> dict[str, dict]:
    """Agrupa partidas y scores por nombre de campeón."""
    buckets: dict[str, dict] = {}
    for m, ms in zip(matches, match_scores):
        champ = m.get("champion") or "Unknown"
        if champ not in buckets:
            buckets[champ] = {
                "wins": 0, "deaths": [], "kills": [], "assists": [],
                "cs_pm": [], "kp": [], "scores": [], "results": [], "dates": [],
            }
        b = buckets[champ]
        b["results"].append(m.get("result", "LOSS"))
        b["wins"] += 1 if m.get("result") == "WIN" else 0
        b["deaths"].append(m.get("deaths") or 0)
        b["kills"].append(m.get("kills") or 0)
        b["assists"].append(m.get("assists") or 0)
        dur_min = max((m.get("duration_sec") or 60) / 60.0, 1.0)
        cs = m.get("cs")
        b["cs_pm"].append(cs / dur_min if cs is not None else 0.0)
        kp = m.get("kill_participation")
        if kp is not None:
            b["kp"].append(float(kp))
        if ms.overall_score is not None:
            b["scores"].append(ms.overall_score)
        if ms.played_at:
            b["dates"].append(ms.played_at)
    return buckets


def _compute_stats(champion: str, b: dict) -> ChampionStats:
    """Calcula ChampionStats desde un bucket de datos crudos."""
    n    = len(b["results"])
    wins = b["wins"]

    scores = b["scores"]
    avg_sc = statistics.mean(scores) if scores else 0.0
    std_sc = statistics.stdev(scores) if len(scores) >= 2 else 0.0

    deaths  = b["deaths"]
    kills   = b["kills"]
    assists = b["assists"]
    avg_deaths = statistics.mean(deaths) if deaths else 0.0
    avg_kda    = statistics.mean(
        [(k + a) / max(d, 1) for k, a, d in zip(kills, assists, deaths)]
    )
    avg_cs_pm = statistics.mean(b["cs_pm"]) if b["cs_pm"] else 0.0
    avg_kp    = statistics.mean(b["kp"])    if b["kp"]    else 0.0

    # Tendencia OLS sobre scores (orden cronológico: el slice está newest-first,
    # así que invertimos para que el índice crezca con el tiempo)
    score_trend = _ols_slope(list(reversed(scores))) if len(scores) >= 3 else 0.0

    # Winrate de las últimas 3 partidas (las más recientes están al inicio de la lista)
    recent_results = b["results"][:3]
    recent_wr      = sum(1 for r in recent_results if r == "WIN") / len(recent_results)

    last_played = max(b["dates"])[:10] if b["dates"] else ""

    return ChampionStats(
        champion    = champion,
        games       = n,
        wins        = wins,
        losses      = n - wins,
        winrate     = wins / n,
        avg_score   = avg_sc,
        score_std   = std_sc,
        avg_deaths  = avg_deaths,
        avg_kda     = avg_kda,
        avg_cs_pm   = avg_cs_pm,
        avg_kp      = avg_kp,
        score_trend = score_trend,
        recent_wr   = recent_wr,
        last_played = last_played,
    )


def _ols_slope(values: list[float]) -> float:
    """Pendiente de regresión lineal OLS (mismo método que scorer_v2)."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = statistics.mean(values)
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den else 0.0


def _classify(qualified: list[ChampionStats]) -> ChampionClassification:
    """
    Asigna los 4 arquetipos a los campeones calificados.

    Prioridad de asignación (para evitar overlap):
      1. TRAP  → WR ≤ TRAP_WR_MAX AND avg_score ≤ TRAP_SCORE_MAX
      2. MAIN  → mayor volumen (puede solaparse con TRAP — ese es el insight clave)
      3. CARRY → mejor carry_index entre no-trap y no-main
      4. COMFORT → mejor comfort_index entre los restantes
    """
    if not qualified:
        return ChampionClassification()

    # TRAP: WR ≤ 40% con suficiente muestra es señal de LP perdido,
    # independientemente del score mecánico.
    trap_names = {s.champion for s in qualified if s.winrate <= TRAP_WR_MAX}
    traps = [s for s in qualified if s.champion in trap_names]

    main = max(qualified, key=lambda s: (s.games, s.avg_score))
    used: set[str] = {main.champion}

    non_trap_eligible = [s for s in qualified if s.champion not in trap_names and s.champion not in used]
    carry = max(non_trap_eligible, key=lambda s: s.carry_index) if non_trap_eligible else None
    if carry:
        used.add(carry.champion)

    comfort_eligible = [
        s for s in qualified
        if s.champion not in used and s.champion not in trap_names
    ]
    comfort = max(comfort_eligible, key=lambda s: s.comfort_index) if comfort_eligible else None

    return ChampionClassification(
        main    = main,
        comfort = comfort,
        carry   = carry,
        trap    = traps,
    )


def _pool_grade(
    qualified: list[ChampionStats],
    all_stats: list[ChampionStats],
    total_games: int,
) -> tuple[float, str]:
    """
    Pool Health Score: 4 factores de 0–25 pts cada uno.

    1. Profundidad   — N de campeones con ≥ MIN_GAMES_QUALIFY (1→8, 2→17, 3→25)
    2. Rendimiento   — avg WR del pool calificado (escalado 0–25)
    3. Consistencia  — avg consistency_score del pool calificado (escalado 0–25)
    4. Distribución  — independencia del campeón más jugado (menor dep. → más pts)

    Letras: A≥80, B≥65, C≥50, D≥35, F<35
    """
    # Factor 1: Profundidad
    depth       = len(qualified)
    depth_score = min(25.0, depth * (25.0 / 3.0))   # 3 champs → 25 pts exactos

    # Factor 2: Rendimiento
    avg_wr      = statistics.mean(s.winrate for s in qualified) if qualified else 0.0
    perf_score  = avg_wr * 25.0

    # Factor 3: Consistencia
    avg_cs      = statistics.mean(s.consistency_score for s in qualified) if qualified else 0.0
    cons_score  = avg_cs / 100.0 * 25.0

    # Factor 4: Distribución (inverso de dependencia)
    if all_stats and total_games > 0:
        top_pct    = max(s.games for s in all_stats) / total_games
        # top_pct = DEPENDENCY_HIGH → 0 pts; top_pct = 0 → 25 pts (lineal)
        dist_score = max(0.0, 25.0 * (1.0 - top_pct / DEPENDENCY_HIGH))
    else:
        dist_score = 0.0

    total = depth_score + perf_score + cons_score + dist_score

    if   total >= 80: grade = "A"
    elif total >= 65: grade = "B"
    elif total >= 50: grade = "C"
    elif total >= 35: grade = "D"
    else:             grade = "F"

    return round(total, 1), grade


def _generate_insights(
    clf:         ChampionClassification,
    qualified:   list[ChampionStats],
    total_games: int,
    top_pct:     float,
) -> list[PoolInsight]:
    """Genera observaciones accionables ordenadas por prioridad."""
    insights: list[PoolInsight] = []

    # 1. Main pick es TRAP → mayor impacto
    trap_names = {s.champion for s in clf.trap}
    if clf.main and clf.main.champion in trap_names:
        insights.append(PoolInsight(
            level="warning",
            text=(
                f"{clf.main.champion} es tu pick más jugado "
                f"({clf.main.games} partidas, {clf.main.winrate:.0%} WR) "
                f"pero los resultados indican que te está costando LP. "
                f"Considera priorizarlo solo en matchups favorables."
            ),
        ))

    # 2. Dependencia del main
    if top_pct >= DEPENDENCY_HIGH:
        champ = clf.main.champion if clf.main else "tu pick principal"
        insights.append(PoolInsight(
            level="warning",
            text=(
                f"El {top_pct:.0%} de tus partidas son con {champ}. "
                f"Un ban te deja sin tu herramienta principal."
            ),
        ))
    elif top_pct >= DEPENDENCY_MED:
        champ = clf.main.champion if clf.main else "un solo campeón"
        insights.append(PoolInsight(
            level="info",
            text=(
                f"{champ} representa el {top_pct:.0%} de tu pool. "
                f"Un segundo pick sólido reduciría tu vulnerabilidad."
            ),
        ))

    # 3. Carry disponible → acción positiva
    if clf.carry and clf.carry.winrate >= CARRY_WR_MIN:
        insights.append(PoolInsight(
            level="positive",
            text=(
                f"{clf.carry.champion} te da un {clf.carry.winrate:.0%} WR "
                f"(score promedio {clf.carry.avg_score:.0f}) en {clf.carry.games} partidas. "
                f"Es tu pick más rentable — priorízalo en draft."
            ),
        ))

    # 4. Caída de rendimiento fuera del mejor pick
    if clf.carry and qualified:
        rest = [s for s in qualified if s.champion != clf.carry.champion]
        if rest:
            avg_rest  = statistics.mean(s.avg_score for s in rest)
            delta_sc  = clf.carry.avg_score - avg_rest
            delta_wr  = clf.carry.winrate - statistics.mean(s.winrate for s in rest)
            if delta_sc >= 10:
                insights.append(PoolInsight(
                    level="info",
                    text=(
                        f"Fuera de {clf.carry.champion} tu score cae "
                        f"{delta_sc:.0f} pts y tu WR baja "
                        f"{delta_wr:.0%} en promedio."
                    ),
                ))

    # 5. Pool pequeño
    if len(qualified) == 0:
        insights.append(PoolInsight(
            level="warning",
            text="Ningún campeón tiene suficiente muestra para análisis fiable. "
                 "Necesitas ≥3 partidas con el mismo campeón.",
        ))
    elif len(qualified) == 1:
        insights.append(PoolInsight(
            level="warning",
            text=f"Solo {qualified[0].champion} tiene suficiente muestra. "
                 f"Un pool de un solo campeón es muy frágil al ban.",
        ))
    elif len(qualified) == 2:
        insights.append(PoolInsight(
            level="info",
            text="Tienes 2 picks analizados. Un tercer campeón sólido completaría tu pool.",
        ))

    # 6. Traps secundarios (que no son el main)
    main_name = clf.main.champion if clf.main else None
    for trap in clf.trap:
        if trap.champion == main_name:
            continue   # ya cubierto en insight 1
        insights.append(PoolInsight(
            level="warning",
            text=(
                f"{trap.champion}: {trap.winrate:.0%} WR, "
                f"score {trap.avg_score:.0f} en {trap.games} partidas — "
                f"considera alejarte de este pick."
            ),
        ))

    return insights


def _empty_analysis(role: str) -> ChampionPoolAnalysis:
    return ChampionPoolAnalysis(
        role=role, grade="F", grade_score=0.0,
        pool_depth=0, dependency_pct=0.0,
        avg_pool_score=0.0, avg_pool_wr=0.0,
        champions=[], classification=ChampionClassification(),
        insights=[PoolInsight(
            "info",
            "No hay partidas suficientes para analizar tu champion pool.",
        )],
        total_games=0,
    )
