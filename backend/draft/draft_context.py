"""
backend/draft/draft_context.py — Perfiles agregados de equipo y enemigos.

TeamProfile  : atributos sumados del equipo aliado.
EnemyProfile : atributos sumados del equipo enemigo + flags de amenaza.

IMPORTANTE: estos objetos solo contienen atributos numéricos.
No almacenan nombres de campeones. Solo atributos agregados.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TeamProfile:
    """
    Perfil del equipo aliado: suma de atributos de todos los campeones
    con perfil disponible.
    """
    count: int = 0

    # Suma de atributos de combate
    total_burst:            float = 0.0
    total_sustained:        float = 0.0
    total_cc:               float = 0.0
    total_engage:           float = 0.0
    total_peel:             float = 0.0
    total_mobility:         float = 0.0
    total_tankiness:        float = 0.0
    total_self_peel:        float = 0.0
    total_scaling:          float = 0.0
    total_anti_tank:        float = 0.0
    total_dive:             float = 0.0
    total_waveclear:        float = 0.0

    # Distribución de daño
    magic_count:    int = 0
    mixed_count:    int = 0
    physical_count: int = 0

    # ── Propiedades derivadas ─────────────────────────────────────────────────

    def avg(self, attr: str) -> float:
        """Promedio del atributo por miembro del equipo (evita división por 0)."""
        return getattr(self, f"total_{attr}") / max(1, self.count)

    @property
    def has_magic_damage(self) -> bool:
        """True si al menos un aliado hace daño mágico o mixto."""
        return self.magic_count + self.mixed_count > 0

    @property
    def needs_magic(self) -> bool:
        """True si ningún aliado aporta daño mágico."""
        return not self.has_magic_damage

    @property
    def is_engage_heavy(self) -> bool:
        return self.avg("engage") >= 2.5

    @property
    def lacks_engage(self) -> bool:
        return self.avg("engage") < 1.5

    @property
    def lacks_peel(self) -> bool:
        return self.avg("peel") < 1.0

    @property
    def lacks_scaling(self) -> bool:
        return self.avg("scaling") < 2.5

    @property
    def lacks_anti_tank(self) -> bool:
        return self.avg("anti_tank") < 1.5

    @property
    def lacks_waveclear(self) -> bool:
        return self.avg("waveclear") < 2.0


@dataclass
class EnemyProfile:
    """
    Perfil del equipo enemigo: suma de atributos + flags de amenaza detectados
    automáticamente en función de los atributos.
    """
    count: int = 0

    # Suma de atributos enemigos
    total_burst:     float = 0.0
    total_dive:      float = 0.0
    total_cc:        float = 0.0
    total_engage:    float = 0.0
    total_anti_tank: float = 0.0
    total_scaling:   float = 0.0
    total_mobility:  float = 0.0
    total_peel:      float = 0.0

    # ── Flags de amenaza (derivados de atributos, no de nombres) ─────────────

    @property
    def avg_burst(self) -> float:
        return self.total_burst / max(1, self.count)

    @property
    def avg_dive(self) -> float:
        return self.total_dive / max(1, self.count)

    @property
    def avg_cc(self) -> float:
        return self.total_cc / max(1, self.count)

    @property
    def avg_engage(self) -> float:
        return self.total_engage / max(1, self.count)

    @property
    def avg_anti_tank(self) -> float:
        return self.total_anti_tank / max(1, self.count)

    @property
    def avg_scaling(self) -> float:
        return self.total_scaling / max(1, self.count)

    @property
    def high_burst(self) -> bool:
        """Composición con alto daño instantáneo."""
        return self.avg_burst >= 2.5

    @property
    def high_dive(self) -> bool:
        """Composición capaz de alcanzar carries."""
        return self.avg_dive >= 2.0

    @property
    def heavy_cc(self) -> bool:
        """Composición con mucho crowd control."""
        return self.avg_cc >= 2.5

    @property
    def high_engage(self) -> bool:
        """Composición con alto potencial de inicio."""
        return self.avg_engage >= 2.5

    @property
    def has_anti_tank(self) -> bool:
        """Composición con daño efectivo contra tanques."""
        return self.avg_anti_tank >= 2.0

    @property
    def late_scaling(self) -> bool:
        """Composición que escala fuerte al late game."""
        return self.avg_scaling >= 3.5
