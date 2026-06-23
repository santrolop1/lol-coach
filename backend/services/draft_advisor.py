"""
backend/services/draft_advisor.py — Motor de recomendaciones de draft.

Fuente de datos: exclusivamente historial personal (ChampionPoolAnalysis)
+ sesión en vivo de Champ Select (ChampSelectSession).

NO usa meta externos, NO usa estadísticas globales, NO usa hardcodes.
Toda recomendación refleja el rendimiento real del jugador.

Fórmulas
────────
Pick Value (0–100): ranking de recomendación
    = wr * 35 + (score/100) * 30 + (consistency/100) * 20 + min(1, games/10) * 15

Draft Score (0–100): confianza en el pick actual
    familiarity_pts (0–30) = min(30, games/10 * 30)
    performance_pts (0–30) = avg_score/100 * 30
    consistency_pts (0–25) = consistency_score/100 * 25
    winrate_pts     (0–15) = winrate * 15

Confidence (0–100): confianza estadística
    = min(100, games / 10 * 100)

Grade: A≥75, B≥55, C≥35, D≥15, F<15
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lcu.models import ChampSelectSession
from backend.services.champion_analyzer import ChampionPoolAnalysis, ChampionStats

# ── Umbrales ──────────────────────────────────────────────────────────────────

_CONFIDENCE_FULL_GAMES = 10   # partidas para confianza 100 %
_SAMPLE_WARNING_MIN    = 3    # menos de esto → aviso muestra pequeña
_DEPENDENCY_WARN       = 0.50 # > 50 % de partidas en un solo campeón → aviso


# ── Dataclasses de resultado ──────────────────────────────────────────────────

@dataclass
class DraftRecommendation:
    champion:       str
    rank:           int      # 1 | 2 | 3
    pick_value:     float    # 0–100
    confidence:     float    # 0–100
    winrate:        float    # 0.0–1.0
    avg_score:      float
    games:          int
    classification: str      # "CARRY" | "COMFORT" | "MAIN" | "SOLID" | "TRAP"
    reason:         str      # texto derivado de datos


@dataclass
class DraftWarning:
    level:    str            # "critical" | "warning" | "info"
    champion: str | None     # None = aviso general del pool
    text:     str


@dataclass
class DraftScore:
    champion:        str
    total:           float   # 0–100
    familiarity_pts: float   # 0–30
    performance_pts: float   # 0–30
    consistency_pts: float   # 0–25
    winrate_pts:     float   # 0–15
    has_data:        bool
    grade:           str     # "A" | "B" | "C" | "D" | "F"
    grade_label:     str     # "Excelente" | "Bueno" | …


@dataclass
class DraftAdvice:
    role:               str
    recommendations:    list[DraftRecommendation]   # top 3 no-trap, ordenados
    avoid:              list[DraftRecommendation]   # traps disponibles
    warnings:           list[DraftWarning]
    current_pick_score: DraftScore | None           # None si no hay pick aún
    pool_has_data:      bool


# ── API pública ───────────────────────────────────────────────────────────────

def analyze_draft(
    session: ChampSelectSession,
    cpa: ChampionPoolAnalysis,
) -> DraftAdvice:
    """
    Combina la sesión en vivo con el historial personal del jugador y
    devuelve recomendaciones, advertencias y el score del pick actual.

    Parámetros
    ----------
    session : ChampSelectSession  — datos en vivo del LCU (Sprint 7)
    cpa     : ChampionPoolAnalysis — análisis del pool histórico (Sprint 5)
    """
    all_bans   = set(session.bans.my_team_bans + session.bans.their_team_bans)
    trap_names = {t.champion for t in cpa.classification.trap}
    champ_lookup: dict[str, ChampionStats] = {cs.champion: cs for cs in cpa.champions}

    # ── Draft Score para pick actual ──────────────────────────────────────────
    current_name = session.my_champion
    current_score: DraftScore | None = None
    if current_name:
        current_score = _draft_score(current_name, champ_lookup.get(current_name))

    # ── Separar recomendaciones vs evitar ─────────────────────────────────────
    recs:  list[DraftRecommendation] = []
    avoid: list[DraftRecommendation] = []

    for cs in cpa.champions:
        if cs.champion in all_bans:
            continue   # baneado: no relevante para el draft
        pv  = _pick_value(cs)
        clf = _classification_label(cs.champion, cpa)
        if cs.champion in trap_names:
            avoid.append(DraftRecommendation(
                champion=cs.champion, rank=0, pick_value=pv,
                confidence=_confidence(cs.games),
                winrate=cs.winrate, avg_score=cs.avg_score, games=cs.games,
                classification="TRAP",
                reason=_trap_reason(cs),
            ))
        else:
            recs.append(DraftRecommendation(
                champion=cs.champion, rank=0, pick_value=pv,
                confidence=_confidence(cs.games),
                winrate=cs.winrate, avg_score=cs.avg_score, games=cs.games,
                classification=clf,
                reason=_rec_reason(cs, clf),
            ))

    recs.sort(key=lambda r: r.pick_value, reverse=True)
    for i, r in enumerate(recs[:3]):
        r.rank = i + 1

    avoid.sort(key=lambda r: r.winrate)   # peor WR primero

    # ── Advertencias ──────────────────────────────────────────────────────────
    warnings = _generate_warnings(
        current_name, cpa, trap_names, all_bans, champ_lookup
    )

    return DraftAdvice(
        role            = session.my_role,
        recommendations = recs[:3],
        avoid           = avoid,
        warnings        = warnings,
        current_pick_score = current_score,
        pool_has_data   = cpa.total_games > 0,
    )


# ── Fórmulas ──────────────────────────────────────────────────────────────────

def _pick_value(cs: ChampionStats) -> float:
    """
    Score de valor de pick (0–100).
    Pesos: WR 35 % · rendimiento 30 % · consistencia 20 % · volumen 15 %.
    """
    return (
        cs.winrate                          * 35.0
        + (cs.avg_score / 100.0)            * 30.0
        + (cs.consistency_score / 100.0)    * 20.0
        + min(1.0, cs.games / _CONFIDENCE_FULL_GAMES) * 15.0
    )


def _confidence(games: int) -> float:
    """Confianza estadística (0–100). 10 partidas = confianza máxima."""
    return min(100.0, games / _CONFIDENCE_FULL_GAMES * 100.0)


def _draft_score(champion: str, cs: ChampionStats | None) -> DraftScore:
    """
    Calcula el Draft Score del pick actual (0–100) desglosado en 4 factores.
    Si no hay historial, devuelve has_data=False con total=0.
    """
    if cs is None:
        return DraftScore(
            champion=champion, total=0.0,
            familiarity_pts=0.0, performance_pts=0.0,
            consistency_pts=0.0, winrate_pts=0.0,
            has_data=False, grade="F", grade_label="Sin historial",
        )
    fam  = min(30.0, cs.games / _CONFIDENCE_FULL_GAMES * 30.0)
    perf = cs.avg_score / 100.0 * 30.0
    cons = cs.consistency_score / 100.0 * 25.0
    wr   = cs.winrate * 15.0
    total = fam + perf + cons + wr
    grade, label = _grade(total)
    return DraftScore(
        champion=champion, total=total,
        familiarity_pts=fam, performance_pts=perf,
        consistency_pts=cons, winrate_pts=wr,
        has_data=True, grade=grade, grade_label=label,
    )


def _grade(score: float) -> tuple[str, str]:
    if score >= 75: return "A", "Excelente"
    if score >= 55: return "B", "Bueno"
    if score >= 35: return "C", "Aceptable"
    if score >= 15: return "D", "Riesgo"
    return "F", "Sin datos"


# ── Clasificación y textos ────────────────────────────────────────────────────

def _classification_label(champion: str, cpa: ChampionPoolAnalysis) -> str:
    clf = cpa.classification
    if clf.carry   and clf.carry.champion   == champion: return "CARRY"
    if clf.comfort and clf.comfort.champion == champion: return "COMFORT"
    if clf.main    and clf.main.champion    == champion: return "MAIN"
    return "SOLID"


def _rec_reason(cs: ChampionStats, clf: str) -> str:
    if clf == "CARRY":
        return f"Mejor WR del pool: {cs.winrate:.0%} en {cs.games} partidas"
    if clf == "COMFORT":
        return f"Alta consistencia ({cs.consistency_score:.0f}/100) · {cs.winrate:.0%} WR"
    if clf == "MAIN":
        return f"Tu pick más jugado: {cs.games} partidas · {cs.winrate:.0%} WR"
    return f"{cs.winrate:.0%} WR · Score {cs.avg_score:.0f} · {cs.games} partidas"


def _trap_reason(cs: ChampionStats) -> str:
    return f"{cs.winrate:.0%} WR en {cs.games} partidas — historial negativo"


# ── Generación de advertencias ────────────────────────────────────────────────

def _generate_warnings(
    current_pick: str,
    cpa: ChampionPoolAnalysis,
    trap_names: set[str],
    all_bans: set[str],
    champ_lookup: dict[str, ChampionStats],
) -> list[DraftWarning]:
    warns: list[DraftWarning] = []

    # 1. Pick actual es un trap conocido
    if current_pick and current_pick in trap_names:
        cs = champ_lookup[current_pick]
        warns.append(DraftWarning(
            level="critical", champion=current_pick,
            text=(
                f"{current_pick}: {cs.winrate:.0%} WR en {cs.games} partidas. "
                f"Tu historial indica que este pick te está costando LP."
            ),
        ))

    # 2. Pick actual sin historial
    if current_pick and current_pick not in champ_lookup:
        warns.append(DraftWarning(
            level="warning", champion=current_pick,
            text=f"Sin historial de {current_pick} — no hay datos para evaluar este pick.",
        ))

    # 3. Pick actual con muestra muy pequeña
    if current_pick and current_pick in champ_lookup:
        cs = champ_lookup[current_pick]
        if 0 < cs.games < _SAMPLE_WARNING_MIN:
            warns.append(DraftWarning(
                level="warning", champion=current_pick,
                text=(
                    f"{current_pick}: solo {cs.games} "
                    f"partida{'s' if cs.games > 1 else ''} — "
                    f"muestra insuficiente para predicciones confiables."
                ),
            ))

    # 4. Dependencia excesiva en un solo campeón
    if cpa.dependency_pct >= _DEPENDENCY_WARN:
        main = cpa.classification.main
        name = main.champion if main else "tu pick principal"
        warns.append(DraftWarning(
            level="info", champion=None,
            text=(
                f"Dependencia alta: {name} representa el {cpa.dependency_pct:.0%} "
                f"de tus partidas en este rol."
            ),
        ))

    # 5. Todos los picks disponibles son traps
    non_trap_available = [
        cs for cs in cpa.champions
        if cs.champion not in trap_names and cs.champion not in all_bans
    ]
    if cpa.total_games > 0 and not non_trap_available:
        warns.append(DraftWarning(
            level="critical", champion=None,
            text=(
                "Todos tus picks con historial tienen WR negativo. "
                "Considera expandir tu pool antes del próximo draft."
            ),
        ))

    return warns
