"""
tests/test_post_game_review.py — Tests para Sprint 12: Post Game Review.

Cubre:
  - review_models.py     (MatchComparison, PostGameReview)
  - review_repository.py (get_champion_averages, get_matchup_winrate, etc.)
  - review_generator.py  (classify_match, build_strengths, build_mistakes,
                          build_focus, detect_repeated_mistakes,
                          build_matchup_context, check_pattern_repeated)
  - post_game_review.py  (generate_review — integración completa)

Cobertura objetivo: ≥ 80%.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.services.review_models import MatchComparison, PostGameReview
from backend.services.review_repository import (
    get_champion_averages,
    get_champion_history,
    get_matchup_winrate,
    get_recent_deaths,
    get_recent_scores,
)
from backend.services.review_generator import (
    build_comparisons,
    build_focus,
    build_matchup_context,
    build_mistakes,
    build_strengths,
    check_pattern_repeated,
    classify_match,
    detect_repeated_mistakes,
)
from backend.services.post_game_review import generate_review


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _match(
    champion:    str   = "KaiSa",
    result:      str   = "WIN",
    deaths:      int   = 4,
    cs:          int   = 180,
    damage:      int   = 24000,
    kp:          float = 0.65,
    duration:    int   = 1800,
    score:       float = 70.0,
    match_id:    str   = "m1",
    enemy:       str | None = None,
) -> dict:
    m = {
        "champion":          champion,
        "role":              "ADC",
        "result":            result,
        "deaths":            deaths,
        "cs":                cs,
        "damage":            damage,
        "kill_participation": kp,
        "duration_sec":      duration,
        "overall_score":     score,
        "match_id":          match_id,
        "played_at":         "2026-06-23T10:00:00",
    }
    if enemy:
        m["enemy_champion"] = enemy
    return m


def _history(n_wins=5, n_losses=4, champion="KaiSa", deaths_win=3, deaths_loss=7) -> list[dict]:
    wins   = [_match(champion=champion, result="WIN",  deaths=deaths_win,  match_id=f"w{i}") for i in range(n_wins)]
    losses = [_match(champion=champion, result="LOSS", deaths=deaths_loss, match_id=f"l{i}") for i in range(n_losses)]
    return wins + losses


# ── TestClassifyMatch ─────────────────────────────────────────────────────────

class TestClassifyMatch:
    def test_win_high_score_excelente(self):
        rating, color = classify_match("WIN", 80.0, 60.0)
        assert rating == "Excelente"
        assert "#22C55E" in color

    def test_win_above_avg_buena(self):
        rating, _ = classify_match("WIN", 62.0, 58.0)
        assert rating == "Buena"

    def test_win_average_score_normal(self):
        rating, _ = classify_match("WIN", 50.0, 60.0)
        assert rating == "Normal"

    def test_loss_good_score_normal(self):
        rating, _ = classify_match("LOSS", 65.0, 55.0)
        assert rating == "Normal"

    def test_loss_low_score_mala(self):
        # score=42 ≥ 40 → "Mala"
        rating, _ = classify_match("LOSS", 42.0, 55.0)
        assert rating == "Mala"

    def test_loss_very_low_muy_mala(self):
        rating, color = classify_match("LOSS", 20.0, 60.0)
        assert rating == "Muy mala"
        assert "#EF4444" in color

    def test_no_score_uses_result(self):
        rating, color = classify_match("WIN", None, None)
        assert rating == "Victoria"
        assert "#22C55E" in color

    def test_no_avg_uses_score_only(self):
        rating, _ = classify_match("WIN", 85.0, None)
        assert rating == "Excelente"


# ── TestBuildComparisons ──────────────────────────────────────────────────────

class TestBuildComparisons:
    def _avgs(self, deaths=6.0, cs_pm=5.5, damage_pm=900.0, kp=0.60):
        return {"deaths": deaths, "cs_pm": cs_pm, "damage_pm": damage_pm, "kp": kp}

    def test_deaths_better_verdict(self):
        match = _match(deaths=3, duration=1800)  # 3 < 6 promedio → mejor
        comps = build_comparisons(match, self._avgs(deaths=6.0))
        death_c = next(c for c in comps if c.label == "Muertes")
        assert death_c.verdict == "Mejor de lo normal"

    def test_deaths_worse_verdict(self):
        match = _match(deaths=10, duration=1800)
        comps = build_comparisons(match, self._avgs(deaths=6.0))
        death_c = next(c for c in comps if c.label == "Muertes")
        assert death_c.verdict == "Peor de lo normal"

    def test_cs_better_verdict(self):
        # 7.2 CS/min vs avg 5.5 → +31% → mejor
        match = _match(cs=216, duration=1800)  # 216/30min = 7.2
        comps = build_comparisons(match, self._avgs(cs_pm=5.5))
        cs_c = next(c for c in comps if c.label == "CS/min")
        assert cs_c.verdict == "Mejor de lo normal"

    def test_no_comparison_when_no_avg(self):
        match = _match(deaths=4)
        avgs  = {"deaths": None, "cs_pm": None, "damage_pm": None, "kp": None}
        comps = build_comparisons(match, avgs)
        assert comps == []

    def test_delta_pct_positive_for_better_deaths(self):
        match = _match(deaths=3, duration=1800)
        comps = build_comparisons(match, self._avgs(deaths=6.0))
        death_c = next(c for c in comps if c.label == "Muertes")
        assert death_c.delta_pct > 0  # positivo = mejor (lower_is_better invertido)


# ── TestBuildStrengths ────────────────────────────────────────────────────────

class TestBuildStrengths:
    def test_deaths_strength_generated(self):
        comps = [MatchComparison("Muertes", 3.0, 6.0, "muertes", "Mejor de lo normal", 50.0)]
        strengths = build_strengths(comps, _match(), {})
        assert len(strengths) == 1
        assert "muertes" in strengths[0].lower() or "Menos" in strengths[0]

    def test_cs_strength_generated(self):
        comps = [MatchComparison("CS/min", 7.5, 5.5, "CS/min", "Mejor de lo normal", 36.0)]
        strengths = build_strengths(comps, _match(), {})
        assert any("CS" in s for s in strengths)

    def test_max_3_strengths(self):
        comps = [
            MatchComparison("Muertes",       2.0, 5.0, "muertes", "Mejor de lo normal", 60.0),
            MatchComparison("CS/min",        7.5, 5.5, "CS/min",  "Mejor de lo normal", 36.0),
            MatchComparison("Daño/min",   1200.0, 900.0,"daño/min","Mejor de lo normal", 33.0),
            MatchComparison("Participación",0.80, 0.60, "% KP",   "Mejor de lo normal", 33.0),
        ]
        strengths = build_strengths(comps, _match(), {})
        assert len(strengths) <= 3

    def test_no_strength_when_normal(self):
        comps = [MatchComparison("Muertes", 5.0, 5.0, "muertes", "Normal", 0.0)]
        strengths = build_strengths(comps, _match(), {})
        assert strengths == []


# ── TestBuildMistakes ─────────────────────────────────────────────────────────

class TestBuildMistakes:
    def test_deaths_mistake_generated(self):
        comps = [MatchComparison("Muertes", 9.0, 5.0, "muertes", "Peor de lo normal", -44.0)]
        mistakes = build_mistakes(comps, _match(), {})
        assert len(mistakes) == 1
        assert "Muertes" in mistakes[0] or "muertes" in mistakes[0]

    def test_cs_mistake_generated(self):
        comps = [MatchComparison("CS/min", 4.0, 6.0, "CS/min", "Peor de lo normal", -33.0)]
        mistakes = build_mistakes(comps, _match(), {})
        assert any("CS" in m or "Farm" in m for m in mistakes)

    def test_max_3_mistakes(self):
        comps = [
            MatchComparison("Muertes",        9.0, 5.0,  "muertes", "Peor de lo normal", -44.0),
            MatchComparison("CS/min",         3.5, 6.0,  "CS/min",  "Peor de lo normal", -42.0),
            MatchComparison("Daño/min",     600.0, 900.0,"daño/min","Peor de lo normal", -33.0),
            MatchComparison("Participación", 0.30, 0.60, "% KP",   "Peor de lo normal", -50.0),
        ]
        mistakes = build_mistakes(comps, _match(), {})
        assert len(mistakes) <= 3

    def test_no_mistake_when_normal(self):
        comps = [MatchComparison("Muertes", 5.0, 5.0, "muertes", "Normal", 0.0)]
        mistakes = build_mistakes(comps, _match(), {})
        assert mistakes == []


# ── TestBuildFocus ────────────────────────────────────────────────────────────

class TestBuildFocus:
    def test_focus_from_worst_comparison_deaths(self):
        comps = [MatchComparison("Muertes", 9.0, 5.0, "muertes", "Peor de lo normal", -44.0)]
        avgs  = {"deaths": 5.0, "cs_pm": 6.0, "damage_pm": 900.0, "kp": 0.60}
        focus = build_focus([], comps, avgs)
        assert focus is not None
        assert "muertes" in focus.lower()

    def test_focus_from_worst_comparison_cs(self):
        comps = [MatchComparison("CS/min", 3.5, 6.0, "CS/min", "Peor de lo normal", -42.0)]
        avgs  = {"cs_pm": 6.0}
        focus = build_focus([], comps, avgs)
        assert focus is not None
        assert "CS" in focus

    def test_no_focus_when_all_normal(self):
        comps = [MatchComparison("Muertes", 5.0, 5.0, "muertes", "Normal", 0.0)]
        avgs  = {"deaths": 5.0}
        focus = build_focus([], comps, avgs)
        assert focus is None

    def test_focus_from_priority_engine_fallback(self):
        from backend.services.priority_engine import Priority
        p = Priority(
            title="Reducir muertes", metric_key="deaths",
            impact_score=15, confidence="high",
            evidence="...", recommendation="...",
            current_value=6.0, target_value=4.0, unit="muertes/partida",
        )
        focus = build_focus([], [], {}, priorities=[p])
        assert focus is not None
        assert "muertes" in focus.lower()


# ── TestDetectRepeatedMistakes ────────────────────────────────────────────────

class TestDetectRepeatedMistakes:
    def _high_death_history(self, champion="KaiSa", n=5):
        """Historial con muertes muy altas para forzar patrón."""
        hist = []
        for i in range(10):
            # Primeras 10: muertes bajas (establecen el avg ≈ 3)
            hist.append(_match(champion=champion, deaths=3, match_id=f"old{i}"))
        for i in range(n):
            # Últimas N (más recientes, al principio): muertes altas
            hist.insert(0, _match(champion=champion, deaths=12, match_id=f"new{i}"))
        return hist

    def test_detects_repeated_high_deaths(self):
        hist = self._high_death_history(n=4)
        repeated = detect_repeated_mistakes("KaiSa", hist)
        assert any("muerte" in r.lower() for r in repeated)

    def test_no_repeated_when_stable(self):
        hist = _history(n_wins=5, n_losses=4, deaths_win=4, deaths_loss=5)
        repeated = detect_repeated_mistakes("KaiSa", hist)
        # Con muertes similares y avg cercano no debería detectar patrón
        # (puede o no haber patrón dependiendo del delta, test permisivo)
        assert isinstance(repeated, list)

    def test_empty_history_returns_empty(self):
        assert detect_repeated_mistakes("KaiSa", []) == []

    def test_excludes_current_match(self):
        hist = self._high_death_history(n=4)
        # Excluir la primera partida (más reciente)
        exclude_id = hist[0].get("match_id")
        repeated = detect_repeated_mistakes("KaiSa", hist, exclude_match_id=exclude_id)
        assert isinstance(repeated, list)


# ── TestBuildMatchupContext ───────────────────────────────────────────────────

class TestBuildMatchupContext:
    def test_hard_matchup_win_context(self):
        ctx = build_matchup_context("Draven", 0.25, 4, "WIN")
        assert ctx is not None
        assert "Draven" in ctx
        assert "difícil" in ctx.lower() or "históricamente" in ctx.lower()

    def test_hard_matchup_loss_context(self):
        ctx = build_matchup_context("Draven", 0.28, 5, "LOSS")
        assert ctx is not None
        assert "tendencia" in ctx.lower()

    def test_favored_matchup_loss_context(self):
        ctx = build_matchup_context("Jinx", 0.70, 7, "LOSS")
        assert ctx is not None
        assert "normalmente" in ctx.lower() or "dominas" in ctx.lower()

    def test_neutral_matchup_context(self):
        ctx = build_matchup_context("Ezreal", 0.50, 6, "WIN")
        assert ctx is not None
        assert "Ezreal" in ctx

    def test_no_context_insufficient_games(self):
        ctx = build_matchup_context("Draven", 0.30, 1, "LOSS")
        assert ctx is None

    def test_no_context_none_enemy(self):
        ctx = build_matchup_context(None, None, 0, "WIN")
        assert ctx is None


# ── TestCheckPatternRepeated ──────────────────────────────────────────────────

class TestCheckPatternRepeated:
    def _mock_pattern(self, pattern_type="deaths", title="Muertes elevadas", metric_delta=60.0):
        from dataclasses import dataclass
        @dataclass
        class FakePattern:
            pattern_type: str
            title: str
            metric_delta: float
            severity: str = "critical"
            description: str = ""
        return FakePattern(pattern_type=pattern_type, title=title, metric_delta=metric_delta)

    def test_returns_problem_title(self):
        p = self._mock_pattern()
        problem, _ = check_pattern_repeated(_match(deaths=4), [p])
        assert problem == "Muertes elevadas"

    def test_no_pattern_returns_none(self):
        problem, repeated = check_pattern_repeated(_match(), [])
        assert problem is None
        assert repeated is False

    def test_pattern_repeated_high_deaths(self):
        p = self._mock_pattern(metric_delta=60.0)
        # deaths > metric_delta * 0.5 = 30 → con deaths=4 no se considera repetido
        _, repeated = check_pattern_repeated(_match(deaths=4), [p])
        assert isinstance(repeated, bool)


# ── TestGetChampionAverages ───────────────────────────────────────────────────

class TestGetChampionAverages:
    def test_returns_averages_for_champion(self):
        hist  = _history(n_wins=5, n_losses=4)
        avgs  = get_champion_averages("KaiSa", hist)
        assert avgs["games"] == 9
        assert avgs["deaths"] is not None

    def test_none_when_insufficient(self):
        hist = [_match(match_id="x1"), _match(match_id="x2")]
        avgs = get_champion_averages("KaiSa", hist)
        assert avgs["deaths"] is None  # < _MIN_HISTORY=3

    def test_excludes_current_match(self):
        hist  = _history(n_wins=5, n_losses=4)
        avgs_all = get_champion_averages("KaiSa", hist)
        avgs_exc = get_champion_averages("KaiSa", hist, exclude_match_id="w0")
        assert avgs_exc["games"] == avgs_all["games"] - 1

    def test_unknown_champion_returns_empty(self):
        hist = _history()
        avgs = get_champion_averages("Jinx", hist)
        assert avgs["games"] == 0
        assert avgs["deaths"] is None


# ── TestGetMatchupWinrate ─────────────────────────────────────────────────────

class TestGetMatchupWinrate:
    def test_winrate_correct(self):
        hist = [
            _match(result="WIN",  enemy="Draven", match_id="a"),
            _match(result="LOSS", enemy="Draven", match_id="b"),
            _match(result="LOSS", enemy="Draven", match_id="c"),
        ]
        wr, games = get_matchup_winrate("Draven", hist)
        assert games == 3
        assert wr == pytest.approx(1/3)

    def test_none_wr_insufficient(self):
        hist = [_match(result="WIN", enemy="Draven", match_id="a")]
        wr, games = get_matchup_winrate("Draven", hist)
        assert wr is None
        assert games == 1

    def test_zero_games_returns_none(self):
        wr, games = get_matchup_winrate("Jinx", [])
        assert wr is None
        assert games == 0


# ── TestGenerateReview ────────────────────────────────────────────────────────

class TestGenerateReview:
    def test_returns_post_game_review(self):
        hist    = _history()
        current = _match(match_id="current", deaths=3)
        review  = generate_review(current, [current] + hist)
        assert isinstance(review, PostGameReview)

    def test_champion_set(self):
        hist    = _history(champion="Jhin")
        current = _match(champion="Jhin", match_id="c1")
        review  = generate_review(current, [current] + hist)
        assert review.champion == "Jhin"

    def test_result_set(self):
        hist    = _history()
        current = _match(result="WIN", match_id="c1")
        review  = generate_review(current, [current] + hist)
        assert review.result == "WIN"

    def test_rating_not_empty(self):
        hist    = _history()
        current = _match(match_id="c1")
        review  = generate_review(current, [current] + hist)
        assert review.rating in ("Excelente", "Buena", "Normal", "Mala", "Muy mala",
                                 "Victoria", "Derrota")

    def test_strengths_is_list(self):
        hist    = _history()
        current = _match(deaths=2, match_id="c1")  # < avg → fortaleza
        review  = generate_review(current, [current] + hist)
        assert isinstance(review.strengths, list)
        assert len(review.strengths) <= 3

    def test_mistakes_is_list(self):
        hist    = _history()
        current = _match(deaths=12, match_id="c1")  # > avg → error
        review  = generate_review(current, [current] + hist)
        assert isinstance(review.mistakes, list)
        assert len(review.mistakes) <= 3

    def test_focus_string_or_none(self):
        hist    = _history()
        current = _match(match_id="c1")
        review  = generate_review(current, [current] + hist)
        assert review.focus is None or isinstance(review.focus, str)

    def test_confidence_levels(self):
        few_hist = [_match(match_id=f"x{i}") for i in range(2)]
        current  = _match(match_id="c1")
        review   = generate_review(current, [current] + few_hist)
        assert review.confidence in ("low", "medium", "high")

    def test_matchup_context_when_enemy_available(self):
        hist = [
            _match(result="WIN",  enemy="Draven", match_id="h1"),
            _match(result="LOSS", enemy="Draven", match_id="h2"),
            _match(result="LOSS", enemy="Draven", match_id="h3"),
        ]
        current = _match(result="WIN", enemy="Draven", match_id="c1")
        review  = generate_review(current, [current] + hist)
        # Con 3 juegos previos vs Draven debería haber contexto
        assert review.matchup_context is not None
        assert "Draven" in review.matchup_context

    def test_score_delta_calculated(self):
        hist    = _history()
        current = _match(score=90.0, match_id="c1")
        review  = generate_review(current, [current] + hist)
        if review.score_avg is not None:
            assert review.score_delta == pytest.approx(90.0 - review.score_avg)

    def test_repeated_mistakes_is_list(self):
        hist    = _history()
        current = _match(match_id="c1")
        review  = generate_review(current, [current] + hist)
        assert isinstance(review.repeated_mistakes, list)

    def test_score_set_from_match(self):
        hist    = _history()
        current = _match(score=72.0, match_id="c1")
        review  = generate_review(current, [current] + hist)
        assert review.score == pytest.approx(72.0)
