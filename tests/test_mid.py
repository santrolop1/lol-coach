"""
Tests de soporte MID (Sprint 3): parser, scorer_v2, coaching_engine,
champion_analyzer y draft_advisor.

Incluye además tests de no-regresión que verifican que agregar MID no
cambió el comportamiento de ADC y TOP en los puntos de dispatch.
"""

import coaching_engine as ce
import coaching_rules as rules
import scorer_v2 as sv2
from parser import parse_match
from backend.services.champion_analyzer import analyze_champion_pool
from backend.services.draft_advisor import analyze_draft
from lcu.champ_select import parse_session


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mid_match(i: int, **overrides) -> dict:
    """Partida MID sintética con métricas sanas por defecto."""
    m = {
        "match_id": f"MID-{i}", "puuid": "p1", "champion": "Ahri", "role": "MID",
        "result": "WIN" if i % 2 == 0 else "LOSS",
        "kills": 7, "deaths": 3, "assists": 8,
        "cs": 210, "damage": 24000, "duration_sec": 1800,
        "played_at": f"2026-02-{i+1:02d}T00:00:00Z",
        "gold_earned": 12500,
        "cs_at_10": 72,
        "max_cs_advantage": 12,
        "kill_participation": 0.62,
        "team_damage_pct": 0.28,
        "time_spent_dead": 60,
        "longest_time_alive": 900,
        "game_ended_surrender": 0,
    }
    m.update(overrides)
    return m


def _mid_matches(n: int, **overrides) -> list[dict]:
    return [_mid_match(i, **overrides) for i in range(n)]


CHAMPION_MAP = {
    103: {"name": "Ahri",    "alias": "Ahri"},
    134: {"name": "Syndra",  "alias": "Syndra"},
    61:  {"name": "Orianna", "alias": "Orianna"},
    38:  {"name": "Kassadin", "alias": "Kassadin"},
}


def _mid_session(my_champ_id: int, my_bans=None, ally_picks=None) -> dict:
    my_team = [{"cellId": 0, "championId": my_champ_id, "assignedPosition": "middle",
                "spell1Id": 4, "spell2Id": 14}]
    for idx, cid in enumerate(ally_picks or [], start=1):
        my_team.append({"cellId": idx, "championId": cid, "assignedPosition": "", "spell1Id": 0, "spell2Id": 0})
    return {
        "localPlayerCellId": 0,
        "myTeam": my_team,
        "theirTeam": [],
        "bans": {"myTeamBans": my_bans or [], "theirTeamBans": []},
        "timer": {"phase": "BAN_PICK", "timeLeftInPhase": 30000, "totalTimeInPhase": 30000, "isInfinite": False},
        "gameId": 1,
    }


# ── Parser: MIDDLE → MID ─────────────────────────────────────────────────────

def _riot_match_json(team_position: str) -> dict:
    return {
        "metadata": {"matchId": "LA1_1"},
        "info": {
            "gameStartTimestamp": 1700000000000,
            "gameDuration": 1800,
            "participants": [{
                "puuid": "p1", "championName": "Ahri", "teamPosition": team_position,
                "win": True, "kills": 5, "deaths": 2, "assists": 7,
                "totalMinionsKilled": 180, "neutralMinionsKilled": 12,
                "totalDamageDealtToChampions": 22000,
            }],
        },
    }


def test_parser_maps_middle_position_to_mid_role():
    md = parse_match(_riot_match_json("MIDDLE"), "p1")
    assert md is not None
    assert md.role == "MID"


def test_parser_still_maps_bottom_and_top():
    assert parse_match(_riot_match_json("BOTTOM"), "p1").role == "ADC"
    assert parse_match(_riot_match_json("TOP"), "p1").role == "TOP"


def test_parser_jungle_and_utility_remain_other():
    assert parse_match(_riot_match_json("JUNGLE"), "p1").role == "OTHER"
    assert parse_match(_riot_match_json("UTILITY"), "p1").role == "OTHER"


# ── Score MID: dimensiones ────────────────────────────────────────────────────

