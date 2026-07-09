"""
LiveDataProvider — interfaz abstracta para proveedores de datos en tiempo real.

El resto del sistema (LiveCoach, widgets, engine) NUNCA conoce la implementación concreta.
Cambiar de Mock a Live Client = cambiar una línea en la instanciación.

Proveedores planificados:
  - MockLiveDataProvider        ← testing y desarrollo
  - RiotLiveClientProvider      ← Live Client Data API (127.0.0.1:2999) — en partida
  - LCUSessionProvider          ← League Client Update API — en champion select
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from ..models import PlayerStats, LiveSession


class LiveDataProvider(ABC):
    """
    Contrato que todo proveedor de datos debe cumplir.

    Todos los métodos son síncronos. Para async, los proveedores usan
    requests con timeout corto — el polling lo gestiona LiveCoach.
    """

    @abstractmethod
    def is_connected(self) -> bool:
        """True si el proveedor tiene conexión activa con la fuente de datos."""
        ...

    @abstractmethod
    def get_player_stats(self) -> PlayerStats | None:
        """
        Devuelve las estadísticas actuales del jugador activo.
        None si no hay partida activa o no hay conexión.
        """
        ...

    @abstractmethod
    def get_game_time(self) -> float:
        """Segundos transcurridos desde el inicio de la partida. 0 si no activa."""
        ...

    @abstractmethod
    def get_phase(self) -> str:
        """
        Fase actual: "idle" | "loading" | "in_game" | "post_game".
        Nunca lanza excepciones — retorna "idle" en caso de error.
        """
        ...

    def get_session_snapshot(self) -> LiveSession:
        """
        Snapshot completo de la sesión. Implementación por defecto
        que combina los métodos abstractos.
        """
        phase = self.get_phase()
        stats = self.get_player_stats()
        return LiveSession(
            active=phase == "in_game",
            champion=stats.champion if stats else "",
            role=stats.role if stats else "",
            game_time=self.get_game_time(),
            player_stats=stats or PlayerStats(),
            phase=phase,
            provider_connected=self.is_connected(),
        )
