"""
launcher.py — Entry point para la build empaquetada con PyInstaller.

En desarrollo: streamlit run main.py
En producción: el ejecutable llama a este launcher.

NO ejecutar directamente en desarrollo.
"""

from __future__ import annotations

import multiprocessing
import os
import sys
from pathlib import Path


def _setup_env() -> None:
    """Variables de entorno para Streamlit embebido."""
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS",               "false")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS",    "false")
    os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE",      "none")
    os.environ.setdefault("STREAMLIT_SERVER_ENABLE_CORS",            "false")
    os.environ.setdefault("STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION", "false")
    os.environ.setdefault("STREAMLIT_THEME_BASE",                    "dark")
    # Deshabilitar developmentMode explícitamente para evitar conflicto
    # con --server.port cuando Streamlit lo detecta como entorno de dev
    os.environ.setdefault("STREAMLIT_GLOBAL_DEVELOPMENT_MODE",       "false")


def _resolve_main_script() -> str:
    """Ruta absoluta a main.py dentro o fuera del bundle."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return str(Path(sys._MEIPASS) / "main.py")   # type: ignore[attr-defined]
    return str(Path(__file__).parent / "main.py")


def main() -> None:
    multiprocessing.freeze_support()
    _setup_env()

    main_script = _resolve_main_script()

    # Asegurar que el bundle dir esté en sys.path
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle = str(sys._MEIPASS)               # type: ignore[attr-defined]
        if bundle not in sys.path:
            sys.path.insert(0, bundle)

    sys.argv = [
        "streamlit", "run", main_script,
        "--server.headless=false",
        "--browser.gatherUsageStats=false",
        "--server.fileWatcherType=none",
        # NO pasar --server.port aquí — en modo frozen Streamlit puede
        # detectar developmentMode=true y rechazar el argumento.
        # El puerto lo controlamos vía variable de entorno si es necesario.
    ]

    from streamlit.web import cli as stcli
    stcli.main()


if __name__ == "__main__":
    main()
