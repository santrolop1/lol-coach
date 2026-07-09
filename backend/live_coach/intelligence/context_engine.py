"""
ContextEngine — interpreta el estado crudo del jugador en un contexto semántico.

Entrada: PlayerStats + ChampionProfile (opcional) + CoachMode
Salida:  GameContext (inmutable, consumido por todos los demás motores)

Ningún otro motor lee PlayerStats directamente.
"""

from __future__ import annotations
from ..models import PlayerStats, LiveSession
from .models import (
    GameContext, GamePhase, GameSituation, CoachMode,
)

# Umbrales de fase basados en tiempo de partida
_PHASE_EARLY_END     = 2.0    # min
_PHASE_LANE_END      = 14.0   # min
_PHASE_MID_END       = 25.0   # min

# HP bajo = necesita cuidado
_LOW_HP_THRESHOLD = 0.30

# Oro suficiente para recall (asume ítems de ~1200–1300g)
_RECALL_GOLD_MIN  = 1000

# CS mínimo esperado a cada minuto (para detectar farm malo)
_CS_THRESHOLD_PER_MIN = 5.5


class ContextEngine:
    """
    Interpreta el estado de la partida.

    Completamente stateless — produce un GameContext nuevo en cada llamada.
    """

    def compute(
        self,
        session: LiveSession,
        profile=None,
        mode: CoachMode = CoachMode.INTERMEDIATE,
    ) -> GameContext:
        """
        Calcula el GameContext actual.

        Args:
            session: snapshot de la partida del LiveDataProvider
            profile: ChampionProfile | None
            mode: nivel de coaching

        Returns:
            GameContext inmutable
        """
        stats = session.player_stats
        t = session.game_time / 60.0  # minutos

        phase        = self._determine_phase(t)
        situation    = self._determine_situation(stats, t, profile)
        is_spike     = self._is_power_spike_window(stats, profile)
        is_recall    = self._is_recall_window(stats, t)
        is_objective = self._is_objective_window(t)
        is_low_hp    = stats.hp_pct < _LOW_HP_THRESHOLD

        cs_pm = (stats.cs / t) if t > 0.5 else 0.0

        return GameContext(
            game_time_minutes=t,
            player_level=stats.level,
            player_gold=stats.gold,
            items_count=len(stats.items),
            has_first_item=len(stats.items) >= 1,
            has_two_items=len(stats.items) >= 2,
            is_dead=stats.is_dead,
            hp_pct=stats.hp_pct,
            deaths_so_far=stats.deaths,
            cs=stats.cs,
            cs_per_min=round(cs_pm, 2),
            phase=phase,
            situation=situation,
            is_power_spike_window=is_spike,
            is_recall_window=is_recall,
            is_objective_window=is_objective,
            is_low_hp=is_low_hp,
            coach_mode=mode,
        )

    # ── Privados ──────────────────────────────────────────────────────────────

    def _determine_phase(self, t: float) -> GamePhase:
        if t < _PHASE_EARLY_END:
            return GamePhase.EARLY
        if t < _PHASE_LANE_END:
            return GamePhase.LANE_PHASE
        if t < _PHASE_MID_END:
            return GamePhase.MID_GAME
        return GamePhase.LATE_GAME

    def _determine_situation(
        self,
        stats: PlayerStats,
        t: float,
        profile,
    ) -> GameSituation:
        if stats.is_dead:
            return GameSituation.DEAD

        if stats.hp_pct < _LOW_HP_THRESHOLD:
            return GameSituation.IN_DANGER

        # Power spike tiene prioridad sobre recall
        if self._is_power_spike_window(stats, profile):
            return GameSituation.POWER_SPIKE

        if self._is_recall_window(stats, t):
            return GameSituation.RECALL_WINDOW

        if self._is_objective_window(t):
            return GameSituation.OBJECTIVE_WINDOW

        # Split push: mid/late game con win condition de split
        if profile and t > _PHASE_LANE_END:
            mc = getattr(profile, "macro_config", None)
            if mc and "split_and_win" in getattr(mc, "win_condition_ids", []):
                return GameSituation.SPLIT_PUSH

        return GameSituation.FARMING

    def _is_power_spike_window(self, stats: PlayerStats, profile) -> bool:
        if profile is None:
            return False
        for spike in getattr(profile, "power_spikes", []):
            if self._spike_matches(spike, stats):
                return True
        return False

    @staticmethod
    def _spike_matches(spike, stats: PlayerStats) -> bool:
        """Verifica si un power spike acaba de activarse."""
        sid = getattr(spike, "id", "")
        window = getattr(spike, "window_minutes", None)

        if sid == "level_6" and stats.level >= 6:
            return True
        if sid == "first_item" and len(stats.items) >= 1:
            return True
        if sid == "two_items" and len(stats.items) >= 2:
            return True

        # Ventana de tiempo (e.g., entre min 8 y min 20 = primer ítem)
        if window and len(window) == 2:
            return False  # sin tiempo en vivo no podemos confirmar exactamente

        return False

    @staticmethod
    def _is_recall_window(stats: PlayerStats, t: float) -> bool:
        """
        Recall window: gold suficiente para ítem clave y no estamos
        en un momento crítico (< min 1.5).
        """
        if t < 1.5:
            return False
        return stats.gold >= _RECALL_GOLD_MIN

    @staticmethod
    def _is_objective_window(t: float) -> bool:
        """
        Ventanas de objetivos estándar:
          Primer Dragón: ~5:00
          Heraldo:       ~8:00–9:30
          Barón:         20:00+
        """
        objective_windows = [
            (4.5, 5.5),    # primer dragón
            (7.5, 9.5),    # heraldo
            (14.0, 15.0),  # segundo heraldo / alma dragón
            (20.0, 21.0),  # barón
            (25.0, 26.0),  # segundo barón
        ]
        return any(lo <= t <= hi for lo, hi in objective_windows)
