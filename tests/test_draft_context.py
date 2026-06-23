"""
tests/test_draft_context.py — Tests de Sprint 9: Context Aware Draft.

Valida champion_profiles, profile_builder, synergy_engine,
threat_engine, draft_score_v2 y draft_advisor_v2.

Cobertura objetivo: ≥ 80% de los módulos backend/draft/*.py
"""

import sys
import os
import pytest

# Asegurar que el root del proyecto está en el path para los imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.draft.champion_profiles import (
    get_profile, all_profiles, ChampionProfile, CHAMPIONS,
)
from backend.draft.draft_context import TeamProfile, EnemyProfile
from backend.draft.profile_builder import build_team_profile, build_enemy_profile
from backend.draft.synergy_engine import compute_synergy, synergy_reasons
from backend.draft.threat_engine import compute_threat, threat_reasons
from backend.draft.draft_score_v2 import compute_draft_score_v2
from backend.draft.draft_advisor_v2 import enhance_recommendations, DraftContextScore


# ── Fixtures ──────────────────────────────────────────────────────────────────

class _FakeRec:
    """Simula un DraftRecommendation del advisor v1."""
    def __init__(self, champion: str, avg_score: float = 70.0):
        self.champion  = champion
        self.avg_score = avg_score


# ── champion_profiles ─────────────────────────────────────────────────────────

class TestChampionProfiles:
    def test_known_champion_found(self):
        p = get_profile("Jinx")
        assert p is not None
        assert p.name == "Jinx"

    def test_case_insensitive_lookup(self):
        assert get_profile("jinx") is not None
        assert get_profile("JINX") is not None
        assert get_profile("Jinx") is not None

    def test_unknown_champion_returns_none(self):
        assert get_profile("InventedChampionXYZ") is None

    def test_all_profiles_non_empty(self):
        profiles = all_profiles()
        assert len(profiles) >= 20  # al menos 20 campeones en el catálogo

    def test_profile_attributes_in_range(self):
        for p in all_profiles():
            for attr in ("burst", "sustained_damage", "cc", "engage", "peel",
                         "mobility", "tankiness", "self_peel", "scaling",
                         "anti_tank", "dive", "waveclear", "range"):
                val = getattr(p, attr)
                assert 0 <= val <= 5, f"{p.name}.{attr}={val} fuera de rango 0-5"

    def test_damage_type_valid(self):
        valid_types = {"physical", "magic", "mixed"}
        for p in all_profiles():
            assert p.damage_type in valid_types, f"{p.name}.damage_type={p.damage_type}"

    def test_vayne_high_anti_tank(self):
        vayne = get_profile("Vayne")
        assert vayne is not None
        assert vayne.anti_tank >= 4

    def test_malphite_high_engage(self):
        m = get_profile("Malphite")
        assert m is not None
        assert m.engage == 5
        assert m.damage_type == "magic"

    def test_caitlyn_high_range(self):
        c = get_profile("Caitlyn")
        assert c is not None
        assert c.range == 5

    def test_both_adc_and_top_present(self):
        assert get_profile("Jinx") is not None    # ADC
        assert get_profile("Darius") is not None   # TOP


# ── profile_builder ───────────────────────────────────────────────────────────

