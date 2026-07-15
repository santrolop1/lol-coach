"""
server/api.py — Endpoints REST del backend de conocimiento.

Ingesta (cliente → servidor):
    POST /telemetry/match     lotes de resúmenes de partida
    POST /telemetry/session   lotes de diagnósticos de coaching
    POST /telemetry/champion  lotes de stats por campeón

Conocimiento (servidor → cliente):
    GET  /knowledge/version   versión del snapshot vigente
    GET  /knowledge/update    snapshot completo (umbrales, stats, tendencias)

Toda la validación de payload la hace Pydantic (schemas.py) — si algo
llega aquí, ya es estructuralmente válido. La ingesta es idempotente:
los duplicados se cuentan y descartan, nunca fallan.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from server.database import get_db
from server.models import (
    AnonUser, Champion, ChampionReport, CoachingSnapshot, KnowledgeVersion,
    MatchDimension, MatchSummary, Patch, SnapshotProblem, SnapshotStrength,
)
from server.schemas import (
    ChampionBatch, IngestResult, KnowledgeOut, KnowledgeVersionOut,
    MatchBatch, SessionBatch,
)

telemetry_router = APIRouter(prefix="/telemetry", tags=["telemetry"])
knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ── Helpers de upsert ─────────────────────────────────────────────────────────

def _get_or_create_user(db: Session, install_id: str, client_version: str) -> AnonUser:
    user = db.scalar(select(AnonUser).where(AnonUser.install_id == install_id))
    if user is None:
        user = AnonUser(install_id=install_id, client_version=client_version)
        db.add(user)
        db.flush()
    else:
        user.client_version = client_version
        from datetime import datetime, timezone
        user.last_seen = datetime.now(timezone.utc)
    return user


def _get_or_create_champion(db: Session, name: str) -> Champion:
    champ = db.scalar(select(Champion).where(Champion.name == name))
    if champ is None:
        champ = Champion(name=name)
        db.add(champ)
        db.flush()
    return champ


def _get_or_create_patch(db: Session, version: str | None) -> Patch | None:
    if not version:
        return None
    patch = db.scalar(select(Patch).where(Patch.version == version))
    if patch is None:
        patch = Patch(version=version)
        db.add(patch)
        db.flush()
    return patch


# ── Ingesta ───────────────────────────────────────────────────────────────────

@telemetry_router.post("/match", response_model=IngestResult, status_code=202)
def ingest_matches(batch: MatchBatch, db: Session = Depends(get_db)) -> IngestResult:
    accepted = duplicates = 0
    for item in batch.items:
        user  = _get_or_create_user(db, item.install_id, item.client_version)
        champ = _get_or_create_champion(db, item.champion)
        patch = _get_or_create_patch(db, item.patch)

        exists = db.scalar(
            select(MatchSummary.id).where(
                MatchSummary.user_id == user.id,
                MatchSummary.match_hash == item.match_hash,
            )
        )
        if exists is not None:
            duplicates += 1
            continue

        summary = MatchSummary(
            user_id=user.id,
            match_hash=item.match_hash,
            champion_id=champ.id,
            patch_id=patch.id if patch else None,
            role=item.role,
            elo_tier=item.elo_tier,
            result=item.result,
            duration_sec=item.duration_sec,
            surrender=item.surrender,
            overall_score=item.overall_score,
            kills=item.stats.kills,
            deaths=item.stats.deaths,
            assists=item.stats.assists,
            cs_per_min=item.stats.cs_per_min,
            gold_per_min=item.stats.gold_per_min,
            damage_per_min=item.stats.damage_per_min,
            kill_participation=item.stats.kill_participation,
            team_damage_pct=item.stats.team_damage_pct,
            cs_at_10=item.stats.cs_at_10,
            vision_score=item.stats.vision_score,
            loadout=item.loadout,
            client_version=item.client_version,
        )
        summary.dimensions = [
            MatchDimension(name=name[:32], score=score)
            for name, score in item.dimensions.items()
            if 0 <= score <= 100
        ]
        db.add(summary)
        try:
            db.flush()
            accepted += 1
        except IntegrityError:
            db.rollback()
            duplicates += 1
    db.commit()
    return IngestResult(accepted=accepted, duplicates=duplicates)


@telemetry_router.post("/session", response_model=IngestResult, status_code=202)
def ingest_sessions(batch: SessionBatch, db: Session = Depends(get_db)) -> IngestResult:
    accepted = 0
    for item in batch.items:
        user = _get_or_create_user(db, item.install_id, item.client_version)
        snap = CoachingSnapshot(
            user_id=user.id,
            role=item.role,
            elo_tier=item.elo_tier,
            confidence_level=item.confidence_level,
            sample_size=item.sample_size,
            primary_problem=item.primary_problem[:128],
            overall_score=item.overall_score,
            consistency=item.consistency,
            trend=item.trend,
        )
        snap.problems = (
            [SnapshotProblem(name=item.primary_problem[:128], is_primary=True)]
            + [SnapshotProblem(name=p[:128], is_primary=False) for p in item.improvements]
        )
        snap.strengths = [SnapshotStrength(name=s[:128]) for s in item.strengths]
        db.add(snap)
        accepted += 1
    db.commit()
    return IngestResult(accepted=accepted, duplicates=0)


@telemetry_router.post("/champion", response_model=IngestResult, status_code=202)
def ingest_champions(batch: ChampionBatch, db: Session = Depends(get_db)) -> IngestResult:
    accepted = 0
    for item in batch.items:
        user  = _get_or_create_user(db, item.install_id, item.client_version)
        champ = _get_or_create_champion(db, item.champion)
        db.add(ChampionReport(
            user_id=user.id,
            champion_id=champ.id,
            role=item.role,
            elo_tier=item.elo_tier,
            games=item.games,
            wins=min(item.wins, item.games),
            avg_score=item.avg_score,
            classification=item.classification,
        ))
        accepted += 1
    db.commit()
    return IngestResult(accepted=accepted, duplicates=0)


# ── Conocimiento ──────────────────────────────────────────────────────────────

def _latest_knowledge(db: Session) -> KnowledgeVersion | None:
    return db.scalar(
        select(KnowledgeVersion).order_by(KnowledgeVersion.version.desc()).limit(1)
    )


@knowledge_router.get("/version", response_model=KnowledgeVersionOut)
def knowledge_version(db: Session = Depends(get_db)) -> KnowledgeVersionOut:
    latest = _latest_knowledge(db)
    if latest is None:
        raise HTTPException(404, "Todavía no se ha publicado ningún snapshot de conocimiento.")
    return KnowledgeVersionOut(
        version=latest.version, created_at=latest.created_at.isoformat()
    )


@knowledge_router.get("/update", response_model=KnowledgeOut)
def knowledge_update(db: Session = Depends(get_db)) -> KnowledgeOut:
    latest = _latest_knowledge(db)
    if latest is None:
        raise HTTPException(404, "Todavía no se ha publicado ningún snapshot de conocimiento.")
    return KnowledgeOut(
        version=latest.version,
        created_at=latest.created_at.isoformat(),
        payload=latest.payload,
    )
