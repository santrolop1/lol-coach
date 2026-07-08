"""Tests de scorer_v2.py — motor de scoring por rol."""

import scorer_v2 as sv2


def _match(**overrides) -> dict:
    """Partida base ADC válida; overrides sobreescriben campos puntuales."""
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


def _matches(n: int, role: str = "ADC", **overrides) -> list[dict]:
    out = []
    for i in range(n):
        m = _match(match_id=f"m{i}", role=role, played_at=f"2026-01-{i+1:02d}T00:00:00Z")
        m.update(overrides)
        out.append(m)
    return out


# ── _percentile_score ────────────────────────────────────────────────────────

def test_percentile_score_neutral_with_small_reference():
    """N < _MIN_REF_SAMPLES (3) -> score neutral 50.0, no hay base estadística."""
    assert sv2._percentile_score(10.0, [5.0, 6.0]) == 50.0


def test_percentile_score_higher_is_better():
    ref = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert sv2._percentile_score(5.0, ref, higher_is_better=True) == 100.0
    assert sv2._percentile_score(1.0, ref, higher_is_better=True) == 20.0


def test_percentile_score_lower_is_better_inverts_rank():
    ref = [1.0, 2.0, 3.0, 4.0, 5.0]
    # El valor más bajo es el mejor cuando lower_is_better -> rank más alto
    assert sv2._percentile_score(1.0, ref, higher_is_better=False) == 100.0
    assert sv2._percentile_score(5.0, ref, higher_is_better=False) == 20.0


# ── _linear_slope (OLS) ──────────────────────────────────────────────────────

def test_linear_slope_zero_with_fewer_than_two_points():
    assert sv2._linear_slope([]) == 0.0
    assert sv2._linear_slope([42.0]) == 0.0


def test_linear_slope_positive_for_increasing_series():
    assert sv2._linear_slope([10.0, 20.0, 30.0, 40.0]) > 0


def test_linear_slope_negative_for_decreasing_series():
    assert sv2._linear_slope([40.0, 30.0, 20.0, 10.0]) < 0


def test_linear_slope_zero_for_flat_series():
    assert sv2._linear_slope([50.0, 50.0, 50.0]) == 0.0


# ── _classify_trend ───────────────────────────────────────────────────────────

def test_classify_trend_boundaries():
    assert sv2._classify_trend(1.5) == "stable"      # exactamente en el umbral: no es ">"
    assert sv2._classify_trend(1.51) == "improving"
    assert sv2._classify_trend(-1.51) == "declining"
    assert sv2._classify_trend(0.0) == "stable"


# ── _consistency_cv ───────────────────────────────────────────────────────────

def test_consistency_cv_none_with_fewer_than_two_scores():
    assert sv2._consistency_cv([50.0]) is None
    assert sv2._consistency_cv([]) is None


def test_consistency_cv_perfect_for_identical_scores():
    assert sv2._consistency_cv([70.0, 70.0, 70.0]) == 100.0


def test_consistency_cv_zero_mean_edge_case():
    """mean≈0 evita división por cero — usa std directamente."""
    result = sv2._consistency_cv([-5.0, 5.0])
    assert result is not None
    assert 0.0 <= result <= 100.0


# ── _confidence_level ─────────────────────────────────────────────────────────

def test_confidence_level_boundaries():
    assert sv2._confidence_level(0) == "insufficient"
    assert sv2._confidence_level(4) == "insufficient"
    assert sv2._confidence_level(5) == "preliminary"
    assert sv2._confidence_level(9) == "preliminary"
    assert sv2._confidence_level(10) == "reliable"
    assert sv2._confidence_level(19) == "reliable"
    assert sv2._confidence_level(20) == "robust"


# ── score_match ───────────────────────────────────────────────────────────────

def test_score_match_returns_none_for_unsupported_role():
    m = _match(role="SUPPORT")
    assert sv2.score_match(m, [m]) is None


def test_score_match_computes_overall_for_supported_role():
    ref = _matches(10)
    ms = sv2.score_match(ref[0], ref)
    assert ms is not None
    assert ms.role == "ADC"
    assert ms.overall_score is not None
    assert 0.0 <= ms.overall_score <= 100.0
    assert len(ms.dimensions) == 3  # Economy, Positioning, Combat Impact


def test_score_match_marks_surrender_flag():
    m = _match(game_ended_surrender=1)
    ms = sv2.score_match(m, [m])
    assert ms.is_surrender is True


def test_score_match_handles_missing_optional_fields_without_crashing():
    """Partidas viejas (pre-12.x) sin challenges.* no deben crashear el scoring."""
    m = _match(kill_participation=None, cs_at_10=None, team_damage_pct=None,
               damage_to_objectives=None, gold_earned=None)
    ms = sv2.score_match(m, [m])
    assert ms is not None
    # overall_score puede ser None si ninguna dimensión tuvo datos, pero no debe crashear
    assert ms.dimensions is not None


# ── analyze_player ────────────────────────────────────────────────────────────

def test_analyze_player_empty_matches_is_insufficient():
    result = sv2.analyze_player([], "ADC")
    assert result.confidence_level == "insufficient"
    assert result.sample_size == 0
    assert result.match_scores == []
    assert result.overall_score is None


def test_analyze_player_filters_by_role():
    matches = _matches(6, role="ADC") + _matches(3, role="TOP")
    result = sv2.analyze_player(matches, "ADC")
    assert result.sample_size == 6
    assert all(ms.role == "ADC" for ms in result.match_scores)


def test_analyze_player_trend_and_consistency_present_with_enough_samples():
    matches = _matches(12)
    result = sv2.analyze_player(matches, "ADC")
    assert result.confidence_level == "reliable"
    assert result.trend in ("improving", "stable", "declining")
    assert result.consistency_score is not None


def test_analyze_player_counts_surrenders():
    matches = _matches(5) + _matches(2, game_ended_surrender=1)
    # IDs únicos para evitar colisión de match_id entre los dos bloques
    for i, m in enumerate(matches):
        m["match_id"] = f"s{i}"
    result = sv2.analyze_player(matches, "ADC")
    assert result.surrender_count == 2


# ── calculate_benchmarks ──────────────────────────────────────────────────────

def test_calculate_benchmarks_notes_small_sample():
    matches = _matches(3)
    bm = sv2.calculate_benchmarks(matches, "ADC")
    assert bm.sample_size == 3
    assert "insuficiente" in bm.note.lower() or "muestra" in bm.note.lower()


def test_calculate_benchmarks_skips_metrics_with_no_data():
    matches = _matches(5, max_cs_advantage=None)
    bm = sv2.calculate_benchmarks(matches, "ADC")
    assert "max_cs_advantage" not in bm.metrics
