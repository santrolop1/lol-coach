"""
backend/services/champion_coach.py — Motor de coaching específico por campeón.

Analiza el rendimiento de un campeón concreto dentro del historial del jugador.
Calcula patrones, fortalezas, debilidades, un objetivo específico y clasifica
el campeón como Main / Growth Pick / Risk Pick.

Sin benchmarks externos. Todo derivado del historial real del jugador.
"""

from __future__ import annotations

import statistics
from collections import defaultdict

from backend.config.constants import MIN_CHAMPION_GAMES, ROBUST_CHAMPION_GAMES
from .champion_models import ChampionAnalysis, ChampionCoachResult
from .champion_patterns import detect_patterns
from .champion_goals import generate_goal

# ── Clasificación de campeón ──────────────────────────────────────────────────

# WR mínima para Growth Pick
_GROWTH_WR_MIN   = 0.55
# WR máxima para Risk Pick
_RISK_WR_MAX     = 0.45


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _mean(vals: list) -> float:
    filtered = [v for v in vals if v is not None]
    return statistics.mean(filtered) if filtered else 0.0


def _cs_pm(m: dict) -> float | None:
    cs  = _safe_float(m.get("cs"))
    dur = _safe_float(m.get("duration_sec"))
    if cs is not None and dur and dur > 60:
        return cs / (dur / 60.0)
    return None


def _dmg_pm(m: dict) -> float | None:
    dmg = _safe_float(m.get("damage"))
    dur = _safe_float(m.get("duration_sec"))
    if dmg is not None and dur and dur > 60:
        return dmg / (dur / 60.0)
    return None


def _trend_label(scores: list[float]) -> str:
    if len(scores) < 4:
        return "insufficient"
    mid    = len(scores) // 2
    recent = statistics.mean(scores[:mid])
    older  = statistics.mean(scores[mid:])
    diff   = recent - older
    if diff > 3:
        return "improving"
    if diff < -3:
        return "declining"
    return "stable"


def _confidence(games: int) -> str:
    if games < MIN_CHAMPION_GAMES:
        return "low"
    if games < ROBUST_CHAMPION_GAMES:
        return "medium"
    return "high"


# ── Construcción del análisis ─────────────────────────────────────────────────

def _build_analysis(champ_matches: list[dict], champion: str, role: str) -> ChampionAnalysis:
    """Construye ChampionAnalysis con splits win/loss desde partidas brutas."""
    wins_m  = [m for m in champ_matches if m.get("result") == "WIN"]
    losses_m = [m for m in champ_matches if m.get("result") == "LOSS"]

    n    = len(champ_matches)
    wins = len(wins_m)

    # Scores opcionales
    score_vals = [_safe_float(m.get("overall_score")) for m in champ_matches]
    score_vals = [v for v in score_vals if v is not None]
    avg_score  = statistics.mean(score_vals) if score_vals else None
    score_std  = statistics.stdev(score_vals) if len(score_vals) >= 2 else 0.0

    # Métricas globales
    deaths_all  = [_safe_float(m.get("deaths")) for m in champ_matches]
    cs_all      = [_cs_pm(m)  for m in champ_matches]
    dmg_all     = [_dmg_pm(m) for m in champ_matches]
    kp_all      = [_safe_float(m.get("kill_participation")) for m in champ_matches]

    avg_deaths     = _mean(deaths_all)
    avg_cs_min     = _mean(cs_all)
    avg_damage_min = _mean(dmg_all)
    avg_kp         = _mean(kp_all)

    # Splits
    def _split_mean(matches, fn):
        vals = [fn(m) for m in matches]
        return _mean(vals)

    win_avg_deaths    = _mean([_safe_float(m.get("deaths"))          for m in wins_m])
    loss_avg_deaths   = _mean([_safe_float(m.get("deaths"))          for m in losses_m])
    win_avg_cs_min    = _split_mean(wins_m,   _cs_pm)
    loss_avg_cs_min   = _split_mean(losses_m, _cs_pm)
    win_avg_damage_min  = _split_mean(wins_m,   _dmg_pm)
    loss_avg_damage_min = _split_mean(losses_m, _dmg_pm)
    win_avg_kp        = _mean([_safe_float(m.get("kill_participation")) for m in wins_m])
    loss_avg_kp       = _mean([_safe_float(m.get("kill_participation")) for m in losses_m])

    return ChampionAnalysis(
        champion_name      = champion,
        role               = role,
        games              = n,
        wins               = wins,
        losses             = n - wins,
        winrate            = wins / n if n else 0.0,
        avg_score          = avg_score,
        avg_deaths         = avg_deaths,
        avg_cs_min         = avg_cs_min,
        avg_damage_min     = avg_damage_min,
        avg_kp             = avg_kp,
        trend              = _trend_label(score_vals),
        confidence         = _confidence(n),
        score_std          = score_std,
        win_avg_deaths     = win_avg_deaths,
        loss_avg_deaths    = loss_avg_deaths,
        win_avg_cs_min     = win_avg_cs_min,
        loss_avg_cs_min    = loss_avg_cs_min,
        win_avg_damage_min = win_avg_damage_min,
        loss_avg_damage_min = loss_avg_damage_min,
        win_avg_kp         = win_avg_kp,
        loss_avg_kp        = loss_avg_kp,
    )