class TestProfileBuilder:
    def test_empty_list_returns_zero_profile(self):
        tp = build_team_profile([])
        assert tp.count == 0
        assert tp.total_engage == 0.0

    def test_single_known_champion(self):
        tp = build_team_profile(["Malphite"])
        assert tp.count == 1
        assert tp.total_engage == 5.0
        assert tp.magic_count == 1

    def test_unknown_champion_ignored(self):
        tp = build_team_profile(["Malphite", "NoExiste"])
        assert tp.count == 1

    def test_physical_damage_counted(self):
        tp = build_team_profile(["Jinx", "Caitlyn"])
        assert tp.physical_count == 2
        assert tp.magic_count == 0

    def test_mixed_damage_counted(self):
        tp = build_team_profile(["Ezreal"])
        assert tp.mixed_count == 1

    def test_team_profile_aggregates_correctly(self):
        jinx  = get_profile("Jinx")
        ashe  = get_profile("Ashe")
        tp    = build_team_profile(["Jinx", "Ashe"])
        assert tp.total_engage == jinx.engage + ashe.engage
        assert tp.total_cc     == jinx.cc     + ashe.cc

    def test_enemy_profile_high_dive(self):
        ep = build_enemy_profile(["Camille", "Irelia"])
        assert ep.count == 2
        assert ep.high_dive is True   # ambas tienen dive >= 4

    def test_enemy_profile_empty(self):
        ep = build_enemy_profile([])
        assert ep.count == 0
        assert ep.high_burst is False

    def test_team_avg_property(self):
        tp = build_team_profile(["Malphite", "Ornn"])
        malph = get_profile("Malphite")
        ornn  = get_profile("Ornn")
        expected_avg_engage = (malph.engage + ornn.engage) / 2
        assert tp.avg("engage") == pytest.approx(expected_avg_engage)

    def test_enemy_profile_flags_heavy_cc(self):
        ep = build_enemy_profile(["Malphite", "Ornn", "Ashe"])
        assert ep.heavy_cc is True


# ── TeamProfile propiedades ───────────────────────────────────────────────────

class TestTeamProfileProperties:
    def test_needs_magic_when_no_magic(self):
        tp = build_team_profile(["Jinx", "Darius"])
        assert tp.needs_magic is True

    def test_no_needs_magic_when_magic_present(self):
        tp = build_team_profile(["Jinx", "Malphite"])
        assert tp.needs_magic is False

    def test_engage_heavy_detection(self):
        tp = build_team_profile(["Malphite", "Ornn"])
        assert tp.is_engage_heavy is True

    def test_lacks_engage_detection(self):
        tp = build_team_profile(["Jinx", "Twitch"])
        assert tp.lacks_engage is True

    def test_avg_returns_zero_for_empty(self):
        tp = TeamProfile()
        assert tp.avg("engage") == 0.0


# ── synergy_engine ────────────────────────────────────────────────────────────

class TestSynergyEngine:
    def test_score_range(self):
        for p in all_profiles():
            tp = build_team_profile(["Malphite", "Ornn"])
            s  = compute_synergy(p, tp)
            assert 0.0 <= s <= 20.0, f"{p.name}: synergy={s} fuera de rango"

    def test_empty_team_returns_neutral(self):
        jinx = get_profile("Jinx")
        tp   = TeamProfile()  # count=0
        s    = compute_synergy(jinx, tp)
        assert s == 10.0

    def test_magic_gap_rewarded(self):
        # Equipo sin daño mágico: campeón mágico debe tener mayor sinergia
        all_physical = build_team_profile(["Jinx", "Caitlyn", "Darius"])
        kennen = get_profile("Kennen")
        darius = get_profile("Darius")
        s_kennen = compute_synergy(kennen, all_physical)
        s_darius = compute_synergy(darius, all_physical)
        # Kennen tiene damage_type="magic", debe ser > Darius (también físico)
        assert s_kennen > s_darius

    def test_engage_heavy_team_rewards_scaling(self):
        # Equipo con mucho engage → candidato que escala bien debe tener más sinergia
        engage_team = build_team_profile(["Malphite", "Ornn"])
        jinx   = get_profile("Jinx")    # scaling=5
        draven = get_profile("Draven")  # scaling=2
        s_jinx   = compute_synergy(jinx,   engage_team)
        s_draven = compute_synergy(draven, engage_team)
        assert s_jinx > s_draven

    def test_engage_gap_rewards_engage_champion(self):
        no_engage = build_team_profile(["Jinx", "Twitch"])
        ashe  = get_profile("Ashe")    # engage=3
        twitch = get_profile("Twitch") # engage=0
        s_ashe   = compute_synergy(ashe,  no_engage)
        s_twitch = compute_synergy(twitch, no_engage)
        assert s_ashe > s_twitch

    def test_synergy_reasons_empty_when_low(self):
        tp = TeamProfile()
        # Con team vacío, sinergy = 10.0 (neutro), no hay reasons concretas
        jinx = get_profile("Jinx")
        reasons = synergy_reasons(jinx, tp, synergy=3.0)
        assert reasons == []

    def test_synergy_reasons_non_empty_when_high(self):
        physical_team = build_team_profile(["Jinx", "Darius"])
        kennen = get_profile("Kennen")
        s = compute_synergy(kennen, physical_team)
        reasons = synergy_reasons(kennen, physical_team, s)
        assert len(reasons) > 0


