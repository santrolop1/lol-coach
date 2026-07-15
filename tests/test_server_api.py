"""
Tests del backend de conocimiento (server/): API REST, validación,
idempotencia de la ingesta y generación de snapshots de conocimiento.
"""

import pytest
from fastapi.testclient import TestClient

from server import database
from server.app import create_app
from server.knowledge import MIN_SAMPLE, publish_snapshot


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path):
    """App nueva contra una DB SQLite temporal, por test."""
    database.reset_engine_for_tests(f"sqlite:///{tmp_path}/knowledge.db")
    app = create_app()
    with TestClient(app) as c:
        yield c


INSTALL_ID = "a" * 32


def _match_item(i: int = 0, **overrides) -> dict:
    item = {
        "schema_version": 1,
        "client_version": "1.3.0",
        "install_id": INSTALL_ID,
        "match_hash": f"{i:024x}",
        "patch": "15.13",
        "role": "MID",
        "champion": "Ahri",
        "elo_tier": "GOLD",
        "result": "WIN" if i % 2 == 0 else "LOSS",
        "duration_sec": 1800,
        "surrender": False,
        "overall_score": 60.0,
        "dimensions": {"Lane Dominance": 55.0, "Damage Impact": 62.0, "Survival": 63.0},
        "stats": {"kills": 7, "deaths": 3 + (i % 5), "assists": 8,
                  "cs_per_min": 7.1, "gold_per_min": 410.0,
                  "kill_participation": 0.6, "cs_at_10": 70},
        "loadout": None,
    }
    item.update(overrides)
    return item


# ── Salud ─────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Ingesta de partidas ───────────────────────────────────────────────────────

def test_ingest_valid_match_batch(client):
    r = client.post("/telemetry/match", json={"items": [_match_item(0), _match_item(1)]})
    assert r.status_code == 202
    assert r.json() == {"accepted": 2, "duplicates": 0}


def test_ingest_is_idempotent(client):
    batch = {"items": [_match_item(0)]}
    assert client.post("/telemetry/match", json=batch).json()["accepted"] == 1
    r = client.post("/telemetry/match", json=batch)
    assert r.json() == {"accepted": 0, "duplicates": 1}


def test_same_match_hash_from_other_user_is_not_duplicate(client):
    client.post("/telemetry/match", json={"items": [_match_item(0)]})
    other = _match_item(0, install_id="b" * 32)
    r = client.post("/telemetry/match", json={"items": [other]})
    assert r.json()["accepted"] == 1


# ── Validación estricta ───────────────────────────────────────────────────────

def test_invalid_role_rejected(client):
    r = client.post("/telemetry/match", json={"items": [_match_item(0, role="FEEDER")]})
    assert r.status_code == 422


def test_unknown_extra_field_rejected(client):
    bad = _match_item(0)
    bad["riot_id"] = "Nombre#LA1"       # un cliente defectuoso jamás debe colar esto
    r = client.post("/telemetry/match", json={"items": [bad]})
    assert r.status_code == 422


def test_out_of_range_values_rejected(client):
    assert client.post("/telemetry/match",
                       json={"items": [_match_item(0, duration_sec=60)]}).status_code == 422
    assert client.post("/telemetry/match",
                       json={"items": [_match_item(0, overall_score=150.0)]}).status_code == 422
    assert client.post("/telemetry/match",
                       json={"items": [_match_item(0, champion="a; DROP TABLE--")]}).status_code == 422


def test_oversized_batch_rejected(client):
    items = [_match_item(i) for i in range(101)]
    r = client.post("/telemetry/match", json={"items": items})
    assert r.status_code == 422


def test_empty_batch_rejected(client):
    assert client.post("/telemetry/match", json={"items": []}).status_code == 422


# ── Ingesta de sesiones y campeones ───────────────────────────────────────────

def test_ingest_coaching_session(client):
    item = {
        "schema_version": 1, "client_version": "1.3.0", "install_id": INSTALL_ID,
        "role": "MID", "elo_tier": "GOLD", "confidence_level": "reliable",
        "sample_size": 12, "primary_problem": "Exceso de muertes MID",
        "improvements": ["Farm deficiente en fase de líneas"],
        "strengths": ["Alto impacto de daño"],
        "overall_score": 55.0, "consistency": 68.0, "trend": "improving",
    }
    r = client.post("/telemetry/session", json={"items": [item]})
    assert r.status_code == 202
    assert r.json()["accepted"] == 1


def test_ingest_champion_report_clamps_wins(client):
    item = {
        "schema_version": 1, "client_version": "1.3.0", "install_id": INSTALL_ID,
        "role": "ADC", "elo_tier": "PLATINUM", "champion": "KaiSa",
        "games": 10, "wins": 99, "avg_score": 61.5, "classification": "CARRY",
    }
    r = client.post("/telemetry/champion", json={"items": [item]})
    assert r.status_code == 202


# ── Sistema de conocimiento ───────────────────────────────────────────────────

def test_knowledge_endpoints_404_before_first_snapshot(client):
    assert client.get("/knowledge/version").status_code == 404
    assert client.get("/knowledge/update").status_code == 404


def test_knowledge_snapshot_respects_min_sample(client):
    # 10 partidas < MIN_SAMPLE → snapshot sin umbrales pero con total correcto
    client.post("/telemetry/match", json={"items": [_match_item(i) for i in range(10)]})
    with database.SessionLocal() as s:
        kv = publish_snapshot(s)
    assert kv.version == 1
    assert kv.payload["total_matches"] == 10
    assert kv.payload["thresholds"] == {}          # nunca publicar con N<50
    assert kv.payload["recommendations"] == {}


def test_knowledge_snapshot_generates_thresholds_with_enough_data(client):
    # MIN_SAMPLE partidas del mismo (rol, tier) → percentiles publicados
    for start in range(0, MIN_SAMPLE, 50):
        items = [_match_item(i) for i in range(start, min(start + 50, MIN_SAMPLE))]
        assert client.post("/telemetry/match", json={"items": items}).status_code == 202

    with database.SessionLocal() as s:
        kv = publish_snapshot(s)

    thresholds = kv.payload["thresholds"]
    assert "MID:GOLD" in thresholds
    deaths = thresholds["MID:GOLD"]["deaths"]["all"]
    assert deaths["n"] >= MIN_SAMPLE
    assert deaths["p25"] <= deaths["p50"] <= deaths["p75"]

    stats = kv.payload["global_stats"]["MID:GOLD"]
    assert stats["matches"] == MIN_SAMPLE
    assert 0.0 <= stats["winrate"] <= 1.0

    recs = kv.payload["recommendations"]["MID:GOLD"]
    assert recs[0]["champion"] == "Ahri"

    # Endpoints REST sirven el snapshot
    v = client.get("/knowledge/version").json()
    assert v["version"] == 1
    upd = client.get("/knowledge/update").json()
    assert upd["payload"]["total_matches"] == MIN_SAMPLE


def test_knowledge_versions_increment(client):
    with database.SessionLocal() as s:
        assert publish_snapshot(s).version == 1
        assert publish_snapshot(s).version == 2
    assert client.get("/knowledge/version").json()["version"] == 2
