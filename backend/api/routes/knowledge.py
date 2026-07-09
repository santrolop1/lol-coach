"""
GET /knowledge — El cerebro del Coach.

Solo consume el ViewModel. No contiene lógica de negocio.
"""

from __future__ import annotations

import dataclasses

from fastapi import APIRouter

from backend.knowledge.engine import build_knowledge
from backend.api.schemas.knowledge import KnowledgeResponse

router = APIRouter()


@router.get("/knowledge", response_model=KnowledgeResponse, tags=["Knowledge"])
def get_knowledge() -> KnowledgeResponse:
    """
    Unifica todos los sistemas de análisis para responder:
    ¿Qué debería decirle al jugador en este momento?

    Devuelve: sesión actual, objetivo adaptativo, memoria de objetivos,
    patrones detectados, insights accionables y recomendaciones priorizadas.
    """
    vm = build_knowledge()

    return KnowledgeResponse(
        has_data=      vm.has_data,
        role=          vm.role,
        total_matches= vm.total_matches,
        session=       _s_session(vm.session),
        active_goal=   dataclasses.asdict(vm.active_goal) if vm.active_goal else None,
        memory=        [dataclasses.asdict(e) for e in vm.memory],
        patterns=      [dataclasses.asdict(p) for p in vm.patterns],
        insights=      [dataclasses.asdict(i) for i in vm.insights],
        recommendations= [dataclasses.asdict(r) for r in vm.recommendations],
        confidence=    vm.confidence,
        games_needed_msg= vm.games_needed_msg,
    )


def _s_session(s) -> dict:
    return {
        "has_session":   s.has_session,
        "total_games":   s.total_games,
        "wins":          s.wins,
        "losses":        s.losses,
        "avg_score":     s.avg_score,
        "best_aspect":   s.best_aspect,
        "worst_aspect":  s.worst_aspect,
        "goal_progress": s.goal_progress,
        "tip":           s.tip,
        "session_label": s.session_label,
        "matches":       [dataclasses.asdict(m) for m in s.matches],
    }
