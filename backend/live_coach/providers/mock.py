"""
MockLiveDataProvider — proveedor de datos para testing y desarrollo.

Permite simular partidas completas sin necesidad de tener League abierto.
Útil para:
  - Tests unitarios (estado predecible)
  - Desarrollo del overlay sin League abierto
  - Demos / capturas de pantalla
"""

from __future__ import annotations
from ..models import PlayerStats, LiveSession
from .base import LiveDataProvider


class MockLiveDataProvider(LiveDataProvider):
    """
    Proveedor mock totalmente configurable.

    Uso básico:
        provider = MockLiveDataProvider(champion="tryndamere", role="TOP")
        provider.set_level(6)
        provider.set_phase("in_game")

    Uso avanzado (scenario completo):
        provider = MockLiveDataProvider.scenario_early_game()
    """

    def __init__(
        self,
        champion: str = "tryndamere",
        role: str = "TOP",
        phase: str = "in_game",
        connected: bool = True,
    ) -> None:
        self._connected = connected
        self._phase = phase
        self._stats = PlayerStats(
            champion=champion,
            role=role,
            level=1,
            gold=500,
        )
        self._game_time: float = 0.0

    # ── LiveDataProvider interface ────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self._connected

    def get_player_stats(self) -> PlayerStats | None:
        if self._phase not in ("in_game", "loading"):
            return None
        return self._stats

    def get_game_time(self) -> float:
        return self._game_time

    def get_phase(self) -> str:
        return self._phase

    # ── Mutadores para tests ──────────────────────────────────────────────────

    def set_phase(self, phase: str) -> None:
        self._phase = phase

    def set_connected(self, connected: bool) -> None:
        self._connected = connected

    def set_level(self, level: int) -> None:
        self._stats.level = level

    def set_gold(self, gold: int) -> None:
        self._stats.gold = gold

    def set_kda(self, kills: int, deaths: int, assists: int) -> None:
        self._stats.kills = kills
        self._stats.deaths = deaths
        self._stats.assists = assists

    def set_cs(self, cs: int) -> None:
        self._stats.cs = cs

    def set_game_time(self, seconds: float) -> None:
        self._game_time = seconds

    def set_hp_pct(self, pct: float) -> None:
        self._stats.hp_pct = max(0.0, min(1.0, pct))

    def set_is_dead(self, is_dead: bool) -> None:
        self._stats.is_dead = is_dead

    def add_item(self, item_id: str) -> None:
        if item_id not in self._stats.items:
            self._stats.items.append(item_id)

    # ── Escenarios predefinidos ───────────────────────────────────────────────

    @classmethod
    def scenario_early_game(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(3)
        p.set_gold(800)
        p.set_game_time(180)  # 3 min
        p.set_cs(25)
        return p

    @classmethod
    def scenario_level_6(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(6)
        p.set_gold(1200)
        p.set_game_time(480)  # 8 min
        p.set_cs(55)
        return p

    @classmethod
    def scenario_first_item(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(9)
        p.set_gold(400)
        p.set_game_time(900)  # 15 min
        p.set_cs(110)
        p.add_item("trinity_force")
        return p

    @classmethod
    def scenario_disconnected(cls) -> "MockLiveDataProvider":
        p = cls(connected=False, phase="idle")
        return p

    @classmethod
    def scenario_post_game(cls) -> "MockLiveDataProvider":
        p = cls(phase="post_game")
        p.set_kda(8, 3, 5)
        p.set_cs(210)
        p.set_game_time(1800)
        return p

    @classmethod
    def scenario_level_2(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(2)
        p.set_gold(600)
        p.set_game_time(90)   # 1.5 min
        p.set_cs(8)
        return p

    @classmethod
    def scenario_mid_game(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(11)
        p.set_gold(800)
        p.set_game_time(900)  # 15 min
        p.set_cs(120)
        p.set_kda(2, 1, 1)
        p.add_item("trinity_force")
        return p

    @classmethod
    def scenario_split_push(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(13)
        p.set_gold(1100)
        p.set_game_time(1200)  # 20 min
        p.set_cs(180)
        p.set_kda(4, 1, 2)
        p.add_item("trinity_force")
        p.add_item("ravenous_hydra")
        return p

    @classmethod
    def scenario_teamfight(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(14)
        p.set_gold(600)
        p.set_game_time(1350)  # 22.5 min
        p.set_cs(195)
        p.set_kda(5, 2, 4)
        p.add_item("trinity_force")
        p.add_item("ravenous_hydra")
        return p

    @classmethod
    def scenario_baron(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(15)
        p.set_gold(1800)
        p.set_game_time(1230)  # 20.5 min — ventana de barón
        p.set_cs(210)
        p.set_kda(6, 2, 3)
        p.add_item("trinity_force")
        p.add_item("ravenous_hydra")
        return p

    @classmethod
    def scenario_late_game(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(17)
        p.set_gold(500)
        p.set_game_time(1620)  # 27 min
        p.set_cs(270)
        p.set_kda(8, 3, 5)
        p.add_item("trinity_force")
        p.add_item("ravenous_hydra")
        p.add_item("dead_mans_plate")
        return p

    @classmethod
    def scenario_low_hp(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(7)
        p.set_gold(900)
        p.set_game_time(600)  # 10 min
        p.set_cs(70)
        p.set_hp_pct(0.12)
        return p

    @classmethod
    def scenario_recall_window(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="in_game")
        p.set_level(8)
        p.set_gold(1350)
        p.set_game_time(660)  # 11 min
        p.set_cs(80)
        return p

    @classmethod
    def scenario_victory(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="post_game")
        p.set_kda(11, 2, 7)
        p.set_cs(280)
        p.set_game_time(1980)
        return p

    @classmethod
    def scenario_defeat(cls, champion: str = "tryndamere") -> "MockLiveDataProvider":
        p = cls(champion=champion, phase="post_game")
        p.set_kda(4, 9, 3)
        p.set_cs(140)
        p.set_game_time(2100)
        return p

    # Mapa de nombre → método de clase (para API)
    SCENARIOS: dict[str, str] = {
        "early_game":     "scenario_early_game",
        "level_2":        "scenario_level_2",
        "level_6":        "scenario_level_6",
        "first_item":     "scenario_first_item",
        "mid_game":       "scenario_mid_game",
        "split_push":     "scenario_split_push",
        "teamfight":      "scenario_teamfight",
        "baron":          "scenario_baron",
        "late_game":      "scenario_late_game",
        "low_hp":         "scenario_low_hp",
        "recall_window":  "scenario_recall_window",
        "victory":        "scenario_victory",
        "defeat":         "scenario_defeat",
        "post_game":      "scenario_post_game",
        "disconnected":   "scenario_disconnected",
    }

    @classmethod
    def from_scenario(cls, name: str, champion: str = "tryndamere") -> "MockLiveDataProvider":
        """Crea un provider a partir del nombre del escenario."""
        method_name = cls.SCENARIOS.get(name)
        if not method_name:
            raise ValueError(f"Escenario desconocido: '{name}'. Válidos: {list(cls.SCENARIOS)}")
        method = getattr(cls, method_name)
        try:
            return method(champion=champion)
        except TypeError:
            return method()
