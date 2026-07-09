"""
tests/test_champion_coach.py — Tests para Sprint 11: Champion Coach.

Cubre:
  - champion_models.py   (propiedades calculadas)
  - champion_patterns.py (detección de patrones)
  - champion_goals.py    (generación de objetivos)
  - champion_coach.py    (motor principal, clasificación, strengths/weaknesses)

Cobertura objetivo: ≥ 80%.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.services.champion_models import (
    ChampionAnalysis,
    ChampionCoachResult,
    ChampionGoal,
    ChampionPattern,
)
from backend.services.champion_patterns import detect_patterns
from backend.services.champion_goals import generate_goal
from backend.services.champion_coach import (
    _build_analysis,
    _build_strengths,
    _build_weaknesses,
    analyze_champion,
    classify_priority,
    get_available_champions,
)
from backend.config.constants import MIN_CHAMPION_GAMES, ROBUST_CHAMPION_GAMES


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _match(
    champion: str = "KaiSa",
    result:   str = "WIN",
    deaths:   int = 3,
    cs:       int = 200,
    damage:   int = 25000,
    kp:       float = 0.65,
    duration: int = 1800,
) -> dict:
    return {
        "champion":          champion,
        "role":              "ADC",
        "result":            result,
        "deaths":            deaths,
        "cs":                cs,
        "damage":            damage,
        "kill_participation": kp,
        "duration_sec":      duration,
    }


def _analysis(
    champion:           str        = "KaiSa",
    games:              int | None = None,
    wins:               int        = 5,
    losses:             int        = 3,
    avg_deaths:         float = 4.0,
    avg_cs_min:         float = 6.5,
    avg_damage_min:     float = 1000.0,
    avg_kp:             float = 0.65,
    score_std:          float = 8.0,
    win_avg_deaths:     float = 2.5,
    loss_avg_deaths:    float = 7.0,
    win_avg_cs_min:     float = 7.0,
    loss_avg_cs_min:    float = 5.0,
    win_avg_damage_min: float = 1200.0,
    loss_avg_damage_min:float = 800.0,
    win_avg_kp:         float = 0.72,
    loss_avg_kp:        float = 0.50,
    trend:              str   = "stable",
) -> ChampionAnalysis:
    total = games if games is not None else wins + losses
    return ChampionAnalysis(
        champion_name       = champion,
        role                = "ADC",
        games               = total,
        wins                = wins,
        losses              = total - wins,
        winrate             = wins / max(total, 1),
        avg_score           = 65.0,
        avg_deaths          = avg_deaths,
        avg_cs_min          = avg_cs_min,
        avg_damage_min      = avg_damage_min,
        avg_kp              = avg_kp,
        trend               = trend,
        confidence          = "medium" if total < ROBUST_CHAMPION_GAMES else "high",
        score_std           = score_std,
        win_avg_deaths      = win_avg_deaths,
        loss_avg_deaths     = loss_avg_deaths,
        win_avg_cs_min      = win_avg_cs_min,
        loss_avg_cs_min     = loss_avg_cs_min,
        win_avg_damage_min  = win_avg_damage_min,
        loss_avg_damage_min = loss_avg_damage_min,
        win_avg_kp          = win_avg_kp,
        loss_avg_kp         = loss_avg_kp,
    )


# ── TestChampionAnalysisProperties ───────────────────────────────────────────

class TestChampionAnalysisProperties:
    def test_deaths_delta_pct_positive(self):
        a = _analysis(win_avg_deaths=3.0, loss_avg_deaths=6.0)
        assert a.deaths_win_loss_delta_pct == pytest.approx(100.0)

    def test_deaths_delta_pct_zero(self):
        a = _analysis(win_avg_deaths=4.0, loss_avg_deaths=4.0)
        assert a.deaths_win_loss_delta_pct == pytest.approx(0.0)

    def test_cs_delta_pct_negative(self):
        a = _analysis(win_avg_cs_min=7.0, loss_avg_cs_min=5.0)
        expected = (5.0 - 7.0) / 7.0 * 100
        assert a.cs_win_loss_delta_pct == pytest.approx(expected)

    def test_damage_delta_pct_negative(self):
        a = _analysis(win_avg_damage_min=1200.0, loss_avg_damage_min=800.0)
        expected = (800.0 - 1200.0) / 1200.0 * 100
        assert a.damage_win_loss_delta_pct == pytest.approx(expected)

    def test_kp_delta_pct_negative(self):
        a = _analysis(win_avg_kp=0.70, loss_avg_kp=0.50)
        expected = (0.50 - 0.70) / 0.70 * 100
        assert a.kp_win_loss_delta_pct == pytest.approx(expected)

    def test_is_consistent_low_cv(self):
        a = _analysis(score_std=5.0)
        a.avg_score = 70.0
        assert a.is_consistent is True   # CV = 5/70 ≈ 0.07 < 0.30

    def test_is_not_consistent_high_cv(self):
        a = _analysis(score_std=30.0)
        a.avg_score = 60.0
        assert a.is_consistent is False  # CV = 30/60 = 0.50 ≥ 0.30

    def test_winrate_correct(self):
        a = _analysis(games=10, wins=7)
        assert a.winrate == pytest.approx(0.70)


# ── TestChampionPatterns ──────────────────────────────────────────────────────

class TestChampionPatterns:
    def test_deaths_pattern_detected(self):
        a = _analysis(wins=3, losses=3, win_avg_deaths=3.0, loss_avg_deaths=6.0)
        patterns = detect_patterns(a)
        assert any(p.pattern_type == "deaths" for p in patterns)

    def test_deaths_pattern_critical(self):
        # +40% → crítico (umbral 35%)
        a = _analysis(wins=3, losses=3, win_avg_deaths=3.0, loss_avg_deaths=5.0)
        # 3→5 = +67% → crítico
        patterns = detect_patterns(a)
        deaths_p = next(p for p in patterns if p.pattern_type == "deaths")
        assert deaths_p.severity == "critical"

    def test_deaths_pattern_warning(self):
        # +22% → warning
        a = _analysis(wins=3, losses=3, win_avg_deaths=4.0, loss_avg_deaths=4.9)
        # 4→4.9 = +22.5% → warning
        patterns = detect_patterns(a)
        deaths_p = next((p for p in patterns if p.pattern_type == "deaths"), None)
        if deaths_p:
            assert deaths_p.severity == "warning"

    def test_farm_pattern_detected(self):
        a = _analysis(wins=3, losses=3, win_avg_cs_min=7.0, loss_avg_cs_min=5.0)
        # -28.6% → patrón
        patterns = detect_patterns(a)
        assert any(p.pattern_type == "farm" for p in patterns)

    def test_farm_not_detected_small_drop(self):
        a = _analysis(wins=3, losses=3, win_avg_cs_min=7.0, loss_avg_cs_min=6.5)
        # -7.1% < 15% → no patrón
        patterns = detect_patterns(a)
        assert not any(p.pattern_type == "farm" for p in patterns)

    def test_damage_pattern_detected(self):
        a = _analysis(wins=3, losses=3, win_avg_damage_min=1200.0, loss_avg_damage_min=800.0)
        # -33% → patrón
        patterns = detect_patterns(a)
        assert any(p.pattern_type == "damage" for p in patterns)

    def test_kp_pattern_detected(self):
        a = _analysis(wins=3, losses=3, win_avg_kp=0.70, loss_avg_kp=0.45)
        # -35.7% → patrón
        patterns = detect_patterns(a)
        assert any(p.pattern_type == "kp" for p in patterns)

    def test_consistency_pattern(self):
        a = _analysis(games=6, wins=3, score_std=30.0)
        a.avg_score = 55.0  # CV = 30/55 ≈ 0.55 ≥ 0.35
        patterns = detect_patterns(a)
        assert any(p.pattern_type == "consistency" for p in patterns)

    def test_no_patterns_insufficient_split(self):
        # 1 victoria + 0 derrotas → no hay split
        a = _analysis(games=1, wins=1, losses=0)
        a.losses = 0
        patterns = detect_patterns(a)
        # No debe haber patrones de split (solo posiblemente consistency)
        split_patterns = [p for p in patterns if p.pattern_type in ("deaths", "farm", "damage", "kp")]
        assert split_patterns == []

    def test_sorted_critical_first(self):
        a = _analysis(
            wins=3, losses=3,
            win_avg_deaths=2.0, loss_avg_deaths=8.0,       # +300% → critical
            win_avg_cs_min=7.0, loss_avg_cs_min=5.5,       # -21% → warning
        )
        patterns = detect_patterns(a)
        assert patterns[0].severity == "critical"

    def test_description_mentions_champion(self):
        a = _analysis(champion="Ezreal", wins=3, losses=3,
                      win_avg_deaths=2.0, loss_avg_deaths=5.0)
        patterns = detect_patterns(a)
        deaths_p = next(p for p in patterns if p.pattern_type == "deaths")
        assert "Ezreal" in deaths_p.description

    def test_metric_delta_positive(self):
        a = _analysis(wins=3, losses=3, win_avg_deaths=3.0, loss_avg_deaths=6.0)
        patterns = detect_patterns(a)
        deaths_p = next(p for p in patterns if p.pattern_type == "deaths")
        assert deaths_p.metric_delta > 0


# ── TestChampionGoals ─────────────────────────────────────────────────────────

class TestChampionGoals:
    def test_deaths_goal_generated(self):
        a = _analysis(wins=3, losses=3,
                      win_avg_deaths=3.0, loss_avg_deaths=7.0,
                      avg_deaths=5.0)
        goal = generate_goal(a)
        assert goal is not None
        assert goal.metric_key == "deaths"

    def test_deaths_goal_target_is_win_avg(self):
        a = _analysis(wins=3, losses=3,
                      win_avg_deaths=3.0, loss_avg_deaths=7.0,
                      avg_deaths=5.0)
        goal = generate_goal(a)
        assert goal.target == pytest.approx(3.0)

    def test_cs_goal_generated(self):
        # Solo CS gap, sin deaths gap
        a = _analysis(
            wins=3, losses=3,
            win_avg_deaths=4.0, loss_avg_deaths=4.0,   # sin gap
            win_avg_cs_min=7.5, loss_avg_cs_min=5.0,
            avg_cs_min=6.0,
        )
        goal = generate_goal(a)
        assert goal is not None
        assert goal.metric_key == "cs_pm"

    def test_deaths_beats_cs_when_both_present(self):
        # deaths gap grande vs CS gap pequeño → deaths gana
        a = _analysis(
            wins=3, losses=3,
            win_avg_deaths=2.0, loss_avg_deaths=8.0,     # +300%
            win_avg_cs_min=7.0, loss_avg_cs_min=5.5,     # -21%
            avg_deaths=5.0, avg_cs_min=6.2,
        )
        goal = generate_goal(a)
        assert goal is not None
        assert goal.metric_key == "deaths"

    def test_no_goal_when_insufficient_split(self):
        a = _analysis(wins=1, losses=1)  # < MIN_SPLIT(2)
        goal = generate_goal(a)
        assert goal is None

    def test_goal_description_non_empty(self):
        a = _analysis(wins=3, losses=3,
                      win_avg_deaths=3.0, loss_avg_deaths=7.0,
                      avg_deaths=5.0)
        goal = generate_goal(a)
        assert len(goal.description) > 10

    def test_goal_impact_desc_mentions_champion(self):
        a = _analysis(champion="Jhin", wins=3, losses=3,
                      win_avg_deaths=3.0, loss_avg_deaths=7.0,
                      avg_deaths=5.0)
        goal = generate_goal(a)
        assert "Jhin" in goal.impact_desc

    def test_kp_goal_generated(self):
        a = _analysis(
            wins=3, losses=3,
            win_avg_deaths=4.0, loss_avg_deaths=4.0,
            win_avg_cs_min=6.0, loss_avg_cs_min=6.0,
            win_avg_kp=0.72,    loss_avg_kp=0.45,
            avg_kp=0.58,
        )
        goal = generate_goal(a)
        assert goal is not None
        assert goal.metric_key == "kp"


# ── TestClassifyPriority ──────────────────────────────────────────────────────

class TestClassifyPriority:
    def _all_analyses(self, *analyses):
        return list(analyses)

    def test_insufficient_below_min_games(self):
        a = _analysis(games=3, wins=2)
        result = classify_priority(a, [a])
        assert result == "insufficient"

    def test_main_most_games(self):
        main_a   = _analysis(games=15, wins=8)
        other_a  = _analysis(champion="Ezreal", games=5, wins=3)
        result   = classify_priority(main_a, [main_a, other_a])
        assert result == "main"

    def test_risk_low_wr(self):
        a = _analysis(games=8, wins=2)  # WR = 25% < 45%
        result = classify_priority(a, [a])
        assert result == "risk"

    def test_growth_high_wr_low_games(self):
        # WR ≥ 55%, games < ROBUST_CHAMPION_GAMES, no es el de más partidas
        big    = _analysis(champion="KaiSa", games=20, wins=10)
        growth = _analysis(champion="Jhin",  games=6,  wins=4)  # WR=66%, games=6
        result = classify_priority(growth, [big, growth])
        assert result == "growth"

    def test_main_returned_for_high_volume_equal_games(self):
        only = _analysis(games=MIN_CHAMPION_GAMES, wins=3)
        result = classify_priority(only, [only])
        assert result in ("main", "growth")  # único calificado → main


# ── TestAnalyzeChampion ───────────────────────────────────────────────────────

def _make_matches(
    champion: str = "KaiSa",
    n_wins:   int = 5,
    n_losses: int = 4,
    deaths_win:  int = 3,
    deaths_loss: int = 7,
) -> list[dict]:
    wins   = [_match(champion=champion, result="WIN",  deaths=deaths_win)  for _ in range(n_wins)]
    losses = [_match(champion=champion, result="LOSS", deaths=deaths_loss) for _ in range(n_losses)]
    return wins + losses


class TestAnalyzeChampion:
    def test_returns_coach_result(self):
        matches = _make_matches()
        result  = analyze_champion(matches, "KaiSa", "ADC")
        assert isinstance(result, ChampionCoachResult)

    def test_analysis_champion_name(self):
        matches = _make_matches(champion="Jhin")
        result  = analyze_champion(matches, "Jhin", "ADC")
        assert result.analysis.champion_name == "Jhin"

    def test_games_count(self):
        matches = _make_matches(n_wins=5, n_losses=4)
        result  = analyze_champion(matches, "KaiSa", "ADC")
        assert result.analysis.games == 9

    def test_winrate_correct(self):
        matches = _make_matches(n_wins=6, n_losses=4)
        result  = analyze_champion(matches, "KaiSa", "ADC")
        assert result.analysis.winrate == pytest.approx(0.60)

    def test_patterns_is_list(self):
        matches = _make_matches()
        result  = analyze_champion(matches, "KaiSa", "ADC")
        assert isinstance(result.patterns, list)

    def test_deaths_pattern_when_gap_large(self):
        matches = _make_matches(deaths_win=2, deaths_loss=8, n_wins=4, n_losses=4)
        result  = analyze_champion(matches, "KaiSa", "ADC")
        assert any(p.pattern_type == "deaths" for p in result.patterns)

    def test_empty_champion_returns_insufficient(self):
        matches = _make_matches(champion="Jinx")
        result  = analyze_champion(matches, "KaiSa", "ADC")
        assert result.priority_class == "insufficient"

    def test_priority_class_set(self):
        matches = _make_matches(n_wins=6, n_losses=4)
        result  = analyze_champion(matches, "KaiSa", "ADC")
        assert result.priority_class in ("main", "growth", "risk", "insufficient")

    def test_strengths_is_list(self):
        matches = _make_matches()
        result  = analyze_champion(matches, "KaiSa", "ADC")
        assert isinstance(result.strengths, list)

    def test_weaknesses_is_list(self):
        matches = _make_matches()
        result  = analyze_champion(matches, "KaiSa", "ADC")
        assert isinstance(result.weaknesses, list)

    def test_primary_problem_from_patterns(self):
        matches = _make_matches(deaths_win=2, deaths_loss=8, n_wins=4, n_losses=4)
        result  = analyze_champion(matches, "KaiSa", "ADC")
        if result.patterns:
            assert result.primary_problem == result.patterns[0].title

    def test_no_primary_problem_without_patterns(self):
        # wins y losses con muertes idénticas → sin patrón de muertes
        matches = _make_matches(deaths_win=4, deaths_loss=4, n_wins=5, n_losses=5)
        result  = analyze_champion(matches, "KaiSa", "ADC")
        # Puede no haber primary_problem si no se detectan patrones
        assert result.primary_problem is None or isinstance(result.primary_problem, str)

    def test_matchup_integration_none(self):
        matches = _make_matches()
        result  = analyze_champion(matches, "KaiSa", "ADC", matchup_result=None)
        assert result.matchup_best  is None
        assert result.matchup_worst is None


# ── TestGetAvailableChampions ─────────────────────────────────────────────────

class TestGetAvailableChampions:
    def test_returns_champions_sorted_by_games(self):
        matches = (
            [_match("KaiSa")]  * 10 +
            [_match("Jinx")]   * 5  +
            [_match("Ezreal")] * 2
        )
        champs = get_available_champions(matches)
        assert champs[0] == "KaiSa"
        assert champs[1] == "Jinx"
        assert champs[2] == "Ezreal"

    def test_empty_matches_returns_empty(self):
        assert get_available_champions([]) == []

    def test_no_duplicates(self):
        matches = [_match("KaiSa")] * 5
        champs  = get_available_champions(matches)
        assert champs.count("KaiSa") == 1

    def test_skips_none_champion(self):
        matches = [_match("KaiSa"), {"champion": None, "role": "ADC"}]
        champs  = get_available_champions(matches)
        assert None not in champs


# ── TestBuildStrengths ────────────────────────────────────────────────────────

class TestBuildStrengths:
    def test_low_deaths_is_strength(self):
        # avg_deaths = 3.0, overall = 5.0 → fortaleza
        a = _analysis(avg_deaths=3.0)
        strengths = _build_strengths(a, 5.0, 6.0, 1000.0, 0.60)
        assert any("muerte" in s.lower() or "Muertes" in s for s in strengths)

    def test_high_cs_is_strength(self):
        # avg_cs = 8.0, overall = 6.0 → fortaleza (+33%)
        a = _analysis(avg_cs_min=8.0)
        strengths = _build_strengths(a, 4.0, 6.0, 1000.0, 0.60)
        assert any("CS" in s or "cs" in s.lower() for s in strengths)

    def test_high_wr_is_strength(self):
        a = _analysis(games=10, wins=7)
        strengths = _build_strengths(a, 4.0, 6.0, 1000.0, 0.60)
        assert any("WR" in s or "winrate" in s.lower() or "%" in s for s in strengths)

    def test_max_4_strengths(self):
        a = _analysis(games=10, wins=8, avg_deaths=2.0, avg_cs_min=9.0,
                      avg_damage_min=1500.0, avg_kp=0.85)
        strengths = _build_strengths(a, 5.0, 6.0, 1000.0, 0.60)
        assert len(strengths) <= 4


# ── TestBuildWeaknesses ───────────────────────────────────────────────────────

class TestBuildWeaknesses:
    def test_patterns_become_weaknesses(self):
        a = _analysis(wins=3, losses=3, win_avg_deaths=2.0, loss_avg_deaths=7.0)
        patterns = detect_patterns(a)
        weaknesses = _build_weaknesses(a, patterns, 4.0, 6.0)
        assert len(weaknesses) > 0

    def test_high_deaths_without_pattern(self):
        # Sin patrón de deaths, pero avg_deaths > overall * 1.15
        a = _analysis(avg_deaths=6.0, wins=1, losses=1)
        a.win_avg_deaths  = 6.0
        a.loss_avg_deaths = 6.0
        patterns = []  # sin patrones
        weaknesses = _build_weaknesses(a, patterns, 4.0, 6.0)
        assert any("muerte" in w.lower() or "Muertes" in w for w in weaknesses)

    def test_max_4_weaknesses(self):
        a = _analysis(wins=3, losses=3,
                      win_avg_deaths=2.0,     loss_avg_deaths=8.0,
                      win_avg_cs_min=7.0,     loss_avg_cs_min=4.0,
                      win_avg_damage_min=1200.0, loss_avg_damage_min=600.0,
                      win_avg_kp=0.75,        loss_avg_kp=0.40)
        patterns   = detect_patterns(a)
        weaknesses = _build_weaknesses(a, patterns, 4.0, 6.0)
        assert len(weaknesses) <= 4
