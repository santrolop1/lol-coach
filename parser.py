"""
parser.py — Convierte el JSON crudo de Riot API en un MatchData limpio.

Responsabilidades:
- Extraer solo los campos que necesita la app.
- Detectar el rol del jugador (ADC / TOP / OTHER).
- Calcular el timestamp legible de la partida.
"""

import datetime
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Modelo interno
# ---------------------------------------------------------------------------

@dataclass
class MatchData:
    match_id:     str
    puuid:        str
    champion:     str
    role:         str   # 'ADC' | 'TOP' | 'OTHER'
    result:       str   # 'WIN' | 'LOSS'
    kills:        int
    deaths:       int
    assists:      int
    cs:           int   # minions + neutrales
    damage:       int   # daño total a campeones
    duration_sec: int
    played_at:    str   # ISO 8601 UTC

    def to_dict(self) -> dict:
        """Convierte a dict plano para guardar en SQLite."""
        return {
            "match_id":     self.match_id,
            "puuid":        self.puuid,
            "champion":     self.champion,
            "role":         self.role,
            "result":       self.result,
            "kills":        self.kills,
            "deaths":       self.deaths,
            "assists":      self.assists,
            "cs":           self.cs,
            "damage":       self.damage,
            "duration_sec": self.duration_sec,
            "played_at":    self.played_at,
        }


# ---------------------------------------------------------------------------
# Mapeo de posición → rol interno
# ---------------------------------------------------------------------------

_POSITION_TO_ROLE: dict[str, str] = {
    "BOTTOM": "ADC",
    "TOP":    "TOP",
    # JUNGLE, MIDDLE, UTILITY → "OTHER" (se filtran en la app)
}


# ---------------------------------------------------------------------------
# Parser principal
# ---------------------------------------------------------------------------

def parse_match(match_json: dict, puuid: str) -> MatchData | None:
    """
    Parsea el JSON crudo de GET /lol/match/v5/matches/{matchId}.

    Devuelve MatchData si se encuentra al jugador, None si no está en la partida
    (no debería pasar, pero es defensivo).
    """
    try:
        info = match_json["info"]
        match_id_str = match_json["metadata"]["matchId"]
        participants: list[dict] = info["participants"]
    except KeyError:
        return None

    # Buscar al jugador en los 10 participants
    participant = next((p for p in participants if p.get("puuid") == puuid), None)
    if participant is None:
        return None

    # Rol
    position = participant.get("teamPosition", "")
    role = _POSITION_TO_ROLE.get(position, "OTHER")

    # Resultado
    result = "WIN" if participant.get("win", False) else "LOSS"

    # Timestamp → ISO UTC
    ts_ms = info.get("gameStartTimestamp", 0)
    played_at = datetime.datetime.fromtimestamp(
        ts_ms / 1000, tz=datetime.timezone.utc
    ).isoformat()

    # CS = minions de lane + neutrales (monstruos de jungla/dragones pequeños)
    cs = (
        participant.get("totalMinionsKilled", 0)
        + participant.get("neutralMinionsKilled", 0)
    )

    return MatchData(
        match_id=match_id_str,
        puuid=puuid,
        champion=participant.get("championName", "Unknown"),
        role=role,
        result=result,
        kills=participant.get("kills", 0),
        deaths=participant.get("deaths", 0),
        assists=participant.get("assists", 0),
        cs=cs,
        damage=participant.get("totalDamageDealtToChampions", 0),
        duration_sec=info.get("gameDuration", 0),
        played_at=played_at,
    )