# ── threat_engine ─────────────────────────────────────────────────────────────

class TestThreatEngine:
    def test_score_range(self):
        for p in all_profiles():
            ep = build_enemy_profile(["Camille", "Irelia", "Renekton"])
            t  = compute_threat(p, ep)
            assert -20.0 <= t <= 0.0, f"{p.name}: threat={t} fuera de rango"

    def test_empty_enemy_no_penalty(self):
        jinx = get_profile("Jinx")
        ep   = EnemyProfile()  # count=0
        t    = compute_threat(jinx, ep)
        assert t == 0.0

    def test_dive_threat_penalizes_immobile(self):
        # Composición de dive: Camille + Irelia
        dive_comp = build_enemy_profile(["Camille", "Irelia"])
        ashe  = get_profile("Ashe")    # mobility=0 → muy vulnerable
        ezreal = get_profile("Ezreal") # mobility=4 → menos vulnerable
        t_ashe   = compute_threat(ashe,   dive_comp)
        t_ezreal = compute_threat(ezreal, dive_comp)
        assert t_ashe < t_ezreal   # Ashe más penalizada

    def test_burst_threat_penalizes_low_defense(self):
        burst_comp = build_enemy_profile(["Jhin", "Renekton", "Samira"])
        kogmaw = get_profile("Kog'Maw")  # tankiness=0, mobility=0
        zeri   = get_profile("Zeri")     # mobility=5
        t_kog  = compute_threat(kogmaw, burst_comp)
        t_zeri = compute_threat(zeri,   burst_comp)
        assert t_kog < t_zeri  # Kog'Maw más penalizado

    def test_cc_threat_penalizes_immobile(self):
        cc_comp = build_enemy_profile(["Malphite", "Ornn", "Ashe"])
        ashe_candidate = get_profile("Ashe")  # mobility=0
        zeri   = get_profile("Zeri")           # mobility=5
        t_ashe = compute_threat(ashe_candidate, cc_comp)
        t_zeri = compute_threat(zeri, cc_comp)
        assert t_ashe < t_zeri

    def test_threat_reasons_empty_when_low(self):
        ep      = EnemyProfile()
        jinx    = get_profile("Jinx")
        reasons = threat_reasons(jinx, ep, threat=0.0)
        assert reasons == []

    def test_threat_reasons_for_immobile_vs_dive(self):
        dive_comp = build_enemy_profile(["Camille", "Irelia"])
        ashe = get_profile("Ashe")
        t    = compute_threat(ashe, dive_comp)
        reasons = threat_reasons(ashe, dive_comp, t)
        assert len(reasons) > 0


# ── draft_score_v2 ────────────────────────────────────────────────────────────

