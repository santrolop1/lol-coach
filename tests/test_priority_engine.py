"""
tests/test_priority_engine.py — Tests para backend/services/priority_engine.py

Cobertura objetivo: ≥80% de las ramas del módulo.
No usa mocks: trabaja con datos sintéticos que simulan partidas reales.
"""

import statistics
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.services.priority_engine import (
    Priority,
    _confidence,
    _evidence_text,
    _extract,
    _recommendation_text,
    _safe_float,
    compute_priorities,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _match(
    result: str = "WIN",
    deaths: int = 3,
    cs: int = 200,
    damage: int = 20000,
    vision_score: int = 25,
    kill_participation: float = 0.65,
    damage_to_objectives: int = 5000,
    duration_sec: int = 1800,
) -> dict:
    return {
        "result": result,
        "deaths": deaths,
        "cs": cs,
        "damage": damage,
        "vision_score": vision_score,
        "kill_participation": kill_participation,
        "damage_to_objectives": damage_to_objectives,
        "duration_sec": duration_sec,
    }


def _many_wins(n: int, deaths: int = 3, cs: int = 220) -> list[dict]:
    return [_match("WIN", deaths=deaths, cs=cs) for _ in range(n)]


def _many_losses(n: int, deaths: int = 7, cs: int = 160) -> list[dict]:
    return [_match("LOSS", deaths=deaths, cs=cs) for _ in range(n)]


# ── TestSafeFloat ─────────────────────────────────────────────────────────────

class TestSafeFloat:
    def test_int(self):
        assert _safe_float(5) == 5.0

    def test_float(self):
        assert _safe_float(3.14) == pytest.approx(3.14)

    def test_none(self):
        assert _safe_float(None) is None

    def test_string_numeric(self):
        assert _safe_float("7.5") == pytest.approx(7.5)

    def test_string_invalid(self):
        assert _safe_float("abc") is None

    def test_zero(self):
        assert _safe_float(0) == 0.0


# ── TestExtract ───────────────────────────────────────────────────────────────

class TestExtract:
    def test_deaths_direct(self):
        matches = [_match(deaths=2), _match(deaths=5)]
        vals = _extract(matches, "deaths")
        assert vals == pytest.approx([2.0, 5.0])

    def test_cs_pm(self):
        m = _match(cs=180, duration_sec=1800)  # 180/30min = 6 cs/min
        vals = _extract([m], "cs_pm")
        assert vals == pytest.approx([6.0])

    def test_damage_pm(self):
        m = _match(damage=36000, duration_sec=1800)  # 36000/30 = 1200 dmg/min
        vals = _extract([m], "damage_pm")
        assert vals == pytest.approx([1200.0])

    def test_vision_pm(self):
        m = _match(vision_score=30, duration_sec=1800)  # 30/30 = 1.0
        vals = _extract([m], "vision_pm")
        assert vals == pytest.approx([1.0])

    def test_obj_pm(self):
        m = _match(damage_to_objectives=9000, duration_sec=1800)  # 300/min
        vals = _extract([m], "obj_pm")
        assert vals == pytest.approx([300.0])

    def test_kill_participation_direct(self):
        m = _match(kill_participation=0.70)
        vals = _extract([m], "kill_participation")
        assert vals == pytest.approx([0.70])

    def test_missing_field_returns_empty(self):
        m = {"result": "WIN"}  # sin duration_sec ni cs
        vals = _extract([m], "cs_pm")
        assert vals == []

    def test_short_duration_skipped(self):
        m = _match(cs=100, duration_sec=50)  # <60s debe ignorarse
        vals = _extract([m], "cs_pm")
        assert vals == []

    def test_none_field_skipped(self):
        m = _match()
        m["deaths"] = None
        vals = _extract([m], "deaths")
        assert vals == []


# ── TestConfidence ────────────────────────────────────────────────────────────

class TestConfidence:
    def test_low_not_enough_wins(self):
        assert _confidence(2, 10) == "low"

    def test_low_not_enough_losses(self):
        assert _confidence(10, 2) == "low"

    def test_medium(self):
        assert _confidence(4, 4) == "medium"

    def test_medium_boundary(self):
        assert _confidence(5, 5) == "medium"

    def test_high(self):
        assert _confidence(6, 6) == "high"

    def test_high_asymmetric(self):
        assert _confidence(10, 6) == "high"


# ── TestEvidenceText ──────────────────────────────────────────────────────────

class TestEvidenceText:
    def _call(self, key, win, loss, lower=False, nw=5, nl=5):
        return _evidence_text(key, key, "unit", win, loss, lower, nw, nl)

    def test_deaths_contains_numbers(self):
        text = self._call("deaths", 3.0, 6.0, lower=True)
        assert "3.0" in text and "6.0" in text

    def test_deaths_mentions_victorias_derrotas(self):
        text = self._call("deaths", 3.0, 6.0, lower=True)
        assert "victorias" in text.lower() and "derrotas" in text.lower()

    def test_cs_pm_contains_values(self):
        text = self._call("cs_pm", 7.0, 5.0)
        assert "7.0" in text and "5.0" in text

    def test_kill_participation_percent_format(self):
        text = self._call("kill_participation", 0.70, 0.50)
        assert "70%" in text or "70" in text

    def test_damage_pm_integer_format(self):
        text = self._call("damage_pm", 1200.0, 900.0)
        assert "1200" in text

    def test_vision_pm_decimal_format(self):
        text = self._call("vision_pm", 1.2, 0.8)
        assert "1.2" in text and "0.8" in text

    def test_obj_pm_text(self):
        text = self._call("obj_pm", 400.0, 200.0)
        assert "400" in text

    def test_generic_fallback(self):
        text = self._call("unknown_metric", 5.0, 3.0)
        assert "5.00" in text


# ── TestRecommendationText ────────────────────────────────────────────────────

class TestRecommendationText:
    def _call(self, key, current, target):
        return _recommendation_text(key, "unit", current, target, key)

    def test_deaths_mentions_10_partidas(self):
        text = self._call("deaths", 6.0, 3.0)
        assert "10 partidas" in text and "3.0" in text and "6.0" in text

    def test_cs_pm_values(self):
        text = self._call("cs_pm", 5.1, 7.8)
        assert "7.8" in text and "5.1" in text

    def test_kp_percent(self):
        text = self._call("kill_participation", 0.50, 0.70)
        assert "70%" in text or "70" in text

    def test_damage_pm_integer(self):
        text = self._call("damage_pm", 800.0, 1200.0)
        assert "1200" in text

    def test_vision_pm_decimal(self):
        text = self._call("vision_pm", 0.7, 1.2)
        assert "1.2" in text

    def test_generic_fallback(self):
        text = self._call("unknown", 5.0, 8.0)
        assert "8.00" in text


# ── TestComputePriorities ─────────────────────────────────────────────────────

class TestComputePriorities:
    def _make_matches(self):
        """Dataset con diferencias claras wins vs losses."""
        wins   = _many_wins(6,   deaths=3, cs=220)
        losses = _many_losses(6, deaths=7, cs=160)
        return wins + losses

    def test_returns_list(self):
        result = compute_priorities(self._make_matches(), "ADC")
        assert isinstance(result, list)

    def test_not_empty_with_sufficient_data(self):
        result = compute_priorities(self._make_matches(), "ADC")
        assert len(result) > 0

    def test_all_items_are_priority(self):
        result = compute_priorities(self._make_matches(), "ADC")
        for p in result:
            assert isinstance(p, Priority)

    def test_sorted_by_impact_desc(self):
        result = compute_priorities(self._make_matches(), "ADC")
        impacts = [p.impact_score for p in result]
        assert impacts == sorted(impacts, reverse=True)

    def test_max_5_priorities(self):
        result = compute_priorities(self._make_matches() * 3, "ADC")
        assert len(result) <= 5

    def test_impact_score_in_range(self):
        result = compute_priorities(self._make_matches(), "ADC")
        for p in result:
            assert 1 <= p.impact_score <= 20

    def test_evidence_is_non_empty_string(self):
        result = compute_priorities(self._make_matches(), "ADC")
        for p in result:
            assert isinstance(p.evidence, str) and len(p.evidence) > 10

    def test_recommendation_is_non_empty(self):
        result = compute_priorities(self._make_matches(), "ADC")
        for p in result:
            assert isinstance(p.recommendation, str) and len(p.recommendation) > 10

    def test_deaths_is_highest_when_deaths_gap_large(self):
        wins   = [_match("WIN", deaths=2, cs=210) for _ in range(8)]
        losses = [_match("LOSS", deaths=9, cs=190) for _ in range(8)]
        result = compute_priorities(wins + losses, "ADC")
        assert result[0].metric_key == "deaths"

    def test_too_few_wins_returns_empty(self):
        matches = _many_wins(2) + _many_losses(10)
        result = compute_priorities(matches, "ADC")
        assert result == []

    def test_too_few_losses_returns_empty(self):
        matches = _many_wins(10) + _many_losses(1)
        result = compute_priorities(matches, "ADC")
        assert result == []

    def test_empty_matches_returns_empty(self):
        result = compute_priorities([], "ADC")
        assert result == []

    def test_top_role_uses_top_metrics(self):
        wins   = [_match("WIN",  deaths=2, cs=180, damage_to_objectives=12000) for _ in range(7)]
        losses = [_match("LOSS", deaths=8, cs=130, damage_to_objectives=2000)  for _ in range(7)]
        result = compute_priorities(wins + losses, "TOP")
        keys = [p.metric_key for p in result]
        # TOP tiene obj_pm en lugar de kill_participation
        assert "kill_participation" not in keys

    def test_no_gap_metric_excluded(self):
        """Si wins y losses tienen el mismo CS, no debe aparecer cs_pm."""
        wins   = [_match("WIN",  deaths=3, cs=200) for _ in range(8)]
        losses = [_match("LOSS", deaths=8, cs=200) for _ in range(8)]  # mismo CS
        result = compute_priorities(wins + losses, "ADC")
        keys = [p.metric_key for p in result]
        assert "cs_pm" not in keys

    def test_metric_already_at_win_level_excluded(self):
        """Si el jugador ya tiene el mismo CS que en victorias, no es prioridad."""
        # cs idéntico en wins y losses → sin gap → excluido
        wins   = [_match("WIN",  deaths=3, cs=200) for _ in range(8)]
        losses = [_match("LOSS", deaths=8, cs=199) for _ in range(8)]  # 0.5% gap < 7%
        result = compute_priorities(wins + losses, "ADC")
        keys = [p.metric_key for p in result]
        assert "cs_pm" not in keys

    def test_confidence_field_set(self):
        matches = self._make_matches()
        result  = compute_priorities(matches, "ADC")
        for p in result:
            assert p.confidence in ("medium", "high")

    def test_current_value_is_float(self):
        result = compute_priorities(self._make_matches(), "ADC")
        for p in result:
            assert isinstance(p.current_value, float)

    def test_target_value_is_float(self):
        result = compute_priorities(self._make_matches(), "ADC")
        for p in result:
            assert isinstance(p.target_value, float)

    def test_target_better_than_current_for_deaths(self):
        wins   = [_match("WIN",  deaths=3) for _ in range(8)]
        losses = [_match("LOSS", deaths=8) for _ in range(8)]
        result = compute_priorities(wins + losses, "ADC")
        deaths_p = next((p for p in result if p.metric_key == "deaths"), None)
        if deaths_p:
            assert deaths_p.target_value < deaths_p.current_value

    def test_target_better_than_current_for_cs_pm(self):
        wins   = [_match("WIN",  cs=220, deaths=4) for _ in range(8)]
        losses = [_match("LOSS", cs=150, deaths=4) for _ in range(8)]
        result = compute_priorities(wins + losses, "ADC")
        cs_p = next((p for p in result if p.metric_key == "cs_pm"), None)
        if cs_p:
            assert cs_p.target_value > cs_p.current_value
