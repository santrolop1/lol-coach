"""
server/models.py — Esquema normalizado del backend de conocimiento.

Diseño:
    anon_users      1─N  match_summaries  1─N  match_dimensions
    anon_users      1─N  coaching_snapshots 1─N snapshot_problems / snapshot_strengths
    anon_users      1─N  champion_reports
    champions       1─N  match_summaries / champion_reports
    patches         1─N  match_summaries
    knowledge_versions (snapshots versionados generados por knowledge.py)

Los usuarios son ANÓNIMOS: `install_id` es un UUID aleatorio generado por
el cliente, sin relación con la cuenta de Riot. `match_hash` es un hash
salteado del match_id — el ID real de Riot nunca llega al servidor.

Índices pensados para las consultas del sistema de conocimiento:
percentiles por (rol, tier), winrate por campeón/parche, y dedup por usuario.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer,
    String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnonUser(Base):
    __tablename__ = "anon_users"

    id:             Mapped[int]      = mapped_column(Integer, primary_key=True)
    install_id:     Mapped[str]      = mapped_column(String(64), unique=True, index=True)
    client_version: Mapped[str]      = mapped_column(String(32))
    first_seen:     Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    last_seen:      Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    matches: Mapped[list["MatchSummary"]] = relationship(back_populates="user")


class Patch(Base):
    __tablename__ = "patches"

    id:      Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # "15.13"


class Champion(Base):
    __tablename__ = "champions"

    id:   Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)     # alias Riot


class MatchSummary(Base):
    __tablename__ = "match_summaries"
    __table_args__ = (
        # Dedup: un cliente no puede reportar la misma partida dos veces.
        UniqueConstraint("user_id", "match_hash", name="uq_user_match"),
        # Consultas del sistema de conocimiento.
        Index("ix_match_role_tier", "role", "elo_tier"),
        Index("ix_match_champion_patch", "champion_id", "patch_id"),
    )

    id:            Mapped[int]   = mapped_column(Integer, primary_key=True)
    user_id:       Mapped[int]   = mapped_column(ForeignKey("anon_users.id"), index=True)
    match_hash:    Mapped[str]   = mapped_column(String(32))
    champion_id:   Mapped[int]   = mapped_column(ForeignKey("champions.id"))
    patch_id:      Mapped[int | None] = mapped_column(ForeignKey("patches.id"), nullable=True)

    role:          Mapped[str]   = mapped_column(String(8))
    elo_tier:      Mapped[str]   = mapped_column(String(16))
    result:        Mapped[str]   = mapped_column(String(8))     # WIN | LOSS
    duration_sec:  Mapped[int]   = mapped_column(Integer)
    surrender:     Mapped[bool]  = mapped_column(Boolean, default=False)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Estadísticas agregadas (desnormalizadas a propósito: son la materia
    # prima de los percentiles y se consultan siempre juntas).
    kills:              Mapped[int | None]   = mapped_column(Integer, nullable=True)
    deaths:             Mapped[int | None]   = mapped_column(Integer, nullable=True)
    assists:            Mapped[int | None]   = mapped_column(Integer, nullable=True)
    cs_per_min:         Mapped[float | None] = mapped_column(Float, nullable=True)
    gold_per_min:       Mapped[float | None] = mapped_column(Float, nullable=True)
    damage_per_min:     Mapped[float | None] = mapped_column(Float, nullable=True)
    kill_participation: Mapped[float | None] = mapped_column(Float, nullable=True)
    team_damage_pct:    Mapped[float | None] = mapped_column(Float, nullable=True)
    cs_at_10:           Mapped[int | None]   = mapped_column(Integer, nullable=True)
    vision_score:       Mapped[int | None]   = mapped_column(Integer, nullable=True)

    # Build / runas / hechizos: el cliente aún no los captura. El campo ya
    # existe para no migrar el esquema cuando lleguen (JSON opcional).
    loadout: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    client_version: Mapped[str]      = mapped_column(String(32))
    created_at:     Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    user:       Mapped[AnonUser]              = relationship(back_populates="matches")
    dimensions: Mapped[list["MatchDimension"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class MatchDimension(Base):
    __tablename__ = "match_dimensions"
    __table_args__ = (Index("ix_dim_name", "name"),)

    id:       Mapped[int]   = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int]   = mapped_column(ForeignKey("match_summaries.id"), index=True)
    name:     Mapped[str]   = mapped_column(String(32))   # "Economy", "Lane Dominance"…
    score:    Mapped[float] = mapped_column(Float)

    match: Mapped[MatchSummary] = relationship(back_populates="dimensions")


class CoachingSnapshot(Base):
    __tablename__ = "coaching_snapshots"
    __table_args__ = (Index("ix_snap_role_tier", "role", "elo_tier"),)

    id:               Mapped[int]   = mapped_column(Integer, primary_key=True)
    user_id:          Mapped[int]   = mapped_column(ForeignKey("anon_users.id"), index=True)
    role:             Mapped[str]   = mapped_column(String(8))
    elo_tier:         Mapped[str]   = mapped_column(String(16))
    confidence_level: Mapped[str]   = mapped_column(String(16))
    sample_size:      Mapped[int]   = mapped_column(Integer)
    primary_problem:  Mapped[str]   = mapped_column(String(128))
    overall_score:    Mapped[float | None] = mapped_column(Float, nullable=True)
    consistency:      Mapped[float | None] = mapped_column(Float, nullable=True)
    trend:            Mapped[str]   = mapped_column(String(16))
    created_at:       Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    problems: Mapped[list["SnapshotProblem"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )
    strengths: Mapped[list["SnapshotStrength"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class SnapshotProblem(Base):
    __tablename__ = "snapshot_problems"
    __table_args__ = (Index("ix_problem_name", "name"),)

    id:          Mapped[int]  = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int]  = mapped_column(ForeignKey("coaching_snapshots.id"), index=True)
    name:        Mapped[str]  = mapped_column(String(128))
    is_primary:  Mapped[bool] = mapped_column(Boolean, default=False)

    snapshot: Mapped[CoachingSnapshot] = relationship(back_populates="problems")


class SnapshotStrength(Base):
    __tablename__ = "snapshot_strengths"

    id:          Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("coaching_snapshots.id"), index=True)
    name:        Mapped[str] = mapped_column(String(128))

    snapshot: Mapped[CoachingSnapshot] = relationship(back_populates="strengths")


class ChampionReport(Base):
    __tablename__ = "champion_reports"
    __table_args__ = (Index("ix_champrep_champ_role", "champion_id", "role"),)

    id:             Mapped[int]   = mapped_column(Integer, primary_key=True)
    user_id:        Mapped[int]   = mapped_column(ForeignKey("anon_users.id"), index=True)
    champion_id:    Mapped[int]   = mapped_column(ForeignKey("champions.id"))
    role:           Mapped[str]   = mapped_column(String(8))
    elo_tier:       Mapped[str]   = mapped_column(String(16))
    games:          Mapped[int]   = mapped_column(Integer)
    wins:           Mapped[int]   = mapped_column(Integer)
    avg_score:      Mapped[float] = mapped_column(Float)
    classification: Mapped[str]   = mapped_column(String(16))   # MAIN/CARRY/COMFORT/TRAP/SOLID
    created_at:     Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True)
    version:    Mapped[int]      = mapped_column(Integer, unique=True, index=True)
    payload:    Mapped[dict]     = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