def test_mid_match_score_has_three_named_dimensions():
    matches = _mid_matches(10)
    ms = sv2.score_match(matches[0], matches)
    assert ms is not None
    assert [d.name for d in ms.dimensions] == ["Lane Dominance", "Damage Impact", "Survival"]
    assert ms.overall_score is not None


def test_mid_supported_in_roles_constant():
    assert "MID" in sv2.SUPPORTED_ROLES
    assert "JGL" not in sv2.SUPPORTED_ROLES


def test_unsupported_role_still_returns_none():
    m = _mid_match(0, role="JGL")
    assert sv2.score_match(m, [m]) is None


def test_mid_percentile_scoring_rewards_better_match():
    """La mejor partida de la muestra debe puntuar por encima de la peor."""
    matches = _mid_matches(10)
    worst = _mid_match(0, cs_at_10=40, gold_earned=8000, damage=12000,
                       deaths=9, kill_participation=0.3, team_damage_pct=0.15,
                       max_cs_advantage=-20)
    best = _mid_match(1, cs_at_10=95, gold_earned=16000, damage=35000,
                      deaths=1, kill_participation=0.85, team_damage_pct=0.40,
                      max_cs_advantage=40)
    ref = matches + [worst, best]
    s_worst = sv2.score_match(worst, ref).overall_score
    s_best  = sv2.score_match(best, ref).overall_score
    assert s_best > s_worst


def test_mid_dimensions_handle_missing_challenge_fields():
    """Campos NULL (partidas antiguas) no deben crashear: se excluyen con nota."""
    matches = _mid_matches(8, cs_at_10=None, max_cs_advantage=None,
                           team_damage_pct=None, kill_participation=None)
    ms = sv2.score_match(matches[0], matches)
    assert ms is not None
    # Lane Dominance sigue teniendo score (queda gold_per_min)
    lane = next(d for d in ms.dimensions if d.name == "Lane Dominance")
    assert lane.score is not None
    assert any("cs_at_10" in n for n in lane.notes)


def test_mid_analyze_player_full_result():
    sr = sv2.analyze_player(_mid_matches(12), "MID")
    assert sr.role == "MID"
    assert sr.sample_size == 12
    assert sr.overall_score is not None
    assert set(sr.dimensions.keys()) == {"Lane Dominance", "Damage Impact", "Survival"}
    assert sr.confidence_level == "reliable"
    assert sr.primary_problem in sr.dimensions


def test_mid_analyze_player_empty_is_safe():
    sr = sv2.analyze_player([], "MID")
    assert sr.sample_size == 0
    assert sr.overall_score is None
    assert sr.confidence_level == "insufficient"


def test_mid_small_sample_limitation_documented():
    sr = sv2.analyze_player(_mid_matches(6), "MID")
    assert any("MID" in lim for lim in sr.limitations)


def test_benchmarks_include_damage_per_min():
    bm = sv2.calculate_benchmarks(_mid_matches(10), "MID")
    assert "damage_per_min" in bm.metrics
    assert bm.metrics["damage_per_min"].n == 10


# ── Coaching MID ──────────────────────────────────────────────────────────────

def _coaching_for(matches: list[dict]):
    sr = sv2.analyze_player(matches, "MID")
    return ce.analyze_coaching(sr, matches, "MID"), sr


def test_mid_no_longer_reports_unsupported_role():
    cr, _ = _coaching_for(_mid_matches(10))
    assert "no implementado" not in cr.primary_problem


def test_jgl_still_reports_unsupported_role():
    matches = [_mid_match(i, role="JGL") for i in range(10)]
    sr = sv2.analyze_player(matches, "JGL")
    cr = ce.analyze_coaching(sr, matches, "JGL")
    assert "no implementado" in cr.primary_problem
    assert "MID" in cr.weekly_goal.description  # el texto ya ofrece MID


