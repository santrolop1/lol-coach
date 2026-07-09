"""Tests de backend/services/champion_analyzer.py."""

import scorer_v2 as sv2
from backend.services.champion_analyzer import (
    analyze_champion_pool, _classify, _pool_grade, _ols_slope, ChampionStats,
)


def _matches_for_champion(champion: str, n: int, result: str = "WIN", role: str = "ADC", **overrides) -> list[dict]:
    out = []
    for i in range(n):
        m = {
            "match_id": f"{champion}-{i}", "puuid": "p1", "champion": champion, "role": role,
            "result": result, "kills": 8, "deaths": 3, "assists": 6, "cs": 200, "damage": 20000,
            "duration_sec": 1800, "played_at": f"2026-01-{i+1:02d}T00:00:00Z",
            "kill_participation": 0.6, "cs_at_10": 70,
        }
        m.update(overrides)
        out.append(m)
    return out


def _stats(champion="X", games=10, winrate=0.5, avg_score=50.0, score_std=5.0) -> ChampionStats:
    return ChampionStats(
        champion=champion, games=games, wins=int(games * winrate), losses=games - int(games * winrate),
        winrate=winrate, avg_score=avg_score, score_std=score_std, avg_deaths=3.0, avg_kda=2.0,
        avg_cs_pm=6.0, avg_kp=0.5, score_trend=0.0, recent_wr=winrate, last_played="2026-01-01",
    )


# ── analyze_champion_pool — casos borde ───────────────────────────────────────

def test_analyze_champion_pool_empty_matches():
    result = analyze_champion_pool([], "ADC")
    assert result.total_games == 0
    assert result.champions == []
    assert result.grade == "F"
    assert result.classification.main is None


def test_analyze_champion_pool_single_champion_qualifies():
    matches = _matches_for_champion("Jinx", 5)
    sr = sv2.analyze_player(matches, "ADC")
    result = analyze_champion_pool(matches, "ADC", sr.match_scores)
    assert result.total_games == 5
    assert result.pool_depth == 1
    assert result.classification.main.champion == "Jinx"


def test_analyze_champion_pool_below_qualify_threshold_excluded_from_classification():
    """1-2 partidas de un campeón: aparece en tabla pero no califica para clasificación."""
    matches = _matches_for_champion("Jinx", 2)
    sr = sv2.analyze_player(matches, "ADC")
    result = analyze_champion_pool(matches, "ADC", sr.match_scores)
    assert len(result.champions) == 1        # tabla: umbral MIN_GAMES_TABLE=2
    assert result.pool_depth == 0             # clasificación: umbral MIN_GAMES_QUALIFY=3
    assert result.classification.main is None


def test_analyze_champion_pool_computes_dependency_pct():
    matches = _matches_for_champion("Jinx", 8) + _matches_for_champion("Ashe", 2)
    sr = sv2.analyze_player(matches, "ADC")
    result = analyze_champion_pool(matches, "ADC", sr.match_scores)
    assert result.dependency_pct == 0.8


# ── _classify ─────────────────────────────────────────────────────────────────

def test_classify_empty_qualified_returns_empty_classification():
    clf = _classify([])
    assert clf.main is None and clf.carry is None and clf.comfort is None and clf.trap == []


def test_classify_main_is_highest_volume():
    stats = [_stats("A", games=20, winrate=0.5), _stats("B", games=5, winrate=0.9)]
    clf = _classify(stats)
    assert clf.main.champion == "A"


def test_classify_trap_flagged_by_low_winrate_regardless_of_score():
    stats = [
        _stats("Main", games=20, winrate=0.5, avg_score=60),
        _stats("Trap", games=5, winrate=0.2, avg_score=60),  # WR bajo -> trap, aunque el score no sea malo
    ]
    clf = _classify(stats)
    trap_names = {t.champion for t in clf.trap}
    assert "Trap" in trap_names


def test_classify_main_can_overlap_with_trap():
    """Cuando el pick más jugado también tiene WR bajo, debe aparecer en AMBOS
    main y trap — ese solapamiento es intencional (es el insight más importante)."""
    stats = [_stats("BadMain", games=20, winrate=0.3, avg_score=40)]
    clf = _classify(stats)
    assert clf.main.champion == "BadMain"
    assert any(t.champion == "BadMain" for t in clf.trap)


def test_classify_second_trap_not_hidden_when_first_equals_main():
    """
    Regresión del bug de UI (ui/coaching.py): si trap[0] coincide con main,
    un segundo trap real en la lista no debe desaparecer. Esto prueba que la
    lista `clf.trap` en sí conserva ambos — la UI es responsable de no
    quedarse solo con el índice 0 (ya corregido).
    """
    stats = [
        _stats("BadMain", games=20, winrate=0.3, avg_score=40),   # main + trap
        _stats("OtroTrap", games=5, winrate=0.15, avg_score=30),  # trap independiente
    ]
    clf = _classify(stats)
    trap_names = {t.champion for t in clf.trap}
    assert "BadMain" in trap_names
    assert "OtroTrap" in trap_names
    assert len(clf.trap) == 2


# ── _pool_grade ────────────────────────────────────────────────────────────────

def test_pool_grade_empty_pool_is_f():
    score, grade = _pool_grade([], [], 0)
    assert grade == "F"
    assert score == 0.0


def test_pool_grade_letter_boundaries():
    # Construimos un pool que maximiza los 4 factores para forzar grade A.
    strong = [_stats(f"C{i}", games=10, winrate=0.9, score_std=0.0, avg_score=90) for i in range(3)]
    score, grade = _pool_grade(strong, strong, total_games=30)
    assert grade in ("A", "B")  # dependencia baja + WR/consistencia altas


# ── _ols_slope ────────────────────────────────────────────────────────────────

def test_ols_slope_zero_with_fewer_than_two_values():
    assert _ols_slope([]) == 0.0
    assert _ols_slope([10.0]) == 0.0


def test_ols_slope_positive_for_improving_trend():
    assert _ols_slope([40.0, 50.0, 60.0, 70.0]) > 0


# ── ChampionStats.consistency_score ────────────────────────────────────────────

def test_consistency_score_zero_when_avg_score_zero():
    s = _stats(avg_score=0.0, score_std=0.0)
    assert s.consistency_score == 0.0


def test_consistency_score_perfect_when_no_variation():
    s = _stats(avg_score=60.0, score_std=0.0)
    assert s.consistency_score == 100.0
