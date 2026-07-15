"""
Tests del cliente de telemetría (telemetry.py + cola en db.py).

Lo crítico aquí es la privacidad: los payloads se construyen por lista
blanca y estos tests verifican que NINGÚN dato identificable (puuid,
riot_id, api_key, match_id real) sale en ningún resumen.
"""

import json

import pytest
import requests

import db
import scorer_v2 as sv2
import telemetry


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Cada test corre contra una DB SQLite limpia y temporal."""
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    yield


PUUID = "puuid-secreto-abc-123"


def _setup_account(tier: str = "GOLD") -> None:
    db.save_config("puuid", PUUID)
    db.save_config("api_key", "RGAPI-super-secreta")
    db.save_player({
        "puuid": PUUID, "riot_id": "NombreReal", "tag": "LA1",
        "level": 120, "rank": f"{tier} II", "tier": tier, "lp": 50,
        "updated_at": "2026-07-08T00:00:00+00:00",
    })


def _save_matches(n: int = 6, role: str = "MID") -> None:
    for i in range(n):
        db.save_match({
            "match_id": f"LA1_{1000+i}", "puuid": PUUID, "champion": "Ahri",
            "role": role, "result": "WIN" if i % 2 == 0 else "LOSS",
            "kills": 7, "deaths": 3, "assists": 8, "cs": 210, "damage": 24000,
            "duration_sec": 1800, "played_at": f"2026-07-{i+1:02d}T00:00:00+00:00",
            "gold_earned": 12000, "cs_at_10": 70, "kill_participation": 0.6,
            "team_damage_pct": 0.28, "game_version": "15.13",
        })


# ── Consentimiento ────────────────────────────────────────────────────────────

def test_consent_defaults_to_not_asked():
    assert telemetry.consent_status() is None
    assert telemetry.is_enabled() is False


def test_consent_can_be_granted_and_revoked():
    telemetry.set_consent(True)
    assert telemetry.is_enabled() is True
    telemetry.set_consent(False)
    assert telemetry.is_enabled() is False
    assert telemetry.consent_status() == "no"


def test_no_consent_means_no_enqueue():
    _setup_account()
    _save_matches()
    assert telemetry.enqueue_match_summaries(PUUID) == 0
    assert db.telemetry_queue_stats() == {}


# ── Anonimización (lista blanca) ─────────────────────────────────────────────

def test_match_summary_contains_no_identifying_data():
    _setup_account()
    _save_matches()
    telemetry.set_consent(True)

    matches = db.get_matches(PUUID, role="MID", limit=50)
    ms = sv2.score_match(matches[0], matches)
    payload = telemetry.build_match_summary(matches[0], ms)
    raw = json.dumps(payload)

    assert PUUID not in raw                    # puuid jamás
    assert "NombreReal" not in raw             # riot_id jamás
    assert "RGAPI" not in raw                  # api_key jamás
    assert "LA1_" not in raw                   # match_id real jamás (solo hash)
    assert payload["elo_tier"] == "GOLD"       # tier sí, división no
    assert "II" not in raw.replace("15.13", "")  # sin división del rango
    assert payload["patch"] == "15.13"
    assert payload["role"] == "MID"
    assert payload["champion"] == "Ahri"


def test_match_hash_is_salted_per_install():
    _setup_account()
    h1 = telemetry._match_hash("LA1_999")
    # Otra instalación (otro install_id) produce otro hash para el mismo match
    db.save_config("telemetry_install_id", "f" * 32)
    h2 = telemetry._match_hash("LA1_999")
    assert h1 != h2


def test_unranked_player_reports_unranked_tier():
    _setup_account(tier="")
    telemetry.set_consent(True)
    _save_matches(1)
    m = db.get_matches(PUUID, limit=1)[0]
    payload = telemetry.build_match_summary(m, None)
    assert payload["elo_tier"] == "UNRANKED"


# ── Cola: dedup, backoff, cap ─────────────────────────────────────────────────

def test_enqueue_is_deduplicated():
    _setup_account()
    _save_matches(6)
    telemetry.set_consent(True)

    first  = telemetry.enqueue_match_summaries(PUUID)
    second = telemetry.enqueue_match_summaries(PUUID)
    assert first == 6
    assert second == 0
    assert db.telemetry_queue_stats() == {"pending": 6}


def test_coaching_summary_dedups_per_day():
    _setup_account()
    telemetry.set_consent(True)

    class FakeCR:
        confidence_level = "reliable"; sample_size = 10
        primary_problem = "Exceso de muertes MID"
        improvements = ["Farm deficiente"]; strengths = []

    class FakeSR:
        overall_score = 55.0; consistency_score = 70.0; trend = "stable"

    assert telemetry.enqueue_coaching_summary("MID", FakeCR(), FakeSR()) is True
    assert telemetry.enqueue_coaching_summary("MID", FakeCR(), FakeSR()) is False


def test_failed_send_schedules_retry_with_backoff():
    db.telemetry_enqueue("match", "k1", {"a": 1})
    item = db.telemetry_pending()[0]
    db.telemetry_mark_failed([item["id"]])
    # Tras el fallo el elemento sigue pendiente pero con next_attempt futuro
    assert db.telemetry_queue_stats() == {"pending": 1}
    assert db.telemetry_pending() == []     # aún no venció el backoff


def test_queue_cap_evicts_oldest(monkeypatch):
    monkeypatch.setattr(db, "_TELEMETRY_QUEUE_CAP", 3)
    for i in range(5):
        db.telemetry_enqueue("match", f"k{i}", {"i": i})
    stats = db.telemetry_queue_stats()
    assert stats["pending"] == 3
    keys = {p["dedup_key"] for p in db.telemetry_pending()}
    assert keys == {"k2", "k3", "k4"}       # los 2 más antiguos descartados


def test_champion_summaries_enqueued_with_classification():
    _setup_account()
    _save_matches(6)
    telemetry.set_consent(True)

    from backend.services.champion_analyzer import analyze_champion_pool
    matches = db.get_matches(PUUID, role="MID", limit=50)
    sr = sv2.analyze_player(matches, "MID")
    cpa = analyze_champion_pool(matches, "MID", sr.match_scores)

    queued = telemetry.enqueue_champion_summaries("MID", cpa)
    assert queued >= 1
    # dedup por día: segunda llamada no encola nada
    assert telemetry.enqueue_champion_summaries("MID", cpa) == 0

    payloads = [p["payload"] for p in db.telemetry_pending() if p["kind"] == "champion"]
    assert payloads[0]["champion"] == "Ahri"
    assert payloads[0]["classification"] in ("MAIN", "CARRY", "COMFORT", "TRAP", "SOLID")
    raw = json.dumps(payloads)
    assert PUUID not in raw and "NombreReal" not in raw


# ── Envío en segundo plano ────────────────────────────────────────────────────

def _enable_sending():
    telemetry.set_consent(True)
    db.save_config("telemetry_server_url", "http://localhost:9")


def test_flush_marks_sent_on_success(monkeypatch):
    _enable_sending()
    db.telemetry_enqueue("match", "k1", {"a": 1})

    class OKResp:
        status_code = 202

    monkeypatch.setattr(telemetry.requests, "post", lambda *a, **k: OKResp())
    telemetry._flush()
    assert db.telemetry_queue_stats() == {"sent": 1}


def test_flush_survives_connection_error(monkeypatch):
    _enable_sending()
    db.telemetry_enqueue("match", "k1", {"a": 1})

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("sin internet")

    monkeypatch.setattr(telemetry.requests, "post", boom)
    telemetry._flush()                       # no debe lanzar excepción
    assert db.telemetry_queue_stats() == {"pending": 1}


def test_flush_drops_permanently_rejected_payloads(monkeypatch):
    _enable_sending()
    db.telemetry_enqueue("match", "k1", {"a": 1})

    class Rejected:
        status_code = 422

    monkeypatch.setattr(telemetry.requests, "post", lambda *a, **k: Rejected())
    telemetry._flush()
    assert db.telemetry_queue_stats() == {"sent": 1}   # fuera de la cola, no reintento eterno


def test_flush_async_is_noop_without_server_url(monkeypatch):
    telemetry.set_consent(True)
    called = []
    monkeypatch.setattr(telemetry.threading, "Thread",
                        lambda **k: called.append(1) or type("T", (), {"start": lambda s: None})())
    telemetry.flush_async()
    assert called == []                      # sin URL no se lanza ni el hilo