# ── Strengths y weaknesses ────────────────────────────────────────────────────

def _build_strengths(
    analysis: ChampionAnalysis,
    overall_avg_deaths: float,
    overall_avg_cs_min: float,
    overall_avg_damage_min: float,
    overall_avg_kp: float,
) -> list[str]:
    """Genera fortalezas comparando el campeón con la media del rol."""
    strengths: list[str] = []

    # Muertes por debajo de media del rol
    if overall_avg_deaths > 0 and analysis.avg_deaths < overall_avg_deaths * 0.90:
        diff_pct = (overall_avg_deaths - analysis.avg_deaths) / overall_avg_deaths * 100
        strengths.append(
            f"Muertes con {analysis.champion_name} ({analysis.avg_deaths:.1f}) "
            f"están {diff_pct:.0f}% por debajo de tu media {analysis.role} "
            f"({overall_avg_deaths:.1f})."
        )

    # CS/min superior a media del rol
    if overall_avg_cs_min > 0 and analysis.avg_cs_min > overall_avg_cs_min * 1.10:
        diff_pct = (analysis.avg_cs_min - overall_avg_cs_min) / overall_avg_cs_min * 100
        strengths.append(
            f"Tu CS/min con {analysis.champion_name} ({analysis.avg_cs_min:.1f}) "
            f"es {diff_pct:.0f}% superior a tu media {analysis.role} "
            f"({overall_avg_cs_min:.1f})."
        )

    # Daño superior a media del rol
    if overall_avg_damage_min > 0 and analysis.avg_damage_min > overall_avg_damage_min * 1.10:
        diff_pct = (analysis.avg_damage_min - overall_avg_damage_min) / overall_avg_damage_min * 100
        strengths.append(
            f"Tu daño/min con {analysis.champion_name} ({analysis.avg_damage_min:.0f}) "
            f"es {diff_pct:.0f}% superior a tu media {analysis.role}."
        )

    # KP superior a media del rol
    if overall_avg_kp > 0 and analysis.avg_kp > overall_avg_kp * 1.10:
        diff_pct = (analysis.avg_kp - overall_avg_kp) / overall_avg_kp * 100
        strengths.append(
            f"Tu participación en peleas con {analysis.champion_name} "
            f"({analysis.avg_kp:.0%}) es {diff_pct:.0f}% superior a tu media {analysis.role}."
        )

    # Consistencia
    if analysis.is_consistent and analysis.games >= 4:
        strengths.append(
            f"Rendimiento consistente con {analysis.champion_name} "
            f"(variabilidad σ = {analysis.score_std:.1f})."
        )

    # WR positiva como fortaleza
    if analysis.winrate >= 0.60 and analysis.games >= MIN_CHAMPION_GAMES:
        strengths.append(
            f"WR positiva: {analysis.winrate:.0%} en "
            f"{analysis.games} partidas con {analysis.champion_name}."
        )

    return strengths[:4]