def test_mid_high_deaths_detected_with_evidence_and_goal():
    # Promedio 8 muertes (>6 = umbral MID), con menos muertes en victorias
    # para que el target (= promedio en victorias) sea menor que el actual.
    matches = _mid_matches(10, deaths=8)
    for m in matches:
        m["deaths"] = 6 if m["result"] == "WIN" else 10
    cr, _ = _coaching_for(matches)
    assert cr.primary_problem == rules.MID_PROBLEMS["HIGH_DEATHS_MID"]["name"]
    assert "8" in cr.evidence or "8.0" in cr.evidence
    assert cr.weekly_goal.metric == "deaths"
    assert cr.weekly_goal.current > cr.weekly_goal.target
    assert cr.training_plan.primary == rules.MID_PROBLEMS["HIGH_DEATHS_MID"]["primary_action"]


def test_mid_bad_lane_phase_detected():
    matches = _mid_matches(10, cs_at_10=40)
    cr, _ = _coaching_for(matches)
    assert cr.primary_problem == rules.MID_PROBLEMS["BAD_LANE_PHASE"]["name"]
    assert "partidas MID" in cr.evidence
    assert cr.weekly_goal.metric == "cs_at_10"


def test_mid_low_kill_participation_detected():
    matches = _mid_matches(10, kill_participation=0.30)
    cr, _ = _coaching_for(matches)
    assert cr.primary_problem == rules.MID_PROBLEMS["LOW_KILL_PARTICIPATION"]["name"]
    assert "MID" in cr.evidence
    assert cr.weekly_goal.metric == "kill_participation"


def test_mid_low_damage_impact_rule():
    """Regla LOW_DAMAGE_IMPACT: dimensión Damage Impact < 40 dispara el problema."""
    matches = _mid_matches(10)
    sr = sv2.analyze_player(matches, "MID")
    sr.dimensions["Damage Impact"] = 30.0   # forzar la condición de datos
    problems = ce._evaluate_mid_problems(matches, sr.benchmarks, sr)
    keys = {p["key"] for p in problems}
    assert "LOW_DAMAGE_IMPACT" in keys

    p = next(p for p in problems if p["key"] == "LOW_DAMAGE_IMPACT")
    evidence = ce._generate_evidence(p, "MID")
    assert "Damage Impact" in evidence
    goal = ce._generate_weekly_goal(p, "MID")
    assert goal.metric == "damage_per_min"
    assert goal.target >= goal.current


def test_mid_healthy_player_gets_no_critical_problems():
    cr, _ = _coaching_for(_mid_matches(10))
    assert cr.primary_problem == "Sin problemas criticos detectados"


def test_mid_insufficient_sample_message():
    cr, _ = _coaching_for(_mid_matches(3))
    assert cr.confidence_level == "insufficient"
    assert "3" in cr.evidence


def test_mid_strengths_detected_from_data():
    """Con métricas sanas y uniformes, las 3 fortalezas MID deben detectarse."""
    matches = _mid_matches(10)
    sr = sv2.analyze_player(matches, "MID")
    strengths = ce._detect_strengths_mid(matches, sr.benchmarks, sr)
    names = {s.name for s in strengths}
    assert "Alto impacto de daño" in names
    assert len(strengths) <= 3


