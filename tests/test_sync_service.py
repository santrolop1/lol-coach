"""
tests/test_sync_service.py — Tests para backend/services/sync_service.py

Cubre:
- Constante SYNC_FETCH_COUNT correcta (fix del bug de partidas perdidas)
- Lógica de tiempo (should_sync, minutes_since_last_sync)
- Estructura de SyncResult
- sync_status_label con distintos tiempos
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.sync_service import (
    SYNC_FETCH_COUNT,
    SYNC_INTERVAL_MINUTES,
    SyncResult,
    get_last_sync,
    minutes_since_last_sync,
    should_sync,
    sync_status_label,
    invalidate_caches,
)


# ── Constantes ─────────────────────────────────────────────────────────────────

class TestConstants:
    def test_fetch_count_at_least_50(self):
        """Bug fix: el count debe ser ≥50 para no perder partidas en sesiones largas."""
        assert SYNC_FETCH_COUNT >= 50, (
            f"SYNC_FETCH_COUNT={SYNC_FETCH_COUNT} es demasiado bajo. "
            "Con 20 se pierden partidas si el usuario juega mucho entre syncs."
        )

    def test_fetch_count_is_public(self):
        """La constante debe ser pública (sin guión bajo) para ser configurable."""
        import backend.services.sync_service as svc
        assert hasattr(svc, "SYNC_FETCH_COUNT"), "SYNC_FETCH_COUNT debe ser pública"

    def test_sync_interval_is_positive(self):
        assert SYNC_INTERVAL_MINUTES > 0


# ── SyncResult ─────────────────────────────────────────────────────────────────

class TestSyncResult:
    def test_fields_exist(self):
        r = SyncResult(
            status="ok", saved=3, skipped=1,
            new_found=4, error_msg=None,
            synced_at=datetime.now(timezone.utc),
        )
        assert r.status == "ok"
        assert r.saved == 3
        assert r.skipped == 1
        assert r.new_found == 4
        assert r.error_msg is None
        assert r.synced_at is not None

    def test_no_credentials_status(self):
        r = SyncResult(
            status="no_credentials", saved=0, skipped=0,
            new_found=0, error_msg=None, synced_at=None,
        )
        assert r.status == "no_credentials"
        assert r.saved == 0

    def test_rate_limited_status(self):
        r = SyncResult(
            status="rate_limited", saved=2, skipped=0,
            new_found=5, error_msg="Rate limit alcanzado.",
            synced_at=datetime.now(timezone.utc),
        )
        assert r.status == "rate_limited"
        assert r.error_msg is not None


# ── Tiempo ─────────────────────────────────────────────────────────────────────

class TestSyncTiming:
    def test_minutes_since_never_synced_returns_inf(self):
        with patch("backend.services.sync_service.get_last_sync", return_value=None):
            assert minutes_since_last_sync() == float("inf")

    def test_minutes_since_recent_sync_is_small(self):
        recent = datetime.now(timezone.utc) - timedelta(minutes=5)
        with patch("backend.services.sync_service.get_last_sync", return_value=recent):
            mins = minutes_since_last_sync()
            assert 4.9 < mins < 5.1

    def test_should_sync_when_never_synced(self):
        with patch("backend.services.sync_service.minutes_since_last_sync", return_value=float("inf")):
            assert should_sync() is True

    def test_should_not_sync_when_recent(self):
        with patch("backend.services.sync_service.minutes_since_last_sync", return_value=2.0):
            assert should_sync() is False

    def test_should_sync_after_interval(self):
        with patch("backend.services.sync_service.minutes_since_last_sync",
                   return_value=float(SYNC_INTERVAL_MINUTES + 1)):
            assert should_sync() is True


# ── sync_status_label ──────────────────────────────────────────────────────────

class TestSyncStatusLabel:
    def test_never_synced(self):
        with patch("backend.services.sync_service.get_last_sync", return_value=None):
            assert sync_status_label() == "Sin sincronizar"

    def test_just_synced(self):
        now = datetime.now(timezone.utc)
        with patch("backend.services.sync_service.get_last_sync", return_value=now):
            label = sync_status_label()
            assert "ahora" in label.lower() or "min" in label.lower()

    def test_synced_minutes_ago(self):
        past = datetime.now(timezone.utc) - timedelta(minutes=10)
        with patch("backend.services.sync_service.get_last_sync", return_value=past):
            label = sync_status_label()
            assert "min" in label

    def test_synced_hours_ago(self):
        past = datetime.now(timezone.utc) - timedelta(hours=3)
        with patch("backend.services.sync_service.get_last_sync", return_value=past):
            label = sync_status_label()
            assert "h" in label

    def test_synced_days_ago(self):
        past = datetime.now(timezone.utc) - timedelta(days=2)
        with patch("backend.services.sync_service.get_last_sync", return_value=past):
            label = sync_status_label()
            assert "día" in label


# ── invalidate_caches ──────────────────────────────────────────────────────────

class TestInvalidateCaches:
    def test_removes_cpa_keys(self):
        state = {"cpa_ADC_8080_10_abc": "data", "other_key": "keep"}
        invalidate_caches(state)
        assert "cpa_ADC_8080_10_abc" not in state
        assert "other_key" in state

    def test_removes_champ_map_keys(self):
        state = {"champ_map_8080_secret": {1: "Jinx"}, "foo": "bar"}
        invalidate_caches(state)
        assert "champ_map_8080_secret" not in state
        assert "foo" in state

    def test_empty_state_no_error(self):
        state = {}
        invalidate_caches(state)
        assert state == {}

    def test_no_matching_keys_unchanged(self):
        state = {"coaching_role": "ADC", "coaching_window": "Últimas 20"}
        invalidate_caches(state)
        assert len(state) == 2