def _build_weaknesses(
    analysis: ChampionAnalysis,
    patterns: list,
    overall_avg_deaths: float,
    overall_avg_cs_min: float,
) -> list[str]:
    """Genera debilidades a partir de patrones detectados y comparación con media."""
    weaknesses: list[str] = []

    # Patrones como debilidades primarias
    for p in patterns[:3]:
        weaknesses.append(f"{p.description}")

    # Muertes por encima de media del rol (si no ya incluido por patrón)
    death_already = any(p.pattern_type == "deaths" for p in patterns)
    if not death_already and overall_avg_deaths > 0:
        if analysis.avg_deaths > overall_avg_deaths * 1.15:
            diff_pct = (analysis.avg_deaths - overall_avg_deaths) / overall_avg_deaths * 100
            weaknesses.append(
                f"Muertes elevadas con {analysis.champion_name} "
                f"({analysis.avg_deaths:.1f} vs {overall_avg_deaths:.1f} media, "
                f"+{diff_pct:.0f}%)."
            )

    # CS inferior a media del rol (si no ya incluido)
    cs_already = any(p.pattern_type == "farm" for p in patterns)
    if not cs_already and overall_avg_cs_min > 0:
        if analysis.avg_cs_min < overall_avg_cs_min * 0.88:
            diff_pct = (overall_avg_cs_min - analysis.avg_cs_min) / overall_avg_cs_min * 100
            weaknesses.append(
                f"Farm inferior a tu media {analysis.role} "
                f"con {analysis.champion_name} "
                f"({analysis.avg_cs_min:.1f} vs {overall_avg_cs_min:.1f} CS/min, "
                f"-{diff_pct:.0f}%)."
            )

    return weaknesses[:4]


# ── Clasificación de prioridad ────────────────────────────────────────────────

def classify_priority(
    analysis: ChampionAnalysis,
    all_analyses: list[ChampionAnalysis],
) -> str:
    """
    Clasifica el campeón desde la perspectiva del coach:

    insufficient — menos de MIN_CHAMPION_GAMES partidas
    risk         — WR baja con muestra suficiente (pick problemático)
    growth       — WR prometedora pero poca muestra (potencial)
    main         — pick principal (mayor volumen con WR aceptable)

    El orden de evaluación importa: risk tiene prioridad sobre main.
    """
    if analysis.games < MIN_CHAMPION_GAMES:
        return "insufficient"

    # Risk: WR baja, independientemente del volumen
    if analysis.winrate < _RISK_WR_MAX:
        return "risk"

    # Growth: WR prometedora pero poca muestra
    if analysis.winrate >= _GROWTH_WR_MIN and analysis.games < ROBUST_CHAMPION_GAMES:
        # Solo es growth si no es el campeón más jugado (ese es main)
        qualified = [a for a in all_analyses if a.games >= MIN_CHAMPION_GAMES]
        most_played = max(qualified, key=lambda a: (a.games, a.winrate)) if qualified else None
        if most_played is not None and analysis is not most_played:
            return "growth"

    return "main"


# ── Motor principal ───────────────────────────────────────────────────────────

