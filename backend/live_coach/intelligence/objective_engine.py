"""
ObjectiveEngine — decide el único objetivo que el jugador debe perseguir ahora.

Regla: devuelve exactamente UN CoachObjective.
Nunca devuelve None si hay contexto válido — siempre hay algo que hacer.
Nunca usa if champion == "X" — todo viene del ChampionProfile genérico.
"""

from __future__ import annotations
from .models import (
    CoachState, CoachObjective, GameContext, GamePhase, GameSituation, CoachMode,
)

# Objetivos genéricos de fallback (cuando no hay perfil de campeón)
_GENERIC_OBJECTIVES: dict[CoachState, tuple[str, str, str, str, int]] = {
    # (id, title, description, action_verb, priority)
    CoachState.LOADING: (
        "wait_loading", "Esperando inicio",
        "La partida está cargando. Prepárate mentalmente para el nivel 1.",
        "Esperar", 10,
    ),
    CoachState.LEVEL_1: (
        "farm_level1", "Establecer posición de nivel 1",
        "No arriesgues en nivel 1. Llega al nivel 2 sin morir.",
        "Farmear", 50,
    ),
    CoachState.LANE_PHASE: (
        "farm_lane", "Farmear y escalar",
        "Prioriza el CS. Evita peleas innecesarias. Construye tu ventaja silenciosamente.",
        "Farmear", 40,
    ),
    CoachState.RECALL_WINDOW: (
        "recall_now", "Recall y comprar",
        "Tienes oro suficiente. Empuja la oleada hasta la torre y haz recall.",
        "Recall", 70,
    ),
    CoachState.POWER_SPIKE: (
        "use_spike", "Aprovechar el Power Spike",
        "Acabas de alcanzar un punto de poder. Busca un intercambio favorable.",
        "Atacar", 80,
    ),
    CoachState.OBJECTIVE_WINDOW: (
        "contest_objective", "Participar en objetivo",
        "Hay un objetivo importante ahora. Agrúpate con tu equipo o presiona para forzar reacción.",
        "Rotación", 75,
    ),
    CoachState.SPLIT_PUSH: (
        "split_push", "Split Push",
        "Presiona el carril lateral, empuja hacia la torre y amenaza las estructuras.",
        "Split Push", 70,
    ),
    CoachState.TEAMFIGHT: (
        "teamfight", "Peleas de equipo",
        "Sigue a tu equipo. Prioriza los carries enemigos.",
        "Pelear", 70,
    ),
    CoachState.LATE_GAME: (
        "late_game", "Juego tardío",
        "No te pierdas. Muévete con tu equipo hacia el Barón o Nexo.",
        "Agruparse", 60,
    ),
    CoachState.DEAD: (
        "wait_respawn", "Esperando respawn",
        "Analiza qué salió mal. Planifica tu próxima rotación de compras.",
        "Esperar", 20,
    ),
    CoachState.POST_GAME: (
        "post_game", "Partida terminada",
        "Revisa las estadísticas y los errores para mejorar en la siguiente partida.",
        "Analizar", 10,
    ),
}


