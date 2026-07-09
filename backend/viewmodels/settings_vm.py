"""
backend/viewmodels/settings_vm.py — ViewModel para la pantalla de Configuración.

FastAPI (Sprint E-2):
    GET /settings
    return build_settings()
"""

from __future__ import annotations

from dataclasses import dataclass

import db


PLATFORMS = {
    "Latinoamérica Norte (LA1)": "la1",
    "Latinoamérica Sur (LA2)":   "la2",
    "Norteamérica (NA1)":        "na1",
    "Europa Oeste (EUW1)":       "euw1",
    "Europa Norte/Este (EUN1)":  "eun1",
    "Brasil (BR1)":              "br1",
    "Corea (KR)":                "kr",
    "Japón (JP1)":               "jp1",
    "Oceanía (OC1)":             "oc1",
}

PLATFORM_NAMES = {v: k for k, v in PLATFORMS.items()}


@dataclass
class SettingsViewModel:
    is_configured: bool
    puuid:         str | None
    platform:      str | None
    platform_name: str | None
    player:        dict | None
    riot_id:       str | None
    tag:           str | None
    level:         int | None
    rank:          str | None
    tier:          str | None
    lp:            int | None


def build_settings() -> SettingsViewModel:
    """
    Construye el ViewModel para la pantalla de Configuración.
    """
    puuid    = db.get_config("puuid")
    platform = db.get_config("platform")
    player   = db.get_player(puuid) if puuid else None

    return SettingsViewModel(
        is_configured= bool(puuid and db.get_config("api_key")),
        puuid=         puuid,
        platform=      platform,
        platform_name= PLATFORM_NAMES.get(platform or "", platform),
        player=        player,
        riot_id=       player.get("riot_id")  if player else None,
        tag=           player.get("tag")       if player else None,
        level=         player.get("level")     if player else None,
        rank=          player.get("rank")      if player else None,
        tier=          player.get("tier")      if player else None,
        lp=            player.get("lp")        if player else None,
    )
