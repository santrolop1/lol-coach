"""
parser.py — Convierte el JSON crudo de Riot API en un MatchData limpio.

Responsabilidades:
- Extraer solo los campos que necesita la app.
- Detectar el rol del jugador (ADC / TOP / OTHER).
- Calcular el timestamp legible de la partida.
- Extraer campos V2: visión, objetivos, challenges, flags de partida.
"""

import datetime
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Modelo interno
# ---------------------------------------------------------------------------

@dataclass
class MatchData:
    # ── Campos V1 (siempre presentes) ──────────────────────────────────────
    match_id:     str
    puuid:        str
    champion:     str
    role:         str          # 'ADC' | 'TOP' | 'OTHER'
    result:       str          # 'WIN' | 'LOSS'
    kills:        int
    deaths:       int
    assists:      int
    cs:           int          # totalMinionsKilled + neutralMinionsKilled
    damage:       int          # totalDamageDealtToChampions
    duration_sec: int
    played_at:    str          # ISO 8601 UTC

    # ── Campos V2: Economía ─────────────────────────────────────────────────
    gold_earned:           Optional[int]  = None  # goldEarned

    # ── Campos V2: Visión ───────────────────────────────────────────────────
    vision_score:          Optional[int]  = None  # visionScore
    wards_placed:          Optional[int]  = None  # wardsPlaced
    wards_killed:          Optional[int]  = None  # wardsKilled
    control_wards_placed:  Optional[int]  = None  # detectorWardsPlaced
    control_wards_bought:  Optional[int]  = None  # visionWardsBoughtInGame

    # ── Campos V2: Daño y objetivos ─────────────────────────────────────────
    damage_to_objectives:  Optional[int]  = None  # damageDealtToObjectives
    damage_to_turrets:     Optional[int]  = None  # damageDealtToTurrets
    damage_taken:          Optional[int]  = None  # totalDamageTaken
    damage_self_mitigated: Optional[int]  = None  # damageSelfMitigated

    # ── Campos V2: Utilidad ─────────────────────────────────────────────────
    heals_on_teammates:    Optional[int]  = None  # totalHealsOnTeammates
    time_ccing_others:     Optional[float] = None # timeCCingOthers (segundos)
    turret_takedowns:      Optional[int]  = None  # turretTakedowns
    turret_plates_taken:   Optional[int]  = None  # challenges.turretPlatesTaken

    # ── Campos V2: Supervivencia ────────────────────────────────────────────
    time_spent_dead:       Optional[int]  = None  # totalTimeSpentDead
    longest_time_alive:    Optional[int]  = None  # longestTimeSpentLiving

    # ── Campos V2: Challenges (calculados por Riot) ─────────────────────────
    kill_participation:    Optional[float] = None # challenges.killParticipation [0-1]
    team_damage_pct:       Optional[float] = None # challenges.teamDamagePercentage [0-1]
    cs_at_10:              Optional[int]  = None  # challenges.laneMinionsFirst10Minutes
    max_cs_advantage:      Optional[int]  = None  # challenges.maxCsAdvantageOnLaneOpponent

    # ── Campos V2: Objetivos mayores (JGL) ──────────────────────────────────
    baron_kills:           Optional[int]  = None  # baronKills
    dragon_kills:          Optional[int]  = None  # dragonKills
    objectives_stolen:     Optional[int]  = None  # objectivesStolen
    enemy_jungle_cs:       Optional[int]  = None  # totalEnemyJungleMinionsKilled

    # ── Campos V2: Flags de partida ──────────────────────────────────────────
    game_ended_surrender:  Optional[int]  = None  # gameEndedInEarlySurrender → 0/1
    first_blood:           Optional[int]  = None  # firstBloodKill → 0/1

    def to_dict(self) -> dict:
        """Convierte a dict plano para guardar en SQLite."""
        return {
            # V1
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
            # V2 — Economía
            "gold_earned":            self.gold_earned,
            # V2 — Visión
            "vision_score":           self.vision_score,
            "wards_placed":           self.wards_placed,
            "wards_killed":           self.wards_killed,
            "control_wards_placed":   self.control_wards_placed,
            "control_wards_bought":   self.control_wards_bought,
            # V2 — Daño y objetivos
            "damage_to_objectives":   self.damage_to_objectives,
            "damage_to_turrets":      self.damage_to_turrets,
            "damage_taken":           self.damage_taken,
            "damage_self_mitigated":  self.damage_self_mitigated,
            # V2 — Utilidad
            "heals_on_teammates":     self.heals_on_teammates,
            "time_ccing_others":      self.time_ccing_others,
            "turret_takedowns":       self.turret_takedowns,
            "turret_plates_taken":    self.turret_plates_taken,
            # V2 — Supervivencia
            "time_spent_dead":        self.time_spent_dead,
            "longest_time_alive":     self.longest_time_alive,
            # V2 — Challenges
            "kill_participation":     self.kill_participation,
            "team_damage_pct":        self.team_damage_pct,
            "cs_at_10":               self.cs_at_10,
            "max_cs_advantage":       self.max_cs_advantage,
            # V2 — Objetivos mayores
            "baron_kills":            self.baron_kills,
            "dragon_kills":           self.dragon_kills,
            "objectives_stolen":      self.objectives_stolen,
            "enemy_jungle_cs":        self.enemy_jungle_cs,
            # V2 — Flags
            "game_ended_surrender":   self.game_ended_surrender,
            "first_blood":            self.first_blood,
        }

    def to_v2_fields(self) -> dict:
        """Devuelve solo los campos V2 (sin None) para usar en update_match_v2()."""
        full = self.to_dict()
        v1_keys = {
            "match_id", "puuid", "champion", "role", "result",
            "kills", "deaths", "assists", "cs", "damage",
            "duration_sec", "played_at",
        }
        return {k: v for k, v in full.items() if k not in v1_keys and v is not None}


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

