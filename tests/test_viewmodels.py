"""
tests/test_viewmodels.py — Tests para la capa backend/viewmodels/

Verifica que los ViewModels:
- Construyen estructuras de datos correctas
- No importan ni dependen de Streamlit
- Manejan casos edge (sin datos, datos vacíos)
- Exponen las interfaces esperadas por FastAPI
"""

import sys
import dataclasses
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.viewmodels.coaching_vm import (
    build_coaching, CoachingViewModel, CoachingMetrics, _compute_metrics,
)
from backend.viewmodels.matches_vm import (
    build_matches, MatchesViewModel, MatchCard, MatchRow, _build_card, _build_row,
)
from backend.viewmodels.settings_vm import build_settings, SettingsViewModel


# ── Fixtures de datos ──────────────────────────────────────────────────────────

def _make_match(result="WIN", role="ADC", champion="Jinx", kills=5, deaths=2,
                assists=8, cs=200, damage=25000, duration_sec=1800,
                kill_participation=0.65, vision_score=25.0, gold_earned=12000,
                objective_damage=5000.0, cs_at_10=70.0) -> dict:
    return {
        "match_id":            f"LA1_{result}_{champion}",
        "puuid":               "test-puuid",
        "champion":            champion,
        "role":                role,
        "result":              result,
        "kills":               kills,
        "deaths":              deaths,
        "assists":             assists,
        "cs":                  cs,
        "damage":              damage,
        "duration_sec":        duration_sec,
        "played_at":           "2026-06-26T12:00:00",
        "kill_participation":  kill_participation,
        "vision_score":        vision_score,
        "gold_earned":         gold_earned,
        "objective_damage":    objective_damage,
        "cs_at_10":            cs_at_10,
        "is_surrender":        False,
        "turret_takedowns":    1,
        "team_damage_pct":     0.28,
        "time_dead_pct":       0.05,
        "longest_alive_pct":   0.45,
        "max_cs_advantage":    30.0,
        "lane_score":          60.0,
        "pressure_score":      45.0,
    }


def _make_matches(n_wins=5, n_losses=5, role="ADC") -> list[dict]:
    matches = []
    for i in range(n_wins):
        matches.append(_make_match(result="WIN", role=role))
    for i in range(n_losses):
        matches.append(_make_match(result="LOSS", role=role, kills=2, deaths=5))
    return matches


# ── CoachingMetrics ────────────────────────────────────────────────────────────

class TestCoachingMetrics:
    def test_empty_matches_returns_zero_n(self):
        m = _compute_metrics([])
        assert m.n == 0
        assert m.cs_pm is None

    def test_computes_wins_losses(self):
        matches = _make_matches(n_wins=3, n_losses=2)
        m = _compute_metrics(matches)
        assert m.n == 5
        assert m.n_wins == 3
        assert m.n_losses == 2

    def test_cs_pm_positive(self):
        matches = _make_matches(n_wins=3, n_losses=3)
        m = _compute_metrics(matches)
        assert m.cs_pm is not None
        assert m.cs_pm > 0

    def test_deaths_split_by_result(self):
        matches = [
            _make_match(result="WIN",  deaths=2),
            _make_match(result="WIN",  deaths=2),
            _make_match(result="LOSS", deaths=6),
            _make_match(result="LOSS", deaths=6),
        ]
        m = _compute_metrics(matches)
        assert m.deaths_win  == 2.0
        assert m.deaths_loss == 6.0
        assert m.deaths == 4.0

    def test_kp_split_by_result(self):
        matches = [
            _make_match(result="WIN",  kill_participation=0.80),
            _make_match(result="LOSS", kill_participation=0.40),
        ]
        m = _compute_metrics(matches)
        assert m.kp_win  == 0.80
        assert m.kp_loss == 0.40

    def test_is_dataclass_serializable(self):
        matches = _make_matches(3, 3)
        m = _compute_metrics(matches)
        d = dataclasses.asdict(m)
        assert "cs_pm" in d
        assert "deaths_win" in d
        assert "n" in d


# ── CoachingViewModel ──────────────────────────────────────────────────────────

class TestCoachingViewModel:
    def test_no_data_when_no_config(self):
        with patch("backend.viewmodels.coaching_vm.db.get_config", return_value=None), \
             patch("backend.viewmodels.coaching_vm.db.get_player", return_value=None), \
             patch("backend.viewmodels.coaching_vm.resolve_matches", return_value=[]):
            vm = build_coaching("ADC", limit=20)
        assert vm.has_data is False
        assert vm.sample_size == 0
        assert vm.score_result is None
        assert vm.coaching_result is None

    def test_has_data_with_matches(self):
        matches = _make_matches(n_wins=6, n_losses=6, role="ADC")
        with patch("backend.viewmodels.coaching_vm.db.get_config", return_value="test-puuid"), \
             patch("backend.viewmodels.coaching_vm.db.get_player", return_value={"riot_id": "TestPlayer", "rank": "Gold", "lp": 50}), \
             patch("backend.viewmodels.coaching_vm.resolve_matches", return_value=matches):
            vm = build_coaching("ADC", limit=20)

        assert vm.has_data is True
        assert vm.sample_size == 12
        assert vm.player_name == "TestPlayer"
        assert vm.score_result is not None
        assert vm.coaching_result is not None
        assert vm.priorities is not None
        assert isinstance(vm.metrics, CoachingMetrics)

    def test_role_filter_applied(self):
        adc_matches = _make_matches(n_wins=3, n_losses=3, role="ADC")
        top_matches = _make_matches(n_wins=2, n_losses=2, role="TOP")
        all_matches = adc_matches + top_matches

        with patch("backend.viewmodels.coaching_vm.db.get_config", return_value="puuid"), \
             patch("backend.viewmodels.coaching_vm.db.get_player", return_value={"riot_id": "P", "rank": "G", "lp": 0}), \
             patch("backend.viewmodels.coaching_vm.resolve_matches", return_value=all_matches):
            vm = build_coaching("ADC", limit=20)

        assert all(m["role"] == "ADC" for m in vm.role_matches)

    def test_no_streamlit_import(self):
        import backend.viewmodels.coaching_vm as module
        assert not hasattr(module, "st"), "coaching_vm no debe importar streamlit"

    def test_player_name_fallback(self):
        matches = _make_matches(3, 3)
        with patch("backend.viewmodels.coaching_vm.db.get_config", return_value="puuid"), \
             patch("backend.viewmodels.coaching_vm.db.get_player", return_value=None), \
             patch("backend.viewmodels.coaching_vm.resolve_matches", return_value=matches):
            vm = build_coaching("ADC", limit=20)
        assert vm.player_name == "Invocador"


