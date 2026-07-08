"""
db.py — Capa de almacenamiento SQLite para LoL Coach.

Responsabilidades:
- Crear la base de datos y las tablas al arrancar.
- Migrar columnas V2 sin perder datos existentes.
- Proveer funciones directas de lectura y escritura (sin Repository pattern).
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "lol_coach.db"


@contextmanager
def _get_conn():
    """
    Abre (o crea) la conexión SQLite con row_factory para devolver dicts.

    Usar siempre como `with _get_conn() as conn:` — además de manejar el
    commit/rollback de la transacción (comportamiento nativo de sqlite3.Connection
    como context manager), esto también CIERRA la conexión al salir del bloque.
    Antes se devolvía la conexión directamente: `with` solo gestiona la
    transacción, nunca cierra el socket/handle del archivo, así que cada
    llamada a una función de este módulo dejaba una conexión abierta sin
    liberar durante toda la vida del proceso.
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Definición de columnas V2 (nombre, tipo SQLite)
# ---------------------------------------------------------------------------

_V2_COLUMNS: list[tuple[str, str]] = [
    # Economía
    ("gold_earned",           "INTEGER"),
    # Visión
    ("vision_score",          "INTEGER"),
    ("wards_placed",          "INTEGER"),
    ("wards_killed",          "INTEGER"),
    ("control_wards_placed",  "INTEGER"),  # detectorWardsPlaced
    ("control_wards_bought",  "INTEGER"),  # visionWardsBoughtInGame
    # Daño y objetivos
    ("damage_to_objectives",  "INTEGER"),
    ("damage_to_turrets",     "INTEGER"),
    ("damage_taken",          "INTEGER"),
    ("damage_self_mitigated", "INTEGER"),
    # Utilidad
    ("heals_on_teammates",    "INTEGER"),
    ("time_ccing_others",     "REAL"),
    ("turret_takedowns",      "INTEGER"),
    ("turret_plates_taken",   "INTEGER"),  # challenges.turretPlatesTaken
    # Supervivencia
    ("time_spent_dead",       "INTEGER"),
    ("longest_time_alive",    "INTEGER"),
    # Challenges (calculados por Riot)
    ("kill_participation",    "REAL"),     # challenges.killParticipation
    ("team_damage_pct",       "REAL"),     # challenges.teamDamagePercentage
    ("cs_at_10",              "INTEGER"),  # challenges.laneMinionsFirst10Minutes
    ("max_cs_advantage",      "INTEGER"),  # challenges.maxCsAdvantageOnLaneOpponent
    # Objetivos mayores (JGL)
    ("baron_kills",           "INTEGER"),
    ("dragon_kills",          "INTEGER"),
    ("objectives_stolen",     "INTEGER"),
    ("enemy_jungle_cs",       "INTEGER"),  # totalEnemyJungleMinionsKilled
    # Flags
    ("game_ended_surrender",  "INTEGER"),  # gameEndedInEarlySurrender (BOOL → 0/1)
    ("first_blood",           "INTEGER"),  # firstBloodKill (BOOL → 0/1)
]


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

def _migrate_match_table(conn: sqlite3.Connection) -> int:
    """
    Añade las columnas V2 a la tabla match si no existen todavía.
    Usa PRAGMA table_info para detectar columnas existentes (compatible con
    todas las versiones de SQLite sin necesidad de ALTER TABLE IF NOT EXISTS).

    Devuelve el número de columnas añadidas en esta ejecución.
    """
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(match)").fetchall()
    }
    added = 0
    for col_name, col_type in _V2_COLUMNS:
        if col_name not in existing:
            conn.execute(
                f"ALTER TABLE match ADD COLUMN {col_name} {col_type};"
            )
            added += 1
    return added


CREATE_MATCH_INDEX = """
CREATE INDEX IF NOT EXISTS idx_match_puuid_role_played
ON match (puuid, role, played_at DESC);
"""

CREATE_EVENT_LOG = """
CREATE TABLE IF NOT EXISTS event_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    screen     TEXT,
    payload    TEXT,
    created_at TEXT NOT NULL
);
"""

CREATE_EVENT_LOG_INDEX = """
CREATE INDEX IF NOT EXISTS idx_event_log_session_created
ON event_log (session_id, created_at);
"""

CREATE_FEEDBACK = """
CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    context    TEXT NOT NULL,
    champion   TEXT,
    stars      INTEGER NOT NULL,
    comment    TEXT,
    created_at TEXT NOT NULL
);
"""


