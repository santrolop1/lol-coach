"""
MissionEngine — crea y actualiza misiones activas.

Una misión es un objetivo medible y temporal.
Ejemplo: "No morir antes del minuto 10", "Conseguir 80 CS en 10 minutos".

Las misiones vienen de:
  1. El perfil del campeón (learning roadmap → graduation_criteria)
  2. Misiones universales adaptadas al contexto
  3. Patrones de error detectados (deaths, low CS)

La engine activa una misión a la vez. La actualiza en cada tick.
"""

from __future__ import annotations
from .models import GameContext, GamePhase, CoachState, Mission, MissionState


class MissionEngine:
    """
    Gestiona la misión activa.

    Es stateful — mantiene la misión entre ticks y actualiza su progreso.
    """

    def __init__(self) -> None:
        self._mission: Mission | None = None

    @property
    def active_mission(self) -> Mission | None:
        return self._mission if (self._mission and self._mission.is_active) else None

    def tick(
        self,
        ctx: GameContext,
        state: CoachState,
        profile=None,
    ) -> Mission | None:
        """
        Actualiza o selecciona la misión activa.

        Returns:
            La misión activa actualizada, o None si no hay.
        """
        # Actualizar misión existente
        if self._mission and self._mission.is_active:
            self._update_mission(ctx)
            if self._mission.is_active:
                return self._mission
            # Misión completada o fallida — limpiar para seleccionar la siguiente
            self._mission = None

        # Seleccionar nueva misión
        self._mission = self._select_mission(ctx, state, profile)
        return self._mission

    def reset(self) -> None:
        self._mission = None

    # ── Actualización ─────────────────────────────────────────────────────────

    def _update_mission(self, ctx: GameContext) -> None:
        m = self._mission
        if m is None:
            return

        if m.id == "no_deaths_early":
            # Progreso: tiempo transcurrido (objetivo: sobrevivir hasta min 10)
            m.progress_current = min(ctx.game_time_minutes, m.progress_target)
            if ctx.game_time_minutes >= m.progress_target:
                m.state = MissionState.SUCCESS
            elif ctx.deaths_so_far > 0:
                m.state = MissionState.FAILED
                m.failure_message = f"Moriste {ctx.deaths_so_far} vez/veces antes del minuto {m.progress_target:.0f}."

        elif m.id == "cs_target":
            # Progreso: CS actual
            m.progress_current = float(ctx.cs)
            if ctx.cs >= m.progress_target:
                m.state = MissionState.SUCCESS
                m.success_message = f"¡Conseguiste {ctx.cs} CS! Misión completada."
            # Expirar si pasó el tiempo límite
            elif m.time_limit_minutes > 0 and ctx.game_time_minutes > m.time_limit_minutes:
                if ctx.cs < m.progress_target:
                    m.state = MissionState.FAILED
                    m.failure_message = f"Solo {ctx.cs} CS al minuto {m.time_limit_minutes:.0f}. Objetivo: {m.progress_target:.0f}."

        elif m.id == "deaths_limit":
            # Progreso: muertes acumuladas (queremos que se mantengan BAJO el target)
            m.progress_current = float(ctx.deaths_so_far)
            if ctx.deaths_so_far > m.progress_target:
                m.state = MissionState.FAILED
                m.failure_message = f"Superaste el límite de muertes ({ctx.deaths_so_far} > {m.progress_target:.0f})."
            elif m.time_limit_minutes > 0 and ctx.game_time_minutes >= m.time_limit_minutes:
                m.state = MissionState.SUCCESS
                m.success_message = f"¡Solo {ctx.deaths_so_far} muertes en {m.time_limit_minutes:.0f} minutos!"

        elif m.id == "reach_first_item":
            m.progress_current = float(ctx.player_gold)
            if ctx.has_first_item:
                m.state = MissionState.SUCCESS
                m.success_message = "¡Primer ítem completado!"

        elif m.id == "survive_to_spike":
            m.progress_current = min(ctx.game_time_minutes, m.progress_target)
            if ctx.is_power_spike_window:
                m.state = MissionState.SUCCESS
                m.success_message = "¡Alcanzaste tu power spike!"

    # ── Selección ─────────────────────────────────────────────────────────────

    def _select_mission(
        self,
        ctx: GameContext,
        state: CoachState,
        profile,
    ) -> Mission | None:
        """Elige la misión más apropiada para el contexto actual."""
        t = ctx.game_time_minutes

        # Partida recién empezada → no morir en early
        if t < 2.0 and ctx.deaths_so_far == 0:
            return Mission(
                id="no_deaths_early",
                title="No morir antes del minuto 10",
                description="Sobrevive la fase de carril sin morir. Construye tu ventaja de forma segura.",
                progress_current=t,
                progress_target=10.0,
                progress_unit="minutos",
                time_limit_minutes=10.0,
            )

        # Lane phase sin primer ítem → llegar al primer ítem
        if ctx.phase == GamePhase.LANE_PHASE and not ctx.has_first_item:
            return self._cs_or_item_mission(ctx, profile)

        # Deaths altas → reducir muertes en las próximas partidas
        if ctx.deaths_so_far >= 3 and t < 20:
            return Mission(
                id="deaths_limit",
                title=f"Máximo {ctx.deaths_so_far + 1} muertes esta partida",
                description="Estás muriendo mucho. Juega más conservador y prioriza la supervivencia.",
                progress_current=float(ctx.deaths_so_far),
                progress_target=float(ctx.deaths_so_far + 1),
                progress_unit="muertes",
                time_limit_minutes=40.0,
            )

        # Alcanzar power spike si el campeón es late scaler
        if profile and not ctx.is_power_spike_window and not ctx.has_first_item:
            scaling = getattr(profile, "scaling", "")
            if scaling == "late" and t < 14:
                return Mission(
                    id="survive_to_spike",
                    title="Sobrevivir hasta el Power Spike",
                    description="Escala con seguridad. Tu primer ítem o nivel 6 cambia el juego.",
                    progress_current=t,
                    progress_target=14.0,
                    progress_unit="minutos",
                    time_limit_minutes=20.0,
                )

        return None

    def _cs_or_item_mission(self, ctx: GameContext, profile) -> Mission:
        """Misión de CS/oro para llegar al primer ítem."""
        # CS target según el minuto
        t = ctx.game_time_minutes
        if t < 5:
            target_cs = 30.0
        elif t < 10:
            target_cs = 70.0
        else:
            target_cs = 100.0

        time_limit = max(t + 3.0, 10.0)  # al menos 3 minutos para conseguirlo

        return Mission(
            id="cs_target",
            title=f"Conseguir {int(target_cs)} CS",
            description=(
                f"Tienes {ctx.cs} CS. Objetivo: {int(target_cs)} CS "
                f"para el minuto {time_limit:.0f}. Cada minion acerca tu primer ítem."
            ),
            progress_current=float(ctx.cs),
            progress_target=target_cs,
            progress_unit="CS",
            time_limit_minutes=time_limit,
        )
