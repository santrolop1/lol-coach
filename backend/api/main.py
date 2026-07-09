"""
backend/api/main.py — Servidor FastAPI de LoL Coach.

Capa de transporte pura: registra rutas y middleware.
Toda la lógica de negocio vive en los ViewModels y Servicios.

Uso:
    uvicorn backend.api.main:app --host 127.0.0.1 --port 8766 --reload

Documentación automática:
    http://127.0.0.1:8766/docs    (Swagger UI)
    http://127.0.0.1:8766/redoc  (ReDoc)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Asegurar que el root del proyecto está en el path para imports locales
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import db
from backend.api.middleware.logging import RequestLoggingMiddleware
from backend.api.exception_handlers import riot_api_error_handler, general_error_handler
from backend.api.routes import health, dashboard, matches, coaching, draft, settings, progress, knowledge, training
from backend.api.routes import live_coach as live_coach_route
from backend.api.websocket.draft_ws import router as ws_router
from backend.api.websocket.live_coach_ws import router as live_coach_ws_router
from riot_api import RiotAPIError

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="LoL Coach API",
    description=(
        "Backend de LoL Coach. Consume ViewModels para alimentar "
        "la interfaz Electron/React sin duplicar lógica de negocio."
    ),
    version="E-2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (necesario para que Electron/React llame al backend local) ────────────
# La API solo escucha en 127.0.0.1 — allow_origins=["*"] es seguro aquí
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Logging ────────────────────────────────────────────────────────────────────
app.add_middleware(RequestLoggingMiddleware)

# ── Manejadores de errores ─────────────────────────────────────────────────────
app.add_exception_handler(RiotAPIError, riot_api_error_handler)
app.add_exception_handler(Exception, general_error_handler)

# ── Rutas REST ─────────────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"

app.include_router(health.router,   prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(matches.router,  prefix=API_PREFIX)
app.include_router(coaching.router, prefix=API_PREFIX)
app.include_router(draft.router,    prefix=API_PREFIX)
app.include_router(settings.router,  prefix=API_PREFIX)
app.include_router(progress.router,   prefix=API_PREFIX)
app.include_router(knowledge.router,  prefix=API_PREFIX)
app.include_router(training.router,        prefix=API_PREFIX)
app.include_router(live_coach_route.router, prefix=API_PREFIX)

# ── WebSocket (sin prefijo) ────────────────────────────────────────────────────
app.include_router(ws_router)
app.include_router(live_coach_ws_router)


# ── Startup ────────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup() -> None:
    """Inicializa la DB al arrancar el servidor."""
    db.init_db()
    logging.getLogger("lol_coach").info("LoL Coach API iniciada — http://127.0.0.1:8765/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host="127.0.0.1", port=8765, reload=False)