def init_db() -> None:
    """Crea todas las tablas si no existen y aplica migraciones V2."""
    with _get_conn() as conn:
        conn.execute(CREATE_CONFIG)
        conn.execute(CREATE_PLAYER)
        conn.execute(CREATE_MATCH)
        _migrate_match_table(conn)
        conn.execute(CREATE_MATCH_INDEX)
        conn.execute(CREATE_EVENT_LOG)
        conn.execute(CREATE_EVENT_LOG_INDEX)
        conn.execute(CREATE_FEEDBACK)
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
    Soporta tanto el esquema V1 (12 campos) como V2 (38 campos).
    """
    # Columnas base V1 siempre presentes
    base_cols = [
        "match_id", "puuid", "champion", "role", "result",
        "kills", "deaths", "assists", "cs", "damage", "duration_sec", "played_at",
    ]
    # Columnas V2 opcionales
    v2_col_names = [c for c, _ in _V2_COLUMNS]

    # Determinar qué columnas están presentes en el dict de entrada
    all_cols = base_cols + [c for c in v2_col_names if c in match]

    placeholders = ", ".join(f":{c}" for c in all_cols)
    col_list     = ", ".join(all_cols)

    with _get_conn() as conn:
        conn.execute(
            f"INSERT OR IGNORE INTO match ({col_list}) VALUES ({placeholders})",
            match,
        )
        conn.commit()


def update_match_v2(match_id: str, fields: dict) -> bool:
    """
    Actualiza los campos V2 de una partida ya existente en la DB.
    Solo modifica las columnas presentes en `fields`.
    Devuelve True si se actualizó al menos una fila.
    """
    if not fields:
        return False

    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    params = {**fields, "_match_id": match_id}

    with _get_conn() as conn:
        cur = conn.execute(
            f"UPDATE match SET {set_clause} WHERE match_id = :_match_id",
            params,
        )
        conn.commit()
    return cur.rowcount > 0


def get_matches(puuid: str, role: str | None = None, limit: int = 50) -> list[dict]:
    """
    Devuelve las últimas `limit` partidas del jugador.
    Si `role` se especifica ('ADC' | 'TOP' | 'MID'), filtra por rol.
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
# Analítica local (Sprint 2)
#
# Todo se guarda únicamente en data/lol_coach.db — nunca se envía a internet.
# No se registran datos personales: ni riot_id, ni puuid, ni api_key. Los
# nombres de campeón no son datos personales (son públicos del juego).
# ---------------------------------------------------------------------------

def log_event(
    session_id: str,
    event_type: str,
    screen: str | None = None,
    payload: dict | None = None,
) -> None:
    """
    Registra un evento de uso local.

    event_type esperados: "screen_open", "screen_time", "session_start",
    "session_end", "draft_recommendations_shown", "draft_pick_locked", "error".
    """
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO event_log (session_id, event_type, screen, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                session_id,
                event_type,
                screen,
                json.dumps(payload, ensure_ascii=False) if payload else None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def get_events(event_type: str | None = None, limit: int = 5000) -> list[dict]:
    """Devuelve eventos registrados, más recientes primero."""
    with _get_conn() as conn:
        if event_type:
            rows = conn.execute(
                "SELECT * FROM event_log WHERE event_type = ? ORDER BY created_at DESC LIMIT ?",
                (event_type, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM event_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Feedback (Sprint 2)
# ---------------------------------------------------------------------------

def save_feedback(
    context: str,
    stars: int,
    champion: str | None = None,
    comment: str | None = None,
) -> None:
    """Guarda una valoración del usuario (1-5 estrellas + comentario opcional)."""
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO feedback (context, champion, stars, comment, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (context, champion, stars, comment, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def get_feedback(limit: int = 200) -> list[dict]:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM feedback ORDER BY created_at DESC LIMIT ?", (limit,)
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
    print("OK config: save/get OK")

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
    print("OK player: save/get OK")

    # --- Prueba match V1 (compatibilidad) ---
    match_v1 = {
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
    save_match(match_v1)

    # --- Prueba update V2 ---
    update_match_v2("EUW1_123456", {
        "vision_score": 32,
        "kill_participation": 0.68,
        "cs_at_10": 74,
        "game_ended_surrender": 0,
    })
    matches = get_matches("abc-puuid-123", role="ADC")
    assert len(matches) == 1
    assert matches[0]["champion"] == "Jinx"
    assert matches[0]["vision_score"] == 32
    assert matches[0]["kill_participation"] == 0.68
    print("OK match V2: save/update/get OK")

    print("\nTodos los tests pasaron.")
