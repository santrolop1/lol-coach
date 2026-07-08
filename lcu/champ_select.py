"""
lcu/champ_select.py — Parseo del JSON de sesión de champ select.

Extrae: mi rol, mi pick, picks aliados, picks enemigos, bans, timer.
Todo dato proviene directamente del JSON del LCU; nada es inventado.
"""

from __future__ import annotations

from lcu.models import (
    BanPhase,
    ChampionSlot,
    ChampSelectSession,
    SelectTimer,
    POSITION_ORDER,
)


# ── Fases (para UI) ───────────────────────────────────────────────────────────

PHASE_LABELS: dict[str, str] = {
    "PLANNING":     "Fase de intención",
    "BAN_PICK":     "Bans y picks",
    "FINALIZATION": "Finalización",
    "GAME_STARTING":"Iniciando partida",
    "":             "Esperando",
}

# Fases globales del gameflow
GAMEFLOW_LABELS: dict[str, str] = {
    "None":           "Menú principal",
    "Lobby":          "Sala",
    "Matchmaking":    "Buscando partida",
    "ReadyCheck":     "¡Partida encontrada!",
    "ChampSelect":    "Champ Select",
    "GameStart":      "Iniciando partida",
    "InProgress":     "Partida en curso",
    "WaitingForStats":"Esperando resultados",
    "PreEndOfGame":   "Fin de partida",
    "EndOfGame":      "Pantalla de resultados",
}


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_session(raw: dict, champion_map: dict[int, dict[str, str]]) -> ChampSelectSession:
    """
    Convierte el JSON crudo de /lol-champ-select/v1/session en un
    ChampSelectSession tipado.

    champion_map: {champion_id: {"name": ..., "alias": ...}} desde get_champion_map().
    Si un ID no está en el mapa, se muestra "Campeón #{id}" en ambos campos.
    """

    def resolve(champ_id: int) -> tuple[str, str]:
        """Devuelve (display_name, alias). alias = formato Riot API, para cruzar con la DB."""
        if champ_id == 0:
            return "", ""
        entry = champion_map.get(champ_id)
        if entry:
            return entry["name"], entry["alias"]
        fallback = f"Campeón #{champ_id}"
        return fallback, fallback

    local_cell_id = raw.get("localPlayerCellId", -1)

    def _parse_slots(team_list: list[dict]) -> list[ChampionSlot]:
        slots = []
        for slot in team_list:
            cid = slot.get("championId", 0)
            name, alias = resolve(cid)
            slots.append(ChampionSlot(
                cell_id           = slot.get("cellId", -1),
                champion_id       = cid,
                champion_name     = name,
                champion_alias    = alias,
                assigned_position = slot.get("assignedPosition", ""),
                spell1_id         = slot.get("spell1Id", 0),
                spell2_id         = slot.get("spell2Id", 0),
                is_local_player   = slot.get("cellId", -1) == local_cell_id,
            ))
        # Ordenar por posición estándar
        def _pos_key(s: ChampionSlot) -> int:
            try:
                return POSITION_ORDER.index(s.assigned_position)
            except ValueError:
                return 99
        slots.sort(key=_pos_key)
        return slots

    # Bans: filtrar IDs 0 (sin banear aún)
    raw_bans = raw.get("bans", {})
    my_bans_raw    = [resolve(cid) for cid in raw_bans.get("myTeamBans", [])    if cid != 0]
    their_bans_raw = [resolve(cid) for cid in raw_bans.get("theirTeamBans", []) if cid != 0]
    bans = BanPhase(
        my_team_bans          = [n for n, _ in my_bans_raw],
        their_team_bans       = [n for n, _ in their_bans_raw],
        my_team_bans_alias    = [a for _, a in my_bans_raw],
        their_team_bans_alias = [a for _, a in their_bans_raw],
    )

    raw_timer = raw.get("timer", {})
    timer = SelectTimer(
        phase         = raw_timer.get("phase", ""),
        time_left_ms  = int(raw_timer.get("timeLeftInPhase", 0)),
        total_time_ms = int(raw_timer.get("totalTimeInPhase", 0)),
        is_infinite   = bool(raw_timer.get("isInfinite", False)),
    )

    return ChampSelectSession(
        game_id       = raw.get("gameId", 0),
        my_team       = _parse_slots(raw.get("myTeam", [])),
        their_team    = _parse_slots(raw.get("theirTeam", [])),
        bans          = bans,
        timer         = timer,
        local_cell_id = local_cell_id,
    )
