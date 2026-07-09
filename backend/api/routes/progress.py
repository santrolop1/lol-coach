"""
GET /progress — Coaching Progresivo: evolución del jugador.

Solo consume el ViewModel. No contiene lógica de negocio.
"""

from __future__ import annotations

import dataclasses

from fastapi import APIRouter

from backend.viewmodels.progress_vm import build_progress
from backend.api.schemas.progress import ProgressResponse

router = APIRouter()


@router.get("/progress", response_model=ProgressResponse, tags=["Progreso"])
def get_progress() -> ProgressResponse:
    """
    Analiza la evolución del jugador en las últimas 10–50 partidas.

    Devuelve tendencias por dimensión, objetivo semanal, hábitos detectados,
    análisis por campeón y recomendaciones priorizadas. Todo el análisis
    ocurre en el backend — el frontend solo organiza la presentación.
    """
    vm = build_progress()

    return ProgressResponse(
        has_data=    vm.has_data,
        role=        vm.role,
        total_matches= vm.total_matches,
        overall_trend=       vm.overall_trend,
        overall_trend_label= vm.overall_trend_label,
        overall_delta=       vm.overall_delta,
        avg_recent=          vm.avg_recent,
        confidence=          vm.confidence,
        timeline=      [dataclasses.asdict(p) for p in vm.timeline],
        score_series=  vm.score_series,
        improving= [dataclasses.asdict(i) for i in vm.improving],
        declining= [dataclasses.asdict(i) for i in vm.declining],
        stable=    [dataclasses.asdict(i) for i in vm.stable],
        habits=    [dataclasses.asdict(h) for h in vm.habits],
        weekly_goal= dataclasses.asdict(vm.weekly_goal) if vm.weekly_goal else None,
        champion_insights= [dataclasses.asdict(c) for c in vm.champion_insights],
        recommendations=   [dataclasses.asdict(r) for r in vm.recommendations],
        min_games_needed= vm.min_games_needed,
        games_needed_msg= vm.games_needed_msg,
    )
