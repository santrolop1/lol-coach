"""
server/app.py — Aplicación FastAPI del backend de conocimiento.

Ejecución local:
    pip install -r server/requirements.txt
    uvicorn server.app:app --port 8787

Producción (PostgreSQL):
    DATABASE_URL=postgresql+psycopg://user:pass@host/db \
        uvicorn server.app:app --host 0.0.0.0 --port 8787
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from server import database
from server.api import knowledge_router, telemetry_router
from server.models import Base
from version import __version__


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Para producción con PostgreSQL se recomienda Alembic; create_all es
    # idempotente y suficiente para SQLite/dev y el primer despliegue.
    # database.engine se resuelve en runtime (los tests lo reapuntan).
    Base.metadata.create_all(database.engine)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="LoL Coach — Knowledge API",
        version=__version__,
        lifespan=_lifespan,
    )
    app.include_router(telemetry_router)
    app.include_router(knowledge_router)

    @app.get("/health", tags=["ops"])
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
