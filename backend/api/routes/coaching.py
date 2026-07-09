"""
GET /coaching — Datos completos de coaching para un rol y ventana.

Solo consume el ViewModel. No contiene lógica de negocio.
"""

from __future__ import annotations

import dataclasses
from typing import Literal

from fastapi import APIRouter, Query

from backend.viewmodels.coaching_vm import build_coaching, build_champion_coach
from backend.api.schemas.coaching import CoachingResponse

router = APIRouter()


@router.get("/coaching", response_model=CoachingResponse, tags=["Coaching"])
def get_coaching(
    role:  Literal["ADC", "TOP"] = Query(default="ADC", description="Rol a analizar"),
    limit: int                   = Query(default=20, ge=5, le=200, description="Número de partidas"),
) -> CoachingResponse:
    """
    Devuelve el análisis completo de coaching para el rol y ventana indicados.

    Incluye: score, coaching result, prioridades, métricas, matchups, champion pool.
    """
    vm = build_coaching(role, limit)

    score_schema  = _serialize_score_result(vm.score_result) if vm.score_result else None
    coach_schema  = _serialize_coaching_result(vm.coaching_result) if vm.coaching_result else None
    metrics_schema = dataclasses.asdict(vm.metrics) if vm.metrics else None
    priorities    = [_serialize_priority(p) for p in vm.priorities]

    return CoachingResponse(
        player_name=     vm.player_name,
        rank=            vm.rank,
        lp=              vm.lp,
        last_match_date= vm.last_match_date,
        role=            vm.role,
        sample_size=     vm.sample_size,
        has_data=        vm.has_data,
        score_result=    score_schema,
        coaching_result= coach_schema,
        metrics=         metrics_schema,
        priorities=      priorities,
        available_champions= vm.available_champions,
    )


@router.get("/coaching/champion", tags=["Coaching"])
def get_champion_coach(
    champion: str                    = Query(..., description="Nombre del campeón"),
    role:     Literal["ADC", "TOP"] = Query(default="ADC"),
    limit:    int                    = Query(default=20, ge=5, le=200),
) -> dict:
    """
    Análisis detallado de Champion Coach para un campeón específico.
    """
    vm     = build_coaching(role, limit)
    result = build_champion_coach(vm, champion)
    return dataclasses.asdict(result)


# ── Serialización ──────────────────────────────────────────────────────────────

def _serialize_score_result(sr) -> dict:
    return {
        "role":              sr.role,
        "overall_score":     sr.overall_score,
        "trend":             getattr(sr, "trend", None),
        "consistency_score": getattr(sr, "consistency_score", None),
        "confidence_level":  sr.confidence_level,
        "dimensions":        sr.dimensions if isinstance(sr.dimensions, dict) else {},
        "match_scores": [
            {
                "match_id":      ms.match_id,
                "role":          ms.role,
                "overall_score": ms.overall_score,
                "is_surrender":  ms.is_surrender,
                "result":        ms.result,
                "champion":      ms.champion,
                "dimensions": [
                    {"name": d.name, "score": d.score, "metrics": d.metrics, "notes": d.notes}
                    for d in ms.dimensions
                ],
            }
            for ms in (sr.match_scores or [])
        ],
    }


def _serialize_coaching_result(cr) -> dict:
    return {
        "role":            cr.role,
        "sample_size":     cr.sample_size,
        "confidence_level": cr.confidence_level,
        "primary_problem": cr.primary_problem,
        "evidence":        getattr(cr, "evidence", None),
        "probable_cause":  getattr(cr, "probable_cause", None),
        "impact":          getattr(cr, "impact", None),
        "trend_summary":   getattr(cr, "trend_summary", None),
        "session_warning": cr.session_warning,
        "strengths":    [dataclasses.asdict(s) for s in (cr.strengths or [])],
        "improvements": getattr(cr, "improvements", []) or [],
        "weekly_goal":  dataclasses.asdict(cr.weekly_goal) if cr.weekly_goal else None,
        "training_plan": dataclasses.asdict(cr.training_plan) if cr.training_plan else None,
    }


def _serialize_priority(p) -> dict:
    return {
        "title":          p.title,
        "metric_key":     p.metric_key,
        "impact_score":   p.impact_score,
        "confidence":     p.confidence,
        "evidence":       p.evidence,
        "recommendation": p.recommendation,
        "current_value":  p.current_value,
        "target_value":   p.target_value,
        "unit":           p.unit,
    }
