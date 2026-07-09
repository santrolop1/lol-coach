"""
tests/test_api.py — Tests de integración para la API FastAPI.

Usa httpx.AsyncClient con el servidor en modo test (sin DB real, sin LCU).
Todos los ViewModels se mockean para probar solo el contrato de la API.
"""

from __future__ import annotations

import sys
import dataclasses
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api.main import app

client = TestClient(app, raise_server_exceptions=False)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _mock_coaching_vm(has_data=True, role="ADC"):
    """Construye un CoachingViewModel mínimo para tests."""
    from backend.viewmodels.coaching_vm import CoachingViewModel, CoachingMetrics

    metrics = CoachingMetrics(
        cs_pm=7.5, dmg_pm=800.0, kp=0.65, kp_win=0.75, kp_loss=0.50,
        deaths=3.0, deaths_win=2.0, deaths_loss=5.0,
        vision_pm=1.2, gold_pm=400.0, obj_pm=200.0,
        n=10, n_wins=6, n_losses=4,
    )

    if not has_data:
        return CoachingViewModel(
            player_name="TestPlayer", rank="Gold IV", lp=50,
            last_match_date=None, score_result=None, coaching_result=None,
            metrics=CoachingMetrics(
                cs_pm=None, dmg_pm=None, kp=None, kp_win=None, kp_loss=None,
                deaths=None, deaths_win=None, deaths_loss=None,
                vision_pm=None, gold_pm=None, obj_pm=None,
                n=0, n_wins=0, n_losses=0,
            ),
            priorities=[], matchup_result=None, champion_pool=None,
            available_champions=[], role=role, sample_size=0, has_data=False, role_matches=[],
        )

    # ScoreResult mínimo con dataclass real para serialización
    import scorer_v2
    sr = scorer_v2.ScoreResultV2(
        role=role,
        dominant_role=role,
        role_distribution={},
        overall_score=62.5,
        dimensions={"Economía": 65.0, "Posicionamiento": 58.0, "Combate": 64.0},
        primary_problem=None,
        trend="stable",
        trend_slope=0.0,
        consistency_score=55.0,
        confidence_level="reliable",
        sample_size=10,
        surrender_count=0,
        match_scores=[],
        benchmarks=None,
        limitations=[],
    )

    # CoachingResult mínimo con campos reales
    from coaching_engine import WeeklyGoal, TrainingPlan, Strength, CoachingResult
    cr = CoachingResult(
        role=role,
        confidence_level="reliable",
        primary_problem="HIGH_DEATHS",
        evidence="Promedio 5.2 muertes en derrotas",
        probable_cause="Posicionamiento en teamfights",
        impact="Cada muerte regala ventaja de oro al enemigo",
        weekly_goal=WeeklyGoal("Reduce muertes", "deaths", 3.0, 2.0, "proximas 10 partidas"),
        training_plan=TrainingPlan("Practica posicionamiento", ["Estudia replays"]),
        strengths=[Strength("Buen CS", "7.5 CS/min promedio")],
        improvements=["Demasiadas muertes"],
        trend_summary="Tendencia estable en las últimas 10 partidas",
        sample_size=10,
        session_warning=None,
    )

    return CoachingViewModel(
        player_name="TestPlayer", rank="Gold IV", lp=50,
        last_match_date="2026-06-26",
        score_result=sr, coaching_result=cr, metrics=metrics,
        priorities=[], matchup_result=None, champion_pool=None,
        available_champions=["Jinx", "Caitlyn"],
        role=role, sample_size=10, has_data=True, role_matches=[],
    )


def _mock_matches_vm():
    from backend.viewmodels.matches_vm import (
        MatchesViewModel, MatchCard, MatchRow, MatchesSummary,
    )
    return MatchesViewModel(
        has_config=True,
        player={"riot_id": "TestPlayer", "tag": "LAN", "level": 200, "rank": "Gold IV", "tier": "GOLD", "lp": 50},
        recent_cards=[
            MatchCard(is_win=True, champion="Jinx", role="ADC", kda="5/2/8",
                      overall_score=72.0, best_dim="Farm", worst_dim="Combate", match_id="LA1_1"),
        ],
        table_rows=[
            MatchRow(result="✅ Victoria", champion="Jinx", role="ADC",
                     kda="5/2/8", cs=200, cs_pm=6.7, damage="25,000",
                     duration="30m 00s", date="2026-06-26"),
        ],
        summary=MatchesSummary(total=10, wins=6, losses=4, winrate=60.0),
        v2_analysis=None,
        available_roles=["ADC", "TOP"],
        available_champs=["Jinx", "Caitlyn"],
    )


def _mock_settings_vm():
    from backend.viewmodels.settings_vm import SettingsViewModel
    return SettingsViewModel(
        is_configured=True, puuid="test-puuid",
        platform="la1", platform_name="Latinoamérica Norte (LA1)",
        player={"riot_id": "TestPlayer"}, riot_id="TestPlayer",
        tag="LAN", level=200, rank="Gold IV", tier="GOLD", lp=50,
    )


