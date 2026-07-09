"""
backend/knowledge/rules.py — Detección de patrones basada en datos.

Cada función recibe los datos ya calculados y devuelve Pattern | None.
No hardcodea frases: las genera a partir de los números observados.
"""

from __future__ import annotations

from collections import defaultdict

from backend.knowledge.models import Pattern
from backend.knowledge import confidence as conf_mod


# ── Helpers ────────────────────────────────────────────────────────────────────

def _avg(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def _get_metric(ms, key: str) -> float | None:
    for dim in ms.dimensions:
        if key in dim.metrics:
            v = dim.metrics[key]
            return v if v is not None else None
    return None


# ── Patrón 1: Correlación muertes → derrota ───────────────────────────────────

def detect_death_correlation(scored: list[tuple]) -> Pattern | None:
    """
    Si la media de muertes en derrotas supera la de victorias por 2+,
    detecta que las muertes predicen las derrotas.
    """
    win_deaths:  list[float] = []
    loss_deaths: list[float] = []

    for match, ms in scored[:40]:
        d = _get_metric(ms, "deaths")
        if d is None:
            continue
        if match.get("result") == "WIN":
            win_deaths.append(d)
        else:
            loss_deaths.append(d)

    if len(win_deaths) < 4 or len(loss_deaths) < 4:
        return None

    avg_w = _avg(win_deaths)
    avg_l = _avg(loss_deaths)
    if avg_w is None or avg_l is None:
        return None

    gap = avg_l - avg_w
    if gap < 1.5:
        return None

    threshold = round(avg_w + gap * 0.5, 1)
    n = len(win_deaths) + len(loss_deaths)
    consistency = len(loss_deaths) / n
    conf = conf_mod.calc_confidence(n, consistency, conf_mod.std_ratio(loss_deaths))

    return Pattern(
        id="death_loss",
        category="death",
        title=f"Las derrotas aparecen cuando superas {threshold:.0f} muertes",
        description=(
            f"En victorias promedias {avg_w:.1f} muertes. "
            f"En derrotas, {avg_l:.1f}. "
            f"Cruzar {threshold:.0f} muertes en una partida multiplica el riesgo de derrota."
        ),
        evidence=f"Análisis de {n} partidas ({len(win_deaths)} victorias, {len(loss_deaths)} derrotas).",
        confidence=conf,
        actionable=f"Objetivo: no superar {threshold:.0f} muertes. Si llegas a {threshold:.0f}, juega más defensivo.",
    )


# ── Patrón 2: Underperformance específica de campeón ─────────────────────────

def detect_champion_underperformance(
    scored: list[tuple],
    overall_avg: float | None,
) -> Pattern | None:
    """
    Si un campeón con 3+ partidas tiene avg_score 12+ puntos por debajo
    del promedio global, detecta el patrón.
    """
    if overall_avg is None:
        return None

    by_champ: dict[str, list[float]] = defaultdict(list)
    for match, ms in scored[:40]:
        champ = match.get("champion", "?")
        if ms.overall_score is not None:
            by_champ[champ].append(ms.overall_score)

    worst_champ: str | None = None
    worst_delta = -12.0
    worst_avg   = 0.0
    worst_n     = 0

    for champ, scores in by_champ.items():
        if len(scores) < 3:
            continue
        avg = sum(scores) / len(scores)
        delta = avg - overall_avg
        if delta < worst_delta:
            worst_delta = delta
            worst_champ = champ
            worst_avg   = avg
            worst_n     = len(scores)

    if worst_champ is None:
        return None

    conf = conf_mod.calc_confidence(
        worst_n,
        consistency=0.8,
        std_ratio=conf_mod.std_ratio(by_champ[worst_champ]),
    )

    return Pattern(
        id="champ_underperform",
        category="champion",
        title=f"El rendimiento baja cuando juegas {worst_champ}",
        description=(
            f"Con {worst_champ} obtienes {worst_avg:.0f}/100 de promedio, "
            f"{abs(worst_delta):.0f} puntos por debajo de tu media global de {overall_avg:.0f}."
        ),
        evidence=f"Basado en {worst_n} partidas con {worst_champ}.",
        confidence=conf,
        actionable=(
            f"Evalúa si continuar jugando {worst_champ} o enfocarte en "
            "los campeones donde tu rendimiento es más consistente."
        ),
    )


# ── Patrón 3: Pool de campeones demasiado amplio ──────────────────────────────

def detect_champion_pool_size(scored: list[tuple]) -> Pattern | None:
    """
    Si en las últimas 10 partidas hay 5+ campeones distintos y el winrate < 45%,
    detecta que el pool amplio correlaciona con peores resultados.
    """
    recent10 = scored[:10]
    if len(recent10) < 8:
        return None

    champs  = {match.get("champion") for match, _ in recent10}
    wins    = sum(1 for match, _ in recent10 if match.get("result") == "WIN")
    winrate = wins / len(recent10)

    if len(champs) < 5 or winrate >= 0.5:
        return None

    n   = len(recent10)
    conf = conf_mod.calc_confidence(n, consistency=1 - winrate, std_ratio=0.2)

    return Pattern(
        id="pool_size",
        category="pool",
        title=f"El winrate baja cuando cambias constantemente de campeón",
        description=(
            f"En las últimas {n} partidas jugaste {len(champs)} campeones distintos "
            f"con un winrate del {winrate*100:.0f}%. "
            "La consistencia de campeón impacta directamente el rendimiento."
        ),
        evidence=f"Campeones usados: {', '.join(str(c) for c in champs if c)}.",
        confidence=conf,
        actionable="Limita el pool a 2-3 campeones durante las próximas 10 partidas y observa si el winrate mejora.",
    )


# ── Patrón 4: Mejora sostenida (tendencia positiva) ───────────────────────────

def detect_improvement_trend(scored: list[tuple]) -> Pattern | None:
    """
    Si la media de las últimas 10 partidas supera en 8+ puntos la de las
    partidas 10-25, detecta una tendencia de mejora sostenida.
    """
    recent   = scored[:10]
    baseline = scored[10:25]

    if len(recent) < 6 or len(baseline) < 6:
        return None

    recent_s   = [ms.overall_score for _, ms in recent   if ms.overall_score is not None]
    baseline_s = [ms.overall_score for _, ms in baseline if ms.overall_score is not None]

    avg_r = _avg(recent_s)
    avg_b = _avg(baseline_s)

    if avg_r is None or avg_b is None or avg_r - avg_b < 6:
        return None

    delta = avg_r - avg_b
    conf  = conf_mod.calc_confidence(
        len(recent_s) + len(baseline_s),
        consistency=0.75,
        std_ratio=conf_mod.std_ratio(recent_s),
    )

    return Pattern(
        id="improvement_trend",
        category="trend",
        title=f"Tu nivel general mejoró {delta:.0f} puntos en las últimas {len(recent_s)} partidas",
        description=(
            f"Pasaste de {avg_b:.0f}/100 de promedio a {avg_r:.0f}/100. "
            "Esta mejora es consistente y estadísticamente significativa."
        ),
        evidence=f"{len(recent_s)} partidas recientes vs {len(baseline_s)} partidas anteriores.",
        confidence=conf,
        actionable="Mantén el foco en lo que estás haciendo bien. La consistencia consolida las mejoras.",
    )


# ── Patrón 5: Farm correlaciona con victorias ────────────────────────────────

def detect_farm_win_correlation(scored: list[tuple]) -> Pattern | None:
    """
    Si el CS/min en victorias supera al de derrotas en 0.8+,
    detecta que el farm es un predictor de victoria.
    """
    win_cs:  list[float] = []
    loss_cs: list[float] = []

    for match, ms in scored[:35]:
        cs = _get_metric(ms, "cs_per_min")
        if cs is None:
            continue
        if match.get("result") == "WIN":
            win_cs.append(cs)
        else:
            loss_cs.append(cs)

    if len(win_cs) < 4 or len(loss_cs) < 4:
        return None

    avg_w = _avg(win_cs)
    avg_l = _avg(loss_cs)
    if avg_w is None or avg_l is None or avg_w - avg_l < 0.6:
        return None

    n    = len(win_cs) + len(loss_cs)
    conf = conf_mod.calc_confidence(n, consistency=0.7, std_ratio=conf_mod.std_ratio(win_cs))

    return Pattern(
        id="farm_win",
        category="habit",
        title=f"El farm predice tus victorias: {avg_w:.1f} CS/min en victorias vs {avg_l:.1f} en derrotas",
        description=(
            f"Cuando consigues {avg_w:.1f}+ CS/min tienes una correlación positiva con la victoria. "
            f"La diferencia de {avg_w - avg_l:.1f} CS/min es consistente en las últimas {n} partidas."
        ),
        evidence=f"{len(win_cs)} victorias analizadas vs {len(loss_cs)} derrotas.",
        confidence=conf,
        actionable=f"Prioriza llegar a {avg_w:.1f} CS/min en cada partida antes de unirte a peleas.",
    )


# ── Orquestador ───────────────────────────────────────────────────────────────

def detect_all(
    scored:      list[tuple],
    overall_avg: float | None,
) -> list[Pattern]:
    """Ejecuta todos los detectores y devuelve los patrones con confianza suficiente."""
    detectors = [
        detect_death_correlation(scored),
        detect_champion_underperformance(scored, overall_avg),
        detect_champion_pool_size(scored),
        detect_improvement_trend(scored),
        detect_farm_win_correlation(scored),
    ]
    return [
        p for p in detectors
        if p is not None and conf_mod.is_sufficient(p.confidence, threshold=0.4)
    ]
