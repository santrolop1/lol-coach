"""
backend/api/routes/live_coach.py — Endpoints REST del Live Coach.

GET  /api/v1/live-coach          → estado actual del overlay (snapshot)
GET  /api/v1/live-coach/config   → configuración del overlay
POST /api/v1/live-coach/config   → actualizar configuración
POST /api/v1/live-coach/champion → configurar campeón activo manualmente

Sin lógica de negocio — delega todo al LiveCoach facade (instancia de proceso).
"""

from __future__ import annotations
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.live_coach.coach import LiveCoach
from backend.live_coach.models import OverlayState
from backend.live_coach.config import OverlayConfig, load_config, save_config
from backend.live_coach.providers.live_client import RiotLiveClientProvider
from backend.live_coach.providers.mock import MockLiveDataProvider
from backend.live_coach.demo_controller import DemoController

router = APIRouter(tags=["live-coach"])
logger = logging.getLogger("lol_coach.api.live_coach")

# ── Instancia de proceso (singleton ligero) ───────────────────────────────────
# Inicializa con Mock en dev, con Live Client en producción.
# El WebSocket usa la misma instancia.

def _make_coach() -> LiveCoach:
    try:
        from backend.game_intelligence.registries.registry_facade import knowledge
        provider = RiotLiveClientProvider()
        return LiveCoach(provider=provider, knowledge_api=knowledge)
    except Exception as exc:
        logger.warning("No se pudo inicializar Live Client provider: %s. Usando Mock.", exc)
        return LiveCoach(provider=MockLiveDataProvider(), knowledge_api=None)


_coach: LiveCoach = _make_coach()
_demo: DemoController = DemoController()


def get_coach() -> LiveCoach:
    """Acceso a la instancia compartida del proceso."""
    return _coach


def get_demo() -> DemoController:
    return _demo


# ── Schemas ───────────────────────────────────────────────────────────────────

class SetChampionRequest(BaseModel):
    champion: str
    role: str = "TOP"


class DemoActivateRequest(BaseModel):
    champion: str = "tryndamere"
    scenario: str = "early_game"


class DemoScenarioRequest(BaseModel):
    scenario: str
    champion: str | None = None


class DemoEventRequest(BaseModel):
    event_type: str        # nombre del EventType: "LEVEL_UP", "DEATH", etc.
    data: dict = {}


class ConfigUpdateRequest(BaseModel):
    opacity: float | None = None
    compact_mode: bool | None = None
    always_on_top: bool | None = None
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    scale: float | None = None
    detail_level: str | None = None
    widgets_enabled: dict[str, bool] | None = None
    tip_interval_seconds: int | None = None
    auto_hide_on_idle: bool | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/live-coach")
def get_live_coach_state() -> dict:
    """
    Snapshot del estado actual del Live Coach.
    El frontend puede hacer polling cada 2-5s si no usa WebSocket.
    """
    coach = get_coach()
    coach.tick()
    state = coach.get_state()
    return state.to_dict()


@router.post("/live-coach/champion")
def set_champion(req: SetChampionRequest) -> dict:
    """
    Configura manualmente el campeón que está jugando el usuario.
    Útil cuando el Live Client no está disponible.
    """
    if not req.champion.strip():
        raise HTTPException(status_code=400, detail="champion no puede estar vacío")
    coach = get_coach()
    coach.set_champion(req.champion.lower(), req.role.upper())
    return {"ok": True, "champion": req.champion.lower(), "role": req.role.upper()}


@router.get("/live-coach/config")
def get_config() -> dict:
    """Devuelve la configuración persistida del overlay."""
    config = load_config()
    return config.to_dict()


@router.post("/live-coach/config")
def update_config(req: ConfigUpdateRequest) -> dict:
    """Actualiza parcialmente la configuración del overlay y la persiste."""
    config = load_config()
    update_data = req.model_dump(exclude_none=True)
    for key, value in update_data.items():
        if hasattr(config, key):
            setattr(config, key, value)
    save_config(config)
    return config.to_dict()