def _mock_draft_vm(connected=False):
    from backend.viewmodels.draft_vm import DraftViewModel
    return DraftViewModel(
        lcu_connected=connected, credentials=None, phase=None,
        phase_label="Desconectado", session=None, champion_map={},
        advice=None, champion_pool=None, role=None, role_supported=False,
    )


# ── Health ─────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_returns_200(self):
        with patch("backend.api.routes.health.db.get_config", return_value=None), \
             patch("backend.api.routes.health.lcu_client.read_credentials", return_value=None), \
             patch("backend.api.routes.health.get_last_sync", return_value=None):
            r = client.get("/api/v1/health")
        assert r.status_code == 200

    def test_response_has_required_fields(self):
        with patch("backend.api.routes.health.db.get_config", return_value=None), \
             patch("backend.api.routes.health.lcu_client.read_credentials", return_value=None), \
             patch("backend.api.routes.health.get_last_sync", return_value=None):
            r = client.get("/api/v1/health")
        data = r.json()
        assert "status" in data
        assert "version" in data
        assert "db" in data
        assert "lcu" in data
        assert "riot_api" in data

    def test_lcu_disconnected_when_no_lockfile(self):
        with patch("backend.api.routes.health.db.get_config", return_value=None), \
             patch("backend.api.routes.health.lcu_client.read_credentials", return_value=None), \
             patch("backend.api.routes.health.get_last_sync", return_value=None):
            r = client.get("/api/v1/health")
        assert r.json()["lcu"] == "disconnected"

    def test_riot_api_configured_when_key_present(self):
        with patch("backend.api.routes.health.db.get_config", return_value="test-key"), \
             patch("backend.api.routes.health.lcu_client.read_credentials", return_value=None), \
             patch("backend.api.routes.health.get_last_sync", return_value=None):
            r = client.get("/api/v1/health")
        assert r.json()["riot_api"] == "configured"

    def test_last_sync_none_when_never_synced(self):
        with patch("backend.api.routes.health.db.get_config", return_value=None), \
             patch("backend.api.routes.health.lcu_client.read_credentials", return_value=None), \
             patch("backend.api.routes.health.get_last_sync", return_value=None):
            r = client.get("/api/v1/health")
        assert r.json()["last_sync"] is None

    def test_last_sync_present_when_synced(self):
        ts = datetime(2026, 6, 26, 12, 0, 0, tzinfo=timezone.utc)
        with patch("backend.api.routes.health.db.get_config", return_value=None), \
             patch("backend.api.routes.health.lcu_client.read_credentials", return_value=None), \
             patch("backend.api.routes.health.get_last_sync", return_value=ts):
            r = client.get("/api/v1/health")
        assert r.json()["last_sync"] is not None
        assert "2026" in r.json()["last_sync"]


# ── Coaching ───────────────────────────────────────────────────────────────────

class TestCoachingEndpoint:
    def test_returns_200_with_data(self):
        vm = _mock_coaching_vm(has_data=True)
        with patch("backend.api.routes.coaching.build_coaching", return_value=vm):
            r = client.get("/api/v1/coaching?role=ADC&limit=20")
        assert r.status_code == 200

    def test_returns_200_no_data(self):
        vm = _mock_coaching_vm(has_data=False)
        with patch("backend.api.routes.coaching.build_coaching", return_value=vm):
            r = client.get("/api/v1/coaching?role=ADC")
        assert r.status_code == 200
        assert r.json()["has_data"] is False

    def test_response_has_required_fields(self):
        vm = _mock_coaching_vm(has_data=True)
        with patch("backend.api.routes.coaching.build_coaching", return_value=vm):
            r = client.get("/api/v1/coaching")
        data = r.json()
        assert "player_name" in data
        assert "role" in data
        assert "has_data" in data
        assert "priorities" in data
        assert "available_champions" in data

    def test_player_name_in_response(self):
        vm = _mock_coaching_vm()
        with patch("backend.api.routes.coaching.build_coaching", return_value=vm):
            r = client.get("/api/v1/coaching")
        assert r.json()["player_name"] == "TestPlayer"

    def test_role_parameter_passed_to_vm(self):
        vm = _mock_coaching_vm(role="TOP")
        with patch("backend.api.routes.coaching.build_coaching", return_value=vm) as mock_build:
            client.get("/api/v1/coaching?role=TOP&limit=30")
        mock_build.assert_called_once_with("TOP", 30)

    def test_invalid_role_returns_422(self):
        r = client.get("/api/v1/coaching?role=JUNGLE")
        assert r.status_code == 422

    def test_limit_too_small_returns_422(self):
        r = client.get("/api/v1/coaching?limit=2")
        assert r.status_code == 422

    def test_limit_too_large_returns_422(self):
        r = client.get("/api/v1/coaching?limit=999")
        assert r.status_code == 422

    def test_coaching_result_serialized_when_has_data(self):
        vm = _mock_coaching_vm(has_data=True)
        with patch("backend.api.routes.coaching.build_coaching", return_value=vm):
            r = client.get("/api/v1/coaching")
        data = r.json()
        assert data["coaching_result"] is not None
        assert data["coaching_result"]["primary_problem"] == "HIGH_DEATHS"

    def test_metrics_serialized_when_has_data(self):
        vm = _mock_coaching_vm(has_data=True)
        with patch("backend.api.routes.coaching.build_coaching", return_value=vm):
            r = client.get("/api/v1/coaching")
        data = r.json()
        assert data["metrics"] is not None
        assert data["metrics"]["n"] == 10
        assert data["metrics"]["n_wins"] == 6

    def test_available_champions_list(self):
        vm = _mock_coaching_vm(has_data=True)
        with patch("backend.api.routes.coaching.build_coaching", return_value=vm):
            r = client.get("/api/v1/coaching")
        assert r.json()["available_champions"] == ["Jinx", "Caitlyn"]


