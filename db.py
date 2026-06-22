"""
db.py — Capa de almacenamiento SQLite para LoL Coach.

Responsabilidades:
- Crear la base de datos y las tablas al arrancar.
- Proveer funciones directas de lectura y escritura (sin Repository pattern).
"""

import sqlite3
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "lol_coach.db"


def _get_conn() -> sqlite3.Connection:
    """Abre (o crea) la conexión SQLite con row_factory para devolver dicts."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ---------------------------------------------------------------------------
# Inicialización de tablas
# ---------------------------------------------------------------------------

CREATE_CONFIG = """
CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_PLAYER = """
CREATE TABLE IF NOT EXISTS player (
    puuid      TEXT PRIMARY KEY,
    riot_id    TEXT NOT NULL,
    tag        TEXT NOT NULL,
    level      INTEGER,
    rank       TEXT,
    tier       TEXT,
    lp         INTEGER,
    updated_at TEXT
);
"""

CREATE_MATCH = """
CREATE TABLE IF NOT EXISTS match (
    match_id     TEXT PRIMARY KEY,
    puuid        TEXT NOT NULL,
    champion     TEXT,
    role         TEXT,
    result       TEXT,
    kills        INTEGER,
    deaths       INTEGER,
    assists      INTEGER,
    cs           INTEGER,
    damage       INTEGER,
    duration_sec INTEGER,
    played_at    TEXT
);
"""

CREATE_ANALYSIS = """
CREATE TABLE IF NOT EXISTS analysis (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id     TEXT NOT NULL,
    farm_score   REAL,
    fight_score  REAL,
    survival_score REAL,
    overall_score  REAL,
    strengths_json    TEXT,
    weaknesses_json   TEXT,
    created_at   TEXT,
    FOREIGN KEY (match_id) REFERENCES match(match_id)
);
"""


def init_db() -> None:
    """Crea todas las tablas si no existen. Llamar al arrancar la app."""
    with _get_conn() as conn:
        conn.execute(CREATE_CONFIG)
        conn.execute(CREATE_PLAYER)
        conn.execute(CREATE_MATCH)
        conn.execute(CREATE_ANALYSIS)
        conn.commit()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def save_config(key: str, value: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()


def get_config(key: str) -> str | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else None


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

def save_player(player: dict) -> None:
    """
    Inserta o actualiza el perfil del jugador.

    Campos esperados en `player`:
        puuid, riot_id, tag, level, rank, tier, lp, updated_at
    """
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO player
                (puuid, riot_id, tag, level, rank, tier, lp, updated_at)
            VALUES
                (:puuid, :riot_id, :tag, :level, :rank, :tier, :lp, :updated_at)
            """,
            player,
        )
        conn.commit()


def get_player(puuid: str) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM player WHERE puuid = ?", (puuid,)
        ).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------

def save_match(match: dict) -> None:
    """
    Inserta una partida. Ignora si el match_id ya existe.

    Campos esperados en `match`:
        match_id, puuid, champion, role, result,
        kills, deaths, assists, cs, damage, duration_sec, played_at
    """
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO match
                (match_id, puuid, champion, role, result,
                 kills, deaths, assists, cs, damage, duration_sec, played_at)
            VALUES
                (:match_id, :puuid, :champion, :role, :result,
                 :kills, :deaths, :assists, :cs, :damage, :duration_sec, :played_at)
            """,
            match,
        )
        conn.commit()


def get_matches(puuid: str, role: str | None = None, limit: int = 50) -> list[dict]:
    """
    Devuelve las últimas `limit` partidas del jugador.
    Si `role` se especifica ('ADC' | 'TOP'), filtra por rol.
    """
    with _get_conn() as conn:
        if role:
            rows = conn.execute(
                """
                SELECT * FROM match
                WHERE puuid = ? AND role = ?
                ORDER BY played_at DESC
                LIMIT ?
                """,
                (puuid, role, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM match
                WHERE puuid = ?
                ORDER BY played_at DESC
                LIMIT ?
                """,
                (puuid, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def match_exists(match_id: str) -> bool:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM match WHERE match_id = ?", (match_id,)
        ).fetchone()
    return row is not None


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def save_analysis(analysis: dict) -> None:
    """
    Guarda el resultado de scoring de una partida.

    Campos esperados en `analysis`:
        match_id, farm_score, fight_score, survival_score, overall_score,
        strengths_json (str JSON), weaknesses_json (str JSON), created_at
    """
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO analysis
                (match_id, farm_score, fight_score, survival_score, overall_score,
                 strengths_json, weaknesses_json, created_at)
            VALUES
                (:match_id, :farm_score, :fight_score, :survival_score, :overall_score,
                 :strengths_json, :weaknesses_json, :created_at)
            """,
            analysis,
        )
        conn.commit()


def get_analysis(puuid: str, role: str | None = None, limit: int = 20) -> list[dict]:
    """
    Devuelve los análisis de las últimas partidas del jugador,
    joinados con la tabla match para incluir rol y campeón.
    """
    with _get_conn() as conn:
        if role:
            rows = conn.execute(
                """
                SELECT a.*, m.champion, m.role, m.result, m.played_at
                FROM analysis a
                JOIN match m ON a.match_id = m.match_id
                WHERE m.puuid = ? AND m.role = ?
                ORDER BY m.played_at DESC
                LIMIT ?
                """,
                (puuid, role, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT a.*, m.champion, m.role, m.result, m.played_at
                FROM analysis a
                JOIN match m ON a.match_id = m.match_id
                WHERE m.puuid = ?
                ORDER BY m.played_at DESC
                LIMIT ?
                """,
                (puuid, limit),
            ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Entry point de prueba
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    print(f"Base de datos lista en: {DB_PATH}")

    # --- Prueba config ---
    save_config("api_key", "TEST-KEY-123")
    assert get_config("api_key") == "TEST-KEY-123"
    print("✓ config: save/get OK")

    # --- Prueba player ---
    from datetime import datetime, timezone
    player_data = {
        "puuid": "abc-puuid-123",
        "riot_id": "Faker",
        "tag": "T1",
        "level": 500,
        "rank": "CHALLENGER",
        "tier": "I",
        "lp": 1200,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_player(player_data)
    p = get_player("abc-puuid-123")
    assert p["riot_id"] == "Faker"
    print("✓ player: save/get OK")

    # --- Prueba match ---
    match_data = {
        "match_id": "EUW1_123456",
        "puuid": "abc-puuid-123",
        "champion": "Jinx",
        "role": "ADC",
        "result": "WIN",
        "kills": 8,
        "deaths": 2,
        "assists": 5,
        "cs": 210,
        "damage": 35000,
        "duration_sec": 1800,
        "played_at": datetime.now(timezone.utc).isoformat(),
    }
    save_match(match_data)
    matches = get_matches("abc-puuid-123", role="ADC")
    assert len(matches) == 1
    assert matches[0]["champion"] == "Jinx"
    print("✓ match: save/get OK")

    # --- Prueba analysis ---
    analysis_data = {
        "match_id": "EUW1_123456",
        "farm_score": 72.5,
        "fight_score": 85.0,
        "survival_score": 90.0,
        "overall_score": 82.5,
        "strengths_json": json.dumps(["Buen KDA", "Daño alto"]),
        "weaknesses_json": json.dumps(["CS mejorable"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    save_analysis(analysis_data)
    analysis = get_analysis("abc-puuid-123")
    assert len(analysis) == 1
    assert analysis[0]["overall_score"] == 82.5
    print("✓ analysis: save/get OK")

    print("\nTodos los tests pasaron.")
