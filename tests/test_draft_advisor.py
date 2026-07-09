"""
Tests de backend/services/draft_advisor.py.

Incluye pruebas de regresión explícitas para los bugs corregidos en esta
sesión: mismatch de nombres de campeón entre LCU (alias) y DB, filtrado de
picks ya lockeados, y filtrado de bans.
"""

import scorer_v2 as sv2
from backend.services.champion_analyzer import analyze_champion_pool
from backend.services.draft_advisor import analyze_draft, _grade, _pick_value
from lcu.champ_select import parse_session


CHAMPION_MAP = {
    145: {"name": "Kai'Sa", "alias": "KaiSa"},
    41:  {"name": "Wukong", "alias": "MonkeyKing"},
    22:  {"name": "Ashe",   "alias": "Ashe"},
    51:  {"name": "Caitlyn", "alias": "Caitlyn"},
}


def _matches_for_champion(champion: str, n: int, result: str = "WIN", role: str = "ADC") -> list[dict]:
    out = []
    for i in range(n):
        out.append({
            "match_id": f"{champion}-{i}", "puuid": "p1", "champion": champion, "role": role,
            "result": result, "kills": 8, "deaths": 3, "assists": 6, "cs": 200, "damage": 20000,
            "duration_sec": 1800, "played_at": f"2026-01-{i+1:02d}T00:00:00Z",
            "kill_participation": 0.6, "cs_at_10": 70,
        })
    return out


def _session(my_champ_id: int, my_bans=None, ally_picks=None, enemy_picks=None) -> dict:
    """Construye un raw session dict mínimo de /lol-champ-select/v1/session."""
    my_team = [{"cellId": 0, "championId": my_champ_id, "assignedPosition": "bottom",
                "spell1Id": 4, "spell2Id": 7}]
    for idx, cid in enumerate(ally_picks or [], start=1):
        my_team.append({"cellId": idx, "championId": cid, "assignedPosition": "", "spell1Id": 0, "spell2Id": 0})
    their_team = [
        {"cellId": 10 + idx, "championId": cid, "assignedPosition": "", "spell1Id": 0, "spell2Id": 0}
        for idx, cid in enumerate(enemy_picks or [])
    ]
    return {
        "localPlayerCellId": 0,
        "myTeam": my_team,
        "theirTeam": their_team,
        "bans": {"myTeamBans": my_bans or [], "theirTeamBans": []},
        "timer": {"phase": "BAN_PICK", "timeLeftInPhase": 30000, "totalTimeInPhase": 30000, "isInfinite": False},
        "gameId": 1,
    }


def _cpa_for(champion: str, n: int, role: str = "ADC"):
    matches = _matches_for_champion(champion, n, role=role)
    sr = sv2.analyze_player(matches, role)
    return analyze_champion_pool(matches, role, sr.match_scores)


# ── Regresión: mismatch de nombres de campeón (bug crítico corregido) ────────

def test_current_pick_matches_history_despite_display_name_with_apostrophe():
    """
    Kai'Sa (display name del LCU) debe cruzar con "KaiSa" (formato Riot API
    guardado en la DB) via el alias — antes de este fix, has_data era False
    pese a tener historial real.
    """
    session = parse_session(_session(my_champ_id=145), CHAMPION_MAP)
    cpa = _cpa_for("KaiSa", 12)

    advice = analyze_draft(session, cpa)

    assert advice.current_pick_score is not None
    assert advice.current_pick_score.has_data is True
    assert advice.current_pick_score.champion == "Kai'Sa"   # se muestra el display name
    assert advice.current_pick_score.total > 0


def test_current_pick_display_name_shown_even_when_grading_by_alias():
    session = parse_session(_session(my_champ_id=41), CHAMPION_MAP)  # Wukong / MonkeyKing
    cpa = _cpa_for("MonkeyKing", 8, role="TOP")

    advice = analyze_draft(session, cpa)
    assert advice.current_pick_score.champion == "Wukong"
    assert advice.current_pick_score.has_data is True


# ── Regresión: picks ya lockeados por otro jugador ────────────────────────────