class ObjectiveEngine:
    """
    Motor de objetivos. Stateless — produce CoachObjective en cada llamada.
    """

    def compute(
        self,
        ctx: GameContext,
        state: CoachState,
        profile=None,
    ) -> CoachObjective:
        """
        Determina el objetivo principal.

        Args:
            ctx: contexto interpretado de la partida
            state: estado actual del coach
            profile: ChampionProfile | None

        Returns:
            CoachObjective — siempre retorna uno (nunca None)
        """
        # Prioridad máxima: situaciones críticas
        if ctx.is_dead:
            return self._death_objective(ctx)
        if ctx.is_low_hp and ctx.situation != GameSituation.DEAD:
            return self._low_hp_objective(ctx)

        # Usar perfil del campeón si disponible
        if profile is not None:
            obj = self._profile_objective(ctx, state, profile)
            if obj:
                return obj

        # Fallback genérico
        return self._generic_objective(state, ctx)

    # ── Situaciones críticas ──────────────────────────────────────────────────

    def _death_objective(self, ctx: GameContext) -> CoachObjective:
        return CoachObjective(
            id="dead_wait",
            title="Muerto — analiza el error",
            description=(
                "Mientras esperas el respawn, piensa qué causó la muerte. "
                "¿Te posicionaste mal? ¿Ignoraste la visión?"
            ),
            priority=90,
            action_verb="Analizar",
            context="dead",
            highlight=False,
        )

    def _low_hp_objective(self, ctx: GameContext) -> CoachObjective:
        hp_pct = int(ctx.hp_pct * 100)
        return CoachObjective(
            id="low_hp_back_off",
            title=f"Vida baja ({hp_pct}%) — aléjate",
            description=(
                f"Con solo {hp_pct}% de vida eres un objetivo fácil. "
                "Retrocede y cura antes de comprometerte."
            ),
            priority=95,
            action_verb="Retroceder",
            context="in_danger",
            highlight=True,
        )

    # ── Objetivos basados en perfil ───────────────────────────────────────────

    def _profile_objective(
        self,
        ctx: GameContext,
        state: CoachState,
        profile,
    ) -> CoachObjective | None:
        """
        Genera un objetivo leyendo del ChampionProfile.
        Nunca usa if champion == "X".
        """
        mc = getattr(profile, "macro_config", None)
        wc = getattr(profile, "wave_config", None)
        spikes = getattr(profile, "power_spikes", [])
        playstyle = getattr(profile, "playstyle", "scaling")
        scaling = getattr(profile, "scaling", "late")

        win_conditions = getattr(mc, "win_condition_ids", []) if mc else []
        primary_patterns = getattr(mc, "primary_pattern_ids", []) if mc else []
        wave_techniques = getattr(wc, "preferred_technique_ids", []) if wc else []

        # Power Spike: nivel 6 recién alcanzado
        if state == CoachState.POWER_SPIKE:
            spike = next((s for s in spikes if s.id == "level_6" and ctx.player_level == 6), None)
            if spike:
                return CoachObjective(
                    id="lvl6_spike",
                    title="Nivel 6 — Power Spike activo",
                    description=(
                        f"{getattr(spike, 'action', 'Usa tu nueva habilidad para buscar intercambios favorables.')} "
                        f"{getattr(spike, 'enemy_spike_context', '')}"
                    ).strip(),
                    priority=85,
                    action_verb="Atacar",
                    context="power_spike",
                    highlight=True,
                )
            spike = next((s for s in spikes if s.id == "first_item" and ctx.has_first_item), None)
            if spike:
                return CoachObjective(
                    id="first_item_spike",
                    title="Primer ítem — inicia tu plan",
                    description=getattr(spike, "action", "Empuja el carril y empieza a presionar."),
                    priority=80,
                    action_verb="Presionar",
                    context="power_spike",
                    highlight=True,
                )

        # Recall window: empujar y recall
        if state == CoachState.RECALL_WINDOW:
            recall_wave = getattr(wc, "recall_setup_technique_id", "crash") if wc else "crash"
            tech_name = recall_wave.replace("_", " ").title()
            return CoachObjective(
                id="recall_setup",
                title=f"Preparar recall — {tech_name} la oleada",
                description=(
                    f"Tienes {ctx.player_gold}g. "
                    f"Usa la técnica '{tech_name}' para crashear la oleada antes de recall."
                ),
                priority=70,
                action_verb="Recall",
                context="recall_window",
            )

        # Objetivo window: depende del win condition
        if state == CoachState.OBJECTIVE_WINDOW:
            if "split_and_win" in win_conditions:
                return CoachObjective(
                    id="pressure_to_force",
                    title="Presionar para forzar rotaciones",
                    description=(
                        "Hay un objetivo importante. No te unas directamente — "
                        "empuja el carril para forzar al equipo enemigo a dividirse."
                    ),
                    priority=75,
                    action_verb="Presionar",
                    context="objective_window",
                )
            return CoachObjective(
                id="join_objective",
                title="Participar en el objetivo",
                description="Tu equipo necesita números. Rota al objetivo.",
                priority=75,
                action_verb="Rotar",
                context="objective_window",
            )

        # Split Push: el win condition principal
        if state == CoachState.SPLIT_PUSH and "split_and_win" in win_conditions:
            return CoachObjective(
                id="execute_split",
                title="Split Push — presiona estructuras",
                description=(
                    "Empuja el carril lateral, amenaza la torre y "
                    "fuerza al enemigo a responder. Nunca te peles 2v1 sin tu R."
                ),
                priority=70,
                action_verb="Split Push",
                context="split_push",
            )

        # Lane Phase: elegir técnica de oleada
        if state == CoachState.LANE_PHASE:
            if wave_techniques:
                technique = wave_techniques[0]
                tips = {
                    "freeze": (
                        "Congela la oleada cerca de tu torre. "
                        "Denias CS al enemigo y reduces el riesgo de gankeo."
                    ),
                    "slow_push": (
                        "Empuja lento acumulando una oleada grande. "
                        "Úsala para recall o para preparar un gankeo."
                    ),
                    "crash": (
                        "Empuja la oleada hasta la torre enemiga. "
                        "Úsala antes del recall o antes de rotar."
                    ),
                    "fast_push": (
                        "Empuja rápido y libera presión de mapa. "
                        "Aprovecha para rotar o warding."
                    ),
                    "bounce": (
                        "Haz rebotar la oleada desde el lado enemigo. "
                        "Mantén la oleada en posición favorable."
                    ),
                }
                desc = tips.get(technique, technique.replace("_", " ").title())

                # Escalar: si el perfil es late-scaler, enfatizar evitar peleas
                prefix = ""
                if scaling == "late" and not ctx.has_first_item:
                    prefix = "Escalar es tu prioridad. "

                return CoachObjective(
                    id=f"wave_{technique}",
                    title=f"Gestión de oleada: {technique.replace('_', ' ').title()}",
                    description=prefix + desc,
                    priority=50,
                    action_verb=technique.replace("_", " ").title(),
                    context="lane_phase",
                )

            # Sin técnica específica → farmear
            if scaling == "late":
                return CoachObjective(
                    id="scale_farm",
                    title="Farmear y escalar",
                    description=(
                        "Este campeón escala a late game. "
                        "Prioriza el CS sobre los intercambios. "
                        "Cada minion cuenta para tu primer ítem."
                    ),
                    priority=45,
                    action_verb="Farmear",
                    context="lane_phase",
                )

        # Late game con split push
        if state == CoachState.LATE_GAME and "split_and_win" in win_conditions:
            return CoachObjective(
                id="late_split",
                title="Split Push tardío — ganar 1vX",
                description=(
                    "Con tu build completa, dominas el 1v1. "
                    "Presiona un carril y amenaza el Nexo mientras tu equipo distrae."
                ),
                priority=65,
                action_verb="Split Push",
                context="late_game",
            )

        return None  # fallback al objetivo genérico

    def _generic_objective(self, state: CoachState, ctx: GameContext) -> CoachObjective:
        fallback = _GENERIC_OBJECTIVES.get(state, _GENERIC_OBJECTIVES[CoachState.LANE_PHASE])
        obj_id, title, desc, verb, priority = fallback
        return CoachObjective(
            id=obj_id,
            title=title,
            description=desc,
            priority=priority,
            action_verb=verb,
            context=state.value,
        )