# ── Matches ────────────────────────────────────────────────────────────────────

class TestMatchesEndpoint:
    def test_returns_200(self):
        vm = _mock_matches_vm()
        with patch("backend.api.routes.matches.build_matches", return_value=vm):
            r = client.get("/api/v1/matches")
        assert r.status_code == 200

    def test_response_has_required_fields(self):
        vm = _mock_matches_vm()
        with patch("backend.api.routes.matches.build_matches", return_value=vm):
            r = client.get("/api/v1/matches")
        data = r.json()
        assert "has_config" in data
        assert "recent_cards" in data
        assert "table_rows" in data
        assert "summary" in data
        assert "available_champs" in data

    def test_summary_fields(self):
        vm = _mock_matches_vm()
        with patch("backend.api.routes.matches.build_matches", return_value=vm):
            r = client.get("/api/v1/matches")
        s = r.json()["summary"]
        assert s["total"] == 10
        assert s["wins"] == 6
        assert s["winrate"] == 60.0

    def test_recent_cards_structure(self):
        vm = _mock_matches_vm()
        with patch("backend.api.routes.matches.build_matches", return_value=vm):
            r = client.get("/api/v1/matches")
        cards = r.json()["recent_cards"]
        assert len(cards) == 1
        assert cards[0]["champion"] == "Jinx"
        assert cards[0]["is_win"] is True

    def test_role_filter_passed_to_vm(self):
        vm = _mock_matches_vm()
        with patch("backend.api.routes.matches.build_matches", return_value=vm) as mock_build:
            client.get("/api/v1/matches?role=ADC")
        mock_build.assert_called_once_with(role_filter="ADC", champion_filter=None)

    def test_champion_filter_passed_to_vm(self):
        vm = _mock_matches_vm()
        with patch("backend.api.routes.matches.build_matches", return_value=vm) as mock_build:
            client.get("/api/v1/matches?champion=Jinx")
        mock_build.assert_called_once_with(role_filter=None, champion_filter="Jinx")

    def test_no_config_returns_200_with_flag(self):
        from backend.viewmodels.matches_vm import MatchesViewModel, MatchesSummary
        empty_vm = MatchesViewModel(
            has_config=False, player=None, recent_cards=[], table_rows=[],
            summary=MatchesSummary(total=0, wins=0, losses=0, winrate=0.0),
            v2_analysis=None, available_roles=[], available_champs=[],
        )
        with patch("backend.api.routes.matches.build_matches", return_value=empty_vm):
            r = client.get("/api/v1/matches")
        assert r.status_code == 200
        assert r.json()["has_config"] is False


# ── Settings ───────────────────────────────────────────────────────────────────

class TestSettingsEndpoint:
    def test_returns_200(self):
        vm = _mock_settings_vm()
        with patch("backend.api.routes.settings.build_settings", return_value=vm):
            r = client.get("/api/v1/settings")
        assert r.status_code == 200

    def test_response_fields(self):
        vm = _mock_settings_vm()
        with patch("backend.api.routes.settings.build_settings", return_value=vm):
            r = client.get("/api/v1/settings")
        data = r.json()
        assert data["is_configured"] is True
        assert data["riot_id"] == "TestPlayer"
        assert data["platform_name"] == "Latinoamérica Norte (LA1)"
        assert data["rank"] == "Gold IV"

    def test_not_configured_returns_flag(self):
        from backend.viewmodels.settings_vm import SettingsViewModel
        empty_vm = SettingsViewModel(
            is_configured=False, puuid=None, platform=None,
            platform_name=None, player=None, riot_id=None, tag=None,
            level=None, rank=None, tier=None, lp=None,
        )
        with patch("backend.api.routes.settings.build_settings", return_value=empty_vm):
            r = client.get("/api/v1/settings")
        assert r.json()["is_configured"] is False


# ── Draft ──────────────────────────────────────────────────────────────────────

class TestDraftEndpoint:
    def test_returns_200_when_disconnected(self):
        vm = _mock_draft_vm(connected=False)
        with patch("backend.api.routes.draft.build_draft", return_value=vm):
            r = client.get("/api/v1/draft")
        assert r.status_code == 200

    def test_lcu_connected_false_when_no_lockfile(self):
        vm = _mock_draft_vm(connected=False)
        with patch("backend.api.routes.draft.build_draft", return_value=vm):
            r = client.get("/api/v1/draft")
        assert r.json()["lcu_connected"] is False

    def test_response_has_required_fields(self):
        vm = _mock_draft_vm()
        with patch("backend.api.routes.draft.build_draft", return_value=vm):
            r = client.get("/api/v1/draft")
        data = r.json()
        assert "lcu_connected" in data
        assert "phase" in data
        assert "phase_label" in data
        assert "role_supported" in data


