"""
TimelineEngine — genera la línea temporal de la partida.

La timeline combina:
  - Eventos universales (recall óptimo, objetivos del mapa)
  - Eventos del campeón (power spikes del perfil)
  - Técnicas de oleada del campeón

El jugador siempre sabe qué viene a continuación.
"""

from __future__ import annotations
from .models import GameContext, TimelineEvent


# Eventos universales que ocurren en toda partida de League
_UNIVERSAL_EVENTS: list[tuple[float, str, str, str, str]] = [
    # (tiempo_min, id, título, descripción, tipo)
    (0.0,  "game_start",      "Inicio",             "Avanza al carril. No invadas sin visión.", "macro"),
    (1.5,  "first_recall",    "Primera ventana",     "Si tienes >800g y la wave está empujada, considera recall.", "recall"),
    (3.5,  "ward_river",      "Ward el río",         "Coloca un ward en el río antes del min 4 para evitar gankeos.", "macro"),
    (5.0,  "dragon_spawn",    "Primer Dragón",       "El dragón aparece. Empuja y prepárate para rotar si tu equipo lo necesita.", "objective"),
    (6.0,  "second_recall",   "Segunda ventana",     "Segunda oportunidad de recall óptimo. Construye hacia tu primer ítem.", "recall"),
    (8.0,  "herald_spawn",    "Heraldo de la Grieta","El Heraldo aparece. Presiona o rota según tu win condition.", "objective"),
    (10.0, "mid_check",       "Control de partida",  "Evalúa el estado: ¿estás cumpliendo tu objetivo? ¿Tienes primer ítem?", "macro"),
    (14.0, "phase_transition","Transición al mid",   "La fase de carril termina. Adapta tu macro al objetivo del equipo.", "macro"),
    (20.0, "baron_spawn",     "Barón Nashor",        "El Barón aparece. Prepárate para peleas decisivas.", "objective"),
    (25.0, "late_game_start", "Late Game",           "La partida entra en fase decisiva. Cada mujer puede costar la partida.", "macro"),
]


class TimelineEngine:
    """
    Genera la línea temporal para el contexto actual.

    Stateless — produce una nueva timeline en cada llamada.
    """

    def compute(
        self,
        ctx: GameContext,
        profile=None,
    ) -> list[TimelineEvent]:
        """
        Genera la timeline completa con eventos pasados marcados
        y el siguiente evento destacado.

        Args:
            ctx: contexto de partida actual
            profile: ChampionProfile | None

        Returns:
            Lista de TimelineEvent ordenada por tiempo
        """
        events: list[tuple[float, str, str, str, str]] = list(_UNIVERSAL_EVENTS)

        # Añadir eventos del perfil del campeón (power spikes)
        if profile:
            events.extend(self._champion_events(profile))

        # Ordenar por tiempo
        events.sort(key=lambda e: e[0])

        t = ctx.game_time_minutes
        result: list[TimelineEvent] = []
        found_next = False

        for time_min, eid, title, desc, etype in events:
            completed = time_min < t
            is_next = not found_next and not completed
            if is_next:
                found_next = True
            result.append(TimelineEvent(
                id=eid,
                time_minutes=time_min,
                title=title,
                description=desc,
                type=etype,
                completed=completed,
                is_next=is_next,
            ))

        return result

    def _champion_events(
        self,
        profile,
    ) -> list[tuple[float, str, str, str, str]]:
        """Extrae eventos de power spike del perfil."""
        events = []
        for spike in getattr(profile, "power_spikes", []):
            window = getattr(spike, "window_minutes", None)
            if not window or len(window) < 2:
                continue
            time_min = window[0]  # inicio de la ventana
            events.append((
                time_min,
                f"spike_{spike.id}",
                f"⚡ {getattr(spike, 'timing', 'Power Spike')}",
                getattr(spike, "action", "Aprovecha este momento de poder."),
                "power_spike",
            ))
        return events
