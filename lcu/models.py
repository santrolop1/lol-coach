"""
lcu/models.py — Dataclasses para la capa de integración LCU.

Todo campo proviene del JSON real del cliente; ningún valor es inventado.
"""

from dataclasses import dataclass, field


@dataclass
class LCUCredentials:
    port:     int
    password: str
    pid:      int
    source:   str = ""   # "lockfile" | "process"


# ── Posiciones ───────────────────────────────────────────────────────────────

POSITION_ORDER: list[str] = ["top", "jungle", "middle", "bottom", "utility"]

POSITION_DISPLAY: dict[str, str] = {
    "top":     "TOP",
    "jungle":  "JGL",
    "middle":  "MID",
    "bottom":  "ADC",
    "utility": "SUP",
    "":        "?",
}


# ── Champ Select ─────────────────────────────────────────────────────────────

@dataclass
class ChampionSlot:
    cell_id:           int
    champion_id:       int
    champion_name:     str   # resuelto desde /lol-game-data/assets/v1/champion-summary.json
    assigned_position: str   # lowercase: "top" | "jungle" | "middle" | "bottom" | "utility" | ""
    spell1_id:         int
    spell2_id:         int
    is_local_player:   bool

    @property
    def position_label(self) -> str:
        return POSITION_DISPLAY.get(self.assigned_position, "?")

    @property
    def has_pick(self) -> bool:
        return self.champion_id != 0


@dataclass
class BanPhase:
    my_team_bans:    list[str]   # nombres de campeones; vacío si no se ha baneado
    their_team_bans: list[str]


@dataclass
class SelectTimer:
    phase:         str   # "PLANNING" | "BAN_PICK" | "FINALIZATION" | "GAME_STARTING" | ""
    time_left_ms:  int
    total_time_ms: int
    is_infinite:   bool

    @property
    def time_left_sec(self) -> float:
        return self.time_left_ms / 1000

    @property
    def progress_pct(self) -> float:
        if self.is_infinite or self.total_time_ms == 0:
            return 1.0
        return max(0.0, min(1.0, self.time_left_ms / self.total_time_ms))


@dataclass
class ChampSelectSession:
    game_id:       int
    my_team:       list[ChampionSlot]
    their_team:    list[ChampionSlot]
    bans:          BanPhase
    timer:         SelectTimer
    local_cell_id: int

    @property
    def me(self) -> ChampionSlot | None:
        for slot in self.my_team:
            if slot.is_local_player:
                return slot
        return None

    @property
    def my_champion(self) -> str:
        slot = self.me
        return slot.champion_name if (slot and slot.has_pick) else ""

    @property
    def my_role(self) -> str:
        slot = self.me
        return slot.assigned_position if slot else ""

    def sorted_team(self, team: list[ChampionSlot]) -> list[ChampionSlot]:
        """Ordena por posición: TOP JGL MID ADC SUP."""
        def _key(s: ChampionSlot) -> int:
            try:
                return POSITION_ORDER.index(s.assigned_position)
            except ValueError:
                return 99
        return sorted(team, key=_key)
