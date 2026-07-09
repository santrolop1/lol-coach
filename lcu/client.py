"""
lcu/client.py — Capa de comunicación con la League Client Update API.

Lectura del lockfile → autenticación HTTP Basic → requests HTTPS locales.
Certificado auto-firmado: SSL verification desactivada (solo 127.0.0.1).
"""

from __future__ import annotations

import base64
import re
import subprocess
from pathlib import Path

import requests
import urllib3

from lcu.models import LCUCredentials

# Silenciar advertencias de SSL para el certificado auto-firmado del cliente.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Rutas comunes del lockfile ────────────────────────────────────────────────

_LOCKFILE_PATHS: list[str] = [
    r"C:\Riot Games\League of Legends\lockfile",
    r"D:\Riot Games\League of Legends\lockfile",
    r"E:\Riot Games\League of Legends\lockfile",
    r"C:\Program Files\Riot Games\League of Legends\lockfile",
    r"D:\Program Files\Riot Games\League of Legends\lockfile",
]

_TIMEOUT = 3.0   # segundos por request HTTP al LCU


# ── Lectura de credenciales ───────────────────────────────────────────────────

def _read_lockfile(path: Path) -> LCUCredentials | None:
    """Parsea el lockfile: LeagueClient:PID:PORT:PASSWORD:PROTOCOL."""
    try:
        parts = path.read_text(encoding="utf-8").strip().split(":")
        if len(parts) != 5:
            return None
        return LCUCredentials(
            port=int(parts[2]),
            password=parts[3],
            pid=int(parts[1]),
            source="lockfile",
        )
    except (OSError, ValueError):
        return None


def _read_from_process() -> LCUCredentials | None:
    """
    Fallback: extrae puerto y token desde los argumentos del proceso
    LeagueClientUx.exe usando wmic. Útil cuando el cliente está instalado
    en un directorio no estándar.
    """
    try:
        result = subprocess.run(
            ["wmic", "PROCESS", "WHERE", "name='LeagueClientUx.exe'", "GET", "commandline"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        cmdline = result.stdout
        port_m = re.search(r"--app-port=(\d+)", cmdline)
        auth_m = re.search(r"--remoting-auth-token=([\w-]+)", cmdline)
        pid_m  = re.search(r"--ux-helper-pid=(\d+)", cmdline)

        if port_m and auth_m:
            return LCUCredentials(
                port=int(port_m.group(1)),
                password=auth_m.group(1),
                pid=int(pid_m.group(1)) if pid_m else 0,
                source="process",
            )
    except Exception:
        pass
    return None


def read_credentials() -> LCUCredentials | None:
    """
    Devuelve las credenciales LCU o None si el cliente no está corriendo.

    Intenta primero los lockfile paths comunes; si no encuentra ninguno,
    usa el fallback de proceso (wmic).
    """
    for path_str in _LOCKFILE_PATHS:
        p = Path(path_str)
        if p.exists():
            creds = _read_lockfile(p)
            if creds:
                return creds

    return _read_from_process()


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _auth_header(creds: LCUCredentials) -> dict[str, str]:
    token = base64.b64encode(f"riot:{creds.password}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def _get(creds: LCUCredentials, endpoint: str) -> dict | list | str | None:
    """
    GET https://127.0.0.1:{port}/{endpoint}.
    Devuelve el JSON parseado, o None si hay error de conexión o el
    endpoint no está disponible (404 / 503).
    """
    url = f"https://127.0.0.1:{creds.port}{endpoint}"
    try:
        resp = requests.get(
            url,
            headers=_auth_header(creds),
            verify=False,
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            try:
                return resp.json()
            except ValueError:
                return resp.text.strip('"')
        return None
    except requests.exceptions.RequestException:
        # Cubre ConnectionError, Timeout, SSLError (handshake del certificado
        # autofirmado del cliente) y cualquier otro fallo de la capa HTTP —
        # todos deben degradar a "cliente no disponible", nunca reventar la UI.
        return None


# ── API pública ───────────────────────────────────────────────────────────────

def get_phase(creds: LCUCredentials) -> str | None:
    """
    Devuelve la fase actual del cliente:
    "None" | "Lobby" | "Matchmaking" | "ReadyCheck" | "ChampSelect" |
    "GameStart" | "InProgress" | "WaitingForStats" | "PreEndOfGame" | "EndOfGame"

    Devuelve None si el cliente no responde.
    """
    result = _get(creds, "/lol-gameflow/v1/gameflow-phase")
    if isinstance(result, str):
        return result
    return None


def get_current_summoner(creds: LCUCredentials) -> dict | None:
    """Datos del summoner logueado (displayName, puuid, summonerLevel…)."""
    result = _get(creds, "/lol-summoner/v1/current-summoner")
    return result if isinstance(result, dict) else None


def get_champ_select_session(creds: LCUCredentials) -> dict | None:
    """
    Sesión completa de champ select.
    Solo disponible cuando phase == "ChampSelect".
    """
    result = _get(creds, "/lol-champ-select/v1/session")
    return result if isinstance(result, dict) else None


def get_champion_map(creds: LCUCredentials) -> dict[int, dict[str, str]]:
    """
    Devuelve {champion_id: {"name": ..., "alias": ...}} para todos los campeones.
    Fuente: /lol-game-data/assets/v1/champion-summary.json (propio cliente).

    "name" es el nombre de display (ej. "Kai'Sa", "Wukong") — para mostrar en UI.
    "alias" es el id formato Riot API (ej. "KaiSa", "MonkeyKing") — coincide con
    el campo championName que devuelve Match-V5 y que se guarda en match.champion.
    Antes solo se exponía "name", lo que rompía cualquier cruce contra la DB para
    los ~20 campeones cuyo nombre de display difiere de su id (apóstrofes, etc.).

    Si el endpoint falla, devuelve dict vacío y la UI muestra el ID numérico.
    """
    result = _get(creds, "/lol-game-data/assets/v1/champion-summary.json")
    if not isinstance(result, list):
        return {}
    champ_map: dict[int, dict[str, str]] = {}
    for entry in result:
        cid   = entry.get("id", -1)
        name  = entry.get("name", "")
        alias = entry.get("alias", "") or name
        if cid >= 0 and name:
            champ_map[cid] = {"name": name, "alias": alias}
    return champ_map


def is_alive(creds: LCUCredentials) -> bool:
    """Ping rápido para verificar que el cliente responde."""
    return get_phase(creds) is not None
