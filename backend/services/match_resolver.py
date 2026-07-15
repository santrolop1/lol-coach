"""
backend/services/match_resolver.py — Resolución robusta de partidas ante cambios de PUUID.

Problema:
    Si el usuario reconfigura su cuenta, el PUUID en config puede diferir del PUUID
    almacenado en las partidas descargadas anteriormente. Con db.get_matches(puuid)
    directo esto devuelve una lista vacía aunque haya cientos de partidas en DB.

Solución:
    1. Intentar con el PUUID de config (fuente autorizada).
    2. Si hay un puuid extra (ej: del LCU) probarlo también.
    3. Si ninguno tiene datos, buscar en DB el PUUID con más partidas del rol indicado.

Uso:
    from backend.services.match_resolver import resolve_matches
    matches = resolve_matches(role="ADC")
"""

from __future__ import annotations

import sqlite3

import db


def resolve_matches(
    role: str | None = None,
    limit: int = 200,
    extra_puuid: str | None = None,
) -> list[dict]:
    """
    Devuelve las partidas del jugador tolerando discrepancias de PUUID.

    Parámetros
    ----------
    role        : filtrar por rol ("ADC", "TOP", …). None = sin filtro.
    limit       : número máximo de partidas a retornar.
    extra_puuid : PUUID adicional a probar (ej: el reportado por el LCU).
    """
    candidates: list[str | None] = [extra_puuid, db.get_config("puuid")]

    for puuid in filter(None, candidates):
        matches = db.get_matches(puuid, role=role, limit=limit)
        if matches:
            return matches

    # Último recurso: PUUID con más partidas del rol en DB
    try:
        conn = sqlite3.connect(str(db.DB_PATH))
        if role:
            row = conn.execute(
                "SELECT puuid, COUNT(*) cnt FROM match WHERE role = ? "
                "GROUP BY puuid ORDER BY cnt DESC LIMIT 1",
                (role,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT puuid, COUNT(*) cnt FROM match "
                "GROUP BY puuid ORDER BY cnt DESC LIMIT 1"
            ).fetchone()
        conn.close()
        if row:
            return db.get_matches(row[0], role=role, limit=limit)
    except Exception:
        pass

    return []
