"""
backend/services/post_game_review.py — Motor principal de Post Game Review.

Conecta todos los submódulos y produce PostGameReview completo.
"""

from __future__ import annotations

from .review_models import PostGameReview
from .review_repository import (
    get_champion_averages,
    get_recent_scores,
    get_matchup_winrate,
)
from .review_generator import (
    classify_match,
    build_comparisons,
    build_strengths,
    build_mistakes,
    build_focus,
    detect_repeated_mistakes,
    check_pattern_repeated,
    build_matchup_context,
)


def _safe(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _confidence(games: int) -> str:
    if games < 3:
        return "low"
    if games < 8:
        return "medium"
    return "high"


def generate_review(
    match: dict,
    player_history: list[dict],
    champion_patterns: list | None = None,   # list[ChampionPattern] del Champion Coach
    priorities: list | None = None,          # list[Priority] del Priority Engine
) -> PostGameReview:
    """
    Genera la revisión post-partida para la partida indicada.

    Parámetros
    ----------
    match            : dict de la partida a revisar (mismo formato que la BD)
    player_history   : historial completo del jugador en el rol (más reciente primero)
    champion_patterns: patrones del Champion Coach para el campeón de esta partida
    priorities       : prioridades del Priority Engine para el rol

    Retorna
    -------
    PostGameReview completo.
    """
    champion  = match.get("champion") or "Desconocido"
    result    = match.get("result")   or "LOSS"
    match_id  = match.get("match_id") or ""
    score_now = _safe(match.get("overall_score"))

    # ── Promedios históricos del campeón (excluyendo esta partida) ─────────────
    champ_avgs = get_champion_averages(
        champion      = champion,
        history       = player_history,
        exclude_match_id = match_id,
    )

    # ── Score promedio reciente ────────────────────────────────────────────────
    recent_scores = get_recent_scores(
        champion         = champion,
        history          = player_history,
        n                = 10,
        exclude_match_id = match_id,
    )
    score_avg   = (sum(recent_scores) / len(recent_scores)) if recent_scores else None
    score_delta = (score_now - score_avg) if (score_now is not None and score_avg is not None) else None

    # ── Clasificación de partida ───────────────────────────────────────────────
    rating, rating_color = classify_match(result, score_now, score_avg)

    # ── Comparaciones métricas ─────────────────────────────────────────────────
    comparisons = build_comparisons(match, champ_avgs)

    # ── Fortalezas y errores ───────────────────────────────────────────────────
    strengths = build_strengths(comparisons, match, champ_avgs)
    mistakes  = build_mistakes(comparisons,  match, champ_avgs)

    # ── Foco próxima partida ───────────────────────────────────────────────────
    focus = build_focus(mistakes, comparisons, champ_avgs, priorities)

    # ── Errores repetidos ──────────────────────────────────────────────────────
    repeated_mistakes = detect_repeated_mistakes(
        champion         = champion,
        history          = player_history,
        exclude_match_id = match_id,
    )

    # ── Champion Coach integration ─────────────────────────────────────────────
    champ_problem, pattern_repeated = check_pattern_repeated(
        match            = match,
        champion_patterns = champion_patterns or [],
    )

    # ── Matchup Intelligence integration ──────────────────────────────────────
    enemy = match.get("enemy_champion")
    wr, matchup_games = get_matchup_winrate(enemy or "", player_history) if enemy else (None, 0)
    matchup_ctx = build_matchup_context(enemy, wr, matchup_games, result)

    # ── Confianza ─────────────────────────────────────────────────────────────
    confidence = _confidence(champ_avgs.get("games", 0))

    return PostGameReview(
        match_id          = match_id,
        champion          = champion,
        result            = result,
        score             = score_now,
        rating            = rating,
        rating_color      = rating_color,
        score_avg         = score_avg,
        score_delta       = score_delta,
        strengths         = strengths,
        mistakes          = mistakes,
        focus             = focus,
        comparisons       = comparisons,
        champion_problem  = champ_problem,
        pattern_repeated  = pattern_repeated,
        matchup_context   = matchup_ctx,
        repeated_mistakes = repeated_mistakes,
        confidence        = confidence,
    )
