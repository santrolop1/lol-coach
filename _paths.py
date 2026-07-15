"""
_paths.py — Resolución de rutas compatible con desarrollo y PyInstaller.

Cualquier módulo que necesite acceder a datos o activos debe importar
de aquí en lugar de usar Path(__file__).parent directamente.

En desarrollo:   todo vive relativo a la raíz del proyecto.
En PyInstaller:  los datos del usuario van a %APPDATA%/LoLCoach.
                 Los archivos bundleados viven en sys._MEIPASS.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_bundle_dir() -> Path:
    """Directorio donde PyInstaller extrae los archivos bundleados (sys._MEIPASS).
    En desarrollo, es la raíz del proyecto."""
    if _frozen():
        return Path(sys._MEIPASS)          # type: ignore[attr-defined]
    return Path(__file__).parent


def get_app_root() -> Path:
    """Directorio que contiene el ejecutable (o la raíz del proyecto en dev)."""
    if _frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_data_dir() -> Path:
    """Directorio persistente de datos del usuario (SQLite, configuración).

    Packaged: %APPDATA%\\LoLCoach\\
    Dev:      <proyecto>/data/
    """
    if _frozen():
        appdata = os.environ.get("APPDATA") or str(Path.home())
        d = Path(appdata) / "LoLCoach"
    else:
        d = Path(__file__).parent / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_cache_dir() -> Path:
    """Directorio de caché de Riot API (JSONs descargados).

    Packaged: %LOCALAPPDATA%\\LoLCoach\\cache\\
    Dev:      <proyecto>/data/raw/
    """
    if _frozen():
        localappdata = os.environ.get("LOCALAPPDATA") or str(Path.home())
        d = Path(localappdata) / "LoLCoach" / "cache"
    else:
        d = Path(__file__).parent / "data" / "raw"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_knowledge_dir() -> Path:
    """Base de conocimiento de Game Intelligence (archivos bundleados, read-only).

    Packaged: sys._MEIPASS/backend/game_intelligence/knowledge/
    Dev:      <proyecto>/backend/game_intelligence/knowledge/
    """
    return get_bundle_dir() / "backend" / "game_intelligence" / "knowledge"


def get_log_dir() -> Path:
    """Directorio de logs de la aplicación.

    Packaged: %APPDATA%\\LoLCoach\\logs\\
    Dev:      <proyecto>/data/logs/
    """
    if _frozen():
        appdata = os.environ.get("APPDATA") or str(Path.home())
        d = Path(appdata) / "LoLCoach" / "logs"
    else:
        d = Path(__file__).parent / "data" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d
