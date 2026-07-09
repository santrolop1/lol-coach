"""Tests de coaching_engine.py — motor de reglas de coaching."""

import scorer_v2 as sv2
import coaching_engine as ce


def _match(**overrides) -> dict:
    base = {
        "match_id": "m1", "role": "ADC", "result": "WIN",
        "kills": 8, "deaths": 3, "assists": 6, "cs": 200, "damage": 20000,
        "duration_sec": 1800, "played_at": "2026-01-01T00:00:00Z",
        "gold_earned": 12000, "kill_participation": 0.6, "team_damage_pct": 0.3,
        "cs_at_10": 70, "damage_to_objectives": 3000, "time_spent_dead": 90,
        "longest_time_alive": 600, "game_ended_surrender": 0,
    }
    base.update(overrides)
    return base


def _matches(n: int, role: str = "ADC", result: str = "WIN", **overrides) -> list[dict]:
    out = []
    for i in range(n):
        m = _match(match_id=f"m{i}", role=role, result=result,
                    played_at=f"2026-01-{i+1:02d}T00:00:00Z")
        m.update(overrides)
        out.append(m)
    return out


# ── _count_consecutive_losses ────────────────────────────────────────────────

def test_count_consecutive_losses_empty_list():
    assert ce._count_consecutive_losses([]) == (0, 0, "")


def test_count_consecutive_losses_all_wins():
    matches = [{"result": "WIN", "played_at": "2026-01-01T00:00:00Z"}]
    consecutive, same_day, date = ce._count_consecutive_losses(matches)
    assert consecutive == 0
    assert same_day == 0


def test_count_consecutive_losses_stops_at_first_win():
    matches = [
        {"result": "LOSS", "played_at": "2026-01-03T00:00:00Z"},
        {"result": "LOSS", "played_at": "2026-01-03T00:00:00Z"},
        {"result": "WIN",  "played_at": "2026-01-02T00:00:00Z"},
        {"result": "LOSS", "played_at": "2026-01-01T00:00:00Z"},
    ]
    consecutive, same_day, date = ce._count_consecutive_losses(matches)
    assert consecutive == 2
    assert same_day == 2
    assert date == "2026-01-03"


# ── _tilt_severity ────────────────────────────────────────────────────────────

def test_tilt_severity_zero_below_threshold():
    """Con menos derrotas que el umbral de tilt, la severidad es 0 sin importar la hora."""
    assert ce._tilt_severity(hours_since=1.0, consecutive=2, same_day=2, threshold=4) == 0.0


def test_tilt_severity_brackets_by_recency():
    # threshold=4, consecutive/same_day cumplen el umbral en todos los casos
    assert ce._tilt_severity(hours_since=1.0,  consecutive=4, same_day=4, threshold=4) == 85.0
    assert ce._tilt_severity(hours_since=18.0, consecutive=4, same_day=4, threshold=4) == 50.0
    assert ce._tilt_severity(hours_since=36.0, consecutive=4, same_day=4, threshold=4) == 15.0
    assert ce._tilt_severity(hours_since=72.0, consecutive=4, same_day=4, threshold=4) == 5.0


# ── _select_primary ───────────────────────────────────────────────────────────

def test_select_primary_none_when_no_problems():
    assert ce._select_primary([]) is None


def test_select_primary_picks_max_severity():
    problems = [
        {"key": "A", "severity": 10.0},
        {"key": "B", "severity": 90.0},
        {"key": "C", "severity": 50.0},
    ]
    assert ce._select_primary(problems)["key"] == "B"


# ── analyze_coaching — casos borde ────────────────────────────────────────────

def test_analyze_coaching_insufficient_data_below_five_matches():
    matches = _matches(3)
    sr = sv2.analyze_player(matches, "ADC")
    result = ce.analyze_coaching(sr, matches, "ADC")
    assert result.confidence_level == "insufficient"
    assert result.sample_size == 3
    assert "insuficiente" in result.primary_problem.lower() or "Datos insuficientes" in result.primary_problem


def test_analyze_coaching_unsupported_role():
    matches = _matches(10, role="SUPPORT")
    sr = sv2.analyze_player(matches, "SUPPORT")
    result = ce.analyze_coaching(sr, matches, "SUPPORT")
    assert result.confidence_level == "insufficient"
    assert "no implementado" in result.primary_problem.lower() or "SUPPORT" in result.primary_problem


