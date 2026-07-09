"""
Sistema de cobertura de campeones.

Mide qué tan completo está un Champion Profile y calcula un porcentaje.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class CoverageReport:
    """Reporte de completitud de un Champion Profile."""
    champion: str

    # Presencia de secciones
    has_profile: bool = False
    has_all_abilities: bool = False         # Q, W, E, R, P presentes
    has_combos: bool = False                # al menos 1 combo
    has_animation_cancels: bool = False    # al menos 1 cancel
    has_power_spikes: bool = False          # al menos 2 spikes
    has_learning_roadmap: bool = False
    has_build_config: bool = False
    has_rune_config: bool = False
    has_wave_config: bool = False
    has_macro_config: bool = False
    has_strengths: bool = False
    has_weaknesses: bool = False
    has_common_mistakes: bool = False
    has_tips: bool = False

    # Conteos
    abilities_count: int = 0
    combos_count: int = 0
    power_spikes_count: int = 0
    matchups_count: int = 0
    animation_cancels_count: int = 0

    # Errores de validación
    validation_errors: list[str] = field(default_factory=list)

    # Porcentaje general
    overall_pct: float = 0.0

    def __post_init__(self) -> None:
        self.overall_pct = self._compute_pct()

    def _compute_pct(self) -> float:
        """
        Calcula el porcentaje de completitud.
        Ponderación diseñada para que un perfil básico tenga ~60%
        y un perfil completo tenga 100%.
        """
        checks = [
            (self.has_profile, 20),
            (self.has_all_abilities, 15),
            (self.has_combos, 10),
            (self.has_power_spikes, 10),
            (self.has_build_config, 10),
            (self.has_rune_config, 8),
            (self.has_wave_config, 5),
            (self.has_macro_config, 5),
            (self.has_learning_roadmap, 5),
            (self.has_strengths, 3),
            (self.has_weaknesses, 3),
            (self.has_common_mistakes, 3),
            (self.has_tips, 3),
            (self.matchups_count >= 3, 3),        # bonus por matchups
            (self.animation_cancels_count >= 1, 2),
        ]
        total_weight = sum(w for _, w in checks)
        earned = sum(w for check, w in checks if check)
        return round((earned / total_weight) * 100, 1)


def build_coverage_report(champion_slug: str, registry, validator=None) -> CoverageReport:
    """
    Construye un CoverageReport para un campeón.

    Args:
        champion_slug: slug del campeón
        registry: ChampionRegistry
        validator: ChampionValidator opcional para errores de validación
    """
    profile = registry.get(champion_slug)
    if profile is None:
        return CoverageReport(champion=champion_slug, has_profile=False)

    matchups_count = len(registry.list_matchups(champion_slug))

    report = CoverageReport(
        champion=champion_slug,
        has_profile=True,
        has_all_abilities=(
            len(profile.abilities) >= 5 and
            all(k in profile.abilities for k in ("Q", "W", "E", "R", "P"))
        ),
        has_combos=len(profile.combos) > 0,
        has_animation_cancels=len(profile.animation_cancels) > 0,
        has_power_spikes=len(profile.power_spikes) >= 2,
        has_learning_roadmap=bool(profile.learning_roadmap_id),
        has_build_config=bool(profile.build_config.standard_build_id),
        has_rune_config=bool(profile.rune_config.standard_page_id),
        has_wave_config=bool(profile.wave_config.preferred_technique_ids),
        has_macro_config=bool(profile.macro_config.primary_pattern_ids),
        has_strengths=bool(profile.strengths),
        has_weaknesses=bool(profile.weaknesses),
        has_common_mistakes=bool(profile.common_mistakes),
        has_tips=bool(profile.tips),
        abilities_count=len(profile.abilities),
        combos_count=len(profile.combos),
        power_spikes_count=len(profile.power_spikes),
        matchups_count=matchups_count,
        animation_cancels_count=len(profile.animation_cancels),
        validation_errors=validator.validate_full(profile) if validator else [],
    )
    return report
