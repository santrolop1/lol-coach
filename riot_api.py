"""
riot_api.py — Cliente HTTP para Riot Games API.

Responsabilidades:
- Autenticarse con API Key.
- Obtener cuenta, summoner, partidas y detalle de partida.
- Manejar rate limiting, timeouts y errores HTTP.
- Cachear respuestas JSON en data/raw/ para no repetir llamadas.
"""

import json
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuración de routing
# ---------------------------------------------------------------------------

# Plataforma (servidores de juego) → Región (routing global para account/match)
PLATFORM_TO_REGIONAL: dict[str, str] = {
    "na1":  "americas",
    "br1":  "americas",
    "la1":  "americas",
    "la2":  "americas",
    "euw1": "europe",
    "eun1": "europe",
    "tr1":  "europe",
    "ru":   "europe",
    "kr":   "asia",
    "jp1":  "asia",
    "oc1":  "sea",
    "ph2":  "sea",
    "sg2":  "sea",
    "tw2":  "sea",
    "th2":  "sea",
    "vn2":  "sea",
}

CACHE_DIR = Path(__file__).parent / "data" / "raw"


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------

class RiotAPIError(Exception):
    """Error genérico de la API de Riot."""


class RiotNotFoundError(RiotAPIError):
    """El recurso pedido no existe (404)."""


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------

class RiotClient:
    def __init__(self, api_key: str, platform: str = "la1"):
        self.api_key = api_key
        self.platform = platform.lower()
        self.regional = PLATFORM_TO_REGIONAL.get(self.platform, "americas")
        self._headers = {"X-Riot-Token": api_key}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # HTTP interno
    # ------------------------------------------------------------------

    def _get(self, url: str, cache_key: str | None = None) -> dict | list:
        """
        GET con cache opcional.
        Si cache_key se provee, lee de disco antes de ir a la red.
        Cualquier respuesta exitosa se guarda en disco.
        """
        if cache_key:
            cache_file = CACHE_DIR / f"{cache_key}.json"
            if cache_file.exists():
                return json.loads(cache_file.read_text(encoding="utf-8"))

        # Rate limit básico: ≤ 50 req/min con dev key (20/s, 100/2min)
        time.sleep(1.3)

        try:
            resp = requests.get(url, headers=self._headers, timeout=10)
        except requests.Timeout:
            raise RiotAPIError("Timeout al conectar con Riot API. Verifica tu conexión.")
        except requests.ConnectionError:
            raise RiotAPIError("Sin conexión a internet.")

        # Retry automático en rate limit
        if resp.status_code == 429:
            try:
                retry_after = int(resp.headers.get("Retry-After", 10))
            except (ValueError, TypeError):
                retry_after = 10
            time.sleep(retry_after + 1)
            try:
                resp = requests.get(url, headers=self._headers, timeout=10)
            except requests.Timeout:
                raise RiotAPIError("Timeout al conectar con Riot API. Verifica tu conexión.")
            except requests.ConnectionError:
                raise RiotAPIError("Sin conexión a internet.")

        if resp.status_code == 404:
            raise RiotNotFoundError(f"No encontrado: {url}")

        if resp.status_code == 403:
            raise RiotAPIError("API Key inválida o expirada. Genera una nueva en developer.riotgames.com")

        if not resp.ok:
            raise RiotAPIError(f"Error {resp.status_code} de Riot API: {resp.text[:200]}")

        data = resp.json()

        if cache_key:
            cache_file = CACHE_DIR / f"{cache_key}.json"
            cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        return data

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    def get_account(self, game_name: str, tag_line: str) -> dict:
        """
        Obtiene la cuenta por Riot ID (gameName#tagLine).
        Devuelve: { puuid, gameName, tagLine }
        """
        url = (
            f"https://{self.regional}.api.riotgames.com"
            f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        )
        # No cacheamos cuenta — puede cambiar de nombre
        return self._get(url)

    def get_summoner(self, puuid: str) -> dict:
        """
        Obtiene datos del summoner por PUUID.
        Devuelve: { id, accountId, puuid, profileIconId, summonerLevel, ... }
        """
        url = (
            f"https://{self.platform}.api.riotgames.com"
            f"/lol/summoner/v4/summoners/by-puuid/{puuid}"
        )
        return self._get(url, cache_key=f"summoner_{puuid[:12]}")

    def get_league(self, summoner_id: str) -> list:
        """
        Obtiene las entradas de liga por summoner ID (legacy).
        Devuelve lista de { tier, rank, leaguePoints, wins, losses, ... }
        """
        url = (
            f"https://{self.platform}.api.riotgames.com"
            f"/lol/league/v4/entries/by-summoner/{summoner_id}"
        )
        # No cacheamos — el LP cambia constantemente
        return self._get(url)

    def get_league_by_puuid(self, puuid: str) -> list:
        """
        Obtiene las entradas de liga por PUUID (endpoint moderno de Riot).
        Usar en lugar de get_league() — la Summoner API ya no garantiza devolver 'id'.
        Devuelve lista de { tier, rank, leaguePoints, wins, losses, ... }
        """
        url = (
            f"https://{self.platform}.api.riotgames.com"
            f"/lol/league/v4/entries/by-puuid/{puuid}"
        )
        return self._get(url)

    def get_match_ids(self, puuid: str, count: int = 20, queue: int = 420) -> list[str]:
        """
        Obtiene los IDs de las últimas `count` partidas.
        queue=420: Ranked Solo/Duo | queue=440: Ranked Flex | queue=0: todas las colas
        No se cachea — la lista cambia con cada nueva partida.
        """
        base = (
            f"https://{self.regional}.api.riotgames.com"
            f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
            f"?count={count}"
        )
        # queue=0 significa "todas las colas" — se omite el parámetro en la URL
        # porque ?queue=0 es Custom Games en la API de Riot (devuelve lista vacía)
        url = base if queue == 0 else f"{base}&queue={queue}"
        return self._get(url)

    def get_match(self, match_id: str) -> dict:
        """
        Obtiene el detalle completo de una partida.
        Se cachea permanentemente — una partida jugada no cambia.
        """
        url = (
            f"https://{self.regional}.api.riotgames.com"
            f"/lol/match/v5/matches/{match_id}"
        )
        return self._get(url, cache_key=f"match_{match_id}")

    def validate_key(self) -> bool:
        """
        Verifica que la API Key funciona haciendo una llamada mínima.
        Devuelve True si OK, lanza RiotAPIError si no.
        """
        url = f"https://{self.regional}.api.riotgames.com/riot/account/v1/accounts/me"
        try:
            # Esta ruta da 403 con dev key pero NO da 401 — eso es suficiente para validar
            resp = requests.get(url, headers=self._headers, timeout=5)
            return resp.status_code != 401
        except requests.RequestException:
            return False