@router.post("/live-coach/reset")
def reset_coach() -> dict:
    """Reinicia el estado del Live Coach (nueva partida)."""
    get_coach().reset()
    return {"ok": True}


# ── Demo Mode ─────────────────────────────────────────────────────────────────

@router.get("/live-coach/demo")
def get_demo_state() -> dict:
    """Estado actual del Demo Mode + lista de escenarios disponibles."""
    demo = get_demo()
    return {
        **demo.get_state(),
        "scenarios": demo.list_scenarios(),
    }


@router.post("/live-coach/demo/activate")
def activate_demo(req: DemoActivateRequest) -> dict:
    """Activa el Demo Mode con el escenario inicial indicado."""
    demo = get_demo()
    demo.activate(get_coach(), champion=req.champion)
    try:
        demo.set_scenario(req.scenario, req.champion)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return demo.get_state()


@router.post("/live-coach/demo/deactivate")
def deactivate_demo() -> dict:
    """Desactiva el Demo Mode y vuelve al Riot Live Client."""
    get_demo().deactivate()
    return {"ok": True, "active": False}


@router.post("/live-coach/demo/scenario")
def set_demo_scenario(req: DemoScenarioRequest) -> dict:
    """Cambia el escenario activo del Demo Mode."""
    demo = get_demo()
    if not demo.is_active:
        raise HTTPException(status_code=400, detail="Demo Mode no está activo. Actívalo primero con POST /live-coach/demo/activate")
    try:
        demo.set_scenario(req.scenario, req.champion)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return demo.get_state()


@router.post("/live-coach/demo/event")
def fire_demo_event(req: DemoEventRequest) -> dict:
    """Dispara un evento manualmente en el Live Coach (solo en Demo Mode)."""
    demo = get_demo()
    if not demo.is_active:
        raise HTTPException(status_code=400, detail="Demo Mode no está activo")
    try:
        ok = demo.fire_event(req.event_type, req.data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": ok, "event_type": req.event_type}


# ── Debug ─────────────────────────────────────────────────────────────────────

@router.get("/live-coach/debug")
def get_debug_state() -> dict:
    """
    Dump completo del estado interno del Live Coach para depuración.
    Solo para uso en desarrollo — no exponer en producción.
    """
    coach = get_coach()
    coach.tick()
    state = coach.get_state()
    base = state.to_dict()

    demo = get_demo()

    intelligence = base.get("intelligence") or {}
    decision = base.get("current_decision")

    # Widgets detallados
    widgets_detail = [
        {
            "id": w.widget_id.value,
            "title": w.title,
            "lines": w.lines,
            "priority": w.priority.value,
            "highlight": w.highlight,
            "visible": w.visible,
            "ttl": w.ttl,
        }
        for w in state.widgets
    ]

    # Eventos recientes del EventBus
    recent_events = []
    try:
        history = coach.event_bus._history
        recent_events = [
            {
                "type": e.type.value,
                "timestamp": e.timestamp,
                "data": e.data,
            }
            for e in list(history)[-10:]
        ]
    except Exception:
        pass

    # Historial de decisiones
    decision_history = []
    try:
        decision_history = coach._decision_engine.history.to_list()[-10:]
    except Exception:
        pass

    return {
        "session": {
            "active": base.get("active"),
            "champion": base.get("champion"),
            "role": base.get("role"),
            "game_time": base.get("game_time"),
            "phase": base.get("phase"),
            "provider_connected": base.get("provider_connected"),
        },
        "player": base.get("player"),
        "intelligence": {
            "state": intelligence.get("state"),
            "phase": intelligence.get("phase"),
            "situation": intelligence.get("situation"),
            "is_power_spike": intelligence.get("is_power_spike"),
            "is_recall_window": intelligence.get("is_recall_window"),
            "objective": intelligence.get("objective"),
            "mission": intelligence.get("mission"),
            "timeline_next": intelligence.get("timeline_next"),
            "recommendation": intelligence.get("recommendation"),
            "coach_mode": intelligence.get("coach_mode"),
        },
        "decision": decision,
        "widgets": widgets_detail,
        "recent_events": recent_events,
        "decision_history": decision_history,
        "demo": demo.get_state(),
    }
