"""
GET /matches                        — Historial de partidas con análisis.
GET /matches/{match_id}/review      — Revisión detallada de una partida.

Solo consume ViewModels. No contiene lógica de negocio.
"""

from __future__ import annotations

import dataclasses

from fastapi import APIRouter, Query, HTTPException

from backend.viewmodels.matches_vm    import build_matches
from backend.viewmodels.match_review_vm import build_match_review
from backend.api.schemas.matches import MatchesResponse, MatchReviewResponse

router = APIRouter()


@router.get("/matches", response_model=MatchesResponse, tags=["Partidas"])
def get_matches(
    role:     str | None = Query(default=None, description="Filtrar por rol (ADC/TOP)"),
    champion: str | None = Query(default=None, description="Filtrar por campeón"),
) -> MatchesResponse:
    """
    Devuelve el historial de partidas con scoring, tarjetas y análisis V2.

    - **role**: filtra por rol (ADC, TOP). Sin valor = todos los roles.
    - **champion**: filtra por campeón exacto.
    """
    vm = build_matches(role_filter=role, champion_filter=champion)

    return MatchesResponse(
        has_config=       vm.has_config,
        player=           _serialize_player(vm.player) if vm.player else None,
        recent_cards=     [dataclasses.asdict(c) for c in vm.recent_cards],
        table_rows=       [dataclasses.asdict(r) for r in vm.table_rows],
        summary=          dataclasses.asdict(vm.summary),
        v2_analysis=      _serialize_v2(vm.v2_analysis) if vm.v2_analysis else None,
        available_roles=  vm.available_roles,
        available_champs= vm.available_champs,
    )


@router.get("/matches/{match_id}/review", response_model=MatchReviewResponse, tags=["Partidas"])
def get_match_review(match_id: str) -> MatchReviewResponse:
    """
    Revisión detallada post-partida: score, dimensiones, métricas comparadas
    con el promedio del jugador, error principal y tip para la siguiente partida.
    """
    vm = build_match_review(match_id)

    if not vm.found:
        raise HTTPException(status_code=404, detail=f"Partida {match_id!r} no encontrada.")

    return MatchReviewResponse(
        found=          vm.found,
        match_id=       vm.match_id,
        date=           vm.date,
        champion=       vm.champion,
        role=           vm.role,
        is_win=         vm.is_win,
        is_surrender=   vm.is_surrender,
        duration=       vm.duration,
        kda=            vm.kda,
        kills=          vm.kills,
        deaths_n=       vm.deaths_n,
        assists=        vm.assists,
        cs=             vm.cs,
        overall_score=  vm.overall_score,
        avg_overall=    vm.avg_overall,
        overall_delta=  vm.overall_delta,
        dimensions=     [_serialize_dim(d) for d in vm.dimensions],
        best_dim_name=  vm.best_dim_name,
        worst_dim_name= vm.worst_dim_name,
        key_error_title= vm.key_error_title,
        key_error_body=  vm.key_error_body,
        focus_tip=       vm.focus_tip,
        sample_size=    vm.sample_size,
        confidence=     vm.confidence,
        role_supported= vm.role_supported,
    )


# ── Serializers privados ───────────────────────────────────────────────────────

def _serialize_player(p: dict) -> dict:
    return {
        "riot_id": p.get("riot_id", ""),
        "tag":     p.get("tag", ""),
        "level":   p.get("level"),
        "rank":    p.get("rank"),
        "tier":    p.get("tier"),
        "lp":      p.get("lp"),
    }


def _serialize_v2(v2) -> dict:
    return {
        "role":        v2.role,
        "detail_rows": [dataclasses.asdict(r) for r in v2.detail_rows],
        "avg_overall": v2.avg_overall,
        "avg_dims":    v2.avg_dims,
        "available":   v2.available,
    }


def _serialize_dim(d) -> dict:
    return {
        "name":      d.name,
        "name_es":   d.name_es,
        "score":     d.score,
        "avg_score": d.avg_score,
        "delta":     d.delta,
        "is_best":   d.is_best,
        "is_worst":  d.is_worst,
        "metrics":   [dataclasses.asdict(m) for m in d.metrics],
        "notes":     d.notes,
        "context":   d.context,
    }