def parse_match(match_json: dict, puuid: str) -> Optional["MatchData"]:
    """
    Parsea el JSON crudo de GET /lol/match/v5/matches/{matchId}.

    Devuelve MatchData si se encuentra al jugador, None si no está en la partida.
    Todos los campos V2 usan .get() defensivo — None si el campo no existe.
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

    # Challenges (objeto anidado, puede no existir en partidas antiguas)
    ch: dict = participant.get("challenges", {}) or {}

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

    # CS = minions de lane + neutrales
    cs = (
        participant.get("totalMinionsKilled", 0)
        + participant.get("neutralMinionsKilled", 0)
    )

    return MatchData(
        # ── V1 ──────────────────────────────────────────────────────────────
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

        # ── V2: Economía ────────────────────────────────────────────────────
        gold_earned=participant.get("goldEarned"),

        # ── V2: Visión ──────────────────────────────────────────────────────
        vision_score=participant.get("visionScore"),
        wards_placed=participant.get("wardsPlaced"),
        wards_killed=participant.get("wardsKilled"),
        control_wards_placed=participant.get("detectorWardsPlaced"),
        control_wards_bought=participant.get("visionWardsBoughtInGame"),

        # ── V2: Daño y objetivos ────────────────────────────────────────────
        damage_to_objectives=participant.get("damageDealtToObjectives"),
        damage_to_turrets=participant.get("damageDealtToTurrets"),
        damage_taken=participant.get("totalDamageTaken"),
        damage_self_mitigated=participant.get("damageSelfMitigated"),

        # ── V2: Utilidad ────────────────────────────────────────────────────
        heals_on_teammates=participant.get("totalHealsOnTeammates"),
        time_ccing_others=participant.get("timeCCingOthers"),
        turret_takedowns=participant.get("turretTakedowns"),
        turret_plates_taken=_safe_int(ch.get("turretPlatesTaken")),

        # ── V2: Supervivencia ────────────────────────────────────────────────
        time_spent_dead=participant.get("totalTimeSpentDead"),
        longest_time_alive=participant.get("longestTimeSpentLiving"),

        # ── V2: Challenges ───────────────────────────────────────────────────
        kill_participation=ch.get("killParticipation"),
        team_damage_pct=ch.get("teamDamagePercentage"),
        cs_at_10=_safe_int(ch.get("laneMinionsFirst10Minutes")),
        max_cs_advantage=_safe_int(ch.get("maxCsAdvantageOnLaneOpponent")),

        # ── V2: Objetivos mayores ────────────────────────────────────────────
        baron_kills=participant.get("baronKills"),
        dragon_kills=participant.get("dragonKills"),
        objectives_stolen=participant.get("objectivesStolen"),
        enemy_jungle_cs=participant.get("totalEnemyJungleMinionsKilled"),

        # ── V2: Flags ────────────────────────────────────────────────────────
        game_ended_surrender=_bool_to_int(participant.get("gameEndedInEarlySurrender")),
        first_blood=_bool_to_int(participant.get("firstBloodKill")),
    )


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _bool_to_int(value) -> Optional[int]:
    """Convierte bool/None → 1/0/None para almacenamiento en SQLite."""
    if value is None:
        return None
    return 1 if value else 0


def _safe_int(value) -> Optional[int]:
    """Convierte a int si no es None, respetando floats de challenges."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
