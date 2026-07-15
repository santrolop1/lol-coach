"""
server/database.py — Motor de base de datos del backend.

SQLAlchemy 2.0 con URL configurable por entorno:

    DATABASE_URL no definida  → SQLite local (desarrollo / pruebas)
    DATABASE_URL=postgresql+psycopg://user:pass@host/db  → producción

El mismo código sirve para ambos: los modelos usan tipos portables y
ninguna query usa SQL específico de un motor. Migrar a PostgreSQL es
cambiar la variable de entorno.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

_DEFAULT_SQLITE = f"sqlite:///{Path(__file__).parent / 'data' / 'knowledge.db'}"


def _database_url() -> str:
    return os.environ.get("DATABASE_URL", _DEFAULT_SQLITE)


def _make_engine():
    url = _database_url()
    kwargs = {}
    if url.startswith("sqlite"):
        Path(url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
        # Streamlit no aplica aquí, pero TestClient usa threads:
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency de FastAPI: una sesión por request, siempre cerrada."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_engine_for_tests(url: str) -> None:
    """Reapunta el engine (solo para tests, antes de crear la app)."""
    global engine, SessionLocal
    os.environ["DATABASE_URL"] = url
    engine = _make_engine()
    SessionLocal.configure(bind=engine)