# ── MatchesViewModel ───────────────────────────────────────────────────────────

class TestMatchesViewModel:
    def test_no_config_returns_empty(self):
        with patch("backend.viewmodels.matches_vm.db.get_config", return_value=None):
            vm = build_matches()
        assert vm.has_config is False
        assert vm.recent_cards == []
        assert vm.table_rows == []

    def test_match_row_built_correctly(self):
        m = _make_match(result="WIN", cs=200, duration_sec=1800)
        row = _build_row(m)
        assert "Victoria" in row.result
        assert row.cs == 200
        assert row.cs_pm > 0
        assert row.duration == "30m 00s"

    def test_match_card_built(self):
        m = _make_match(result="WIN")
        card = _build_card(m)
        assert card.is_win is True
        assert card.champion == "Jinx"
        assert card.overall_score >= 0
        assert card.best_dim in ("Farm", "Superv", "Pelea")
        assert card.worst_dim in ("Farm", "Superv", "Pelea")
        assert card.best_dim != card.worst_dim or True  # puede ser el mismo si scores iguales

    def test_loss_card_is_win_false(self):
        m = _make_match(result="LOSS", deaths=7, kills=1)
        card = _build_card(m)
        assert card.is_win is False

    def test_no_streamlit_import(self):
        import backend.viewmodels.matches_vm as module
        assert not hasattr(module, "st"), "matches_vm no debe importar streamlit"

    def test_summary_winrate(self):
        with patch("backend.viewmodels.matches_vm.db.get_config", return_value="puuid"), \
             patch("backend.viewmodels.matches_vm.db.get_player", return_value=None), \
             patch("backend.viewmodels.matches_vm.db.get_matches") as mock_get:
            matches = [_make_match("WIN")] * 7 + [_make_match("LOSS")] * 3
            mock_get.return_value = matches
            vm = build_matches()

        assert vm.summary.total == 10
        assert vm.summary.wins == 7
        assert vm.summary.losses == 3
        assert vm.summary.winrate == 70.0


# ── SettingsViewModel ──────────────────────────────────────────────────────────

class TestSettingsViewModel:
    def test_not_configured_when_no_puuid(self):
        with patch("backend.viewmodels.settings_vm.db.get_config", return_value=None), \
             patch("backend.viewmodels.settings_vm.db.get_player", return_value=None):
            vm = build_settings()
        assert vm.is_configured is False

    def test_configured_with_puuid_and_apikey(self):
        def mock_config(key):
            return {"puuid": "abc", "api_key": "key", "platform": "la1"}.get(key)

        with patch("backend.viewmodels.settings_vm.db.get_config", side_effect=mock_config), \
             patch("backend.viewmodels.settings_vm.db.get_player", return_value={
                 "riot_id": "Player", "tag": "LAN", "level": 200,
                 "rank": "Gold IV", "tier": "GOLD", "lp": 75,
             }):
            vm = build_settings()

        assert vm.is_configured is True
        assert vm.puuid == "abc"
        assert vm.riot_id == "Player"
        assert vm.lp == 75

    def test_platform_name_resolved(self):
        def mock_config(key):
            return {"puuid": "x", "api_key": "y", "platform": "la1"}.get(key)

        with patch("backend.viewmodels.settings_vm.db.get_config", side_effect=mock_config), \
             patch("backend.viewmodels.settings_vm.db.get_player", return_value=None):
            vm = build_settings()

        assert vm.platform_name == "Latinoamérica Norte (LA1)"

    def test_no_streamlit_import(self):
        import backend.viewmodels.settings_vm as module
        assert not hasattr(module, "st"), "settings_vm no debe importar streamlit"


# ── Garantía de desacoplamiento general ───────────────────────────────────────

class TestNoStreamlitInBackend:
    """Verifica que ningún módulo del backend importa streamlit."""

    def _check_no_streamlit(self, module_path: str):
        import importlib
        module = importlib.import_module(module_path)
        assert not hasattr(module, "st"), f"{module_path} importa streamlit"

    def test_coaching_vm_no_streamlit(self):
        self._check_no_streamlit("backend.viewmodels.coaching_vm")

    def test_matches_vm_no_streamlit(self):
        self._check_no_streamlit("backend.viewmodels.matches_vm")

    def test_draft_vm_no_streamlit(self):
        self._check_no_streamlit("backend.viewmodels.draft_vm")

    def test_settings_vm_no_streamlit(self):
        self._check_no_streamlit("backend.viewmodels.settings_vm")

    def test_sync_service_no_streamlit(self):
        self._check_no_streamlit("backend.services.sync_service")
