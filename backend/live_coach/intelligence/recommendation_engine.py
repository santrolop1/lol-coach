"""
RecommendationEngine — genera recomendaciones cortas y accionables.

Reglas:
  - Máximo 3 recomendaciones simultáneas
  - Siempre concretas, nunca genéricas
  - Ordenadas por prioridad
  - Específicas del campeón y del momento

Fuentes:
  1. Errores detectados (common_mistakes del perfil contra el contexto)
  2. Recomendaciones de estado (tips del perfil relevantes al CoachState)
  3. Recomendaciones universales de contexto
"""

from __future__ import annotations
from .models import (
    GameContext, CoachState, GamePhase, GameSituation,
    Recommendation, CoachMode,
)

_MAX_RECOMMENDATIONS = 3


class RecommendationEngine:
    """
    Genera recomendaciones. Stateless — produce lista nueva en cada llamada.
    """

    def compute(
        self,
        ctx: GameContext,
        state: CoachState,
        profile=None,
    ) -> list[Recommendation]:
        """
        Genera las recomendaciones más relevantes para el contexto.

        Returns:
            Lista de Recommendation ordenada por prioridad (mayor primero).
        """
        recs: list[Recommendation] = []

        # Errores activos (comparar contexto con common_mistakes del perfil)
        recs.extend(self._mistake_recs(ctx, profile))

        # Tips del perfil relevantes al estado actual
        recs.extend(self._profile_tip_recs(ctx, state, profile))

        # Recomendaciones universales de contexto
        recs.extend(self._context_recs(ctx, state))

        # Dedup por id y ordenar por prioridad
        seen = set()
        unique: list[Recommendation] = []
        for r in sorted(recs, key=lambda r: r.priority, reverse=True):
            if r.id not in seen:
                seen.add(r.id)
                unique.append(r)

        return unique[:_MAX_RECOMMENDATIONS]

    # ── Errores detectados ────────────────────────────────────────────────────

    def _mistake_recs(self, ctx: GameContext, profile) -> list[Recommendation]:
        recs = []
        if profile is None:
            return recs

        mistakes = getattr(profile, "common_mistakes", [])
        abilities = getattr(profile, "abilities", {})

        for i, mistake in enumerate(mistakes[:3]):  # máximo 3 errores del perfil
            priority = self._mistake_priority(mistake, ctx)
            if priority > 0:
                recs.append(Recommendation(
                    id=f"mistake_{i}",
                    title=self._shorten(mistake, 60),
                    reason="Error frecuente para este campeón en esta situación.",
                    priority=priority,
                    type="warning",
                    champion_specific=True,
                ))
        return recs

    def _mistake_priority(self, mistake: str, ctx: GameContext) -> int:
        """Asigna prioridad a un error según si es relevante al contexto."""
        text = mistake.lower()
        priority = 0

        # Errores críticos siempre relevantes
        if "morir" in text or "death" in text or "muert" in text:
            priority = 60 if ctx.deaths_so_far > 2 else 30
        if "r" in text and "activ" in text and ctx.is_low_hp:
            priority = 80  # error de R muy relevante cuando HP es bajo
        if "cs" in text or "farm" in text:
            priority = 40 if ctx.cs_per_min < 5.5 else 10
        if "escape" in text or "e " in text:
            priority = 50 if ctx.phase == GamePhase.LANE_PHASE else 20
        if "ward" in text or "visión" in text or "vision" in text:
            priority = 35

        return priority

    # ── Tips del perfil ───────────────────────────────────────────────────────

    def _profile_tip_recs(
        self,
        ctx: GameContext,
        state: CoachState,
        profile,
    ) -> list[Recommendation]:
        if profile is None:
            return []

        tips = getattr(profile, "tips", [])
        recs = []
        for i, tip in enumerate(tips[:2]):
            priority = self._tip_priority(tip, ctx, state)
            if priority > 0:
                recs.append(Recommendation(
                    id=f"tip_{i}",
                    title=self._shorten(tip, 60),
                    reason="Consejo clave para este campeón.",
                    priority=priority,
                    type="tip",
                    champion_specific=True,
                ))
        return recs

    def _tip_priority(self, tip: str, ctx: GameContext, state: CoachState) -> int:
        text = tip.lower()
        if "split" in text and state in (CoachState.SPLIT_PUSH, CoachState.LATE_GAME):
            return 55
        if "r" in text and ctx.player_level >= 6:
            return 50
        if "e" in text and "escape" in text:
            return 45 if ctx.phase == GamePhase.LANE_PHASE else 20
        if "farm" in text or "cs" in text:
            return 35 if not ctx.has_first_item else 10
        return 20  # relevancia baja por defecto

    # ── Recomendaciones contextuales universales ──────────────────────────────

    def _context_recs(
        self,
        ctx: GameContext,
        state: CoachState,
    ) -> list[Recommendation]:
        recs = []

        if ctx.is_dead:
            recs.append(Recommendation(
                id="plan_next_recall",
                title="Planifica tu siguiente compra",
                reason="El tiempo de respawn es perfecto para decidir qué comprar.",
                priority=70,
                type="action",
            ))
            return recs

        if ctx.is_low_hp:
            recs.append(Recommendation(
                id="back_off_low_hp",
                title=f"Retrocede — solo tienes {int(ctx.hp_pct * 100)}% de vida",
                reason="Eres un objetivo fácil. Curar antes de comprometerte.",
                priority=90,
                type="warning",
            ))

        if ctx.is_recall_window and state == CoachState.RECALL_WINDOW:
            recs.append(Recommendation(
                id="recall_now",
                title=f"Recall ahora — tienes {ctx.player_gold}g",
                reason="El oro te permite completar un ítem importante.",
                priority=65,
                type="action",
            ))

        if ctx.cs_per_min < 5.0 and ctx.game_time_minutes > 3.0:
            recs.append(Recommendation(
                id="improve_cs",
                title=f"CS/min bajo: {ctx.cs_per_min:.1f} (objetivo: 7.0+)",
                reason="Perder CS es perder oro. Cada minion es crucial para tu primer ítem.",
                priority=50,
                type="warning",
            ))

        if ctx.phase == GamePhase.LANE_PHASE and ctx.game_time_minutes > 3.5 and not ctx.is_recall_window:
            recs.append(Recommendation(
                id="ward_reminder",
                title="¿Tienes ward en el río?",
                reason="Sin visión del río eres vulnerable a gankeos del jungler.",
                priority=30,
                type="reminder",
            ))

        if state == CoachState.OBJECTIVE_WINDOW:
            recs.append(Recommendation(
                id="objective_awareness",
                title="Objetivo importante en el mapa",
                reason="No te distraigas en el carril — decide si rotás o presionás.",
                priority=60,
                type="action",
            ))

        # Beginner mode: más básicos
        if ctx.coach_mode == CoachMode.BEGINNER:
            if ctx.player_level < 6:
                recs.append(Recommendation(
                    id="reach_level6",
                    title="Prioridad: llegar a nivel 6",
                    reason="El nivel 6 desbloquea tu habilidad definitiva.",
                    priority=25,
                    type="tip",
                ))

        return recs

    @staticmethod
    def _shorten(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len - 1].rstrip() + "…"