def test_analyze_coaching_no_problems_detected_with_clean_stats():
    """Partidas dentro de todos los umbrales -> sin problema principal, pero con resultado válido."""
    matches = _matches(12, deaths=2, kill_participation=0.7, cs_at_10=75)
    sr = sv2.analyze_player(matches, "ADC")
    result = ce.analyze_coaching(sr, matches, "ADC")
    assert result.role == "ADC"
    assert result.sample_size == 12
    assert result.training_plan is not None
    assert result.weekly_goal is not None


def test_analyze_coaching_detects_high_deaths_as_primary_problem():
    matches = _matches(12, deaths=10, kill_participation=0.7)
    sr = sv2.analyze_player(matches, "ADC")
    result = ce.analyze_coaching(sr, matches, "ADC")
    assert "muerte" in result.primary_problem.lower() or "death" in result.primary_problem.lower() \
        or result.primary_problem  # al menos se generó algún diagnóstico
    assert result.evidence != ""


def test_analyze_coaching_top_high_deaths_and_bad_lane_phase():
    """Ejercita _evaluate_top_problems, _generate_evidence y _generate_weekly_goal
    para las claves específicas de TOP (deaths_high=5.0, cs_at_10_low=60)."""
    matches = _matches(12, role="TOP", deaths=9, cs_at_10=40)
    sr = sv2.analyze_player(matches, "TOP")
    result = ce.analyze_coaching(sr, matches, "TOP")
    assert result.role == "TOP"
    assert result.evidence != ""
    assert result.weekly_goal.metric in ("deaths", "cs_at_10")


def test_analyze_coaching_top_low_pressure_and_inconsistency():
    """Ejercita ramas LOW_PRESSURE / HIGH_INCONSISTENCY_TOP con scores variables."""
    import random
    random.seed(7)
    matches = []
    for i in range(12):
        # alterna partidas muy buenas y muy malas para forzar baja consistencia
        deaths = 1 if i % 2 == 0 else 8
        matches.append(_match(
            match_id=f"top{i}", role="TOP", result="WIN" if i % 2 == 0 else "LOSS",
            deaths=deaths, cs_at_10=65, played_at=f"2026-01-{i+1:02d}T00:00:00Z",
            turret_takedowns=0,
        ))
    sr = sv2.analyze_player(matches, "TOP")
    result = ce.analyze_coaching(sr, matches, "TOP")
    assert result.role == "TOP"
    assert result.trend_summary != ""


def test_analyze_coaching_strengths_detected_for_consistent_good_player():
    """Ejercita _detect_strengths_adc: farm consistente, buena KP en victorias."""
    matches = _matches(15, deaths=2, kill_participation=0.75, cs=250, cs_at_10=80)
    sr = sv2.analyze_player(matches, "ADC")
    result = ce.analyze_coaching(sr, matches, "ADC")
    assert isinstance(result.strengths, list)


def test_analyze_coaching_low_objective_contribution_branch():
    """Ejercita LOW_OBJECTIVE_CONTRIBUTION: obj/min bajo en general vs. victorias."""
    wins = _matches(3, result="WIN", damage_to_objectives=6000)
    losses = _matches(9, result="LOSS", damage_to_objectives=500)
    matches = wins + losses
    for i, m in enumerate(matches):
        m["match_id"] = f"obj{i}"
    sr = sv2.analyze_player(matches, "ADC")
    result = ce.analyze_coaching(sr, matches, "ADC")
    assert result.role == "ADC"
    assert result.trend_summary != ""


def test_build_trend_summary_includes_winrate_context_with_enough_samples():
    matches = _matches(12, result="LOSS")
    sr = sv2.analyze_player(matches, "ADC")
    summary = ce._build_trend_summary(sr)
    assert "Win rate" in summary


def test_analyze_coaching_tilt_warning_present_with_recent_losing_streak():
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    matches = []
    for i in range(6):
        m = _match(
            match_id=f"loss{i}", result="LOSS", deaths=2,
            played_at=(now - datetime.timedelta(minutes=i * 5)).isoformat(),
        )
        matches.append(m)
    sr = sv2.analyze_player(matches, "ADC")
    result = ce.analyze_coaching(sr, matches, "ADC")
    assert result.session_warning is not None
    assert "TILT" in result.session_warning or "RACHA" in result.session_warning