def analyze_champion(
    matches: list[dict],
    champion: str,
    role: str,
    all_role_matches: list[dict] | None = None,
    matchup_result=None,       # MatchupResult de Sprint 10 (opcional)
) -> ChampionCoachResult:
    """
    Genera el coaching completo para un campeón específico.

    Parámetros
    ----------
    matches          : partidas ya filtradas por rol (todas, no solo del campeón)
    champion         : nombre del campeón a analizar (debe coincidir con campo "champion")
    role             : "ADC" | "TOP"
    all_role_matches : si se provee, se usa para calcular medias del rol
                       (por defecto = matches)
    matchup_result   : MatchupResult de Sprint 10 para integrar best/worst matchup

    Retorna
    -------
    ChampionCoachResult completo.
    """
    base_matches = all_role_matches if all_role_matches is not None else matches
    champ_matches = [m for m in matches if m.get("champion") == champion]

    # ── Análisis por campeón ──────────────────────────────────────────────────
    if not champ_matches:
        # Análisis vacío
        empty_analysis = ChampionAnalysis(
            champion_name=champion, role=role, games=0, wins=0, losses=0,
            winrate=0.0, avg_score=None, avg_deaths=0.0, avg_cs_min=0.0,
            avg_damage_min=0.0, avg_kp=0.0, trend="insufficient",
            confidence="low",
        )
        return ChampionCoachResult(
            analysis=empty_analysis, patterns=[], goal=None,
            strengths=[], weaknesses=[], priority_class="insufficient",
            primary_problem=None,
        )

    analysis = _build_analysis(champ_matches, champion, role)

    # ── Promedios del rol como referencia ─────────────────────────────────────
    all_deaths  = [_safe_float(m.get("deaths"))           for m in base_matches]
    all_cs      = [_cs_pm(m)                               for m in base_matches]
    all_dmg     = [_dmg_pm(m)                              for m in base_matches]
    all_kp      = [_safe_float(m.get("kill_participation")) for m in base_matches]

    overall_avg_deaths  = _mean(all_deaths)
    overall_avg_cs      = _mean(all_cs)
    overall_avg_dmg     = _mean(all_dmg)
    overall_avg_kp      = _mean(all_kp)

    # ── Análisis de todos los campeones (para clasificación) ──────────────────
    champs_played = list({m.get("champion") for m in matches if m.get("champion")})
    all_analyses  = [
        _build_analysis([m for m in matches if m.get("champion") == c], c, role)
        for c in champs_played
    ]

    # ── Patrones ──────────────────────────────────────────────────────────────
    patterns = detect_patterns(analysis)

    # ── Objetivo ──────────────────────────────────────────────────────────────
    goal = generate_goal(analysis)

    # ── Strengths y Weaknesses ─────────────────────────────────────────────────
    strengths  = _build_strengths(analysis, overall_avg_deaths, overall_avg_cs, overall_avg_dmg, overall_avg_kp)
    weaknesses = _build_weaknesses(analysis, patterns, overall_avg_deaths, overall_avg_cs)

    # ── Clasificación ─────────────────────────────────────────────────────────
    priority_class = classify_priority(analysis, all_analyses)

    # ── Problema principal ────────────────────────────────────────────────────
    primary_problem = patterns[0].title if patterns else None

    # ── Integración Matchup Intelligence ─────────────────────────────────────
    matchup_best  = None
    matchup_worst = None
    if matchup_result is not None:
        # Filtrar matchups donde el jugador usó este campeón específico
        # Los registros de Sprint 10 son "ALL" vs enemy (no por mi campeón)
        # Solo los tomamos como orientación general del rol
        if matchup_result.best:
            matchup_best  = matchup_result.best[0].enemy
        if matchup_result.worst:
            matchup_worst = matchup_result.worst[0].enemy

    return ChampionCoachResult(
        analysis        = analysis,
        patterns        = patterns,
        goal            = goal,
        strengths       = strengths,
        weaknesses      = weaknesses,
        priority_class  = priority_class,
        primary_problem = primary_problem,
        matchup_best    = matchup_best,
        matchup_worst   = matchup_worst,
    )


def get_available_champions(matches: list[dict]) -> list[str]:
    """
    Devuelve los campeones disponibles para Champion Coach,
    ordenados por número de partidas (mayor primero).
    """
    counts: dict[str, int] = defaultdict(int)
    for m in matches:
        champ = m.get("champion")
        if champ:
            counts[champ] += 1
    return sorted(counts, key=lambda c: -counts[c])