class TestDraftScoreV2:
    def test_pure_pick_value_when_neutral_context(self):
        # synergy=10 → synergy_norm=50, threat=0 → threat_norm=100
        # 0.70×80 + 0.20×50 + 0.10×100 = 56 + 10 + 10 = 76
        result = compute_draft_score_v2(pick_value=80.0, synergy=10.0, threat=0.0)
        assert result == pytest.approx(76.0, abs=0.5)

    def test_high_synergy_boosts_score(self):
        base = compute_draft_score_v2(80.0, synergy=5.0,  threat=0.0)
        high = compute_draft_score_v2(80.0, synergy=20.0, threat=0.0)
        assert high > base

    def test_high_threat_reduces_score(self):
        no_threat = compute_draft_score_v2(80.0, synergy=10.0, threat=0.0)
        threatened = compute_draft_score_v2(80.0, synergy=10.0, threat=-20.0)
        assert no_threat > threatened

    def test_output_clamped_to_0_100(self):
        assert 0.0 <= compute_draft_score_v2(100.0, 20.0, 0.0) <= 100.0
        assert 0.0 <= compute_draft_score_v2(0.0, 0.0, -20.0) <= 100.0

    def test_formula_correctness(self):
        pv = 60.0; sy = 15.0; th = -10.0
        s_norm = (sy / 20.0) * 100.0          # 75
        t_norm = ((th + 20.0) / 20.0) * 100.0 # 50
        expected = 0.70 * pv + 0.20 * s_norm + 0.10 * t_norm
        assert compute_draft_score_v2(pv, sy, th) == pytest.approx(expected, abs=0.1)


# ── draft_advisor_v2 ──────────────────────────────────────────────────────────

class TestDraftAdvisorV2:
    def _make_recs(self, champions_scores: dict[str, float]) -> list[_FakeRec]:
        return [_FakeRec(c, s) for c, s in champions_scores.items()]

    def test_basic_enhancement(self):
        recs   = self._make_recs({"Jinx": 80.0, "Kai'Sa": 70.0})
        result = enhance_recommendations(recs, ["Malphite"], ["Camille"])
        assert "jinx"  in result.scores
        assert "kai'sa" in result.scores

    def test_unknown_champion_gets_no_context(self):
        recs   = self._make_recs({"NoExisteXYZ": 65.0})
        result = enhance_recommendations(recs, [], [])
        score  = result.scores["noexistexyz"]
        assert score.context_available is False
        assert score.draft_score_v2 == 65.0

    def test_draft_score_v2_computed(self):
        recs   = self._make_recs({"Jinx": 80.0})
        result = enhance_recommendations(recs, ["Malphite"], ["Camille"])
        score  = result.scores["jinx"]
        assert score.context_available is True
        assert 0.0 <= score.draft_score_v2 <= 100.0
        assert score.synergy >= 0.0
        assert score.threat <= 0.0

    def test_team_profile_in_result(self):
        recs   = self._make_recs({"Jinx": 70.0})
        result = enhance_recommendations(recs, ["Malphite", "Ornn"], [])
        assert result.team_profile.count == 2
        assert result.ally_coverage == 2

    def test_enemy_profile_in_result(self):
        recs   = self._make_recs({"Jinx": 70.0})
        result = enhance_recommendations(recs, [], ["Camille", "Irelia"])
        assert result.enemy_profile.count == 2
        assert result.enemy_coverage == 2

    def test_high_engage_team_boosts_scaling_carries(self):
        recs = self._make_recs({"Jinx": 70.0, "Draven": 70.0})
        # Equipo de engage → Jinx (scaling=5) debe tener más sinergia que Draven (scaling=2)
        result = enhance_recommendations(recs, ["Malphite", "Ornn"], [])
        s_jinx   = result.scores["jinx"].synergy
        s_draven = result.scores["draven"].synergy
        assert s_jinx > s_draven

    def test_dive_comp_penalizes_immobile(self):
        recs = self._make_recs({"Ashe": 70.0, "Zeri": 70.0})
        # Composición de dive → Ashe (mobility=0) más penalizada que Zeri (mobility=5)
        result = enhance_recommendations(recs, [], ["Camille", "Irelia"])
        t_ashe = result.scores["ashe"].threat
        t_zeri = result.scores["zeri"].threat
        assert t_ashe < t_zeri  # Ashe más penalizada

    def test_empty_context_neutral_score(self):
        recs   = self._make_recs({"Jinx": 80.0})
        result = enhance_recommendations(recs, [], [])
        score  = result.scores["jinx"]
        # Con contexto vacío (team_count=0) synergy=10 (neutro), threat=0
        assert score.synergy == pytest.approx(10.0)
        assert score.threat  == pytest.approx(0.0)
