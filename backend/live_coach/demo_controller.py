"""
DemoController — gestiona el modo demostración del Live Coach.

En Demo Mode el LiveCoach usa MockLiveDataProvider en lugar del
Riot Live Client. Permite simular partidas sin tener League abierto.

El DemoController es el único punto de escritura sobre el provider del coach.
"""

from __future__ import annotations
import time
import logging
from .providers.mock import MockLiveDataProvider
from .models import GameEvent, EventType

logger = logging.getLogger("lol_coach.demo")

# Descripción de cada escenario para la UI
SCENARIO_DESCRIPTIONS: dict[str, dict] = {
    "early_game":    {"label": "Early Game",       "description": "Minuto 3, nivel 3. Fase de carril inicial.", "phase": "in_game"},
    "level_2":       {"label": "Nivel 2",           "description": "Minuto 1.5, nivel 2. Primeros intercambios.", "phase": "in_game"},
    "level_6":       {"label": "Nivel 6 (Spike)",   "description": "Minuto 8, nivel 6. R desbloqueada.", "phase": "in_game"},
    "first_item":    {"label": "Primer Ítem",       "description": "Minuto 15, primer ítem completado.", "phase": "in_game"},
    "mid_game":      {"label": "Mid Game",          "description": "Minuto 15, transición al mapa.", "phase": "in_game"},
    "split_push":    {"label": "Split Push",        "description": "Minuto 20, presión carril lateral con 2 ítems.", "phase": "in_game"},
    "teamfight":     {"label": "Teamfight",         "description": "Minuto 22, peleas de equipo.", "phase": "in_game"},
    "baron":         {"label": "Ventana Barón",     "description": "Minuto 20.5, barón disponible.", "phase": "in_game"},
    "late_game":     {"label": "Late Game",         "description": "Minuto 27, 3 ítems, fase decisiva.", "phase": "in_game"},
    "low_hp":        {"label": "Vida Baja",         "description": "Minuto 10, 12% de vida. ¿Escapas o peleas?", "phase": "in_game"},
    "recall_window": {"label": "Ventana Recall",    "description": "Minuto 11, 1350g. Momento óptimo de recall.", "phase": "in_game"},
    "victory":       {"label": "Victoria",          "description": "Post-partida — 11/2/7.", "phase": "post_game"},
    "defeat":        {"label": "Derrota",           "description": "Post-partida — 4/9/3.", "phase": "post_game"},
    "disconnected":  {"label": "Sin Conexión",      "description": "Proveedor desconectado.", "phase": "idle"},
}

# Orden de presentación en la UI
SCENARIO_ORDER = [
    "early_game", "level_2", "level_6", "first_item",
    "mid_game", "split_push", "teamfight", "baron",
    "late_game", "low_hp", "recall_window",
    "victory", "defeat", "disconnected",
]


class DemoController:
    """
    Controla el modo demostración.

    Mantiene una referencia al LiveCoach para poder cambiar su provider.
    """

    def __init__(self) -> None:
        self._active = False
        self._current_scenario: str = "early_game"
        self._champion: str = "tryndamere"
        self._coach_ref = None   # LiveCoach | None — inyectado en activate()

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def current_scenario(self) -> str:
        return self._current_scenario

    @property
    def champion(self) -> str:
        return self._champion

    def activate(self, coach, champion: str = "tryndamere") -> None:
        """Activa el Demo Mode cambiando el provider del LiveCoach."""
        self._coach_ref = coach
        self._champion = champion
        self._active = True
        self._apply_scenario(self._current_scenario)
        logger.info("Demo Mode activado — campeón: %s, escenario: %s", champion, self._current_scenario)

    def deactivate(self) -> None:
        """Desactiva el Demo Mode. El LiveCoach vuelve al Live Client."""
        if not self._active:
            return
        self._active = False
        self._coach_ref = None
        logger.info("Demo Mode desactivado")

    def set_scenario(self, scenario: str, champion: str | None = None) -> None:
        """Cambia el escenario activo."""
        if scenario not in SCENARIO_DESCRIPTIONS:
            raise ValueError(f"Escenario inválido: '{scenario}'")
        if champion:
            self._champion = champion
        self._current_scenario = scenario
        if self._active and self._coach_ref:
            self._apply_scenario(scenario)

    def fire_event(self, event_type: str, data: dict | None = None) -> bool:
        """
        Dispara un evento manualmente en el EventBus del LiveCoach.

        Args:
            event_type: nombre del EventType (ej: "LEVEL_UP", "DEATH")
            data: datos extra del evento

        Returns:
            True si el evento fue publicado.
        """
        if not self._active or not self._coach_ref:
            return False
        try:
            etype = EventType[event_type.upper()]
            event = GameEvent(type=etype, data=data or {})
            self._coach_ref.event_bus.publish(event)
            logger.debug("Demo evento disparado: %s %s", event_type, data)
            return True
        except KeyError:
            raise ValueError(f"EventType inválido: '{event_type}'. Válidos: {[e.value for e in EventType]}")

    def get_state(self) -> dict:
        return {
            "active": self._active,
            "current_scenario": self._current_scenario,
            "champion": self._champion,
            "scenario_info": SCENARIO_DESCRIPTIONS.get(self._current_scenario, {}),
        }

    def list_scenarios(self) -> list[dict]:
        return [
            {
                "id": sid,
                **SCENARIO_DESCRIPTIONS[sid],
                "current": sid == self._current_scenario,
            }
            for sid in SCENARIO_ORDER
            if sid in SCENARIO_DESCRIPTIONS
        ]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _apply_scenario(self, scenario: str) -> None:
        """Crea un MockProvider con el escenario y lo aplanta en el coach."""
        provider = MockLiveDataProvider.from_scenario(scenario, self._champion)
        coach = self._coach_ref
        # Reemplazar el provider interno del coach
        coach._provider = provider
        coach.reset()
        # Configurar el campeón en el coach
        if provider.get_phase() == "in_game":
            coach.set_champion(self._champion, "TOP")
        logger.debug("Demo: escenario '%s' aplicado", scenario)