# ── Dashboard ──────────────────────────────────────────────────────────────────

class TestDashboardEndpoint:
    def test_returns_200(self):
        vm_adc  = _mock_coaching_vm(role="ADC")
        vm_top  = _mock_coaching_vm(role="TOP")
        s_vm    = _mock_settings_vm()

        with patch("backend.api.routes.dashboard.build_coaching",
                   side_effect=[vm_adc, vm_top]), \
             patch("backend.api.routes.dashboard.build_settings", return_value=s_vm), \
             patch("backend.api.routes.dashboard.get_last_sync", return_value=None), \
             patch("backend.api.routes.dashboard.sync_status_label", return_value="Sin sincronizar"):
            r = client.get("/api/v1/dashboard")

        assert r.status_code == 200

    def test_response_has_roles(self):
        vm_adc = _mock_coaching_vm(role="ADC")
        vm_top = _mock_coaching_vm(has_data=False, role="TOP")
        s_vm   = _mock_settings_vm()

        with patch("backend.api.routes.dashboard.build_coaching",
                   side_effect=[vm_adc, vm_top]), \
             patch("backend.api.routes.dashboard.build_settings", return_value=s_vm), \
             patch("backend.api.routes.dashboard.get_last_sync", return_value=None), \
             patch("backend.api.routes.dashboard.sync_status_label", return_value="Sin sincronizar"):
            r = client.get("/api/v1/dashboard")

        data = r.json()
        assert "ADC" in data["roles"]
        assert "TOP" in data["roles"]
        assert data["roles"]["ADC"]["overall_score"] == 62.5
        assert data["roles"]["TOP"]["has_data"] is False


# ── WebSocket Manager ──────────────────────────────────────────────────────────

class TestConnectionManager:
    def test_connect_increases_count(self):
        import asyncio
        from backend.api.websocket.manager import ConnectionManager

        mgr = ConnectionManager()
        ws  = MagicMock()

        async def fake_accept():
            return None

        ws.accept = fake_accept

        async def run():
            await mgr.connect(ws)
            assert mgr.count == 1
            mgr.disconnect(ws)
            assert mgr.count == 0

        asyncio.run(run())

    def test_disconnect_removes_client(self):
        from backend.api.websocket.manager import ConnectionManager
        mgr = ConnectionManager()
        ws  = MagicMock()
        mgr._active.append(ws)
        assert mgr.count == 1
        mgr.disconnect(ws)
        assert mgr.count == 0

    def test_disconnect_nonexistent_no_error(self):
        from backend.api.websocket.manager import ConnectionManager
        mgr = ConnectionManager()
        ws  = MagicMock()
        mgr.disconnect(ws)  # no debe lanzar
        assert mgr.count == 0


# ── API Key Management ─────────────────────────────────────────────────────────

