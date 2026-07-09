"""
RiotLiveClientProvider — proveedor via Live Client Data API de Riot.

Endpoint base: https://127.0.0.1:2999/liveclientdata/

Documentación oficial:
  https://developer.riotgames.com/docs/lol#game-client-api

El certificado SSL del cliente de juego es auto-firmado, por eso verify=False.
Esta API solo responde mientras el juego está activo en pantalla.
"""

from __future__ import annotations
import logging
import time

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

from ..models import PlayerStats, LiveSession
from .base import LiveDataProvider

logger = logging.getLogger(__name__)

_BASE_URL = "https://127.0.0.1:2999/liveclientdata"
_TIMEOUT = 1.5  # segundos — debe ser corto para no bloquear el overlay

# Mapeo de posición Riot → role interno
_POSITION_MAP = {
    "TOP": "TOP",
    "JUNGLE": "JUNGLE",
    "MIDDLE": "MID",
    "BOTTOM": "ADC",
    "UTILITY": "SUPPORT",
}


class RiotLiveClientProvider(LiveDataProvider):
    """
    Consulta la Live Client Data API de Riot Games.

    La API solo está disponible mientras League of Legends está en partida.
    Cuando no hay partida activa, todos los endpoints retornan 404.

    Caching de 1s para evitar saturar la API en cada frame del overlay.
    """

    def __init__(self, base_url: str = _BASE_URL, timeout: float = _TIMEOUT) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._last_check: float = 0.0
        self._cached_stats: PlayerStats | None = None
        self._cached_time: float = 0.0
        self._cached_phase: str = "idle"
        self._cache_ttl: float = 1.0
        self._connected: bool = False

    # ── LiveDataProvider interface ────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self._connected

    def get_player_stats(self) -> PlayerStats | None:
        self._refresh_if_stale()
        return self._cached_stats

    def get_game_time(self) -> float:
        self._refresh_if_stale()
        return self._cached_time

    def get_phase(self) -> str:
        self._refresh_if_stale()
        return self._cached_phase

    # ── Internos ──────────────────────────────────────────────────────────────

    def _refresh_if_stale(self) -> None:
        if time.time() - self._last_check < self._cache_ttl:
            return
        self._refresh()

    def _refresh(self) -> None:
        if not _REQUESTS_AVAILABLE:
            self._connected = False
            self._cached_phase = "idle"
            self._cached_stats = None
            return

        try:
            resp = requests.get(
                f"{self._base_url}/allgamedata",
                timeout=self._timeout,
                verify=False,  # certificado auto-firmado de Riot
            )
            if resp.status_code == 404:
                self._connected = True   # API responde, pero no hay partida
                self._cached_phase = "idle"
                self._cached_stats = None
                self._cached_time = 0.0
            elif resp.ok:
                self._connected = True
                self._cached_phase = "in_game"
                data = resp.json()
                self._cached_stats = self._parse_stats(data)
                self._cached_time = data.get("gameData", {}).get("gameTime", 0.0)
            else:
                self._connected = False
                self._cached_phase = "idle"
        except Exception:
            self._connected = False
            self._cached_phase = "idle"
            self._cached_stats = None
        finally:
            self._last_check = time.time()

    def _parse_stats(self, data: dict) -> PlayerStats:
        try:
            active = data.get("activePlayer", {})
            summoner_name = active.get("summonerName", "")

            # Buscar el jugador activo en la lista de jugadores
            all_players = data.get("allPlayers", [])
            player_data = next(
                (p for p in all_players if p.get("summonerName") == summoner_name),
                None,
            )

            champion = ""
            role = ""
            items: list[str] = []

            if player_data:
                champion = player_data.get("championName", "").lower().replace(" ", "")
                raw_position = player_data.get("position", "")
                role = _POSITION_MAP.get(raw_position, raw_position)
                items = [
                    i.get("displayName", "")
                    for i in player_data.get("items", [])
                    if i.get("displayName")
                ]

            scores = active.get("currentGold", 0)
            champion_stats = active.get("championStats", {})

            # KDA de player_data.scores
            scores_data = player_data.get("scores", {}) if player_data else {}

            return PlayerStats(
                champion=champion,
                role=role,
                level=active.get("level", 1),
                gold=int(active.get("currentGold", 0)),
                kills=scores_data.get("kills", 0),
                deaths=scores_data.get("deaths", 0),
                assists=scores_data.get("assists", 0),
                cs=scores_data.get("creepScore", 0),
                game_time=data.get("gameData", {}).get("gameTime", 0.0),
                hp_pct=self._safe_pct(
                    champion_stats.get("currentHealth", 1),
                    champion_stats.get("maxHealth", 1),
                ),
                mana_pct=self._safe_pct(
                    champion_stats.get("resourceValue", 1),
                    champion_stats.get("resourceMax", 1),
                ),
                items=items,
                is_dead=player_data.get("isDead", False) if player_data else False,
            )
        except Exception as exc:
            logger.warning("Error parseando stats del Live Client: %s", exc)
            return PlayerStats()

    @staticmethod
    def _safe_pct(current: float, maximum: float) -> float:
        if maximum <= 0:
            return 1.0
        return max(0.0, min(1.0, current / maximum))
