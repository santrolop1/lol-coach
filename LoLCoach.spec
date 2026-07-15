# LoLCoach.spec — PyInstaller 6.x, Python 3.11-3.14, Windows
#
# Build:  pyinstaller LoLCoach.spec --clean --noconfirm
# Script: .\build.ps1

from __future__ import annotations
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# ── Streamlit: incluye static/ (React UI, JS, CSS) ───────────────────────────
st_datas, st_bins, st_hidden = collect_all("streamlit")

# ── Plotly y Altair ───────────────────────────────────────────────────────────
pl_datas, pl_bins, pl_hidden = collect_all("plotly")
alt_datas, alt_bins, alt_hidden = collect_all("altair")

# ── Pydantic (v2 tiene __pydantic_complete__ en módulos compilados) ────────────
pd_datas, pd_bins, pd_hidden = collect_all("pydantic")
pd_core_datas, pd_core_bins, pd_core_hidden = collect_all("pydantic_core")

# ── Archivos del proyecto ─────────────────────────────────────────────────────
_project_datas = [
    ("main.py",            "."),
    ("db.py",              "."),
    ("riot_api.py",        "."),
    ("analytics.py",       "."),
    ("parser.py",          "."),
    ("coaching_engine.py", "."),
    ("coaching_rules.py",  "."),
    ("scorer_v2.py",       "."),
    ("_paths.py",          "."),
    ("backend",            "backend"),
    ("ui",                 "ui"),
    ("lcu",                "lcu"),
]

# ── Análisis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=(
        st_bins + pl_bins + alt_bins + pd_bins + pd_core_bins
    ),
    datas=(
        _project_datas
        + st_datas + pl_datas + alt_datas
        + pd_datas + pd_core_datas
    ),
    hiddenimports=(
        st_hidden + pl_hidden + alt_hidden + pd_hidden + pd_core_hidden
        + [
            # FastAPI / ASGI
            "fastapi", "fastapi.middleware", "fastapi.middleware.cors",
            "uvicorn", "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
            "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
            "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
            "uvicorn.lifespan", "uvicorn.lifespan.on", "uvicorn.lifespan.off",
            "uvicorn.main",
            # WebSockets
            "websockets", "websockets.legacy", "websockets.legacy.server",
            "websockets.legacy.client",
            # HTTP
            "requests", "urllib3", "urllib3.util", "certifi",
            "charset_normalizer", "idna",
            # SQLite
            "sqlite3", "_sqlite3",
            # Stdlib extras
            "email.mime.text", "email.mime.multipart",
            "importlib.resources", "importlib.metadata",
            "pkg_resources",
            "packaging", "packaging.version",
            # Proyecto
            "db", "riot_api", "analytics", "parser",
            "coaching_engine", "coaching_rules", "scorer_v2", "_paths",
            "backend.version",
            # Streamlit extras no capturados por collect_all
            "streamlit.runtime.scriptrunner.magic_funcs",
            "streamlit.runtime.stats",
            "streamlit.components.v1",
            "streamlit.elements.lib.built_in_chart_utils",
            # Click (usado por Streamlit CLI)
            "click", "click.core", "click.decorators",
            # Typer / rich (dependencias Streamlit)
            "rich", "rich.console", "rich.markup",
            "toml", "tomli",
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["runtime_hook.py"],
    excludes=[
        # Testing
        "pytest", "httpx", "_pytest", "py",
        # Frontend Electron (nunca se incluye)
        "frontend",
        # Jupyter
        "IPython", "notebook", "jupyter", "ipykernel",
        # ML/CV (no usados)
        "matplotlib", "scipy", "sklearn", "torch", "tensorflow", "cv2", "PIL",
        # Tkinter
        "tkinter", "_tkinter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LoLCoach",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # BETA: console=True para poder ver errores y hacer soporte
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Icono (opcional — no bloquea el build si no existe)
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="LoLCoach",
)