def test_mid_tilt_session_uses_mid_texts():
    """4 derrotas consecutivas recientes de MID → TILT con regla propia de MID."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    matches = _mid_matches(10)
    for i in range(4):   # las 4 más recientes son derrotas del mismo día
        matches[i]["result"] = "LOSS"
        matches[i]["played_at"] = f"{today}T2{i}:00:00+00:00"
    cr, _ = _coaching_for(matches)
    assert cr.session_warning is not None
    assert cr.primary_problem == rules.MID_PROBLEMS["TILT_SESSION"]["name"]


# ── Champion Intelligence MID ─────────────────────────────────────────────────

def test_mid_champion_pool_classification():
    matches = (
        [_mid_match(i, champion="Ahri", result="WIN") for i in range(6)]
        + [_mid_match(i + 6, champion="Syndra", result="LOSS") for i in range(4)]
    )
    sr = sv2.analyze_player(matches, "MID")
    cpa = analyze_champion_pool(matches, "MID", sr.match_scores)

    assert cpa.role == "MID"
    assert cpa.classification.main is not None
    assert cpa.classification.main.champion == "Ahri"
    trap_names = {t.champion for t in cpa.classification.trap}
    assert "Syndra" in trap_names           # 0% WR en 4 partidas
    assert cpa.grade in ("A", "B", "C", "D", "F")


def test_mid_champion_pool_empty_is_safe():
    cpa = analyze_champion_pool([], "MID")
    assert cpa.total_games == 0
    assert cpa.grade == "F"


# ── Draft Intelligence MID ────────────────────────────────────────────────────

def _mid_cpa(matches: list[dict]):
    sr = sv2.analyze_player(matches, "MID")
    return analyze_champion_pool(matches, "MID", sr.match_scores)


def test_mid_draft_current_pick_scores_with_history():
    session = parse_session(_mid_session(my_champ_id=103), CHAMPION_MAP)  # Ahri
    assert session.my_role == "middle"
    cpa = _mid_cpa([_mid_match(i, champion="Ahri") for i in range(10)])

    advice = analyze_draft(session, cpa)
    assert advice.current_pick_score is not None
    assert advice.current_pick_score.has_data is True
    assert advice.current_pick_score.total > 0


def test_mid_draft_recommendations_generated_and_ranked():
    matches = (
        [_mid_match(i, champion="Ahri", result="WIN") for i in range(8)]
        + [_mid_match(i + 8, champion="Orianna", result="WIN" if i % 2 == 0 else "LOSS") for i in range(6)]
    )
    session = parse_session(_mid_session(my_champ_id=0), CHAMPION_MAP)  # sin pick
    advice = analyze_draft(session, _mid_cpa(matches))

    assert len(advice.recommendations) >= 2
    assert advice.recommendations[0].rank == 1
    ordered = [r.pick_value for r in advice.recommendations]
    assert ordered == sorted(ordered, reverse=True)


def test_mid_draft_banned_champion_excluded():
    matches = [_mid_match(i, champion="Ahri") for i in range(10)]
    session = parse_session(_mid_session(my_champ_id=0, my_bans=[103]), CHAMPION_MAP)
    advice = analyze_draft(session, _mid_cpa(matches))
    names = {r.champion for r in advice.recommendations} | {r.champion for r in advice.avoid}
    assert "Ahri" not in names


def test_mid_draft_trap_pick_flagged_in_avoid():
    matches = [_mid_match(i, champion="Kassadin", result="LOSS") for i in range(5)]
    session = parse_session(_mid_session(my_champ_id=38), CHAMPION_MAP)  # pickeo el trap
    advice = analyze_draft(session, _mid_cpa(matches))
    assert any(a.champion == "Kassadin" for a in advice.avoid)
    assert any(w.level == "critical" for w in advice.warnings)


# ── No-regresión: ADC y TOP intactos tras el dispatch de 3 roles ─────────────

def test_adc_dimensions_unchanged():
    matches = [_mid_match(i, role="ADC") for i in range(8)]
    ms = sv2.score_match(matches[0], matches)
    assert [d.name for d in ms.dimensions] == ["Economy", "Positioning", "Combat Impact"]


def test_top_dimensions_unchanged():
    matches = [_mid_match(i, role="TOP", turret_takedowns=2, damage_to_turrets=4000,
                          damage_to_objectives=6000) for i in range(8)]
    ms = sv2.score_match(matches[0], matches)
    assert [d.name for d in ms.dimensions] == ["Lane Control", "Pressure", "Survival"]


def test_problems_by_role_map_is_complete():
    assert set(rules.PROBLEMS_BY_ROLE.keys()) == {"ADC", "TOP", "MID"}
    assert set(rules.THRESHOLDS.keys()) == {"ADC", "TOP", "MID"}
    # Toda clave de problema MID tiene los campos que la UI y el engine usan
    for key, prob in rules.MID_PROBLEMS.items():
        assert prob.get("name"), key
        assert prob.get("display_name"), key
        assert prob.get("probable_cause"), key
        assert prob.get("impact"), key
        assert prob.get("primary_action"), key
        assert len(prob.get("secondary_actions", [])) >= 2, key
        assert prob.get("goal_template"), key
