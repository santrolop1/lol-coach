"""
tests/test_matchup_intelligence.py — Tests para Matchup Intelligence (Sprint 10).

Cubre:
  - matchup_models.py        (MatchupRecord propiedades)
  - matchup_repository.py    (extracción de enemigo desde raw JSON)
  - matchup_analyzer.py      (agrupación, métricas, patrones, best/worst)
  - ban_advisor.py           (recomendación de ban)

Cobertura objetivo: ≥80%.
No usa mocks de disco — usa archivos temporales reales.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Imports bajo prueba ───────────────────────────────────────────────────────

from backend.services.matchup_models import (
    BanRecommendation,
    MatchupPattern,
    MatchupRecord,
    MatchupResult,
)
from backend.services.ban_advisor import recommend_ban, _build_reasons
from backend.services.matchup_analyzer import (
    _aggregate_by_enemy,
    _confidence,
    _cs_pm,
    _dmg_pm,
    _detect_patterns,
    _trend_from_scores,
    analyze_matchups,
)


# ── Helpers de fixtures ───────────────────────────────────────────────────────

def _match(
    match_id: str = "LA1_001",
    puuid:    str = "player-puuid",
    champion: str = "Jinx",
    result:   str = "WIN",
    deaths:   int = 3,
    cs:       int = 200,
    damage:   int = 25000,
    duration: int = 1800,
    enemy:    str | None = None,
) -> dict:
    m = {
        "match_id":     match_id,
        "puuid":        puuid,
        "champion":     champion,
        "role":         "ADC",
        "result":       result,
        "deaths":       deaths,
        "cs":           cs,
        "damage":       damage,
        "duration_sec": duration,
        "kill_participation": 0.60,
        "vision_score": 22,
    }
    if enemy:
        m["enemy_champion"] = enemy
    return m


def _record(
    enemy:         str = "Draven",
    games:         int = 5,
    wins:          int = 1,
    avg_deaths:    float = 6.0,
    avg_cs_min:    float = 5.0,
    avg_damage_min: float = 800.0,
    overall_deaths: float = 4.0,
    overall_cs:    float = 7.0,
    overall_dmg:   float = 1000.0,
) -> MatchupRecord:
    return MatchupRecord(
        champion        = "ALL",
        enemy           = enemy,
        role            = "ADC",
        games           = games,
        wins            = wins,
        losses          = games - wins,
        winrate         = wins / games,
        avg_score       = None,
        avg_deaths      = avg_deaths,
        avg_cs_min      = avg_cs_min,
        avg_damage_min  = avg_damage_min,
        trend           = "stable",
        confidence      = "medium",
        overall_avg_deaths     = overall_deaths,
        overall_avg_cs_min     = overall_cs,
        overall_avg_damage_min = overall_dmg,
    )


# ── TestMatchupRecord ─────────────────────────────────────────────────────────

class TestMatchupRecord:
    def test_deaths_delta_pct_positive(self):
        r = _record(avg_deaths=6.0, overall_deaths=4.0)
        assert r.deaths_delta_pct == pytest.approx(50.0)

    def test_deaths_delta_pct_negative(self):
        r = _record(avg_deaths=3.0, overall_deaths=4.0)
        assert r.deaths_delta_pct == pytest.approx(-25.0)

    def test_cs_delta_pct_negative(self):
        r = _record(avg_cs_min=5.0, overall_cs=7.0)
        expected = (5.0 - 7.0) / 7.0 * 100
        assert r.cs_delta_pct == pytest.approx(expected)

    def test_damage_delta_pct_equal_to_overall(self):
        r = _record(avg_damage_min=1000.0, overall_dmg=1000.0)
        assert r.damage_delta_pct == pytest.approx(0.0)

    def test_winrate_computed(self):
        r = _record(games=10, wins=7)
        assert r.winrate == pytest.approx(0.70)

    def test_losses_computed(self):
        r = _record(games=10, wins=3)
        assert r.losses == 7


# ── TestHelpers ───────────────────────────────────────────────────────────────

class TestHelpers:
    def test_cs_pm_basic(self):
        m = _match(cs=180, duration=1800)
        assert _cs_pm(m) == pytest.approx(6.0)

    def test_cs_pm_short_duration_returns_none(self):
        m = _match(cs=100, duration=30)
        assert _cs_pm(m) is None

    def test_cs_pm_none_field(self):
        m = _match()
        m["cs"] = None
        assert _cs_pm(m) is None

    def test_dmg_pm_basic(self):
        m = _match(damage=30000, duration=1800)
        assert _dmg_pm(m) == pytest.approx(1000.0)

    def test_dmg_pm_none(self):
        m = _match()
        m["damage"] = None
        assert _dmg_pm(m) is None

    def test_confidence_low(self):
        assert _confidence(1) == "low"

    def test_confidence_medium(self):
        assert _confidence(4) == "medium"
        assert _confidence(7) == "medium"

    def test_confidence_high(self):
        assert _confidence(8) == "high"

    def test_trend_insufficient(self):
        assert _trend_from_scores([70, 60, 65]) == "insufficient"

    def test_trend_improving(self):
        # scores[0] es más reciente; si reciente > antigua → improving
        scores = [80, 75, 50, 45]  # reciente=77.5, antigua=47.5
        assert _trend_from_scores(scores) == "improving"

    def test_trend_declining(self):
        scores = [45, 40, 75, 80]  # reciente=42.5, antigua=77.5
        assert _trend_from_scores(scores) == "declining"

    def test_trend_stable(self):
        scores = [60, 62, 58, 61]
        assert _trend_from_scores(scores) == "stable"


# ── TestAggregateByEnemy ──────────────────────────────────────────────────────

class TestAggregateByEnemy:
    def _overall(self):
        return {"role": "ADC", "avg_deaths": 4.0, "avg_cs_min": 7.0, "avg_damage_min": 1000.0}

    def test_groups_by_enemy(self):
        matches = [
            _match("m1", enemy="Draven", result="WIN"),
            _match("m2", enemy="Draven", result="LOSS"),
            _match("m3", enemy="Caitlyn", result="WIN"),
        ]
        records = _aggregate_by_enemy(matches, self._overall())
        enemies = {r.enemy for r in records}
        assert "Draven" in enemies and "Caitlyn" in enemies

    def test_counts_wins_losses(self):
        matches = [
            _match("m1", enemy="Draven", result="WIN"),
            _match("m2", enemy="Draven", result="LOSS"),
            _match("m3", enemy="Draven", result="LOSS"),
        ]
        records = _aggregate_by_enemy(matches, self._overall())
        draven = next(r for r in records if r.enemy == "Draven")
        assert draven.wins   == 1
        assert draven.losses == 2
        assert draven.games  == 3

    def test_winrate_correct(self):
        matches = [_match(f"m{i}", enemy="Jhin", result="WIN") for i in range(3)]
        records = _aggregate_by_enemy(matches, self._overall())
        jhin = next(r for r in records if r.enemy == "Jhin")
        assert jhin.winrate == pytest.approx(1.0)

    def test_skips_matches_without_enemy(self):
        matches = [_match("m1"), _match("m2", enemy="Draven")]
        records = _aggregate_by_enemy(matches, self._overall())
        assert len(records) == 1
        assert records[0].enemy == "Draven"

    def test_avg_deaths_calculated(self):
        matches = [
            _match("m1", enemy="Draven", deaths=4, duration=1800),
            _match("m2", enemy="Draven", deaths=6, duration=1800),
        ]
        records = _aggregate_by_enemy(matches, self._overall())
        draven = next(r for r in records if r.enemy == "Draven")
        assert draven.avg_deaths == pytest.approx(5.0)

    def test_avg_cs_min_calculated(self):
        matches = [
            _match("m1", enemy="Draven", cs=180, duration=1800),
            _match("m2", enemy="Draven", cs=120, duration=1800),
        ]
        records = _aggregate_by_enemy(matches, self._overall())
        draven = next(r for r in records if r.enemy == "Draven")
        assert draven.avg_cs_min == pytest.approx(5.0)

    def test_empty_matches_returns_empty(self):
        assert _aggregate_by_enemy([], self._overall()) == []


# ── TestDetectPatterns ────────────────────────────────────────────────────────

class TestDetectPatterns:
    def test_deaths_spike_detected(self):
        r = _record(enemy="Draven", games=4, avg_deaths=6.5, overall_deaths=4.0)
        patterns = _detect_patterns([r])
        death_ps = [p for p in patterns if p.pattern_type == "deaths_spike"]
        assert len(death_ps) == 1

    def test_deaths_spike_not_detected_small_gap(self):
        r = _record(enemy="Draven", games=4, avg_deaths=4.2, overall_deaths=4.0)
        patterns = _detect_patterns([r])
        death_ps = [p for p in patterns if p.pattern_type == "deaths_spike"]
        assert len(death_ps) == 0

    def test_cs_drop_detected(self):
        r = _record(enemy="Caitlyn", games=4, avg_cs_min=4.5, overall_cs=7.0)
        patterns = _detect_patterns([r])
        cs_ps = [p for p in patterns if p.pattern_type == "cs_drop"]
        assert len(cs_ps) == 1

    def test_damage_drop_detected(self):
        r = _record(enemy="MissFortune", games=4, avg_damage_min=600.0, overall_dmg=1000.0)
        patterns = _detect_patterns([r])
        dmg_ps = [p for p in patterns if p.pattern_type == "damage_drop"]
        assert len(dmg_ps) == 1

    def test_critical_severity_deaths(self):
        # +50% muertes → crítico
        r = _record(enemy="Draven", games=4, avg_deaths=7.0, overall_deaths=4.0)
        patterns = _detect_patterns([r])
        death_p = next((p for p in patterns if p.pattern_type == "deaths_spike"), None)
        assert death_p is not None and death_p.severity == "critical"

    def test_warning_severity_deaths(self):
        # +25% → warning (no llega a +35%)
        r = _record(enemy="Draven", games=4, avg_deaths=5.0, overall_deaths=4.0)
        patterns = _detect_patterns([r])
        death_p = next((p for p in patterns if p.pattern_type == "deaths_spike"), None)
        assert death_p is not None and death_p.severity == "warning"

    def test_skips_records_with_few_games(self):
        r = _record(enemy="Draven", games=2, avg_deaths=8.0, overall_deaths=4.0)
        patterns = _detect_patterns([r])
        assert patterns == []

    def test_description_contains_enemy_name(self):
        r = _record(enemy="Draven", games=4, avg_deaths=6.0, overall_deaths=4.0)
        patterns = _detect_patterns([r])
        death_p = next(p for p in patterns if p.pattern_type == "deaths_spike")
        assert "Draven" in death_p.description


# ── TestBanAdvisor ────────────────────────────────────────────────────────────

class TestBanAdvisor:
    def test_returns_none_for_empty(self):
        assert recommend_ban([]) is None

    def test_returns_ban_recommendation(self):
        r = _record(enemy="Draven", games=5, wins=1)
        result = recommend_ban([r])
        assert isinstance(result, BanRecommendation)

    def test_worst_winrate_selected(self):
        good = _record(enemy="Jhin",   games=5, wins=4)
        bad  = _record(enemy="Draven", games=5, wins=1)
        result = recommend_ban([good, bad])
        assert result.enemy == "Draven"

    def test_ban_score_in_range(self):
        r = _record(enemy="Draven", games=5, wins=1)
        result = recommend_ban([r])
        assert 0 <= result.ban_score <= 100

    def test_reasons_not_empty(self):
        r = _record(enemy="Draven", games=5, wins=1, avg_deaths=7.0, overall_deaths=4.0)
        result = recommend_ban([r])
        assert len(result.reasons) >= 1

    def test_reasons_mention_winrate(self):
        r = _record(enemy="Draven", games=5, wins=1)
        result = recommend_ban([r])
        assert any("20%" in reason or "Draven" in reason for reason in result.reasons)

    def test_confidence_high_with_many_games(self):
        r = _record(enemy="Draven", games=10, wins=2)
        result = recommend_ban([r])
        assert result.confidence == "high"

    def test_confidence_medium_mid_games(self):
        r = _record(enemy="Draven", games=5, wins=1)
        result = recommend_ban([r])
        assert result.confidence == "medium"

    def test_deaths_spike_adds_reason(self):
        r = _record(enemy="Draven", games=5, wins=1, avg_deaths=7.0, overall_deaths=4.0)
        reasons = _build_reasons(r)
        has_death_reason = any("muer" in rr.lower() for rr in reasons)
        assert has_death_reason

    def test_cs_drop_adds_reason(self):
        r = _record(enemy="Draven", games=5, wins=1, avg_cs_min=4.0, overall_cs=7.0)
        reasons = _build_reasons(r)
        has_cs_reason = any("farm" in rr.lower() or "cs" in rr.lower() for rr in reasons)
        assert has_cs_reason

    def test_reasons_capped_at_3(self):
        r = _record(enemy="Draven", games=5, wins=1, avg_deaths=7.0, avg_cs_min=3.0,
                    overall_deaths=4.0, overall_cs=7.0)
        reasons = _build_reasons(r)
        assert len(reasons) <= 3


# ── TestAnalyzeMatchups ───────────────────────────────────────────────────────

class TestAnalyzeMatchups:
    def _matches_with_enemies(self):
        """8 partidas con enemy_champion ya inyectado (sin leer disco)."""
        base = [
            _match("m1", enemy="Draven", result="LOSS", deaths=7),
            _match("m2", enemy="Draven", result="LOSS", deaths=8),
            _match("m3", enemy="Draven", result="LOSS", deaths=6),
            _match("m4", enemy="Caitlyn", result="WIN",  deaths=2),
            _match("m5", enemy="Caitlyn", result="WIN",  deaths=3),
            _match("m6", enemy="Caitlyn", result="WIN",  deaths=2),
            _match("m7", enemy="Jhin",    result="WIN",  deaths=3),
            _match("m8", enemy="Jhin",    result="LOSS", deaths=5),
        ]
        return base

    def test_returns_matchup_result(self, tmp_path, monkeypatch):
        matches = self._matches_with_enemies()
        # Patch RAW_DIR para que no haya JSONs raw (matches ya tienen enemy_champion)
        import backend.services.matchup_repository as repo
        monkeypatch.setattr(repo, "_RAW_DIR", tmp_path)
        result = analyze_matchups(matches, "ADC")
        assert isinstance(result, MatchupResult)

    def test_best_and_worst_populated(self, tmp_path, monkeypatch):
        import backend.services.matchup_repository as repo
        monkeypatch.setattr(repo, "_RAW_DIR", tmp_path)
        result = analyze_matchups(self._matches_with_enemies(), "ADC")
        assert len(result.best)  > 0
        assert len(result.worst) > 0

    def test_draven_in_worst(self, tmp_path, monkeypatch):
        import backend.services.matchup_repository as repo
        monkeypatch.setattr(repo, "_RAW_DIR", tmp_path)
        result = analyze_matchups(self._matches_with_enemies(), "ADC")
        worst_enemies = [r.enemy for r in result.worst]
        assert "Draven" in worst_enemies

    def test_caitlyn_in_best(self, tmp_path, monkeypatch):
        import backend.services.matchup_repository as repo
        monkeypatch.setattr(repo, "_RAW_DIR", tmp_path)
        result = analyze_matchups(self._matches_with_enemies(), "ADC")
        best_enemies = [r.enemy for r in result.best]
        assert "Caitlyn" in best_enemies

    def test_ban_is_draven(self, tmp_path, monkeypatch):
        import backend.services.matchup_repository as repo
        monkeypatch.setattr(repo, "_RAW_DIR", tmp_path)
        result = analyze_matchups(self._matches_with_enemies(), "ADC")
        assert result.ban is not None
        assert result.ban.enemy == "Draven"

    def test_empty_matches_returns_empty_result(self, tmp_path, monkeypatch):
        import backend.services.matchup_repository as repo
        monkeypatch.setattr(repo, "_RAW_DIR", tmp_path)
        result = analyze_matchups([], "ADC")
        assert result.all_matchups == []
        assert result.ban is None

    def test_role_preserved(self, tmp_path, monkeypatch):
        import backend.services.matchup_repository as repo
        monkeypatch.setattr(repo, "_RAW_DIR", tmp_path)
        result = analyze_matchups(self._matches_with_enemies(), "ADC")
        assert result.role == "ADC"

    def test_total_matches_count(self, tmp_path, monkeypatch):
        import backend.services.matchup_repository as repo
        monkeypatch.setattr(repo, "_RAW_DIR", tmp_path)
        matches = self._matches_with_enemies()
        result  = analyze_matchups(matches, "ADC")
        assert result.total_matches == len(matches)

    def test_all_matchups_sorted_by_games_desc(self, tmp_path, monkeypatch):
        import backend.services.matchup_repository as repo
        monkeypatch.setattr(repo, "_RAW_DIR", tmp_path)
        result = analyze_matchups(self._matches_with_enemies(), "ADC")
        games = [r.games for r in result.all_matchups]
        assert games == sorted(games, reverse=True)

    def test_patterns_list(self, tmp_path, monkeypatch):
        import backend.services.matchup_repository as repo
        monkeypatch.setattr(repo, "_RAW_DIR", tmp_path)
        result = analyze_matchups(self._matches_with_enemies(), "ADC")
        assert isinstance(result.patterns, list)


# ── TestMatchupRepository ─────────────────────────────────────────────────────

class TestMatchupRepository:
    """Tests de extracción desde raw JSONs (usando archivos temporales reales)."""

    def _raw_json(self, puuid: str, player_champ: str, enemy_champ: str,
                  player_team: int = 100) -> dict:
        """Genera un raw JSON mínimo con 2 participantes BOTTOM."""
        enemy_team = 200 if player_team == 100 else 100
        return {
            "metadata": {"matchId": "LA1_TEST"},
            "info": {
                "gameDuration": 1800,
                "participants": [
                    {
                        "puuid":        puuid,
                        "teamId":       player_team,
                        "teamPosition": "BOTTOM",
                        "championName": player_champ,
                        "win":          True,
                    },
                    {
                        "puuid":        "enemy-puuid",
                        "teamId":       enemy_team,
                        "teamPosition": "BOTTOM",
                        "championName": enemy_champ,
                        "win":          False,
                    },
                ],
            },
        }

    def test_finds_enemy_champion(self, tmp_path):
        import backend.services.matchup_repository as repo
        monkeypatch_dir = tmp_path
        # Escribir raw JSON temporal
        raw = self._raw_json("player-puuid", "Jinx", "Draven")
        (monkeypatch_dir / "match_LA1_TEST.json").write_text(
            json.dumps(raw), encoding="utf-8"
        )
        orig = repo._RAW_DIR
        repo._RAW_DIR = monkeypatch_dir
        try:
            matches = [_match("LA1_TEST", puuid="player-puuid")]
            enriched = repo.enrich_with_enemy(matches, "ADC")
            assert enriched[0].get("enemy_champion") == "Draven"
        finally:
            repo._RAW_DIR = orig

    def test_missing_raw_returns_match_without_enemy(self, tmp_path):
        import backend.services.matchup_repository as repo
        orig = repo._RAW_DIR
        repo._RAW_DIR = tmp_path  # directorio vacío
        try:
            matches = [_match("LA1_MISSING", puuid="player-puuid")]
            enriched = repo.enrich_with_enemy(matches, "ADC")
            assert len(enriched) == 1
            assert "enemy_champion" not in enriched[0]
        finally:
            repo._RAW_DIR = orig

    def test_wrong_position_returns_no_enemy(self, tmp_path):
        import backend.services.matchup_repository as repo
        # Partido donde el jugador es TOP, pero pedimos ADC
        raw = {
            "metadata": {"matchId": "LA1_TOP"},
            "info": {
                "participants": [
                    {"puuid": "player-puuid", "teamId": 100, "teamPosition": "TOP",    "championName": "Darius", "win": True},
                    {"puuid": "enemy-puuid",  "teamId": 200, "teamPosition": "BOTTOM", "championName": "Jinx",   "win": False},
                ]
            },
        }
        (tmp_path / "match_LA1_TOP.json").write_text(json.dumps(raw), encoding="utf-8")
        orig = repo._RAW_DIR
        repo._RAW_DIR = tmp_path
        try:
            matches = [_match("LA1_TOP", puuid="player-puuid")]
            enriched = repo.enrich_with_enemy(matches, "ADC")
            assert "enemy_champion" not in enriched[0]
        finally:
            repo._RAW_DIR = orig

    def test_get_raw_coverage(self, tmp_path):
        import backend.services.matchup_repository as repo
        (tmp_path / "match_LA1_001.json").write_text("{}", encoding="utf-8")
        orig = repo._RAW_DIR
        repo._RAW_DIR = tmp_path
        try:
            matches = [_match("LA1_001"), _match("LA1_002")]
            assert repo.get_raw_coverage(matches) == 1
        finally:
            repo._RAW_DIR = orig
