"""
GET /dashboard — Resumen rápido multi-rol para la pantalla principal.

Agrega los datos más importantes de ADC y TOP en una sola llamada.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.viewmodels.coaching_vm import build_coaching
from backend.viewmodels.settings_vm import build_settings
from backend.services.sync_service import get_last_sync, sync_status_label

router = APIRouter()


@router.get("/dashboard", tags=["Dashboard"])
def get_dashboard() -> dict:
    """
    Resumen ejecutivo del jugador.

    Devuelve métricas clave para ADC y TOP sin el detalle completo de coaching.
    Ideal para la pantalla principal de Electron.
    """
    settings = build_settings()
    last_sync = get_last_sync()

    roles_summary = {}
    for role in ("ADC", "TOP"):
        vm = build_coaching(role, limit=20)
        if vm.has_data:
            roles_summary[role] = {
                "overall_score":     vm.score_result.overall_score if vm.score_result else None,
                "trend":             vm.score_result.trend if vm.score_result else None,
                "confidence_level":  vm.score_result.confidence_level if vm.score_result else None,
                "sample_size":       vm.sample_size,
                "primary_problem":   vm.coaching_result.primary_problem if vm.coaching_result else None,
                "top_priority":      vm.priorities[0].title if vm.priorities else None,
                "winrate":           round(vm.metrics.n_wins / vm.metrics.n * 100, 1) if vm.metrics.n else 0,
            }
        else:
            roles_summary[role] = {"has_data": False}

    return {
        "player_name":  settings.riot_id or "Invocador",
        "rank":         settings.rank,
        "lp":           settings.lp,
        "is_configured": settings.is_configured,
        "last_sync":    last_sync.isoformat() if last_sync else None,
        "sync_label":   sync_status_label(),
        "roles":        roles_summary,
    }
