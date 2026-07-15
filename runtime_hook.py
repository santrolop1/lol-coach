"""
runtime_hook.py — Hook ejecutado por PyInstaller al inicio del proceso.

Se corre ANTES que cualquier import del proyecto. Configura el entorno
para que Streamlit encuentre sus archivos estáticos dentro del bundle.
"""

import os
import sys


def _setup_streamlit_static() -> None:
    """Apunta a Streamlit a su directorio estático dentro del bundle."""
    if not (getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")):
        return

    # Streamlit busca sus assets relativos a su propio __file__
    # En el bundle están en _MEIPASS/streamlit/static/
    # La variable STREAMLIT_STATIC_SERVE_PATH no existe en todas las versiones,
    # pero el posicionamiento en sys.path es suficiente.
    bundle = sys._MEIPASS  # type: ignore[attr-defined]
    if bundle not in sys.path:
        sys.path.insert(0, bundle)


_setup_streamlit_static()