class TestApiKeyEndpoints:
    """Tests para GET /api-key/status, POST /api-key, DELETE /api-key."""

    def test_status_not_configured(self):
        with patch("backend.api.routes.settings.db") as mock_db:
            mock_db.get_config.return_value = None
            r = client.get("/api/v1/settings/api-key/status")
        assert r.status_code == 200
        data = r.json()
        assert data["configured"] is False
        assert data["status"] == "not_configured"
        assert data["masked_key"] is None

    def test_status_active(self):
        from datetime import datetime, timezone, timedelta
        saved_at = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()

        def mock_get_config(key: str):
            return {
                "api_key": "RGAPI-00000000-0000-0000-0000-000000000000",
                "api_key_saved_at": saved_at,
                "api_key_expired": None,
            }.get(key)

        with patch("backend.api.routes.settings.db") as mock_db:
            mock_db.get_config.side_effect = mock_get_config
            r = client.get("/api/v1/settings/api-key/status")

        assert r.status_code == 200
        data = r.json()
        assert data["configured"] is True
        assert data["status"] == "active"
        assert data["masked_key"] is not None
        assert "RGAPI-" in data["masked_key"]
        # La key completa nunca debe aparecer en la respuesta
        full_key = "RGAPI-00000000-0000-0000-0000-000000000000"
        assert full_key not in str(data)

    def test_status_expiring_soon(self):
        from datetime import datetime, timezone, timedelta
        saved_at = (datetime.now(timezone.utc) - timedelta(hours=22)).isoformat()

        def mock_get_config(key: str):
            return {
                "api_key": "RGAPI-test-0000-0000-0000-000000000000",
                "api_key_saved_at": saved_at,
                "api_key_expired": None,
            }.get(key)

        with patch("backend.api.routes.settings.db") as mock_db:
            mock_db.get_config.side_effect = mock_get_config
            r = client.get("/api/v1/settings/api-key/status")

        assert r.status_code == 200
        assert r.json()["status"] == "expiring_soon"

    def test_status_expired(self):
        def mock_get_config(key: str):
            return {
                "api_key": "RGAPI-test-0000-0000-0000-000000000000",
                "api_key_saved_at": "2024-01-01T00:00:00+00:00",
                "api_key_expired": "1",
            }.get(key)

        with patch("backend.api.routes.settings.db") as mock_db:
            mock_db.get_config.side_effect = mock_get_config
            r = client.get("/api/v1/settings/api-key/status")

        assert r.status_code == 200
        assert r.json()["status"] == "expired"

    def test_save_valid_key(self):
        with patch("backend.api.routes.settings.db") as mock_db, \
             patch("backend.api.routes.settings.RiotClient") as mock_client_cls:
            mock_db.get_config.return_value = "la1"
            mock_db.save_config.return_value = None
            mock_db.delete_config.return_value = None
            mock_instance = MagicMock()
            mock_instance.validate_key.return_value = True
            mock_client_cls.return_value = mock_instance

            r = client.post(
                "/api/v1/settings/api-key",
                json={"api_key": "RGAPI-00000000-0000-0000-0000-000000000000"},
            )

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["status"] == "active"
        # Key completa no debe devolverse
        assert "8bb443f4" not in str(data.get("masked_key", ""))

    def test_save_invalid_key_format(self):
        r = client.post(
            "/api/v1/settings/api-key",
            json={"api_key": "not-a-valid-key"},
        )
        assert r.status_code == 422

    def test_save_key_rejected_by_riot(self):
        with patch("backend.api.routes.settings.db") as mock_db, \
             patch("backend.api.routes.settings.RiotClient") as mock_client_cls:
            mock_db.get_config.return_value = "la1"
            mock_instance = MagicMock()
            mock_instance.validate_key.return_value = False
            mock_client_cls.return_value = mock_instance

            r = client.post(
                "/api/v1/settings/api-key",
                json={"api_key": "RGAPI-00000000-0000-0000-0000-000000000000"},
            )

        assert r.status_code == 401

    def test_replace_key(self):
        """Reemplazar una key existente con una nueva válida."""
        with patch("backend.api.routes.settings.db") as mock_db, \
             patch("backend.api.routes.settings.RiotClient") as mock_client_cls:
            mock_db.get_config.return_value = "la1"
            mock_db.save_config.return_value = None
            mock_db.delete_config.return_value = None
            mock_instance = MagicMock()
            mock_instance.validate_key.return_value = True
            mock_client_cls.return_value = mock_instance

            r = client.post(
                "/api/v1/settings/api-key",
                json={"api_key": "RGAPI-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
            )

        assert r.status_code == 200
        # Verifica que se llamó save_config al menos una vez
        mock_db.save_config.assert_called()

    def test_delete_key(self):
        with patch("backend.api.routes.settings.db") as mock_db:
            mock_db.delete_config.return_value = None
            r = client.delete("/api/v1/settings/api-key")

        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        # Verifica que se limpiaron las 3 claves de config
        keys_deleted = [call.args[0] for call in mock_db.delete_config.call_args_list]
        assert "api_key" in keys_deleted
        assert "api_key_saved_at" in keys_deleted
        assert "api_key_expired" in keys_deleted


# ── OpenAPI ────────────────────────────────────────────────────────────────────

class TestOpenAPI:
    def test_docs_available(self):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_openapi_json_available(self):
        r = client.get("/openapi.json")
        assert r.status_code == 200

    def test_openapi_has_all_routes(self):
        r = client.get("/openapi.json")
        paths = r.json()["paths"]
        assert "/api/v1/health" in paths
        assert "/api/v1/coaching" in paths
        assert "/api/v1/matches" in paths
        assert "/api/v1/draft" in paths
        assert "/api/v1/settings" in paths
        assert "/api/v1/dashboard" in paths
        assert "/api/v1/settings/api-key/status" in paths
        assert "/api/v1/matches/{match_id}/review" in paths
        assert "/api/v1/progress" in paths
        assert "/api/v1/knowledge" in paths


# ── Tests del endpoint de Progreso ────────────────────────────────────────────

class TestProgress:
    """Tests para GET /api/v1/progress."""

    def _mock_vm_no_data(self):
        from backend.viewmodels.progress_vm import ProgressViewModel
        return ProgressViewModel(
            has_data=False,
            games_needed_msg="Necesitas 5 partidas más de ADC para ver tu progreso.",
        )

    def _mock_vm_full(self):
        from backend.viewmodels.progress_vm import (
            ProgressViewModel, TimelinePoint, TrendInsight,
            WeeklyGoal, Habit, ChampionInsight, Recommendation,
        )
        timeline = [
            TimelinePoint(label="Hace 30", games_ago_start=25, games_ago_end=35,
                          avg_score=58.0, dominant_champion="Jinx", sample_size=5, trend_arrow="up"),
            TimelinePoint(label="Hoy",     games_ago_start=0,  games_ago_end=5,
                          avg_score=66.0, dominant_champion="Jinx", sample_size=5, trend_arrow=""),
        ]
        trend = TrendInsight(
            category="improving", dim_name="Economy", label="Tu economía mejoró un 15%.",
            delta=8.0, delta_pct=15.0, confidence="high", champion=None,
        )
        goal = WeeklyGoal(
            title="< 4 muertes", metric_key="deaths", metric_label="Muertes",
            target_value=4.0, target_str="< 4 muertes",
            current_avg=5.2, baseline=3.8,
            progress_count=3, total_count=5, pct=60.0,
            status="on_track", motivation="Buen progreso.",
        )
        habit = Habit(type="positive", title="Buen farmeo", description="3 partidas seguidas.", streak=3, is_active=True)
        champ = ChampionInsight(champion="Jinx", games=8, avg_score=70.0, vs_overall=5.0, role="ADC")
        rec   = Recommendation(rank=1, title="Mejorar posicionamiento", body="...",
                                evidence="5 partidas de referencia.", impact="high", metric_key="deaths")

        return ProgressViewModel(
            has_data=True, role="ADC", total_matches=20,
            overall_trend="improving", overall_trend_label="Mejorando",
            overall_delta=8.0, avg_recent=66.0, confidence="preliminary",
            timeline=timeline, score_series=[55.0, 60.0, 62.0, 66.0],
            improving=[trend], declining=[], stable=[],
            habits=[habit], weekly_goal=goal,
            champion_insights=[champ], recommendations=[rec],
            min_games_needed=10,
        )

    def test_progress_no_data_returns_200(self):
        with patch("backend.api.routes.progress.build_progress", return_value=self._mock_vm_no_data()):
            r = client.get("/api/v1/progress")
        assert r.status_code == 200
        data = r.json()
        assert data["has_data"] is False
        assert data["games_needed_msg"] is not None

    def test_progress_full_contract(self):
        with patch("backend.api.routes.progress.build_progress", return_value=self._mock_vm_full()):
            r = client.get("/api/v1/progress")
        assert r.status_code == 200
        data = r.json()
        assert data["has_data"] is True
        assert data["role"] == "ADC"
        assert data["overall_trend"] == "improving"
        assert data["overall_delta"] == 8.0
        assert len(data["timeline"]) == 2
        assert data["timeline"][0]["label"] == "Hace 30"
        assert len(data["improving"]) == 1
        assert data["improving"][0]["confidence"] == "high"
        assert data["weekly_goal"] is not None
        assert data["weekly_goal"]["status"] == "on_track"
        assert data["weekly_goal"]["pct"] == 60.0
        assert len(data["habits"]) == 1
        assert data["habits"][0]["type"] == "positive"
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["impact"] == "high"
        assert len(data["champion_insights"]) == 1
        assert data["champion_insights"][0]["champion"] == "Jinx"

    def test_progress_score_series_is_list(self):
        with patch("backend.api.routes.progress.build_progress", return_value=self._mock_vm_full()):
            r = client.get("/api/v1/progress")
        assert isinstance(r.json()["score_series"], list)


# ── Tests del endpoint de revisión de partida ──────────────────────────────────

class TestMatchReview:
    """Tests para GET /api/v1/matches/{match_id}/review."""

    def _mock_vm_not_found(self):
        from backend.viewmodels.match_review_vm import MatchReviewViewModel
        return MatchReviewViewModel(found=False)

    def _mock_vm_role_unsupported(self):
        from backend.viewmodels.match_review_vm import MatchReviewViewModel
        return MatchReviewViewModel(found=True, match_id="EUW1_123", role="JGL",
                                    champion="Amumu", is_win=False, role_supported=False)

    def _mock_vm_full(self):
        from backend.viewmodels.match_review_vm import (
            MatchReviewViewModel, DimensionReview, MetricReview
        )
        metric = MetricReview(
            key="cs_per_min", label="CS/min",
            value_str="6.1", avg_str="7.0",
            raw=6.1, raw_avg=7.0,
            direction="worse", higher_is_better=True,
        )
        dim = DimensionReview(
            name="Economy", name_es="Economía",
            score=55.0, avg_score=65.0, delta=-10.0,
            is_best=False, is_worst=True,
            metrics=[metric], notes=["CS por debajo del promedio"],
            context="10 puntos bajo tu media",
        )
        return MatchReviewViewModel(
            found=True, match_id="EUW1_ABC", date="2025-06-01",
            champion="Jinx", role="ADC", is_win=True, is_surrender=False,
            duration="28m 14s", kda="5/2/8", kills=5, deaths_n=2, assists=8, cs=175,
            overall_score=62.0, avg_overall=68.0, overall_delta=-6.0,
            dimensions=[dim],
            best_dim_name=None, worst_dim_name="Economy",
            key_error_title="Solo 6.1 CS/min — 0.9 por debajo de tu media de 7.0",
            key_error_body="Mejora el farming.",
            focus_tip="Practica el farming en modo customizado.",
            sample_size=15, confidence="reliable", role_supported=True,
        )

    def test_review_not_found_returns_404(self):
        with patch(
            "backend.api.routes.matches.build_match_review",
            return_value=self._mock_vm_not_found()
        ):
            r = client.get("/api/v1/matches/NO_EXISTE/review")
        assert r.status_code == 404

    def test_review_role_unsupported_returns_200(self):
        with patch(
            "backend.api.routes.matches.build_match_review",
            return_value=self._mock_vm_role_unsupported()
        ):
            r = client.get("/api/v1/matches/EUW1_123/review")
        assert r.status_code == 200
        data = r.json()
        assert data["found"] is True
        assert data["role_supported"] is False

    def test_review_full_contract(self):
        with patch(
            "backend.api.routes.matches.build_match_review",
            return_value=self._mock_vm_full()
        ):
            r = client.get("/api/v1/matches/EUW1_ABC/review")
        assert r.status_code == 200
        data = r.json()
        assert data["found"] is True
        assert data["champion"] == "Jinx"
        assert data["role"] == "ADC"
        assert data["is_win"] is True
        assert data["overall_score"] == 62.0
        assert data["overall_delta"] == -6.0
        assert len(data["dimensions"]) == 1
        dim = data["dimensions"][0]
        assert dim["name"] == "Economy"
        assert dim["name_es"] == "Economía"
        assert dim["is_worst"] is True
        assert len(dim["metrics"]) == 1
        assert dim["metrics"][0]["direction"] == "worse"
        assert data["key_error_title"] is not None
        assert data["focus_tip"] is not None

    def test_review_no_sensitive_data_exposed(self):
        """El endpoint no debe exponer datos internos como puuid o match raw."""
        with patch(
            "backend.api.routes.matches.build_match_review",
            return_value=self._mock_vm_full()
        ):
            r = client.get("/api/v1/matches/EUW1_ABC/review")
        body = r.text
        assert "puuid" not in body.lower()
        assert "raw_match" not in body.lower()


# ── Tests del Knowledge Engine ────────────────────────────────────────────────

class TestKnowledge:
    """Tests para GET /api/v1/knowledge."""

    def _mock_vm_no_data(self):
        from backend.knowledge.models import KnowledgeViewModel, SessionSummary
        return KnowledgeViewModel(
            has_data=False,
            games_needed_msg="Necesitas 5 partidas más de ADC.",
            session=SessionSummary(has_session=False),
        )

    def _mock_vm_full(self):
        from backend.knowledge.models import (
            KnowledgeViewModel, SessionSummary, Goal,
            Pattern, Insight, Recommendation, MemoryEntry,
        )
        session = SessionSummary(
            has_session=True, total_games=3, wins=2, losses=1,
            avg_score=71.0, best_aspect="Economía", worst_aspect="Muertes",
            goal_progress="2 / 3 partidas cumpliendo el objetivo",
            tip=None, session_label="Hoy", matches=[],
        )
        goal = Goal(
            id="abc123", metric_key="deaths", metric_label="muertes",
            target_value=4.0, target_str="< 4 muertes", higher_is_better=False,
            check_window=5, status="active",
            created_at="2025-06-01T10:00:00", completed_at=None,
            progress_count=3, total_count=5, pct=60.0,
        )
        pattern = Pattern(
            id="death_loss", category="death",
            title="Las derrotas aparecen cuando superas 5 muertes",
            description="Análisis de 20 partidas.", evidence="20 partidas.",
            confidence=0.72, actionable="No superes 5 muertes.",
        )
        insight = Insight(
            rank=1, text="Tu mayor oportunidad es reducir muertes.",
            evidence="7 partidas con pattern claro.", category="negative",
            confidence=0.75,
        )
        rec = Recommendation(
            rank=1, title="Reducir muertes", body="Prioriza no morir.",
            why="En derrotas tienes 7.2 muertes vs 3.1 en victorias.",
            impact="Alto", impact_pct=85, confidence=0.78,
            difficulty="Media", goal_str="< 4 muertes en 5 partidas.",
            metric_key="deaths",
        )
        mem = MemoryEntry(
            goal_title="< 5 muertes de muertes", status="completed",
            created_at="2025-05-01", completed_at="2025-05-15",
            metric_key="deaths",
        )
        return KnowledgeViewModel(
            has_data=True, role="ADC", total_matches=30,
            session=session, active_goal=goal,
            memory=[mem], patterns=[pattern],
            insights=[insight], recommendations=[rec],
            confidence="reliable",
        )

    def test_knowledge_no_data(self):
        with patch("backend.api.routes.knowledge.build_knowledge", return_value=self._mock_vm_no_data()):
            r = client.get("/api/v1/knowledge")
        assert r.status_code == 200
        data = r.json()
        assert data["has_data"] is False
        assert data["games_needed_msg"] is not None

    def test_knowledge_full_contract(self):
        with patch("backend.api.routes.knowledge.build_knowledge", return_value=self._mock_vm_full()):
            r = client.get("/api/v1/knowledge")
        assert r.status_code == 200
        data = r.json()
        assert data["has_data"] is True
        assert data["role"] == "ADC"
        assert data["confidence"] == "reliable"

        # Session
        assert data["session"]["has_session"] is True
        assert data["session"]["wins"] == 2
        assert data["session"]["avg_score"] == 71.0

        # Goal
        assert data["active_goal"] is not None
        assert data["active_goal"]["metric_key"] == "deaths"
        assert data["active_goal"]["pct"] == 60.0

        # Patterns, insights, recs, memory
        assert len(data["patterns"]) == 1
        assert data["patterns"][0]["confidence"] == 0.72
        assert len(data["insights"]) == 1
        assert data["insights"][0]["category"] == "negative"
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["impact_pct"] == 85
        assert len(data["memory"]) == 1
        assert data["memory"][0]["status"] == "completed"

    def test_knowledge_no_sensitive_data(self):
        """El endpoint nunca debe exponer el puuid ni datos internos."""
        with patch("backend.api.routes.knowledge.build_knowledge", return_value=self._mock_vm_full()):
            r = client.get("/api/v1/knowledge")
        body = r.text
        assert "puuid" not in body.lower()


# ── Tests del Training Engine ──────────────────────────────────────────────────

class TestTraining:
    """Tests para GET /api/v1/training."""

    def _mock_vm_no_data(self):
        from backend.training.models import TrainingViewModel
        return TrainingViewModel(has_data=False, games_needed_msg="Necesitas 5 partidas más de ADC.")

    def _mock_vm_full(self):
        from backend.training.models import (
            TrainingViewModel, SkillNode, Exercise, ExerciseDot,
            DailyPlan, WeeklySlot, TrainingHistoryEntry,
        )
        node = SkillNode(
            key="survival", name="Supervivencia",
            description="Minimizar muertes evitables.",
            score=58.0, confidence=0.7, status="active",
            priority=1, dim_key="Positioning", primary_metric="deaths",
        )
        dot = ExerciseDot(match_id="EUW1_1", success=True, value=3.0, played_at="2025-06-20T10:00:00")
        exercise = Exercise(
            id="survival_deaths_4.00", skill_key="survival", skill_name="Supervivencia",
            title="No morir más de 4 veces por partida",
            description="Ejercicio de supervivencia durante las próximas 5 partidas.",
            metric_key="deaths", threshold=4.0, direction="less_than",
            target_games=5, required_success=4,
            success_count=2, games_checked=3,
            started_at="2025-06-20T08:00:00",
            why="En tus derrotas mueres significativamente más.",
            how_measured="Al finalizar cada partida el sistema comprueba tus muertes.",
            expected_gain="~8-12 puntos de mejora en Posicionamiento.",
            unlocks="farming", status="active", dots=[dot],
        )
        daily_plan = DailyPlan(
            skill_name="Supervivencia",
            exercise_title="No morir más de 4 veces por partida",
            focus_tip="Antes de cada pelea pregúntate: ¿tengo escapatoria?",
            success_condition="Si terminas con ≤ 4 muertes",
            estimated_games=2, priority_label="Media",
        )
        slot = WeeklySlot(
            week=1, skill_name="Supervivencia", skill_key="survival",
            is_current=True, status="active",
            goal_str="Minimizar muertes evitables.",
        )
        hist = TrainingHistoryEntry(
            exercise_id="survival_deaths_5.00", skill_key="survival",
            skill_name="Supervivencia",
            title="No morir más de 5 veces por partida",
            started_at="2025-05-01T10:00:00", completed_at="2025-05-10T10:00:00",
            games_checked=5, success_count=4, impact=4.2,
        )
        return TrainingViewModel(
            has_data=True, role="ADC", total_matches=25,
            skill_tree=[node], active_exercise=exercise,
            daily_plan=daily_plan, weekly_roadmap=[slot],
            history=[hist], next_skill_name="Farm",
            next_skill_reason="Cuando completes este ejercicio desbloquearás Farm.",
            confidence="preliminary",
        )

    def test_training_no_data(self):
        with patch("backend.api.routes.training.build_training", return_value=self._mock_vm_no_data()):
            r = client.get("/api/v1/training")
        assert r.status_code == 200
        data = r.json()
        assert data["has_data"] is False
        assert data["games_needed_msg"] is not None

    def test_training_full_contract(self):
        with patch("backend.api.routes.training.build_training", return_value=self._mock_vm_full()):
            r = client.get("/api/v1/training")
        assert r.status_code == 200
        data = r.json()
        assert data["has_data"] is True
        assert data["role"] == "ADC"
        assert data["confidence"] == "preliminary"

        # Skill tree
        assert len(data["skill_tree"]) == 1
        assert data["skill_tree"][0]["status"] == "active"
        assert data["skill_tree"][0]["score"] == 58.0

        # Exercise
        ex = data["active_exercise"]
        assert ex is not None
        assert ex["metric_key"] == "deaths"
        assert ex["threshold"] == 4.0
        assert ex["direction"] == "less_than"
        assert ex["success_count"] == 2
        assert len(ex["dots"]) == 1
        assert ex["dots"][0]["success"] is True

        # Daily plan
        assert data["daily_plan"] is not None
        assert "muertes" in data["daily_plan"]["success_condition"]

        # Roadmap
        assert len(data["weekly_roadmap"]) == 1
        assert data["weekly_roadmap"][0]["is_current"] is True

        # History
        assert len(data["history"]) == 1
        assert data["history"][0]["impact"] == 4.2

        # Next skill
        assert data["next_skill_name"] == "Farm"

    def test_training_in_openapi_paths(self):
        r = client.get("/openapi.json")
        paths = list(r.json()["paths"].keys())
        assert "/api/v1/training" in paths