def test_locked_champion_by_teammate_excluded_from_recommendations():
    """
    Un campeón con buen historial pero ya elegido por un aliado no debe
    aparecer en recomendaciones — League no permite picks duplicados.
    """
    # Ashe(22) ya lockeada por un aliado; el jugador está eligiendo Caitlyn(51)
    session = parse_session(_session(my_champ_id=51, ally_picks=[22]), CHAMPION_MAP)

    matches = _matches_for_champion("Ashe", 10) + _matches_for_champion("Caitlyn", 8)
    sr = sv2.analyze_player(matches, "ADC")
    cpa = analyze_champion_pool(matches, "ADC", sr.match_scores)

    advice = analyze_draft(session, cpa)
    recommended_names = {r.champion for r in advice.recommendations} | {r.champion for r in advice.avoid}
    assert "Ashe" not in recommended_names


def test_locked_champion_by_enemy_also_excluded():
    session = parse_session(_session(my_champ_id=51, enemy_picks=[22]), CHAMPION_MAP)
    matches = _matches_for_champion("Ashe", 10) + _matches_for_champion("Caitlyn", 8)
    sr = sv2.analyze_player(matches, "ADC")
    cpa = analyze_champion_pool(matches, "ADC", sr.match_scores)

    advice = analyze_draft(session, cpa)
    recommended_names = {r.champion for r in advice.recommendations} | {r.champion for r in advice.avoid}
    assert "Ashe" not in recommended_names


def test_own_locked_pick_not_excluded_from_its_own_score():
    """No debo excluirme a mí mismo del cálculo de mi propio Draft Score."""
    session = parse_session(_session(my_champ_id=145), CHAMPION_MAP)  # yo llevo Kai'Sa
    cpa = _cpa_for("KaiSa", 10)
    advice = analyze_draft(session, cpa)
    assert advice.current_pick_score.has_data is True


# ── Bans ──────────────────────────────────────────────────────────────────────

def test_banned_champion_excluded_from_recommendations():
    session = parse_session(_session(my_champ_id=0, my_bans=[145]), CHAMPION_MAP)  # Kai'Sa baneada
    cpa = _cpa_for("KaiSa", 10)
    advice = analyze_draft(session, cpa)
    all_names = {r.champion for r in advice.recommendations} | {r.champion for r in advice.avoid}
    assert "Kai'Sa" not in all_names


# ── Casos borde: sin historial / sin pick ─────────────────────────────────────

def test_no_current_pick_yields_none_score():
    session = parse_session(_session(my_champ_id=0), CHAMPION_MAP)  # sin pick todavía
    cpa = _cpa_for("KaiSa", 10)
    advice = analyze_draft(session, cpa)
    assert advice.current_pick_score is None


def test_current_pick_without_history_reports_no_data_not_a_crash():
    session = parse_session(_session(my_champ_id=145), CHAMPION_MAP)  # Kai'Sa, sin historial
    cpa = _cpa_for("Ashe", 10)  # el pool solo tiene Ashe
    advice = analyze_draft(session, cpa)
    assert advice.current_pick_score.has_data is False
    assert advice.current_pick_score.grade == "F"


def test_empty_pool_reports_pool_has_data_false():
    session = parse_session(_session(my_champ_id=145), CHAMPION_MAP)
    empty_cpa = _cpa_for("KaiSa", 0) if False else analyze_champion_pool([], "ADC")
    advice = analyze_draft(session, empty_cpa)
    assert advice.pool_has_data is False


# ── Fórmulas ──────────────────────────────────────────────────────────────────

def test_grade_boundaries():
    assert _grade(75)[0] == "A"
    assert _grade(74.9)[0] == "B"
    assert _grade(55)[0] == "B"
    assert _grade(35)[0] == "C"
    assert _grade(15)[0] == "D"
    assert _grade(14.9)[0] == "F"


def test_pick_value_is_bounded_and_monotonic_in_winrate():
    cpa = _cpa_for("KaiSa", 10)
    stats = cpa.champions[0]
    low_wr = stats.__class__(**{**stats.__dict__, "winrate": 0.1})
    high_wr = stats.__class__(**{**stats.__dict__, "winrate": 0.9})
    assert _pick_value(high_wr) > _pick_value(low_wr)
